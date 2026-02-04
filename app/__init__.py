# This file initialises the Flask application and registers all of the blueprints that form the web app.
from flask import Flask
from .main import main_bp

def create_app():
    """Creates and configures the Flask applicationfrom all of the registered blueprints."""
    app = Flask(__name__)
    
    app.register_blueprint(main_bp)
    #app.register_blueprint(other_blueprint)  # Register other blueprints as needed
    
    return app