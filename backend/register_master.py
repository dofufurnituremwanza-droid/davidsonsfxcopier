import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent
sys.path.append(str(backend_path))

from app.database import SessionLocal, engine, Base
from app.models import MasterAccount

Base.metadata.create_all(bind=engine)

def register():
    db = SessionLocal()
    try:
        # Check if already exists
        master = db.query(MasterAccount).filter(MasterAccount.login == 106660140).first()
        if not master:
            master = MasterAccount(
                name="DavidsonsFX FBS Master",
                login=106660140,
                server="FBS-DEMO",
                broker="FBS Markets Inc.",
                is_active=True,
                balance=10000.0,
                equity=10000.0,
                currency="USD"
            )
            db.add(master)
            print("[+] Successfully registered Master Account: 106660140 (FBS-DEMO)")
        else:
            master.name = "DavidsonsFX FBS Master"
            master.server = "FBS-DEMO"
            master.broker = "FBS Markets Inc."
            master.is_active = True
            print("[+] Updated existing Master Account: 106660140 (FBS-DEMO)")
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    register()

