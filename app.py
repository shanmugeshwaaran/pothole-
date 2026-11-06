
import os
import time
import base64
import sqlite3
from pathlib import Path

# Load environment variables from .env.local (or .env) before anything else.
# python-dotenv is listed in requirements.txt.
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")
    load_dotenv()           # fallback to plain .env if present
except ImportError:
    pass  # dotenv not installed – rely on the shell environment

import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
from ultralytics import YOLO

# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "potholes.db"
MODEL_PATH = BASE_DIR / "best.pt"

app = Flask(__name__)

# Secret key is required for Flask sessions (admin login).
# Always set FLASK_SECRET_KEY in .env.local – never hardcode it.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "CHANGE_ME_IN_ENV_LOCAL")

# Limit uploaded images to 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# --------------------------------------------------
# LOAD YOLO MODEL
# --------------------------------------------------

print(f"Loading YOLO model from: {MODEL_PATH}")

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"\nAI model not found: {MODEL_PATH}\n"
        "Place your trained best.pt file in the same "
        "folder as app.py."
    )

model = YOLO(str(MODEL_PATH))
print("YOLO model loaded successfully!")

# --------------------------------------------------
# LIVE GPS TRACKER
# --------------------------------------------------

current_gps = {
    "lat": 13.0827,
    "lng": 80.2707
}


