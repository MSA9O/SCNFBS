# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

login_manager.login_view = "auth.login"

@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
   
    if dbapi_connection.__class__.__module__ == 'sqlite3':
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
        except Exception as e:   
            pass
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

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

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    with app.app_context():
        from . import models 

        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

        from .routes import auth, main, booking, admin, navigation, user

        app.register_blueprint(auth.bp)
        app.register_blueprint(main.bp)
        app.register_blueprint(booking.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(navigation.bp_navigation)
        app.register_blueprint(user.bp)

        return app