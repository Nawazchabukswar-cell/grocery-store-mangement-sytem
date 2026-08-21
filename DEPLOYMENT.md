# 🚀 GroceryHub Deployment Guide (Direct Deploy)

This document provides step-by-step instructions to deploy **GroceryHub** directly to production cloud hosts.

---

## 🟢 Option 1: Deploy on Render.com (Recommended - 1-Click Free Hosting)

1. Push your project to GitHub.
2. Log into [Render.com](https://render.com) and click **New +** -> **Blueprint**.
3. Connect your repository.
4. Render will automatically pick up `render.yaml` and configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
5. Click **Apply**. Your app will be live on an `https://...onrender.com` URL!

---

## 🟣 Option 2: Deploy on Railway.app

1. Go to [Railway.app](https://railway.app) and create a **New Project**.
2. Select **Deploy from GitHub repo**.
3. Railway automatically detects `Procfile` and `requirements.txt` and deploys your server.

---

## 🔷 Option 3: Deploy via Docker / Docker Compose

To test locally or deploy on any VPS / Cloud Run / DigitalOcean droplet:

```bash
# Build and run container locally
docker-compose up -d
```
Access the application at `http://localhost:5000`.

---

## 🐍 Option 4: Deploy on PythonAnywhere

1. Upload the files to PythonAnywhere.
2. In the **Web** tab, configure:
   - **WSGI Configuration File**:
     ```python
     import sys
     path = '/home/yourusername/grocery_store'
     if path not in sys.path:
         sys.path.append(path)

     from web_app import app as application
     ```
3. Click **Reload**.

---

## 🛠 Project Files Included for Deployment

- `requirements.txt`: Clean dependencies (`Flask`, `gunicorn`, `werkzeug`).
- `wsgi.py`: WSGI entry point.
- `Procfile`: Process command for Heroku/Render/Railway.
- `render.yaml`: Render blueprint.
- `Dockerfile` & `docker-compose.yml`: Container configuration.
- `.env.example`: Environment template.
