# Pothole GO 🚧

An AI-powered pothole detection and reporting web app built with Flask, YOLOv8, OpenCV, and Leaflet.js.

---

## ⚡ Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/pothole-go.git
cd pothole-go
```

### 2. Set up a virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the template and fill in your values:
```bash
cp .env.local .env.local   # already exists – just edit it
```

| Variable | Description |
|---|---|
| `FLASK_SECRET_KEY` | Random hex string for Flask sessions |
| `ADMIN_USERNAME` | Admin panel login username |
| `ADMIN_PASSWORD` | Admin panel login password |
| `FLASK_ENV` | `development` or `production` |
| `NGROK_AUTHTOKEN` | Your ngrok auth token (optional) |

> **Never commit `.env.local` to Git.** It is already listed in `.gitignore`.

### 5. Add the YOLO model

Place your trained `best.pt` file in the project root (same folder as `app.py`).

> `best.pt` is excluded from Git via `.gitignore` because of its size. Distribute it separately (e.g. Google Drive, Hugging Face Hub, or GitHub Releases).

### 6. Run the app
```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🌐 Remote Access with ngrok (Optional)

1. [Download ngrok](https://ngrok.com/download) and authenticate:
   ```bash
   ngrok config add-authtoken <your-authtoken>
   ```
2. In a **second terminal**, while `python app.py` is running:
   ```bash
   ngrok http 5000
   ```
3. Share the generated `https://…ngrok-free.app` URL.

---

## 📁 Project Structure

```
Pothole_GO/
├── app.py               # Main Flask application
├── database.py          # SQLite helpers (get_db, init_db, …)
├── requirements.txt     # Python dependencies
├── .env.local           # 🔒 Local secrets (not committed)
├── .gitignore
├── best.pt              # 🔒 YOLO model weights (not committed)
├── routes/
│   ├── admin.py         # Admin blueprint
│   ├── api.py           # REST API blueprint
│   └── customer.py      # Customer-facing blueprint
├── static/
│   ├── css/
│   └── js/
└── templates/
    ├── admin/
    └── customer/
```

---

## 🔐 Security Notes

- Admin credentials are read from environment variables (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
- The Flask secret key is read from `FLASK_SECRET_KEY`.
- Database files (`*.db`) and model weights (`*.pt`) are gitignored.

