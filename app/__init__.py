# This file initialises the Flask application and registers all of the blueprints that form the web app.
from flask import Flask, flash, redirect, url_for, session, flask_login
from flask_login import LoginManager, login_user, logout_user, login_required
from .main import main_bp
from .auth import auth_bp


def create_app():
    """Creates and configures the Flask applicationfrom all of the registered blueprints."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-key' # In production, use an actual secret key for security purposes.
    
    app.register_blueprint(main_bp)  # Register the main blueprint with a URL prefix for main routes
    app.register_blueprint(auth_bp, url_prefix='/auth')  # Register the auth blueprint with a URL prefix for authentication routes
    #app.register_blueprint(other_blueprint)  # Register other blueprints as needed
    
    return app

# Sets up Flask-Login for user authentication and session management. The login view is set to the login route defined in the auth blueprint, and a user loader function is defined to load the user from the database based on the user ID stored in the session.
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Set the login view for Flask-Login

@login_manager.user_loader
def load_user(user_id):
    """Loads the user from the database based on the user ID stored in the session."""
    return User.query.get(int(user_id))  # Assuming User model has a primary key of type integer