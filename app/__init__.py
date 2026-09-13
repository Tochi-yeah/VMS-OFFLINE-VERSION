# app/__init__.py
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_login import LoginManager
from dateutil import parser  # Kept this as it is used in your custom filter

# --- POSTGRESQL IMPORTS ---
from sqlalchemy import event
from sqlalchemy.engine import Engine

load_dotenv()

# Global extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    # ---------------------------------------------------------
    # 1. PATH CONFIGURATION
    # ---------------------------------------------------------
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        template_dir = os.path.join(base_dir, 'app', 'templates')
        static_dir = os.path.join(base_dir, 'app', 'static')
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(base_dir, 'templates')):
             template_dir = os.path.join(base_dir, 'templates')
             static_dir = os.path.join(base_dir, 'static')
        else:
             template_dir = os.path.join(base_dir, 'app', 'templates')
             static_dir = os.path.join(base_dir, 'app', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # ---------------------------------------------------------
    # 2. CONFIGURATION
    # ---------------------------------------------------------
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-key-123")
    
    # DATABASE CONNECTION (Pulls from run.py or .env)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['RATELIMIT_STORAGE_URI'] = os.getenv("REDIS_URL", "memory://")

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)

    # Rate Limiter defaults
    limiter.default_limits = ["100 per day", "20 per hour"]

    # ---------------------------------------------------------
    # 3. REGISTER BLUEPRINTS (YOUR ACTUAL ONES)
    # ---------------------------------------------------------
    from app.routes import main, auth, request, scan, download_log, analytic, profile, download_template
    
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(request.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(download_log.bp)
    app.register_blueprint(analytic.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(download_template.bp)

    # ---------------------------------------------------------
    # 4. CUSTOM FILTERS
    # ---------------------------------------------------------
    from app.models import User
    from app.utils.helpers import convert_to_ph_time_only
    app.jinja_env.filters['ph_time_only'] = convert_to_ph_time_only

    @app.template_filter('format_date')
    def format_date_filter(value, format="%B %d, %Y"):
        if not value: return "—"
        if isinstance(value, str):
            try:
                if "." in value: value = value.split(".")[0]
                dt = parser.parse(value)
                return dt.strftime(format)
            except: return value
        return value.strftime(format)

    # ---------------------------------------------------------
    # 5. DATABASE INITIALIZATION
    # ---------------------------------------------------------
    if getattr(sys, 'frozen', False):
        with app.app_context():
            db.create_all()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app