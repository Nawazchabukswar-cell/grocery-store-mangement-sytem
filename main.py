"""
main.py
Entry point for the Grocery Store Management System.
Initializes the SQLite database and launches the dashboard GUI.
"""

from database import initialize_database
from dashboard import DashboardWindow


def main():
    # Create the database file and tables if they don't already exist
    initialize_database()

    # Launch the main dashboard window
    app = DashboardWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
