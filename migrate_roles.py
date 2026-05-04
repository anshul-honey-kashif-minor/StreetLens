"""Migration script for Supabase PostgreSQL to add roles and owner_id."""
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
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'customer' NOT NULL;
                ALTER TABLE shops ADD COLUMN IF NOT EXISTS owner_id INTEGER;
            """))
            conn.commit()
        print("Migration successful: Added role to users and owner_id to shops.")
    except Exception as e:
        print(f"Migration note: {e}")
        print("This is normal if the tables haven't been created yet.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
