# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv

# --- ADD THESE IMPORTS ---
from sqlalchemy import event
from sqlalchemy.engine import Engine
# --- END ADDED IMPORTS ---

load_dotenv()

# Create extension instances
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

login_manager.login_view = "auth.login"

# --- ADD THIS FUNCTION ---
# This function will be called when a new connection to the SQLite database is made.
@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """
    Sets PRAGMAs for SQLite to improve concurrency and prevent "database is locked" errors.
    """
    # Check if we are using SQLite. This is a basic check;
    # for more robust checking, you might inspect connection_record.get_dialect().name
    # or the app.config['SQLALCHEMY_DATABASE_URI'] more closely if you support multiple DBs.
    # However, directly checking the dbapi_connection type is often sufficient for pysqlite.
    if dbapi_connection.__class__.__module__ == 'sqlite3': # Check if it's a standard sqlite3 connection
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout = 5000;") # 5 seconds
            # Optionally, log that this happened if you have app.logger configured early enough
            # For now, we'll assume it works silently or rely on errors if it fails.
            # print("SQLite PRAGMAs (WAL, busy_timeout) set.") # For debugging
        except Exception as e:
            # print(f"Failed to set SQLite PRAGMAs: {e}") # For debugging
            # In a real app, use app.logger.error(...)
            pass # Or raise the error if critical
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
# --- END ADDED FUNCTION ---


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or 'a-fallback-dev-key',
        SQLALCHEMY_DATABASE_URI="sqlite:///scnfbs.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAIL_SERVER=os.environ.get('MAIL_SERVER'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS') is not None,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    )

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Import models and define user_loader within the app context
    with app.app_context():
        from . import models # This will trigger model definitions which might use db

        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

        # Import and register blueprints
        from .routes import auth, main, booking, admin, navigation, user

        app.register_blueprint(auth.bp)
        app.register_blueprint(main.bp)
        app.register_blueprint(booking.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(navigation.bp_navigation)
        app.register_blueprint(user.bp)

        # It's good practice to create database tables if they don't exist,
        # especially for SQLite during development/first run.
        # db.create_all() # Uncomment if you want this; Flask-Migrate is usually preferred for schema changes.

        return app