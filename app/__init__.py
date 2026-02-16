# This file initialises the Flask application and registers all of the blueprints that form the web app.
from flask import Flask
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager
import os

db = SQLAlchemy()  # Create an instance of SQLAlchemy to be used for database interactions
login_manager = LoginManager()  # Create an instance of LoginManager to handle user authentication and session management

def create_app():
    """Creates and configures the Flask applicationfrom all of the registered blueprints."""
    app = Flask(__name__, instance_relative_config=True)  # Create a Flask application instance with relative configuration
    os.makedirs(app.instance_path, exist_ok=True)  # Ensure the instance folder exists for storing the database file
    db_path = os.path.join(app.instance_path, 'app.db')  # Define the
    
    app.config['SECRET_KEY'] = 'dev-key' # In production, use an actual secret key for security purposes.
    # Set up the database path and URI for SQLAlchemy. The database file will be created in the instance folder of the application.
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}" 

    db.init_app(app)  # Initialises SQLAlchemy with the Flask application
    login_manager.init_app(app)  # Initialises Flask-Login with the Flask application
    login_manager.login_view = 'auth.login'  # Set the login view for Flask-Login
   
    from .models import User, Experiment, Variant, Mutations, Activity, ControlData  # Import the User model and other models
    
    @login_manager.user_loader
    def load_user(user_id):
        """Loads the user object from the database based on the user ID stored in the session."""
        return db.session.get(User, int(user_id))  # Retrieves the user from the database using SQLAlchemy's session.get method
    
    from .main import main_bp 
    from .auth import auth_bp   

    app.register_blueprint(main_bp)  # Register the main blueprint with a URL prefix for main routes
    app.register_blueprint(auth_bp, url_prefix='/auth')  # Register the auth blueprint with a URL prefix for authentication routes
    #app.register_blueprint(other_blueprint)  # Register other blueprints as needed
    
    with app.app_context():
        db.create_all()  # Creates the database tables based on the defined models if they do not already exist

    return app
