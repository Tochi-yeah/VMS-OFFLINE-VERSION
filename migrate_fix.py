import sqlite3
import os

# 1. Connect to the database
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'vms_offline.db')

print(f"🔧 MIGRATION FIX FOR: {db_path}")

if not os.path.exists(db_path):
    print("❌ Database not found!")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("\n--- 1. PREPARING NEW TABLE ---")
    # Enable foreign keys to ensure we don't break relationships
    cursor.execute("PRAGMA foreign_keys=OFF")
    
    # Rename the current (broken) table
    cursor.execute("ALTER TABLE visitor_log RENAME TO visitor_log_old")
    
    # Create the NEW table with explicit AUTOINCREMENT
    # This is the magic keyword missing from your Postgres migration
    create_table_sql = """
    CREATE TABLE visitor_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        visitor_id INTEGER,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(120) NOT NULL,
        number VARCHAR(20) NOT NULL,
        purpose VARCHAR(200) NOT NULL,
        destination VARCHAR(100) NOT NULL DEFAULT 'General',
        address VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        unique_code VARCHAR(10),
        visit_session_id VARCHAR(50),
        approved_by_id INTEGER,
        check_in_by_id INTEGER,
        check_out_by_id INTEGER,
        check_in_gate VARCHAR(50),
        check_out_gate VARCHAR(50),
        FOREIGN KEY(visitor_id) REFERENCES visitor(id),
        FOREIGN KEY(approved_by_id) REFERENCES user(id),
        FOREIGN KEY(check_in_by_id) REFERENCES user(id),
        FOREIGN KEY(check_out_by_id) REFERENCES user(id)
    );
    """
    cursor.execute(create_table_sql)
    print("✅ Created new table with AUTOINCREMENT.")

    print("\n--- 2. MIGRATING DATA ---")
    # Copy data from the old table to the new one
    # We copy the ID explicitly to preserve your history (1176, etc.)
    cols = "id, visitor_id, name, email, number, purpose, destination, address, status, timestamp, unique_code, visit_session_id, approved_by_id, check_in_by_id, check_out_by_id, check_in_gate, check_out_gate"
    
    cursor.execute(f"""
        INSERT INTO visitor_log ({cols})
        SELECT {cols} FROM visitor_log_old
    """)
    print("✅ Data migrated successfully.")

    print("\n--- 3. FIXING SEQUENCE COUNTER ---")
    # Get the max ID we just moved over
    cursor.execute("SELECT MAX(id) FROM visitor_log")
    max_id = cursor.fetchone()[0]
    
    if max_id is None: max_id = 0
    print(f"📈 Highest ID is: {max_id}")
    
    # Manually update the sqlite_sequence table
    # This tells SQLite: "Don't fill gaps! Start counting from 1177!"
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='visitor_log'")
    cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('visitor_log', ?)", (max_id,))
    print(f"✅ Sequence set to {max_id}. Next ID will be {max_id + 1}.")

    print("\n--- 4. CLEANUP ---")
    cursor.execute("DROP TABLE visitor_log_old")
    cursor.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    print("🎉 MIGRATION COMPLETE.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    conn.rollback()

finally:
    conn.close()