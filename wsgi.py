"""
wsgi.py
WSGI entrypoint for production cloud deployment (Gunicorn / Render / Heroku / Railway / PythonAnywhere).
"""

from web_app import app

if __name__ == "__main__":
    app.run()
