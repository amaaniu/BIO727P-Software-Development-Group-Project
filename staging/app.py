from flask import Flask
from routes import routes_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev"  # change later

    app.register_blueprint(routes_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
