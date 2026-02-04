# This file defines the main blueprint for the Flask application, enabling navigation between the different pages of the app.
from flask import Flask, render_template,Blueprint
main = Blueprint('main', __name__)

# Creates the route for the home page
@main.route('/')
def home():
    """Renders the home page."""

    return render_template('index.html')

# Creates the route for the registration page
@main.route('/register', methods=['GET', 'POST'])
def register():
    """Renders the registration page."""

    return render_template('register.html')

# Creates the route for the login page
@main.route('/login', methods=['GET', 'POST'])
def login():
    """Renders the login page."""

    return render_template('login.html')

# Creates the route for the features page
@main.route('/features')
def features():
    """Renders the features page."""

    return 'soon rendering template features'

# Creates the route for the documentation page
@main.route('/documentation')
def documentation():
    """Renders the documentation page."""

    return 'soon rendering template documentation'

# Creates the route for the case study tutorial page
@main.route('/casestudy_tutorial')
def casestudy_tutorial():
    """Renders the case study tutorial page."""

    return 'soon rendering template casestudy tutorial'
