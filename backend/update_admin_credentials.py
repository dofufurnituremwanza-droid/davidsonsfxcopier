import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent
sys.path.append(str(backend_path))

from app.database import SessionLocal, engine, Base
from app.models import User
from app.security import get_password_hash

Base.metadata.create_all(bind=engine)

def update_admin():
    db = SessionLocal()
    try:
        # Check if old admin exists
        old_admin = db.query(User).filter(User.username == "admin").first()
        if old_admin:
            old_admin.username = "davidsonsfx"
            old_admin.full_name = "DavidsonsFX Administrator"
            old_admin.hashed_password = get_password_hash("davidson2026")
            old_admin.is_admin = True
            db.commit()
            print("[+] Updated existing admin to 'davidsonsfx' with new password.")
            return

        # Check if davidsonsfx already exists
        new_admin = db.query(User).filter(User.username == "davidsonsfx").first()
        if new_admin:
            new_admin.hashed_password = get_password_hash("davidson2026")
            new_admin.is_admin = True
            db.commit()
            print("[+] Updated password for 'davidsonsfx'.")
            return

        # Otherwise create new admin
        admin = User(
            username="davidsonsfx",
            email="admin@davidsonsfx.com",
            full_name="DavidsonsFX Administrator",
            hashed_password=get_password_hash("davidson2026"),
            is_admin=True
        )
        db.add(admin)
        db.commit()
        print("[+] Created new admin user: davidsonsfx / davidson2026")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin()

