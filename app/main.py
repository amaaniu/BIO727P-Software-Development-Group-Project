# This file defines the main blueprint for the Flask application, enabling navigation between the different pages of the app.
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

# Creates the route for the case study tutorial page
@main_bp.route('/casestudy_tutorial')
def casestudy_tutorial():
    """Renders the case study tutorial page."""

    return 'soon rendering template casestudy tutorial'

# Creates the route for the dashboard page, which is only accessible to authenticated users
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the dashboard page, after user is authenticated."""

    return render_template('dashboard.html')