from flask import Blueprint, render_template

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/')
def index():
    """Customer Homepage displaying the map (Map logic coming in later stages)."""
    return render_template('customer/index.html')