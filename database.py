"""
database.py
Handles SQLite database connection and table initialization for the
Grocery Store Management System.
"""

import sqlite3
import os

DB_NAME = "grocery_store.db"


def get_db_path():
    """Return the absolute path to the database file (same folder as this script)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)


def get_connection():
    """
    Create and return a new SQLite connection.
    Rows can be accessed like dictionaries (row['column_name']).
    A fresh connection is opened per call to keep the code simple and to
    avoid sharing a single connection across multiple Tkinter windows.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """
    Create all required tables if they do not already exist, and perform migrations
    for existing tables (e.g. adding payment_method to sales).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Products table: stores inventory details
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL CHECK (price >= 0),
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            expiry_date TEXT,
            supplier TEXT,
            image_url TEXT
        )
    """)

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            total_purchases REAL DEFAULT 0.0
        )
    """)

    # Suppliers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT
        )
    """)

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Cashier',
            name TEXT NOT NULL
        )
    """)

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Sales table: one row per completed bill/invoice
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL UNIQUE,
            sale_date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'Cash',
            discount REAL DEFAULT 0.0,
            tax REAL DEFAULT 0.0,
            customer_name TEXT DEFAULT 'Walk-in Customer'
        )
    """)

    # Schema migration: check if columns exist in sales table for existing databases
    cursor.execute("PRAGMA table_info(sales)")
    existing_sales_cols = [col[1] for col in cursor.fetchall()]
    if "payment_method" not in existing_sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    if "discount" not in existing_sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0.0")
    if "tax" not in existing_sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN tax REAL DEFAULT 0.0")
    if "customer_name" not in existing_sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer_name TEXT DEFAULT 'Walk-in Customer'")

    # Schema migration: check products columns
    cursor.execute("PRAGMA table_info(products)")
    existing_prod_cols = [col[1] for col in cursor.fetchall()]
    if "supplier" not in existing_prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN supplier TEXT")
    if "image_url" not in existing_prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN image_url TEXT")

    # Sale items table: individual line items belonging to a sale/invoice
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            item_total REAL NOT NULL,
            FOREIGN KEY (invoice_no) REFERENCES sales (invoice_no),
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL
        )
    """)

    # Populate seed data if empty
    _seed_initial_data(cursor)

    conn.commit()
    conn.close()


def _seed_initial_data(cursor):
    """Seed initial categories, products, customers, settings, and users if missing."""
    # Seed categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        categories = [
            ("Grains", "Rice, Wheat, Pulses & Grains"),
            ("Beverages", "Juices, Soft drinks, Tea, Coffee, Water"),
            ("Snacks", "Biscuits, Chips, Chocolates & Namkeen"),
            ("Dairy", "Milk, Cheese, Butter, Curd & Yogurt"),
            ("Pantry", "Spices, Oil, Sugar, Salt & Sauces"),
        ]
        cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories)

    # Seed products if only 1 or 0 products
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] <= 1:
        sample_products = [
            ("Rice (1kg)", "Grains", 60.0, 120, "2027-12-31", "Fresh Agro", "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=300"),
            ("Sunflower Oil (1L)", "Pantry", 150.0, 45, "2027-06-30", "SunPure Co", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=300"),
            ("Wheat Flour (1kg)", "Grains", 45.0, 80, "2027-10-15", "Golden Harvest", "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300"),
            ("Sugar (1kg)", "Pantry", 50.0, 100, "2028-01-01", "SweetLife Inc", "https://images.unsplash.com/photo-1581441363689-1f3c3c414635?w=300"),
            ("Fresh Milk (1L)", "Dairy", 30.0, 35, "2026-08-25", "DairyFresh", "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=300"),
            ("Green Tea (250g)", "Beverages", 120.0, 25, "2027-09-30", "TeaGardens", "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=300"),
            ("Butter (500g)", "Dairy", 240.0, 18, "2026-11-20", "DairyFresh", "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=300"),
            ("Potato Chips (100g)", "Snacks", 20.0, 60, "2026-12-10", "CrispySnacks", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=300")
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, price, quantity, expiry_date, supplier, image_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample_products
        )

    # Seed customers
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        customers = [
            ("Rahul Verma", "+91 98765 43210", "rahul@example.com", 1250.0),
            ("Priya Sharma", "+91 98123 45678", "priya@example.com", 3400.0),
            ("Amit Patel", "+91 97111 22233", "amit@example.com", 850.0)
        ]
        cursor.executemany("INSERT INTO customers (name, phone, email, total_purchases) VALUES (?, ?, ?, ?)", customers)

    # Seed suppliers
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        suppliers = [
            ("Fresh Agro Ltd", "Ramesh Kumar", "+91 99887 76655", "orders@freshagro.com"),
            ("DairyFresh Co", "Suresh Nair", "+91 98877 66554", "supply@dairyfresh.com"),
            ("SunPure Oils", "Anita Roy", "+91 97766 55443", "info@sunpure.com")
        ]
        cursor.executemany("INSERT INTO suppliers (name, contact_person, phone, email) VALUES (?, ?, ?, ?)", suppliers)

    # Seed users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("admin", "admin123", "Admin", "Store Owner"),
            ("cashier1", "cashier123", "Cashier", "Rahul Sharma")
        ]
        cursor.executemany("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)", users)

    # Seed settings
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        settings = [
            ("store_name", "GroceryHub"),
            ("store_address", "123 Main Street, Commerce Zone"),
            ("store_phone", "+91 98765 00000"),
            ("tax_rate", "5"),
            ("currency", "₹")
        ]
        cursor.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", settings)

    # Make sure existing sales have valid payment methods if NULL
    cursor.execute("UPDATE sales SET payment_method = 'Cash' WHERE payment_method IS NULL OR payment_method = ''")

