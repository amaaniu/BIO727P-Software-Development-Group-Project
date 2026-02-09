#This file runs the Flask application.
from app import create_app
from app import db
from app.models import User, Variants, Mutations  # Import the database models
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
