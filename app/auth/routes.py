# This file defines the routes for the authentication blueprint of the Flask application. It includes routes for user login, registration, and logout, as well as any other functionality users must login to access. The routes will render the appropriate templates and handle form submissions for user authentication processes.
from flask import Blueprint, render_template, redirect, session, url_for, request, flash
auth_bp = Blueprint('auth', __name__)

# Creates the route for the login page
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Renders the login page and handles user login."""

    if request.method == 'POST':
        # Handles the login form submission by retrieving the email and password from the form data
        email = request.form.get('email')
        password = request.form.get('password')

        # Here you would typically validate the user's credentials against the database
        # If the credentials are valid, you would log the user in and redirect them to the dashboard
        # We will just use an example condition to demonstrate this
        if email == 'test@test.com' and password == 'password':
            # Redirect to the dashboard after successful login
            return redirect(url_for('main.dashboard'))
        else:
            # If the credentials are invalid, an error message appears and the user is prompted to try again
            flash('Invalid email or password. Please try again.', 'danger') #Uses Flask's flash function to display an error message to the user in bootstrap's alert format
    return render_template('login.html')


# Creates the route for the registration page
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Renders the registration page and handles user registration."""

    if request.method == 'POST':
        # Handles the registration form submission by retrieving the email, password, and confirm password from the form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if username or email already exists in the database
        if user_exists(username, email):
            flash('Username or email already exists. Please try again.', 'danger')
        elif password == confirm_password:
            # Redirect to the dashboard page after successful registration (the user is automatically logged in after registration)
            return redirect(url_for('main.dashboard'))
        else:
            # If the passwords do not match, an error message appears and the user is prompted to try again
            flash('Passwords do not match. Please try again.', 'danger')
    return render_template('register.html')

# Creates the route for the logout functionality
@auth_bp.route('/logout')
def logout():
    """Handles user logout."""
    
    session.clear()
    # After logging out, you would redirect them to the home page or login page
    return redirect(url_for('main.home'))