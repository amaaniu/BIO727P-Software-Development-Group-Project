# This file defines the routes for the main blueprint of the Flask application. It includes routes for the home page, features page, documentation page, tutorial page, and dashboard page. The dashboard page is protected by a login_required decorator, meaning that only authenticated users can access it. The routes will render the appropriate templates for each page.
from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)

# Creates the route for the home page
@main_bp.route('/')
def home():
    """Renders the home page."""

    return render_template('index.html')

# Creates the route for the features page
@main_bp.route('/features')
def features():
    """Renders the features page."""

    return 'soon rendering template features'

# Creates the route for the documentation page
@main_bp.route('/documentation')
def documentation():
    """Renders the documentation page."""

    return 'soon rendering template documentation'

# Creates the route for the tutorial page
@main_bp.route('/tutorial')
def tutorial():
    """Renders the tutorial page."""

    return 'soon rendering template tutorial'

# Creates the route for the dashboard page, which is only accessible to authenticated users.
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the dashboard page, after user is authenticated."""

    return render_template('dashboard.html')
