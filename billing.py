"""
billing.py
Customer billing workflow: cart management, payment method selection (Cash, Online/UPI, Card),
atomic invoice generation, and the Tkinter GUI window used to create bills.
"""

import os
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TKINTER = True
except (ImportError, RuntimeError):
    HAS_TKINTER = False
    tk = None
    ttk = None
    messagebox = None

from database import get_connection
from products import get_all_products, search_products



# ---------------------------------------------------------------------------
# Data access layer
# ---------------------------------------------------------------------------

def generate_invoice_number():
    """Generate a unique invoice number based on the current timestamp."""
    return "INV" + datetime.now().strftime("%Y%m%d%H%M%S%f")


def create_sale(cart_items, payment_method="Cash", discount=0.0, tax=0.0, customer_name="Walk-in Customer"):
    """
    Save a completed sale to the database as a single atomic transaction:
      - Insert a row into 'sales' (including payment_method, discount, tax, customer_name)
      - Insert one row per item into 'sale_items'
      - Reduce stock for every product sold

    cart_items: list of dicts with keys: product_id, product_name, price, quantity, item_total
    payment_method: "Cash", "Online / UPI", or "Card"
    """
    if not cart_items:
        raise ValueError("Cannot generate a bill for an empty cart.")

    subtotal = sum(item["item_total"] for item in cart_items)
    grand_total = max(0.0, subtotal - discount + tax)
    invoice_no = generate_invoice_number()
    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        # Re-check stock for every item inside the transaction so we never oversell
        for item in cart_items:
            cursor.execute("SELECT quantity, name FROM products WHERE id=?", (item["product_id"],))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Product '{item['product_name']}' no longer exists.")
            if row["quantity"] < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for '{row['name']}'. "
                    f"Available: {row['quantity']}, Requested: {item['quantity']}."
                )

        # Insert sale header with payment_method
        cursor.execute(
            "INSERT INTO sales (invoice_no, sale_date, total_amount, payment_method, discount, tax, customer_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (invoice_no, sale_date, grand_total, payment_method, discount, tax, customer_name)
        )

        # Insert each line item and reduce stock
        for item in cart_items:
            cursor.execute(
                "INSERT INTO sale_items "
                "(invoice_no, product_id, product_name, quantity, price, item_total) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (invoice_no, item["product_id"], item["product_name"],
                 item["quantity"], item["price"], item["item_total"])
            )
            cursor.execute(
                "UPDATE products SET quantity = quantity - ? WHERE id=?",
                (item["quantity"], item["product_id"])
            )

        conn.commit()
        return {
            "invoice_no": invoice_no,
            "sale_date": sale_date,
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "grand_total": grand_total,
            "payment_method": payment_method,
            "customer_name": customer_name
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GUI layer
# ---------------------------------------------------------------------------

class BillingWindow(tk.Toplevel if HAS_TKINTER else object):
    """Window used to build a shopping cart, choose payment method, and generate a bill."""

    def __init__(self, master, on_close_callback=None):
        super().__init__(master)
        self.title("Customer Billing (POS) - GroceryHub")
        self.geometry("940x720")
        self.on_close_callback = on_close_callback

        self.cart = []  # list of dicts
        self.available_products = {}

        self._build_search_section()
        self._build_cart_section()
        self._build_payment_and_total_section()

        self.refresh_product_list()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- UI construction -----------------------------------------------
    def _build_search_section(self):
        top_frame = tk.LabelFrame(self, text="Find & Add Product", padx=10, pady=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(top_frame, text="Search:").grid(row=0, column=0, sticky="e", padx=5)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=25)
        search_entry.grid(row=0, column=1, padx=5)
        search_entry.bind("<Return>", lambda e: self.refresh_product_list())
        tk.Button(top_frame, text="Search", command=self.refresh_product_list).grid(row=0, column=2, padx=5)
        tk.Button(top_frame, text="Show All", command=self.refresh_product_list_all).grid(row=0, column=3, padx=5)

        columns = ("id", "name", "category", "price", "stock")
        self.product_tree = ttk.Treeview(top_frame, columns=columns, show="headings", height=5)
        for col, text in zip(columns, ["ID", "Name", "Category", "Price (₹)", "In Stock"]):
            self.product_tree.heading(col, text=text)
            self.product_tree.column(col, width=120, anchor="center")
        self.product_tree.grid(row=1, column=0, columnspan=4, pady=6, sticky="nsew")

        tk.Label(top_frame, text="Quantity:").grid(row=2, column=0, sticky="e", padx=5)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(top_frame, textvariable=self.qty_var, width=10).grid(row=2, column=1, sticky="w", padx=5)
        tk.Button(top_frame, text="Add to Cart", command=self.handle_add_to_cart,
                  bg="#2ecc71", fg="white", font=("Arial", 9, "bold")).grid(row=2, column=2, padx=5)

    def _build_cart_section(self):
        cart_frame = tk.LabelFrame(self, text="Shopping Cart", padx=10, pady=10)
        cart_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("product_id", "name", "price", "quantity", "item_total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", height=6)
        for col, text in zip(columns, ["ID", "Name", "Price (₹)", "Qty", "Item Total (₹)"]):
            self.cart_tree.heading(col, text=text)
            self.cart_tree.column(col, width=120, anchor="center")
        self.cart_tree.pack(fill="both", expand=True)

        tk.Button(cart_frame, text="Remove Selected Item", command=self.handle_remove_from_cart).pack(
            anchor="e", pady=5
        )

    def _build_payment_and_total_section(self):
        bottom_frame = tk.LabelFrame(self, text="Payment & Checkout", padx=15, pady=10)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Row 0: Customer name & Payment Method
        tk.Label(bottom_frame, text="Customer Name:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.customer_name_var = tk.StringVar(value="Walk-in Customer")
        tk.Entry(bottom_frame, textvariable=self.customer_name_var, width=20).grid(row=0, column=1, sticky="w", padx=5, pady=3)

        tk.Label(bottom_frame, text="Payment Method:").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.payment_method_var = tk.StringVar(value="Cash")
        payment_combo = ttk.Combobox(
            bottom_frame, textvariable=self.payment_method_var,
            values=["Cash", "Online / UPI", "Card"], state="readonly", width=15
        )
        payment_combo.grid(row=0, column=3, sticky="w", padx=5, pady=3)
        payment_combo.bind("<<ComboboxSelected>>", self._on_payment_method_change)

        # Row 1: Payment Details (Tendered amount for Cash, Ref ID for Online/Card)
        self.pay_detail_label = tk.Label(bottom_frame, text="Cash Tendered (₹):")
        self.pay_detail_label.grid(row=1, column=0, sticky="e", padx=5, pady=3)

        self.pay_detail_var = tk.StringVar()
        self.pay_detail_var.trace_add("write", lambda *args: self._update_change_calculation())
        self.pay_detail_entry = tk.Entry(bottom_frame, textvariable=self.pay_detail_var, width=20)
        self.pay_detail_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        self.change_label = tk.Label(bottom_frame, text="Change: ₹0.00", font=("Arial", 10, "bold"), fg="#27ae60")
        self.change_label.grid(row=1, column=2, columnspan=2, sticky="w", padx=15, pady=3)

        # Row 2: Discount & Tax
        tk.Label(bottom_frame, text="Discount (₹):").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.discount_var = tk.StringVar(value="0")
        self.discount_var.trace_add("write", lambda *args: self._refresh_totals_display())
        tk.Entry(bottom_frame, textvariable=self.discount_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=3)

        tk.Label(bottom_frame, text="Tax (%):").grid(row=2, column=2, sticky="e", padx=5, pady=3)
        self.tax_rate_var = tk.StringVar(value="5")
        self.tax_rate_var.trace_add("write", lambda *args: self._refresh_totals_display())
        tk.Entry(bottom_frame, textvariable=self.tax_rate_var, width=15).grid(row=2, column=3, sticky="w", padx=5, pady=3)

        # Summary line & action buttons
        self.summary_label = tk.Label(
            bottom_frame, text="Subtotal: ₹0.00 | Tax: ₹0.00 | Grand Total: ₹0.00",
            font=("Arial", 11, "bold"), fg="#2c3e50"
        )
        self.summary_label.grid(row=3, column=0, columnspan=4, pady=10)

        btn_box = tk.Frame(bottom_frame)
        btn_box.grid(row=4, column=0, columnspan=4, pady=5)

        tk.Button(btn_box, text="Clear Cart", command=self.handle_clear_cart, width=14).pack(side="left", padx=10)
        tk.Button(
            btn_box, text="Generate Bill & Complete Sale", command=self.handle_generate_bill,
            bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=30
        ).pack(side="left", padx=10)

    # -- Event Handlers & Calculations ---------------------------------
    def _on_payment_method_change(self, event=None):
        method = self.payment_method_var.get()
        if method == "Cash":
            self.pay_detail_label.config(text="Cash Tendered (₹):")
            self.change_label.grid()
        elif method == "Online / UPI":
            self.pay_detail_label.config(text="UPI / Ref ID:")
            self.change_label.grid_remove()
        elif method == "Card":
            self.pay_detail_label.config(text="Card Auth / Last 4:")
            self.change_label.grid_remove()
        self._update_change_calculation()

    def _update_change_calculation(self):
        method = self.payment_method_var.get()
        if method != "Cash":
            return
        subtotal, tax_amt, discount_amt, grand_total = self._calculate_totals()
        try:
            tendered = float(self.pay_detail_var.get().strip())
            change = tendered - grand_total
            if change >= 0:
                self.change_label.config(text=f"Change to Return: ₹{change:.2f}", fg="#27ae60")
            else:
                self.change_label.config(text=f"Shortage: ₹{abs(change):.2f}", fg="#c0392b")
        except ValueError:
            self.change_label.config(text="Change: ₹0.00", fg="#7f8c8d")

    def _calculate_totals(self):
        subtotal = sum(item["item_total"] for item in self.cart)
        try:
            discount_amt = float(self.discount_var.get().strip() or 0)
        except ValueError:
            discount_amt = 0.0

        try:
            tax_rate = float(self.tax_rate_var.get().strip() or 0)
            tax_amt = (subtotal - discount_amt) * (tax_rate / 100.0)
            if tax_amt < 0:
                tax_amt = 0.0
        except ValueError:
            tax_amt = 0.0

        grand_total = max(0.0, subtotal - discount_amt + tax_amt)
        return subtotal, tax_amt, discount_amt, grand_total

    def _refresh_totals_display(self):
        subtotal, tax_amt, discount_amt, grand_total = self._calculate_totals()
        self.summary_label.config(
            text=f"Subtotal: ₹{subtotal:.2f} | Discount: ₹{discount_amt:.2f} | Tax: ₹{tax_amt:.2f} | Grand Total: ₹{grand_total:.2f}"
        )
        self._update_change_calculation()

    # -- Product search / listing -----------------------------------------------
    def refresh_product_list_all(self):
        self.search_var.set("")
        self.refresh_product_list()

    def refresh_product_list(self):
        keyword = self.search_var.get().strip()
        rows = search_products(keyword) if keyword else get_all_products()

        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        self.available_products = {}
        for row in rows:
            self.available_products[row["id"]] = row
            self.product_tree.insert("", "end", values=(
                row["id"], row["name"], row["category"], f"{row['price']:.2f}", row["quantity"]
            ))

    # -- Cart operations -----------------------------------------------
    def handle_add_to_cart(self):
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to add.")
            return

        values = self.product_tree.item(selected[0], "values")
        product_id = int(values[0])
        product = self.available_products.get(product_id)
        if product is None:
            messagebox.showerror("Error", "Selected product could not be found. Please refresh.")
            return

        qty_text = self.qty_var.get().strip()
        try:
            quantity = int(qty_text)
        except ValueError:
            messagebox.showerror("Validation Error", "Quantity must be a valid whole number.")
            return
        if quantity <= 0:
            messagebox.showerror("Validation Error", "Quantity must be positive.")
            return

        existing_qty_in_cart = sum(i["quantity"] for i in self.cart if i["product_id"] == product_id)
        total_requested = existing_qty_in_cart + quantity

        if total_requested > product["quantity"]:
            messagebox.showerror(
                "Insufficient Stock",
                f"Only {product['quantity']} unit(s) of '{product['name']}' are available "
                f"({existing_qty_in_cart} already in cart)."
            )
            return

        for cart_item in self.cart:
            if cart_item["product_id"] == product_id:
                cart_item["quantity"] += quantity
                cart_item["item_total"] = cart_item["quantity"] * cart_item["price"]
                break
        else:
            self.cart.append({
                "product_id": product_id,
                "product_name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "item_total": quantity * product["price"]
            })

        self.qty_var.set("1")
        self._refresh_cart_view()

    def handle_remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a cart item to remove.")
            return
        values = self.cart_tree.item(selected[0], "values")
        product_id = int(values[0])
        self.cart = [item for item in self.cart if item["product_id"] != product_id]
        self._refresh_cart_view()

    def handle_clear_cart(self):
        if not self.cart:
            return
        if messagebox.askyesno("Clear Cart", "Remove all items from the cart?"):
            self.cart = []
            self._refresh_cart_view()

    def _refresh_cart_view(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        for item in self.cart:
            self.cart_tree.insert("", "end", values=(
                item["product_id"], item["product_name"], f"{item['price']:.2f}",
                item["quantity"], f"{item['item_total']:.2f}"
            ))
        self._refresh_totals_display()

    # -- Bill generation & Payment -------------------------------------
    def handle_generate_bill(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add at least one product before generating a bill.")
            return

        subtotal, tax_amt, discount_amt, grand_total = self._calculate_totals()
        payment_method = self.payment_method_var.get()
        customer_name = self.customer_name_var.get().strip() or "Walk-in Customer"
        pay_detail = self.pay_detail_var.get().strip()

        # Validation for payment details
        if payment_method == "Cash":
            if not pay_detail:
                messagebox.showwarning("Missing Cash Input", "Please enter the Cash Tendered amount.")
                return
            try:
                tendered = float(pay_detail)
                if tendered < grand_total:
                    messagebox.showerror(
                        "Insufficient Payment",
                        f"Tendered amount (₹{tendered:.2f}) is less than grand total (₹{grand_total:.2f})."
                    )
                    return
            except ValueError:
                messagebox.showerror("Validation Error", "Cash Tendered must be a valid number.")
                return
        elif payment_method in ["Online / UPI", "Card"]:
            if not pay_detail:
                # Generate auto reference ID if left blank
                pay_detail = f"REF-{datetime.now().strftime('%H%M%S')}"

        try:
            sale_data = create_sale(
                self.cart,
                payment_method=payment_method,
                discount=discount_amt,
                tax=tax_amt,
                customer_name=customer_name
            )
            sale_data["pay_detail"] = pay_detail
            sale_data["items"] = list(self.cart)

            self._show_invoice(sale_data)

            # Reset cart and inputs after success
            self.cart = []
            self.pay_detail_var.set("")
            self.discount_var.set("0")
            self._refresh_cart_view()
            self.refresh_product_list()
        except ValueError as e:
            messagebox.showerror("Cannot Generate Bill", str(e))
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not save the sale:\n{e}")

    def _show_invoice(self, sale):
        """Display the generated invoice in a popup window with Print/Save option."""
        invoice_win = tk.Toplevel(self)
        invoice_win.title(f"Invoice Receipt - {sale['invoice_no']}")
        invoice_win.geometry("540x560")

        # Format receipt header
        header_text = (
            "====================================================\n"
            "                 GROCERYHUB STORE                   \n"
            "           123 Main Street, Commerce Zone           \n"
            "                 Tel: +91 98765 00000               \n"
            "====================================================\n"
            f" Invoice No  : {sale['invoice_no']}\n"
            f" Date/Time   : {sale['sale_date']}\n"
            f" Customer    : {sale['customer_name']}\n"
            f" Payment Method: {sale['payment_method']}\n"
        )
        if sale['payment_method'] == 'Cash' and sale.get('pay_detail'):
            tendered = float(sale['pay_detail'])
            change = tendered - sale['grand_total']
            header_text += f" Cash Tendered: ₹{tendered:.2f} | Change Returned: ₹{change:.2f}\n"
        elif sale.get('pay_detail'):
            header_text += f" Ref ID      : {sale['pay_detail']}\n"

        header_text += "----------------------------------------------------\n"

        tk.Label(invoice_win, text=header_text, justify="left", font=("Courier", 9)).pack(
            anchor="w", padx=15, pady=(10, 0)
        )

        columns = ("name", "quantity", "price", "item_total")
        tree = ttk.Treeview(invoice_win, columns=columns, show="headings", height=8)
        for col, text in zip(columns, ["Product", "Qty", "Price (₹)", "Total (₹)"]):
            tree.heading(col, text=text)
            tree.column(col, width=110, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=5)

        for item in sale["items"]:
            tree.insert("", "end", values=(
                item["product_name"], item["quantity"],
                f"{item['price']:.2f}", f"{item['item_total']:.2f}"
            ))

        footer_text = (
            f" Subtotal : ₹{sale['subtotal']:.2f}\n"
            f" Discount : ₹{sale['discount']:.2f}\n"
            f" Tax      : ₹{sale['tax']:.2f}\n"
            f" GRAND TOTAL: ₹{sale['grand_total']:.2f}\n"
            "----------------------------------------------------\n"
            "        Thank you for shopping with GroceryHub!      \n"
        )
        tk.Label(invoice_win, text=footer_text, justify="right", font=("Courier", 10, "bold")).pack(
            anchor="e", padx=15, pady=5
        )

        btn_frame = tk.Frame(invoice_win)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Save Receipt File", command=lambda: self._save_receipt_to_file(sale, invoice_win),
            bg="#3498db", fg="white", font=("Arial", 9, "bold")
        ).pack(side="left", padx=5)

        tk.Button(btn_frame, text="Close", command=invoice_win.destroy).pack(side="left", padx=5)

    def _save_receipt_to_file(self, sale, parent_win):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        invoices_dir = os.path.join(base_dir, "invoices")
        os.makedirs(invoices_dir, exist_ok=True)
        file_path = os.path.join(invoices_dir, f"{sale['invoice_no']}.txt")

        content = (
            "====================================================\n"
            "                 GROCERYHUB STORE                   \n"
            "           123 Main Street, Commerce Zone           \n"
            "                 Tel: +91 98765 00000               \n"
            "====================================================\n"
            f"Invoice No    : {sale['invoice_no']}\n"
            f"Date/Time     : {sale['sale_date']}\n"
            f"Customer      : {sale['customer_name']}\n"
            f"Payment Method: {sale['payment_method']}\n"
        )
        if sale.get('pay_detail'):
            content += f"Payment Detail: {sale['pay_detail']}\n"
        content += "----------------------------------------------------\n"
        content += f"{'Item':<25} {'Qty':<6} {'Price':<10} {'Total':<10}\n"
        content += "----------------------------------------------------\n"
        for item in sale["items"]:
            content += f"{item['product_name']:<25} {item['quantity']:<6} {item['price']:<10.2f} {item['item_total']:<10.2f}\n"
        content += "----------------------------------------------------\n"
        content += f"Subtotal    : ₹{sale['subtotal']:.2f}\n"
        content += f"Discount    : ₹{sale['discount']:.2f}\n"
        content += f"Tax         : ₹{sale['tax']:.2f}\n"
        content += f"GRAND TOTAL : ₹{sale['grand_total']:.2f}\n"
        content += "====================================================\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        messagebox.showinfo("Saved", f"Receipt saved to:\n{file_path}", parent=parent_win)

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
