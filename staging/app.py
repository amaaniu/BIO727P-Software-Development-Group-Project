from flask import Flask
from models import db

from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///experiments.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

with app.app_context():
    db.create_all()

from routes import routes_bp
app.register_blueprint(routes_bp)

if __name__ == "__main__":
    app.run(debug=True)
