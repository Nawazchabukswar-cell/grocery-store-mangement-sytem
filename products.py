"""
products.py
Product inventory management: data access functions plus the Tkinter
GUI window used to add, update, delete, search and view products.
Stock management (adding stock, viewing current/low stock) also lives
here since stock is simply a field on each product.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from database import get_connection

LOW_STOCK_THRESHOLD = 10  # Products at or below this quantity are "low stock"


# ---------------------------------------------------------------------------
# Data access layer
# ---------------------------------------------------------------------------

def add_product(name, category, price, quantity, expiry_date, supplier=None, image_url=None):
    """Insert a new product. Returns the new product's id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, category, price, quantity, expiry_date, supplier, image_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, category, price, quantity, expiry_date or None, supplier or None, image_url or None)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_product(product_id, name, category, price, quantity, expiry_date, supplier=None, image_url=None):
    """Update an existing product's details."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET name=?, category=?, price=?, quantity=?, expiry_date=?, supplier=?, image_url=? "
            "WHERE id=?",
            (name, category, price, quantity, expiry_date or None, supplier or None, image_url or None, product_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_product(product_id):
    """Delete a product by id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
    finally:
        conn.close()


def get_all_products():
    """Return every product, ordered by id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY id")
        return cursor.fetchall()
    finally:
        conn.close()


def get_product_by_id(product_id):
    """Return a single product row, or None if not found."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def search_products(keyword):
    """Search products by name or category (case-insensitive, partial match)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        like_pattern = f"%{keyword}%"
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? OR category LIKE ? ORDER BY id",
            (like_pattern, like_pattern)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_low_stock_products(threshold=LOW_STOCK_THRESHOLD):
    """Return products whose quantity is at or below the given threshold."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE quantity <= ? ORDER BY quantity ASC",
            (threshold,)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def adjust_stock(product_id, quantity_delta):
    """
    Increase (positive delta) or decrease (negative delta) a product's stock.
    Raises ValueError if the product does not exist or the result would be negative.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM products WHERE id=?", (product_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError("Product not found.")
        new_quantity = row["quantity"] + quantity_delta
        if new_quantity < 0:
            raise ValueError("Resulting stock cannot be negative.")
        cursor.execute("UPDATE products SET quantity=? WHERE id=?", (new_quantity, product_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GUI layer
# ---------------------------------------------------------------------------

class ProductWindow(tk.Toplevel):
    """Window for managing product inventory and stock (add / update / delete / search)."""

    def __init__(self, master, on_close_callback=None):
        super().__init__(master)
        self.title("Product & Stock Management")
        self.geometry("820x560")
        self.on_close_callback = on_close_callback
        self.selected_product_id = None

        self._build_form()
        self._build_search_bar()
        self._build_table()
        self._build_stock_section()
        self.refresh_table()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- UI construction -----------------------------------------------
    def _build_form(self):
        form_frame = tk.LabelFrame(self, text="Product Details", padx=10, pady=10)
        form_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.name_var, width=25).grid(row=0, column=1, padx=5, pady=4)

        tk.Label(form_frame, text="Category:").grid(row=0, column=2, sticky="e", padx=5, pady=4)
        self.category_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.category_var, width=20).grid(row=0, column=3, padx=5, pady=4)

        tk.Label(form_frame, text="Price:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.price_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.price_var, width=25).grid(row=1, column=1, padx=5, pady=4)

        tk.Label(form_frame, text="Quantity:").grid(row=1, column=2, sticky="e", padx=5, pady=4)
        self.quantity_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.quantity_var, width=20).grid(row=1, column=3, padx=5, pady=4)

        tk.Label(form_frame, text="Expiry Date (YYYY-MM-DD, optional):").grid(
            row=2, column=0, columnspan=2, sticky="e", padx=5, pady=4
        )
        self.expiry_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.expiry_var, width=20).grid(row=2, column=2, padx=5, pady=4)

        button_frame = tk.Frame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=10)

        tk.Button(button_frame, text="Add Product", width=14, command=self.handle_add).pack(side="left", padx=5)
        tk.Button(button_frame, text="Update Selected", width=14, command=self.handle_update).pack(side="left", padx=5)
        tk.Button(button_frame, text="Delete Selected", width=14, command=self.handle_delete).pack(side="left", padx=5)
        tk.Button(button_frame, text="Clear Form", width=14, command=self.clear_form).pack(side="left", padx=5)

    def _build_search_bar(self):
        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", padx=10)

        tk.Label(search_frame, text="Search (name/category):").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda event: self.handle_search())

        tk.Button(search_frame, text="Search", command=self.handle_search).pack(side="left", padx=5)
        tk.Button(search_frame, text="Show All", command=self.refresh_table).pack(side="left", padx=5)
        tk.Button(search_frame, text="Low Stock Only", command=self.show_low_stock).pack(side="left", padx=5)

    def _build_table(self):
        columns = ("id", "name", "category", "price", "quantity", "expiry_date")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=11)
        headings = {
            "id": "ID", "name": "Name", "category": "Category",
            "price": "Price", "quantity": "Stock", "expiry_date": "Expiry Date"
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

    def _build_stock_section(self):
        stock_frame = tk.LabelFrame(self, text="Stock Management", padx=10, pady=8)
        stock_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(stock_frame, text="Add stock quantity to selected product:").pack(side="left")
        self.add_stock_var = tk.StringVar()
        tk.Entry(stock_frame, textvariable=self.add_stock_var, width=8).pack(side="left", padx=5)
        tk.Button(stock_frame, text="Add Stock", command=self.handle_add_stock).pack(side="left", padx=5)

    # -- Data helpers -----------------------------------------------
    def refresh_table(self):
        self.search_var.set("")
        self._populate_rows(get_all_products())

    def show_low_stock(self):
        self._populate_rows(get_low_stock_products())

    def _populate_rows(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", "end", values=(
                row["id"], row["name"], row["category"],
                f"{row['price']:.2f}", row["quantity"], row["expiry_date"] or ""
            ))

    def on_row_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        self.selected_product_id = int(values[0])
        self.name_var.set(values[1])
        self.category_var.set(values[2])
        self.price_var.set(values[3])
        self.quantity_var.set(values[4])
        self.expiry_var.set(values[5])

    def clear_form(self):
        self.selected_product_id = None
        self.name_var.set("")
        self.category_var.set("")
        self.price_var.set("")
        self.quantity_var.set("")
        self.expiry_var.set("")

    # -- Validation -----------------------------------------------
    def _validate_form(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip()
        price_text = self.price_var.get().strip()
        quantity_text = self.quantity_var.get().strip()
        expiry_date = self.expiry_var.get().strip()

        if not name:
            raise ValueError("Product name cannot be empty.")

        try:
            price = float(price_text)
        except ValueError:
            raise ValueError("Price must be a valid number.")
        if price <= 0:
            raise ValueError("Price must be a positive number.")

        try:
            quantity = int(quantity_text)
        except ValueError:
            raise ValueError("Quantity must be a valid whole number.")
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        return name, category, price, quantity, expiry_date

    # -- Button handlers -----------------------------------------------
    def handle_add(self):
        try:
            name, category, price, quantity, expiry_date = self._validate_form()
            add_product(name, category, price, quantity, expiry_date)
            messagebox.showinfo("Success", f"Product '{name}' added successfully.")
            self.clear_form()
            self.refresh_table()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not add product:\n{e}")

    def handle_update(self):
        if self.selected_product_id is None:
            messagebox.showwarning("No Selection", "Please select a product to update.")
            return
        try:
            name, category, price, quantity, expiry_date = self._validate_form()
            update_product(self.selected_product_id, name, category, price, quantity, expiry_date)
            messagebox.showinfo("Success", f"Product '{name}' updated successfully.")
            self.clear_form()
            self.refresh_table()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not update product:\n{e}")

    def handle_delete(self):
        if self.selected_product_id is None:
            messagebox.showwarning("No Selection", "Please select a product to delete.")
            return
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this product?")
        if not confirm:
            return
        try:
            delete_product(self.selected_product_id)
            messagebox.showinfo("Deleted", "Product deleted successfully.")
            self.clear_form()
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not delete product:\n{e}")

    def handle_search(self):
        keyword = self.search_var.get().strip()
        if not keyword:
            self.refresh_table()
            return
        self._populate_rows(search_products(keyword))

    def handle_add_stock(self):
        if self.selected_product_id is None:
            messagebox.showwarning("No Selection", "Please select a product first.")
            return
        text = self.add_stock_var.get().strip()
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError("Stock to add must be a positive whole number.")
            adjust_stock(self.selected_product_id, amount)
            messagebox.showinfo("Stock Updated", f"Added {amount} units to stock.")
            self.add_stock_var.set("")
            self.refresh_table()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not update stock:\n{e}")

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
