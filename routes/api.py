from flask import Blueprint, jsonify
from database import get_db

api_bp = Blueprint('api', __name__)

@api_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "success", "message": "API is responding."})

@api_bp.route('/potholes', methods=['GET'])
def get_potholes():
    """Returns all potholes as JSON for the frontend maps."""
    conn = get_db()
    potholes = conn.execute('SELECT * FROM potholes').fetchall()
    conn.close()
    
    # Convert database rows to a list of dictionaries
    return jsonify([dict(p) for p in potholes])