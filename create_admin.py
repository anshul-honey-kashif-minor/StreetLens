import sys
import os
from database.db import SessionLocal, init_db
from database.models import User

def make_admin(username_or_email):
    with SessionLocal() as db:
        user = db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if not user:
            print(f"User '{username_or_email}' not found in the database.")
            return

        user.role = "admin"
        db.commit()
        print(f"Success! User '{user.username}' (email: {user.email}) is now an admin.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_admin.py <username_or_email>")
        sys.exit(1)

    init_db()
    make_admin(sys.argv[1])
