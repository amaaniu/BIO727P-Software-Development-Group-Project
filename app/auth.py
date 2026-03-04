"""Authentication blueprint routes for registration, login, and logout."""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from app.models import User
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

# Creates the route for the registration page and handles user registration.
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Renders the registration page and handles user registration."""

    if request.method == 'POST':
        # Read submitted credentials from the registration form.
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Checks if username is already in use
        existing_user = db.session.scalar(db.select(User).filter_by(username=username))
        if existing_user:
            flash("Username already exists", 'danger')
            return render_template('register.html', email=email)  # Pre-fill the email field to avoid making the user re-enter it
        
        # Checks if email is already registered
        existing_email = db.session.scalar(db.select(User).filter_by(email=email))
        if existing_email:
            flash("Email already exists", 'danger')
            return render_template('register.html', username=username)  # Pre-fill the username field to avoid making the user re-enter it
        
        # Checks if password and confirm password match. If not, the user is prompted to try again
        if password != confirm_password:
            flash("Passwords do not match", 'danger')
            return render_template('register.html', username=username, email=email)
           
        # Create and store the user with a hashed password.
        user = User(username=username, email=email, password_hash=generate_password_hash(password)) 

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already exists", 'danger')
            return render_template('register.html', username=username, email=email)

        login_user(user)  # Logs the user in immediately after successful registration
        return redirect(url_for("main.dashboard"))
        
    return render_template('register.html')

# Creates the route for the login page and handles user login.
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Renders the login page and handles user login."""
    
    # Prevent authenticated users from seeing the login form again.
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        # Handles the login form submission by retrieving an email or username and password from the form data
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password')
        email_identifier = identifier.lower()

        # The user is queried from the database based on the provided email or username.
        user = db.session.scalar(db.select(User).where(or_(User.email == email_identifier, User.username == identifier)))
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        
        # Show a helpful error if credentials are invalid.
        flash('Invalid email or password. Please try again.', 'danger')
        
    return render_template('login.html')


# Creates the route for the logout functionality.
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))
