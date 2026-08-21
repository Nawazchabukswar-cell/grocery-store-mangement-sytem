"""
dashboard.py
Main application dashboard: shows summary statistics, cash/online sales breakdown,
and provides quick navigation buttons to the modules of the Grocery Store Management System.
"""

import webbrowser
import tkinter as tk
from tkinter import font as tkfont, messagebox

from products import get_all_products, get_low_stock_products, ProductWindow
from billing import BillingWindow
from transactions import TransactionWindow, get_total_sales_count_and_revenue


class DashboardWindow(tk.Tk):
    """The main application window (root)."""

    def __init__(self):
        super().__init__()
        self.title("Grocery Store Management System - GroceryHub")
        self.geometry("640x540")
        self.resizable(False, False)

        self._build_header()
        self._build_stats_section()
        self._build_buttons_section()

        self.refresh_stats()

    # -- UI construction -----------------------------------------------
    def _build_header(self):
        title_font = tkfont.Font(family="Arial", size=18, weight="bold")
        tk.Label(self, text="Grocery Store Management System", font=title_font, fg="#2c3e50").pack(pady=(15, 5))
        tk.Label(self, text="GroceryHub POS & Inventory Control", font=("Arial", 10, "italic"), fg="#7f8c8d").pack(pady=(0, 10))

    def _build_stats_section(self):
        stats_frame = tk.LabelFrame(self, text="Dashboard Overview & Sales Breakdown", padx=15, pady=12)
        stats_frame.pack(fill="x", padx=20, pady=5)

        label_font = ("Arial", 10)
        bold_font = ("Arial", 10, "bold")

        self.total_products_label = tk.Label(stats_frame, text="Total Products: -", font=label_font, anchor="w")
        self.total_products_label.grid(row=0, column=0, sticky="w", pady=3, padx=5)

        self.total_stock_label = tk.Label(stats_frame, text="Total Stock Units: -", font=label_font, anchor="w")
        self.total_stock_label.grid(row=1, column=0, sticky="w", pady=3, padx=5)

        self.low_stock_label = tk.Label(stats_frame, text="Low-Stock Products: -", font=label_font, anchor="w", fg="#c0392b")
        self.low_stock_label.grid(row=2, column=0, sticky="w", pady=3, padx=5)

        self.total_sales_label = tk.Label(stats_frame, text="Total Orders: -", font=label_font, anchor="w")
        self.total_sales_label.grid(row=0, column=1, sticky="w", pady=3, padx=20)

        self.total_revenue_label = tk.Label(stats_frame, text="Total Revenue: -", font=bold_font, anchor="w", fg="#27ae60")
        self.total_revenue_label.grid(row=1, column=1, sticky="w", pady=3, padx=20)

        self.payment_breakdown_label = tk.Label(stats_frame, text="Cash: ₹0.00 | Online/UPI: ₹0.00 | Card: ₹0.00", font=label_font, anchor="w", fg="#2980b9")
        self.payment_breakdown_label.grid(row=2, column=1, sticky="w", pady=3, padx=20)

    def _build_buttons_section(self):
        button_frame = tk.Frame(self)
        button_frame.pack(pady=15)

        button_style = {"width": 24, "height": 2, "font": ("Arial", 10, "bold")}

        tk.Button(button_frame, text="Manage Products", command=self.open_products, bg="#34495e", fg="white",
                  **button_style).grid(row=0, column=0, padx=8, pady=6)
        tk.Button(button_frame, text="Manage Stock", command=self.open_products, bg="#7f8c8d", fg="white",
                  **button_style).grid(row=0, column=1, padx=8, pady=6)
        tk.Button(button_frame, text="Create Bill (POS)", command=self.open_billing, bg="#27ae60", fg="white",
                  **button_style).grid(row=1, column=0, padx=8, pady=6)
        tk.Button(button_frame, text="View Transactions", command=self.open_transactions, bg="#2980b9", fg="white",
                  **button_style).grid(row=1, column=1, padx=8, pady=6)

        tk.Button(button_frame, text="🌐 Launch Web App Dashboard (Browser)", command=self.open_web_app,
                  width=50, height=2, bg="#8e44ad", fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(button_frame, text="🔄 Refresh Dashboard Stats", command=self.refresh_stats,
                  width=50, font=("Arial", 9)).grid(row=3, column=0, columnspan=2, pady=(0, 0))

    # -- Stats -----------------------------------------------
    def refresh_stats(self):
        products = get_all_products()
        total_products = len(products)
        total_stock = sum(p["quantity"] for p in products)
        low_stock_count = len(get_low_stock_products())
        sales_count, revenue, breakdown = get_total_sales_count_and_revenue()

        self.total_products_label.config(text=f"Total Products: {total_products}")
        self.total_stock_label.config(text=f"Total Stock Units: {total_stock}")
        self.low_stock_label.config(text=f"Low-Stock Products: {low_stock_count}")
        self.total_sales_label.config(text=f"Total Sales (Bills): {sales_count}")
        self.total_revenue_label.config(text=f"Total Revenue: ₹{revenue:.2f}")
        self.payment_breakdown_label.config(
            text=f"Cash: ₹{breakdown['Cash']:.2f} | Online: ₹{breakdown['Online']:.2f} | Card: ₹{breakdown['Card']:.2f}"
        )

    # -- Navigation -----------------------------------------------
    def open_products(self):
        ProductWindow(self, on_close_callback=self.refresh_stats)

    def open_billing(self):
        BillingWindow(self, on_close_callback=self.refresh_stats)

    def open_transactions(self):
        TransactionWindow(self, on_close_callback=self.refresh_stats)

    def open_web_app(self):
        url = "http://127.0.0.1:5000"
        webbrowser.open(url)
        messagebox.showinfo("Web App Dashboard", f"Opening Web Dashboard in your browser at:\n{url}\n\nMake sure web_app.py is running!")
