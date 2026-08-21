"""
web_app.py
Flask web server and JSON REST API for the Grocery Store Management System (GroceryHub).
Connects directly to the shared SQLite database (grocery_store.db).
"""

import csv
import io
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, Response

from database import get_connection, initialize_database
from billing import create_sale
from products import get_all_products, get_low_stock_products, add_product, update_product, delete_product, search_products
from transactions import get_all_sales, search_sales, get_sale_items, get_total_sales_count_and_revenue, get_sale_by_invoice

app = Flask(__name__)


# Ensure database and tables exist on server startup
initialize_database()


# ---------------------------------------------------------------------------
# Frontend Route
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API Endpoints: Dashboard & Stats
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def get_stats():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Total products and stock
        cursor.execute("SELECT COUNT(*) AS total_prods, COALESCE(SUM(quantity), 0) AS total_stock FROM products")
        prod_row = cursor.fetchone()
        total_prods = prod_row["total_prods"]
        total_stock = prod_row["total_stock"]

        # Low stock count
        cursor.execute("SELECT COUNT(*) FROM products WHERE quantity <= 10")
        low_stock_count = cursor.fetchone()[0]

        # Total sales count, total revenue, and breakdown
        cnt, total_rev, breakdown = get_total_sales_count_and_revenue()

        # Estimated profit (assuming 25% profit margin for visualization)
        total_profit = total_rev * 0.25

        # Sales overview chart (last 7 days sales aggregation)
        days = []
        sales_trend = []
        for i in range(6, -1, -1):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            days.append(date_str)
            cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM sales WHERE sale_date LIKE ?", (f"{date_str}%",))
            sales_trend.append(cursor.fetchone()[0])

        # Category sales donut breakdown
        cursor.execute("""
            SELECT p.category, COALESCE(SUM(si.item_total), 0) AS cat_total
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            GROUP BY p.category
        """)
        cat_rows = cursor.fetchall()
        cat_labels = [r["category"] or "General" for r in cat_rows]
        cat_data = [r["cat_total"] for r in cat_rows]

        # If no sales yet, provide category stock distribution
        if not cat_labels:
            cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
            stock_cats = cursor.fetchall()
            cat_labels = [r[0] or "General" for r in stock_cats]
            cat_data = [r[1] for r in stock_cats]

        return jsonify({
            "total_sales": total_rev,
            "total_profit": total_profit,
            "total_orders": cnt,
            "low_stock_items": low_stock_count,
            "total_products": total_prods,
            "total_stock": total_stock,
            "cash_sales": breakdown["Cash"],
            "online_sales": breakdown["Online"],
            "card_sales": breakdown["Card"],
            "chart_labels": days,
            "chart_data": sales_trend,
            "cat_labels": cat_labels,
            "cat_data": cat_data
        })
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# API Endpoints: Products
# ---------------------------------------------------------------------------
@app.route("/api/products", methods=["GET"])
def api_get_products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if q:
            query += " AND (name LIKE ? OR category LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%"])
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/products", methods=["POST"])
def api_add_product():
    data = request.json or {}
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    price = float(data.get("price", 0))
    quantity = int(data.get("quantity", 0))
    expiry_date = data.get("expiry_date", "").strip()
    supplier = data.get("supplier", "").strip()
    image_url = data.get("image_url", "").strip()

    if not name or price <= 0 or quantity < 0:
        return jsonify({"error": "Invalid product name, price, or quantity."}), 400

    new_id = add_product(name, category, price, quantity, expiry_date, supplier, image_url)
    return jsonify({"success": True, "id": new_id, "message": "Product added successfully."})


@app.route("/api/products/<int:prod_id>", methods=["PUT"])
def api_update_product(prod_id):
    data = request.json or {}
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    price = float(data.get("price", 0))
    quantity = int(data.get("quantity", 0))
    expiry_date = data.get("expiry_date", "").strip()
    supplier = data.get("supplier", "").strip()
    image_url = data.get("image_url", "").strip()

    if not name or price <= 0 or quantity < 0:
        return jsonify({"error": "Invalid product details."}), 400

    update_product(prod_id, name, category, price, quantity, expiry_date, supplier, image_url)
    return jsonify({"success": True, "message": "Product updated successfully."})


