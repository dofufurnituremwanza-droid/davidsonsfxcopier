import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent
sys.path.append(str(backend_path))

from app.database import SessionLocal, engine, Base
from app.models import User, MasterAccount, SlaveAccount, CopierSetting
from app.security import encrypt_credential

Base.metadata.create_all(bind=engine)

def register_follower():
    db = SessionLocal()
    try:
        # Get admin user or first user
        user = db.query(User).first()
        if not user:
            print("[!] No user found in database.")
            return

        # Get active master account
        master = db.query(MasterAccount).filter(MasterAccount.login == 106660140).first()
        if not master:
            master = db.query(MasterAccount).filter(MasterAccount.is_active == True).first()

        master_id = master.id if master else None

        # Check if slave account exists
        slave = db.query(SlaveAccount).filter(SlaveAccount.login == 81751427).first()
        if not slave:
            slave = SlaveAccount(
                user_id=user.id,
                name="Eric Paul Exness Trial",
                login=81751427,
                encrypted_password=encrypt_credential("Ericpaul2605+"),
                server="Exness-MT5Trial10",
                broker="Exness",
                is_active=True,
                is_approved=True,
                approval_status="APPROVED",
                payment_method="Direct Connect",
                payment_reference="VIP-LIVE",
                status="CONNECTED",
                balance=1000.0,
                equity=1000.0,
                currency="USD"
            )
            db.add(slave)
            db.commit()
            db.refresh(slave)
            print(f"[+] Successfully registered Follower Account #{slave.login} ({slave.server})")
        else:
            slave.encrypted_password = encrypt_credential("Ericpaul2605+")
            slave.server = "Exness-MT5Trial10"
            slave.broker = "Exness"
            slave.is_active = True
            slave.is_approved = True
            slave.approval_status = "APPROVED"
            slave.status = "CONNECTED"
            db.commit()
            print(f"[+] Updated existing Follower Account #{slave.login}")

        # Ensure CopierSetting exists and links to Master
        setting = db.query(CopierSetting).filter(CopierSetting.slave_account_id == slave.id).first()
        if not setting:
            setting = CopierSetting(
                slave_account_id=slave.id,
                master_account_id=master_id,
                is_enabled=True,
                risk_mode="EQUITY_RATIO",
                fixed_lot=0.01,
                lot_multiplier=1.0,
                risk_percent=1.0,
                min_lot=0.01,
                max_lot=20.0,
                max_slippage_pips=3.0,
                max_spread_pips=5.0,
                copy_sl=True,
                copy_tp=True,
                invert_trade=False,
                symbol_mapping="{}",
                allowed_symbols="[]"
            )
            db.add(setting)
        else:
            setting.master_account_id = master_id
            setting.is_enabled = True
        
        db.commit()
        print(f"[+] Follower Account #{slave.login} is now APPROVED and LINKED to Master #{master.login if master else 'None'}")
    finally:
        db.close()

if __name__ == "__main__":
    register_follower()

