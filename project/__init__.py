# project/__init__.py

import os
from flask import Flask
from dotenv import load_dotenv

# Import extensions
from .extensions import db, migrate, login_manager, oauth
# Import models so Flask-Migrate can see them
from .models import User

# Import Blueprints from the routes package
from .routes.main_routes import main
from .routes.auth_routes import auth_bp
from .routes.project_routes import project_bp
from .routes.client_routes import client_bp
from .routes.invoice_routes import invoice_bp
from .routes.expenses_routes import expenses_bp

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates')

    # --- Load Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer_manager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)

    # --- Configure Login Manager ---
    login_manager.login_view = 'auth.login'
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Configure Google OAuth ---
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # --- Register Blueprints ---
    app.register_blueprint(main)
    app.register_blueprint(auth_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(expenses_bp)

    return app