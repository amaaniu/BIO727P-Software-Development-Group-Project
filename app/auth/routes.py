# This file defines the routes for the authentication blueprint of the Flask application. It includes routes for user login, registration, and logout, as well as any other functionality users must login to access. The routes will render the appropriate templates and handle form submissions for user authentication processes.
from flask import Blueprint, render_template, redirect, url_for, request, flash
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

