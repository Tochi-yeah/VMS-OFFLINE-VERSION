import os
from app import create_app, socketio

# ==========================================
# 🔧 POSTGRESQL CONFIGURATION
# ==========================================
DB_PASSWORD = "admin123"  # <--- PUT YOUR PGADMIN PASSWORD HERE

DB_USER = "postgres"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "Vms_offline"

# Build the connection string
pg_db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("="*60)
print(f"🛑 DEBUG FORCE: Switching to Local PostgreSQL")
print(f"🔗 TARGET: {DB_NAME} on {DB_HOST}:{DB_PORT}")
print("="*60)

# ==========================================
# 🚀 START APPLICATION
# ==========================================
# 1. Create the app (which normally loads SQLite)
app = create_app()

# 2. 🛑 FORCE OVERRIDE: Inject PostgreSQL Config
# This ensures we ignore whatever is inside __init__.py
app.config['SQLALCHEMY_DATABASE_URI'] = pg_db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if __name__ == "__main__":
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=5000, 
        debug=True,        
        use_reloader=True, 
        allow_unsafe_werkzeug=True
    )