@app.route("/api/update_location", methods=["POST"])
def update_location():
    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("latitude", current_gps["lat"]))
        lng = float(data.get("longitude", current_gps["lng"]))

        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return jsonify({"error": "Invalid GPS coordinates"}), 400

        current_gps["lat"] = lat
        current_gps["lng"] = lng

        return jsonify({
            "status": "Location updated",
            "latitude": lat,
            "longitude": lng
        })

    except (TypeError, ValueError):
        return jsonify({"error": "Invalid GPS coordinates"}), 400


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS potholes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL,
                longitude REAL,
                status TEXT,
                image_url TEXT,
                fixed_image_url TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pothole_id INTEGER,
                coordinates TEXT,
                notes TEXT,
                timestamp TEXT
            )
        """)


init_db()


def save_pothole(latitude, longitude, status, image_url):
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO potholes
                (latitude, longitude, status, image_url, fixed_image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (latitude, longitude, status, image_url, ""))

        return cursor.lastrowid


def image_to_data_url(image):
    success, buffer = cv2.imencode(".jpg", image)

    if not success:
        raise ValueError("Could not encode image")

    encoded = base64.b64encode(buffer).decode("utf-8")
    return "data:image/jpeg;base64," + encoded


def decode_image_data(image_url):
    """Decode a base64 image supplied by the client."""
    if not isinstance(image_url, str):
        raise ValueError("Image must be a base64 data URL")

    if not image_url.startswith("data:image/"):
        raise ValueError("Expected an image data URL")

    try:
        header, encoded = image_url.split(",", 1)
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Invalid image encoding") from exc

    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Image exceeds 10 MB")

    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise ValueError("Could not read the image")

    return image


def detect_potholes(image, confidence=0.75):
    results = model.predict(
        source=image,
        conf=confidence,
        verbose=False
    )

    return results[0]


# --------------------------------------------------
# 1. REAL-TIME AI DASHCAM
# --------------------------------------------------

def generate_ai_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    last_save_time = 0
    cooldown_seconds = 4

    try:
        while True:
            success, frame = cap.read()

            if not success:
                break

            try:
                result = detect_potholes(frame, confidence=0.45)
                pothole_detected = len(result.boxes) > 0

                for box in result.boxes:
                    x1, y1, x2, y2 = map(
                        int, box.xyxy[0].tolist()
                    )
                    confidence = float(box.conf[0])

                    cv2.rectangle(
                        frame, (x1, y1), (x2, y2),
                        (0, 0, 255), 2
                    )

                    cv2.putText(
                        frame,
                        f"Pothole {confidence:.2f}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2
                    )

                current_time = time.time()

                if (
                    pothole_detected
                    and current_time - last_save_time >= cooldown_seconds
                ):
                    try:
                        image_url = image_to_data_url(frame)

                        save_pothole(
                            current_gps["lat"],
                            current_gps["lng"],
                            "DISCOVERED",
                            image_url
                        )

                        last_save_time = current_time
                        print("Pothole detected and saved.")

                    except Exception as exc:
                        print(f"Database save error: {exc}")

            except Exception as exc:
                print(f"AI detection error: {exc}")

            success, buffer = cv2.imencode(".jpg", frame)

            if not success:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

    finally:
        cap.release()


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_ai_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# --------------------------------------------------
# 2. WEB PAGE ROUTES
# --------------------------------------------------

@app.route("/")
@app.route("/customer")
def index():
    return render_template("customer/index.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html")


@app.route("/admin/map")
def admin_map():
    return render_template("admin/map.html")


@app.route("/admin/potholes")
def admin_potholes():
    return render_template("admin/potholes.html")


@app.route("/admin/dashcam")
def admin_dashcam():
    return render_template("admin/admin_dashcam.html")


@app.route("/admin/reports")
def admin_reports():
    return render_template("admin/reports.html")


# --------------------------------------------------
# 3. GET ALL POTHOLES
# --------------------------------------------------

@app.route("/api/potholes", methods=["GET"])
def get_potholes():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM potholes ORDER BY id DESC"
        ).fetchall()

    return jsonify([dict(row) for row in rows])


# --------------------------------------------------
# 4. DELETE A POTHOLE
# --------------------------------------------------

@app.route("/api/potholes/<int:pothole_id>", methods=["DELETE"])
def delete_pothole(pothole_id):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM potholes WHERE id = ?",
            (pothole_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Pothole not found"}), 404

    return jsonify({"message": "Deleted"}), 200


# --------------------------------------------------
# 5. AI GATEKEEPER - UPLOAD A POTHOLE
# --------------------------------------------------

@app.route("/api/potholes", methods=["POST"])
def add_pothole():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON request"}), 400

    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Valid latitude and longitude required"}), 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify({"error": "Invalid GPS coordinates"}), 400

    image_url = data.get("image_url", "")

    if image_url:
        try:
            image = decode_image_data(image_url)
            result = detect_potholes(image, confidence=0.75)

            if len(result.boxes) == 0:
                return jsonify({
                    "message": "Rejected",
                    "reason": (
                        "AI could not detect a pothole. "
                        "Please upload a clear photo of road damage."
                    )
                }), 400

        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("AI verification failed")
            return jsonify({
                "error": "AI verification failed"
            }), 500

    else:
        return jsonify({"error": "A pothole image is required"}), 400

    try:
        pothole_id = save_pothole(
            latitude, longitude, "DISCOVERED", image_url
        )

        return jsonify({
            "message": "Success",
            "id": pothole_id,
            "status": "DISCOVERED"
        }), 201

    except sqlite3.Error:
        app.logger.exception("Failed to save pothole")
        return jsonify({"error": "Database error"}), 500


# --------------------------------------------------
# 6. AI INSPECTOR - VERIFY A REPAIR
# --------------------------------------------------

@app.route("/api/potholes/<int:pothole_id>/status", methods=["PATCH"])
def update_status(pothole_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON request"}), 400

    new_status = data.get("status")
    fixed_image_url = data.get("fixed_image_url")

    allowed_statuses = {"DISCOVERED", "REVIEW", "FIXED"}

    if new_status not in allowed_statuses:
        return jsonify({"error": "Invalid status"}), 400

    if fixed_image_url:
        try:
            image = decode_image_data(fixed_image_url)
            result = detect_potholes(image, confidence=0.75)

            if len(result.boxes) == 0:
                new_status = "FIXED"
            else:
                new_status = "REVIEW"

        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Repair verification failed")
            return jsonify({
                "error": "AI repair verification failed"
            }), 500

    try:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM potholes WHERE id = ?",
                (pothole_id,)
            ).fetchone()

            if existing is None:
                return jsonify({"error": "Pothole not found"}), 404

            if fixed_image_url:
                conn.execute("""
                    UPDATE potholes
                    SET status = ?, fixed_image_url = ?
                    WHERE id = ?
                """, (new_status, fixed_image_url, pothole_id))
            else:
                conn.execute("""
                    UPDATE potholes SET status = ?
                    WHERE id = ?
                """, (new_status, pothole_id))

        return jsonify({
            "message": "Status Updated",
            "new_status": new_status
        }), 200

    except sqlite3.Error:
        app.logger.exception("Database status update failed")
        return jsonify({"error": "Database error"}), 500


# --------------------------------------------------
# 7. START FLASK SERVER
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )