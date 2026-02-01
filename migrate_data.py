import pandas as pd
from sqlalchemy import create_engine, inspect

# --- CONFIGURATION (Extracted from your image) ---
# I constructed this connection string based on your screenshot
# Note: 'sslmode=require' is critical for Neon databases
PG_CONN_STR = (
    "postgresql+psycopg2://neondb_owner:npg_rqUQmCuPLa02"
    "@ep-autumn-moon-a17z949z-pooler.ap-southeast-1.aws.neon.tech/ICC-VMS"
    "?sslmode=require"
)

# The name of the local file you want to create
SQLITE_DB = "vms_offline.db"
# -------------------------------------------------

def copy_database():
    print("1. Connecting to Neon (PostgreSQL)...")
    try:
        pg_engine = create_engine(PG_CONN_STR)
        sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB}")
        
        # Test connection
        with pg_engine.connect() as conn:
            print("   -> Connection successful!")

        # 2. Automatically find all table names in the 'public' schema
        print("2. Fetching table list...")
        inspector = inspect(pg_engine)
        tables = inspector.get_table_names(schema='public')
        
        if not tables:
            print("   Warning: No tables found in the 'public' schema.")
            return

        print(f"   -> Found {len(tables)} tables: {tables}")

        # 3. Loop through tables and copy data
        print("3. Starting copy process...")
        for table in tables:
            print(f"   -> Copying table: '{table}'...", end=" ")
            
            # Read from Postgres
            df = pd.read_sql(f'SELECT * FROM "public"."{table}"', pg_engine)
            
            # Write to SQLite
            # if_exists='replace' ensures we start fresh
            # index=False prevents creating a new 'index' column
            df.to_sql(table, sqlite_engine, if_exists='replace', index=False)
            print(f"Done! ({len(df)} rows)")

        print("\nSUCCESS! All data copied to", SQLITE_DB)

    except Exception as e:
        print("\nERROR:", e)
        print("Tip: If you get an authentication error, double-check that your IP is allowed in Neon dashboard settings.")

if __name__ == "__main__":
    copy_database()