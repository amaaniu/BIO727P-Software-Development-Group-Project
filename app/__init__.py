# This file initialises the Flask application and registers all of the blueprints that form the web app.
from flask import Flask
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