@app.route("/api/products/<int:prod_id>", methods=["DELETE"])
def api_delete_product(prod_id):
    delete_product(prod_id)
    return jsonify({"success": True, "message": "Product deleted successfully."})


# ---------------------------------------------------------------------------
# API Endpoints: Categories
# ---------------------------------------------------------------------------
@app.route("/api/categories", methods=["GET"])
def api_get_categories():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        rows = cursor.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/categories", methods=["POST"])
def api_add_category():
    data = request.json or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    if not name:
        return jsonify({"error": "Category name is required."}), 400

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, desc))
        conn.commit()
        return jsonify({"success": True, "id": cursor.lastrowid})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# API Endpoints: Sales & Billing
# ---------------------------------------------------------------------------
@app.route("/api/sales", methods=["GET"])
def api_get_sales():
    q = request.args.get("q", "").strip()
    payment_method = request.args.get("payment_method", "").strip()
    rows = search_sales(q, payment_method) if (q or payment_method) else get_all_sales(payment_method)
    return jsonify([dict(r) for r in rows])


@app.route("/api/sales/<invoice_no>", methods=["GET"])
def api_get_sale_detail(invoice_no):
    header = get_sale_by_invoice(invoice_no)
    if not header:
        return jsonify({"error": "Invoice not found."}), 404
    items = get_sale_items(invoice_no)
    return jsonify({
        "sale": dict(header),
        "items": [dict(i) for i in items]
    })


@app.route("/api/sales", methods=["POST"])
def api_create_sale():
    data = request.json or {}
    cart_items = data.get("cart_items", [])
    payment_method = data.get("payment_method", "Cash")
    discount = float(data.get("discount", 0.0))
    tax = float(data.get("tax", 0.0))
    customer_name = data.get("customer_name", "Walk-in Customer")

    try:
        sale_res = create_sale(
            cart_items,
            payment_method=payment_method,
            discount=discount,
            tax=tax,
            customer_name=customer_name
        )
        return jsonify({"success": True, "sale": sale_res})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


# ---------------------------------------------------------------------------
# API Endpoints: Customers, Suppliers, Settings & Reports
# ---------------------------------------------------------------------------
@app.route("/api/customers", methods=["GET"])
def api_get_customers():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers ORDER BY id DESC")
        return jsonify([dict(r) for r in cursor.fetchall()])
    finally:
        conn.close()


@app.route("/api/suppliers", methods=["GET"])
def api_get_suppliers():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers ORDER BY id DESC")
        return jsonify([dict(r) for r in cursor.fetchall()])
    finally:
        conn.close()


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if request.method == "POST":
            data = request.json or {}
            for k, v in data.items():
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
            conn.commit()
            return jsonify({"success": True, "message": "Settings updated."})

        cursor.execute("SELECT * FROM settings")
        rows = cursor.fetchall()
        settings_dict = {r["key"]: r["value"] for r in rows}
        return jsonify(settings_dict)
    finally:
        conn.close()


@app.route("/api/reports/export", methods=["GET"])
def export_sales_csv():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, invoice_no, sale_date, customer_name, payment_method, discount, tax, total_amount FROM sales ORDER BY id DESC")
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Invoice No", "Date", "Customer", "Payment Method", "Discount", "Tax", "Total Amount"])
        for r in rows:
            writer.writerow([r["id"], r["invoice_no"], r["sale_date"], r["customer_name"], r["payment_method"], r["discount"], r["tax"], r["total_amount"]])

        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=sales_report.csv"
        return response
    finally:
        conn.close()


if __name__ == "__main__":
    print("Starting GroceryHub Web Application Server at http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
