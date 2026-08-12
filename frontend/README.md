# Datix Frontend (Vercel)

Static HTML/CSS/JS frontend for Datix. No build step required.

## Deploy to Vercel

1. In Vercel: **Add New → Project**, select this repo, set **Root Directory**
   to `frontend`, framework preset **Other**.
2. Edit `index.html` and set `window.API_BASE_URL` to your Render backend URL:
   ```html
   <script>
     window.API_BASE_URL = "https://datix-backend.onrender.com";
   </script>
   ```
3. Deploy.
4. On the Render backend, set `ALLOWED_ORIGINS` to this project's Vercel URL
   so the backend accepts cross-origin requests with cookies.

## Local development

Serve this folder with any static file server, e.g.:

```bash
cd frontend
python -m http.server 3000
```

Then set `window.API_BASE_URL = "http://127.0.0.1:5000"` in `index.html` and
run the backend locally (`python app.py` from the repo root, which defaults
to allowing `http://localhost:3000`).
