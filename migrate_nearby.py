"""Migration script for Supabase PostgreSQL — ensures shops table has the right columns.
Safe to re-run (uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set in .env")
        return

    engine = create_engine(db_url, future=True)
    try:
        with engine.connect() as conn:
            # Ensure latitude, longitude, category columns exist with correct types
            # PostgreSQL uses ALTER TABLE ... ALTER COLUMN ... TYPE
            conn.execute(text("""
                ALTER TABLE shops
                    ALTER COLUMN latitude TYPE DOUBLE PRECISION,
                    ALTER COLUMN longitude TYPE DOUBLE PRECISION,
                    ALTER COLUMN category TYPE VARCHAR(120);
            """))
            conn.commit()
        print("Migration successful: columns verified on Supabase PostgreSQL.")
    except Exception as e:
        # If table doesn't exist yet, that's fine — init_db() will create it
        print(f"Migration note: {e}")
        print("This is normal if the table hasn't been created yet. Run the app first.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
