# This file initialises the Flask application and registers all of the blueprints that form the app.
from flask import Flask
from app.main import main

def create_app():

    """Creates and configures the Flask application."""
    app = Flask(__name__)
    app.register_blueprint(main)
    return app