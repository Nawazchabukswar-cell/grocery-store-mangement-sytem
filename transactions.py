"""
transactions.py
View and search past sales transactions, filter by payment method (Cash, Online/UPI, Card),
and inspect detailed invoice records.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from database import get_connection


# ---------------------------------------------------------------------------
# Data access layer
# ---------------------------------------------------------------------------

def get_all_sales(payment_filter="All"):
    """Return sales records, optionally filtered by payment method, ordered by id DESC."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if payment_filter and payment_filter != "All":
            cursor.execute(
                "SELECT * FROM sales WHERE payment_method=? ORDER BY id DESC",
                (payment_filter,)
            )
        else:
            cursor.execute("SELECT * FROM sales ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        conn.close()


def search_sales(keyword, payment_filter="All"):
    """Search sales by invoice number, date, or customer name (partial match)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        like_pattern = f"%{keyword}%"
        if payment_filter and payment_filter != "All":
            cursor.execute(
                "SELECT * FROM sales WHERE (invoice_no LIKE ? OR sale_date LIKE ? OR customer_name LIKE ?) "
                "AND payment_method=? ORDER BY id DESC",
                (like_pattern, like_pattern, like_pattern, payment_filter)
            )
        else:
            cursor.execute(
                "SELECT * FROM sales WHERE invoice_no LIKE ? OR sale_date LIKE ? OR customer_name LIKE ? "
                "ORDER BY id DESC",
                (like_pattern, like_pattern, like_pattern)
            )
        return cursor.fetchall()
    finally:
        conn.close()


def get_sale_by_invoice(invoice_no):
    """Return header details for a single sale by invoice number."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE invoice_no=?", (invoice_no,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_sale_items(invoice_no):
    """Return all line items belonging to a given invoice."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sale_items WHERE invoice_no=?", (invoice_no,))
        return cursor.fetchall()
    finally:
        conn.close()


def get_total_sales_count_and_revenue():
    """Return total count, total revenue, and breakdown by payment method."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS revenue FROM sales")
        row = cursor.fetchone()
        cnt, total_rev = row["cnt"], row["revenue"]

        # Payment method breakdown
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN payment_method = 'Cash' THEN total_amount ELSE 0 END), 0) AS cash_rev,
                COALESCE(SUM(CASE WHEN payment_method = 'Online / UPI' THEN total_amount ELSE 0 END), 0) AS online_rev,
                COALESCE(SUM(CASE WHEN payment_method = 'Card' THEN total_amount ELSE 0 END), 0) AS card_rev
            FROM sales
        """)
        breakdown = cursor.fetchone()

        return cnt, total_rev, {
            "Cash": breakdown["cash_rev"],
            "Online": breakdown["online_rev"],
            "Card": breakdown["card_rev"]
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GUI layer
# ---------------------------------------------------------------------------

class TransactionWindow(tk.Toplevel):
    """Window for browsing past transactions, filtering by payment method, and viewing details."""

    def __init__(self, master, on_close_callback=None):
        super().__init__(master)
        self.title("Transaction History & Payment Audit - GroceryHub")
        self.geometry("860x580")
        self.on_close_callback = on_close_callback

        self._build_search_bar()
        self._build_table()
        self._build_summary_bar()
        self.refresh_table()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_search_bar(self):
        frame = tk.LabelFrame(self, text="Search & Filter Transactions", padx=10, pady=8)
        frame.pack(fill="x", padx=10, pady=8)

        tk.Label(frame, text="Search (Invoice/Date/Customer):").pack(side="left")
        self.search_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=self.search_var, width=22)
        entry.pack(side="left", padx=5)
        entry.bind("<Return>", lambda e: self.handle_search())

        tk.Label(frame, text="Payment Method:").pack(side="left", padx=(10, 2))
        self.payment_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            frame, textvariable=self.payment_filter_var,
            values=["All", "Cash", "Online / UPI", "Card"], state="readonly", width=12
        )
        filter_combo.pack(side="left", padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.handle_search())

        tk.Button(frame, text="Search", command=self.handle_search).pack(side="left", padx=5)
        tk.Button(frame, text="Show All", command=self.refresh_table).pack(side="left", padx=5)
        tk.Button(
            frame, text="View Details", command=self.handle_view_details,
            bg="#3498db", fg="white", font=("Arial", 9, "bold")
        ).pack(side="right", padx=5)

    def _build_table(self):
        columns = ("id", "invoice_no", "sale_date", "customer_name", "total_amount", "payment_method")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        headings = {
            "id": "ID",
            "invoice_no": "Invoice No",
            "sale_date": "Date / Time",
            "customer_name": "Customer",
            "total_amount": "Total (₹)",
            "payment_method": "Payment Method"
        }
        widths = {"id": 50, "invoice_no": 190, "sale_date": 150, "customer_name": 140, "total_amount": 110, "payment_method": 130}

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<Double-1>", lambda e: self.handle_view_details())

    def _build_summary_bar(self):
        self.summary_frame = tk.Frame(self, bd=1, relief="solid", padx=10, pady=6)
        self.summary_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.summary_label = tk.Label(
            self.summary_frame, text="Total Revenue: ₹0.00 | Cash: ₹0.00 | Online/UPI: ₹0.00 | Card: ₹0.00",
            font=("Arial", 10, "bold"), fg="#2c3e50"
        )
        self.summary_label.pack(side="left")

    def refresh_table(self):
        self.search_var.set("")
        self.payment_filter_var.set("All")
        self._populate_rows(get_all_sales())
        self._update_summary()

    def handle_search(self):
        keyword = self.search_var.get().strip()
        p_filter = self.payment_filter_var.get()
        if not keyword and p_filter == "All":
            self.refresh_table()
            return
        self._populate_rows(search_sales(keyword, p_filter))

    def _populate_rows(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            p_method = row["payment_method"] if "payment_method" in row.keys() and row["payment_method"] else "Cash"
            c_name = row["customer_name"] if "customer_name" in row.keys() and row["customer_name"] else "Walk-in Customer"
            self.tree.insert("", "end", values=(
                row["id"], row["invoice_no"], row["sale_date"], c_name,
                f"{row['total_amount']:.2f}", p_method
            ))

    def _update_summary(self):
        cnt, total_rev, breakdown = get_total_sales_count_and_revenue()
        self.summary_label.config(
            text=f"Total Sales: {cnt} | Total Revenue: ₹{total_rev:.2f} | "
                 f"Cash: ₹{breakdown['Cash']:.2f} | Online/UPI: ₹{breakdown['Online']:.2f} | Card: ₹{breakdown['Card']:.2f}"
        )

    def handle_view_details(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a transaction row to view.")
            return
        values = self.tree.item(selected[0], "values")
        invoice_no = values[1]
        header = get_sale_by_invoice(invoice_no)
        items = get_sale_items(invoice_no)
        self._show_details_window(header, items)

    def _show_details_window(self, header, items):
        detail_win = tk.Toplevel(self)
        detail_win.title(f"Invoice Details - {header['invoice_no']}")
        detail_win.geometry("540x500")

        cust = header['customer_name'] if 'customer_name' in header.keys() and header['customer_name'] else 'Walk-in Customer'
        p_method = header['payment_method'] if 'payment_method' in header.keys() and header['payment_method'] else 'Cash'
        disc = header['discount'] if 'discount' in header.keys() and header['discount'] else 0.0
        tax = header['tax'] if 'tax' in header.keys() and header['tax'] else 0.0

        header_text = (
            f"Invoice No     : {header['invoice_no']}\n"
            f"Date / Time    : {header['sale_date']}\n"
            f"Customer Name  : {cust}\n"
            f"Payment Method : {p_method}\n"
            + "-" * 55
        )
        tk.Label(detail_win, text=header_text, justify="left", font=("Courier", 10)).pack(
            anchor="w", padx=15, pady=(10, 0)
        )

        columns = ("product_name", "quantity", "price", "item_total")
        tree = ttk.Treeview(detail_win, columns=columns, show="headings", height=8)
        for col, text in zip(columns, ["Product", "Qty", "Price (₹)", "Total (₹)"]):
            tree.heading(col, text=text)
            tree.column(col, width=110, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        for item in items:
            tree.insert("", "end", values=(
                item["product_name"], item["quantity"], f"{item['price']:.2f}", f"{item['item_total']:.2f}"
            ))

        subtotal = sum(i["item_total"] for i in items)
        footer_text = (
            f"Subtotal: ₹{subtotal:.2f} | Discount: ₹{disc:.2f} | Tax: ₹{tax:.2f}\n"
            f"Grand Total: ₹{header['total_amount']:.2f} ({p_method})"
        )
        tk.Label(detail_win, text=footer_text, justify="right", font=("Arial", 11, "bold")).pack(
            anchor="e", padx=15, pady=(0, 10)
        )
        tk.Button(detail_win, text="Close", command=detail_win.destroy).pack(pady=(0, 10))

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
