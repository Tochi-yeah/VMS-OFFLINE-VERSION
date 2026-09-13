import os
import sys
import webbrowser
from threading import Timer
from app import create_app, socketio

# ==========================================
# 🔧 POSTGRESQL CONFIGURATION
# ==========================================
# 1. SETUP CREDENTIALS
# We set these AT THE TOP so they exist before the app starts
DB_PASSWORD = "admin123" 
DB_USER = "postgres"
DB_HOST = "127.0.0.1"          # 🛑 FIXED: Use IPv4 (127.0.0.1) to prevent IPv6 auth errors
DB_PORT = "5432"
DB_NAME = "Vms-offline"

# 2. INJECT INTO ENVIRONMENT
# We force this into the system so __init__.py can find it
os.environ['DATABASE_URL'] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("="*60)
print(f"🛑 RUN MODE: Switching to Local PostgreSQL")
print(f"🔗 TARGET: {DB_NAME} on {DB_HOST}:{DB_PORT}")
print("="*60)

# ==========================================
# 🚀 START APPLICATION
# ==========================================
app = create_app()

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1.5, open_browser).start()
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=5000, 
        debug=False,        
        use_reloader=False, # Keep False if you plan to convert this to an EXE later
        allow_unsafe_werkzeug=True
    )
    