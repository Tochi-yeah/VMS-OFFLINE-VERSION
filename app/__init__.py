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

# --- CRITICAL IMPORTS FOR THE FIX ---
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool  # <--- Disables Connection Pooling
import sqlite3
import pytz
from datetime import datetime
from dateutil import parser
# -------------------------------

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
            template_dir = os.path.join(base_dir, '..', 'templates')
            static_dir = os.path.join(base_dir, '..', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
# ---------------------------------------------------------
    # 2. DATABASE CONFIGURATION
    # ---------------------------------------------------------
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-offline')
    
    # Check if an external script (like debug_offline.py) provided a database
    custom_db_url = os.environ.get('DATABASE_URL')

    if custom_db_url:
        # ✅ CASE 1: Custom Database (PostgreSQL) detected
        app.config['SQLALCHEMY_DATABASE_URI'] = custom_db_url
        print(f"⚙️ CUSTOM CONFIG: Using External Database -> {custom_db_url}")
    
    elif getattr(sys, 'frozen', False):
        # 🧊 CASE 2: Frozen Mode (.exe) - Uses Internal SQLite
        exe_folder = os.path.dirname(sys.executable)
        db_path = os.path.join(exe_folder, 'vms_offline.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        print(f"🔄 OFFLINE MODE: Using database at {db_path}")
        
    else:
        # 🛠️ CASE 3: Standard Debug Mode - Uses Project Root SQLite
        project_root = os.path.abspath(os.path.join(base_dir, '..'))
        db_path = os.path.join(project_root, 'vms_offline.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        print(f"🛠️ DEBUG MODE: Using database at {db_path}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)

    limiter.default_limits = ["100 per day", "20 per hour"]

    from app.routes import main, auth, request, scan, download_log, analytic, profile, download_template
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(request.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(download_log.bp)
    app.register_blueprint(analytic.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(download_template.bp)

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

   # CORRECTED: Commented out for PostgreSQL
    # if getattr(sys, 'frozen', False):
    #     with app.app_context():
    #         db.create_all()
    #         # Force WAL mode for EXE as well
    #         db.session.execute("PRAGMA journal_mode=WAL")
    #         db.session.commit()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app

# =========================================================
#  SQLITE CONFIGURATION (WAL MODE + FOREIGN KEYS)
# =========================================================
@event.listens_for(Engine, "connect")
def set_sqlite_functions(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        
        # ⚡ ENABLE WAL MODE (Fixes locking/phantom writes)
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Enable Foreign Keys
        cursor.execute("PRAGMA foreign_keys=ON")
        
        cursor.close()

        def sql_timezone(zone, val):
            if val is None: return None
            try:
                val_str = str(val)
                dt = parser.parse(val_str)
                if dt.tzinfo is None:
                    dt = pytz.utc.localize(dt)
                target_tz = pytz.timezone(zone)
                local_dt = dt.astimezone(target_tz)
                return local_dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return val

        dbapi_connection.create_function("timezone", 2, sql_timezone)