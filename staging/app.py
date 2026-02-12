from flask import Flask
from models import db

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///experiments.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ✅ CRITICAL LINE
db.init_app(app)

# ✅ Create tables safely inside context
with app.app_context():
    db.create_all()

from routes import routes_bp
app.register_blueprint(routes_bp)

if __name__ == "__main__":
    app.run(debug=True)

