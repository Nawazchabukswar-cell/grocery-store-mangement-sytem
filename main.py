"""
main.py
Entry point for the Grocery Store Management System.
Initializes the SQLite database and launches the dashboard GUI or Web server.
"""

import os
import sys
from database import initialize_database


def main():
    # Create the database file and tables if they don't already exist
    initialize_database()

    # Try launching Tkinter GUI if display server is available, else fallback to web server
    try:
        from dashboard import DashboardWindow, HAS_TKINTER
        if HAS_TKINTER and (os.name == "nt" or os.environ.get("DISPLAY")):
            app = DashboardWindow()
            app.mainloop()
            return
    except Exception as e:
        print(f"GUI launch skipped ({e}). Fallback to Web Server.")

    # Headless fallback: Launch web application
    print("Server environment detected. Launching GroceryHub Web App...")
    from web_app import app
    port = int(os.environ.get("PORT", 5000))
    is_debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=is_debug)


if __name__ == "__main__":
    main()
