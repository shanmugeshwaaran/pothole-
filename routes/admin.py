import os
import time

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

from database import get_db

admin_bp = Blueprint('admin', __name__)

# Credentials are loaded from environment variables (set in .env.local).
# Never hardcode secrets here.
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/', methods=['GET'])
def admin_root():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials.')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    if 'admin_logged_in' not in session: return redirect(url_for('admin.login'))
    
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM potholes').fetchone()[0]
    discovered = conn.execute("SELECT COUNT(*) FROM potholes WHERE status='DISCOVERED'").fetchone()[0]
    reviewed = conn.execute("SELECT COUNT(*) FROM potholes WHERE status='REVIEWED'").fetchone()[0]
    fixed = conn.execute("SELECT COUNT(*) FROM potholes WHERE status='FIXED'").fetchone()[0]
    conn.close()
    
    return render_template('admin/dashboard.html', total=total, discovered=discovered, reviewed=reviewed, fixed=fixed)

@admin_bp.route('/potholes', methods=['GET', 'POST'])
def manage_potholes():
    if 'admin_logged_in' not in session: return redirect(url_for('admin.login'))
    
    conn = get_db()
    if request.method == 'POST':
        # Add new pothole manually
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        status = request.form.get('status')
        notes = request.form.get('notes')
        
        image_filename = ""
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{int(time.time())}_{file.filename}")
            file.save(os.path.join('static', 'pothole_images', filename))
            image_filename = filename
            
        conn.execute('''
            INSERT INTO potholes (latitude, longitude, status, notes, image, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (lat, lng, status, notes, image_filename, 100.0))
        conn.commit()
        return redirect(url_for('admin.manage_potholes'))
        
    potholes = conn.execute('SELECT * FROM potholes ORDER BY detected_at DESC').fetchall()
    conn.close()
    return render_template('admin/potholes.html', potholes=potholes)

@admin_bp.route('/potholes/delete/<int:id>', methods=['POST'])
def delete_pothole(id):
    if 'admin_logged_in' not in session: return redirect(url_for('admin.login'))
    conn = get_db()
    pothole = conn.execute('SELECT image FROM potholes WHERE id = ?', (id,)).fetchone()
    if pothole and pothole['image']:
        try:
            os.remove(os.path.join('static', 'pothole_images', pothole['image']))
        except OSError:
            pass # File doesn't exist
    
    conn.execute('DELETE FROM potholes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.manage_potholes'))

@admin_bp.route('/map')
def admin_map():
    if 'admin_logged_in' not in session: return redirect(url_for('admin.login'))
    return render_template('admin/map.html')