# This file defines the routes for the authentication blueprint of the Flask application. It includes routes for user login, registration, and logout, as well as any other functionality users must login to access. The routes will render the appropriate templates and handle form submissions for user authentication processes.
from flask import Blueprint, render_template, redirect, session, url_for, request, flash, flask_login
from flask_login import login_user, logout_user, login_required
#from . import db
#from .models import User
auth_bp = Blueprint('auth', __name__)

# Creates the route for the registration page
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Renders the registration page and handles user registration."""

    if request.method == 'POST':
        # Handles the registration form submission by retrieving the email, password, and confirmed password from the form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Checks if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", 'danger')
            return redirect(url_for("auth.register"))
        
        # Checks if email is already registered
        if User.query.filter_by(email=email).first():
            flash("Email already exists", 'danger')
            return redirect(url_for("auth.register"))
        
        # Checks if password and confirm password match. If not, the user is prompted to try again
        if password != confirm_password:
            flash("Passwords do not match", 'danger')
            return redirect(url_for("auth.register"))
           
        # A new user is created with the provided username and password, and the password is hashed for security. 
        # The user is then added to the database and committed. After successful registration, the user is automatically logged in and redirected to the dashboard page.
        user = User(username=username, email=email) 
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)  # Logs the user in immediately after successful registration
        return redirect(url_for("main.dashboard"))
        
    return render_template('register.html')

# Creates the route for the login page
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Renders the login page and handles user login."""

    if request.method == 'POST':
        # Handles the login form submission by retrieving the email and password from the form data
        email = request.form.get('email')
        password = request.form.get('password')

        # The application checks if the provided email exists in the database and if the password is correct. If the credentials are valid, the user is logged in and redirected to the dashboard page.
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        
        # If the credentials are invalid, an error message appears and the user is prompted to try again
        flash('Invalid email or password. Please try again.', 'danger') #Uses Flask's flash function to display an error message to the user in bootstrap's alert format
    
        # If the user is already authenticated, they are redirected to the dashboard page without needing to log in again. This prevents authenticated users from accessing the login page unnecessarily.
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        
    return render_template('login.html')

# Creates the route for the logout functionality
@auth_bp.route('/logout')
def logout():
    """Handles user logout."""
    
    session.clear() 
    # After logging out, you would redirect them to the home page or login page
    return redirect(url_for('main.home'))