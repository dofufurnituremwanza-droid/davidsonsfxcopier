import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, MasterAccount, SlaveAccount, CopierSetting
from app.schemas import (
    MasterAccountCreate,
    MasterAccountResponse,
    SlaveAccountCreate,
    SlaveAccountUpdate,
    SlaveAccountResponse,
    CopierSettingUpdate,
    CopierSettingResponse,
)
from app.security import encrypt_credential, decrypt_credential
from app.engine.terminal_manager import TerminalManager
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["Account Management"])

# ==================== MASTER ACCOUNTS ====================

@router.get("/master", response_model=List[MasterAccountResponse])
def get_master_accounts(db: Session = Depends(get_db)):
    return db.query(MasterAccount).all()

@router.post("/master", response_model=MasterAccountResponse)
def create_master_account(
    account_in: MasterAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(MasterAccount).filter(MasterAccount.login == account_in.login).first()
    if existing:
        raise HTTPException(status_code=400, detail="Master account already registered")

    real_balance = 0.0
    real_equity = 0.0
    real_currency = "USD"
    real_broker = account_in.broker or account_in.server

    if account_in.password:
        conn = TerminalManager.test_connection(account_in.login, account_in.password, account_in.server)
        if conn.get("success"):
            real_balance = conn.get("balance", 0.0)
            real_equity = conn.get("equity", 0.0)
            real_currency = conn.get("currency", "USD")
            real_broker = conn.get("broker", real_broker)

    master = MasterAccount(
        name=account_in.name,
        login=account_in.login,
        server=account_in.server,
        broker=real_broker,
        balance=real_balance,
        equity=real_equity,
        currency=real_currency,
        is_active=True
    )
    db.add(master)
    db.commit()
    db.refresh(master)
    return master

@router.delete("/master/{id}")
def delete_master_account(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    master = db.query(MasterAccount).filter(MasterAccount.id == id).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master account not found")
    db.delete(master)
    db.commit()
    return {"message": "Master account deleted"}

# ==================== SLAVE ACCOUNTS ====================

@router.get("/slave", response_model=List[SlaveAccountResponse])
def get_slave_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        return db.query(SlaveAccount).all()
    return db.query(SlaveAccount).filter(SlaveAccount.user_id == current_user.id).all()

@router.post("/slave", response_model=SlaveAccountResponse)
def register_slave_account(
    account_in: SlaveAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify account connection against MT5
    test_result = TerminalManager.test_connection(
        login=account_in.login,
        password=account_in.password,
        server=account_in.server
    )

    encrypted_pwd = encrypt_credential(account_in.password)
    slave = SlaveAccount(
        user_id=current_user.id,
        name=account_in.name,
        login=account_in.login,
        encrypted_password=encrypted_pwd,
        server=account_in.server,
        broker=test_result.get("broker") or account_in.broker or account_in.server,
        status="CONNECTED" if test_result.get("success") else "ERROR",
        balance=test_result.get("balance", 0.0),
        equity=test_result.get("equity", 0.0),
        currency=test_result.get("currency", "USD"),
        last_ping=datetime.utcnow() if test_result.get("success") else None,
        last_error=test_result.get("error"),
        is_active=True
    )
    db.add(slave)
    db.commit()
    db.refresh(slave)

    # Automatically create default CopierSetting for this account
    default_setting = CopierSetting(
        slave_account_id=slave.id,
        is_enabled=True,
        risk_mode="EQUITY_RATIO",
        fixed_lot=0.01,
        lot_multiplier=1.0,
        risk_percent=1.0,
        min_lot=0.01,
        max_lot=50.0,
        max_slippage_pips=3.0,
        max_spread_pips=5.0,
        copy_sl=True,
        copy_tp=True,
        invert_trade=False,
        symbol_mapping="{}",
        allowed_symbols="[]"
    )
    db.add(default_setting)
    db.commit()

    return slave

@router.put("/slave/{id}", response_model=SlaveAccountResponse)
def update_slave_account(
    id: int,
    account_in: SlaveAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SlaveAccount).filter(SlaveAccount.id == id)
    if not current_user.is_admin:
        query = query.filter(SlaveAccount.user_id == current_user.id)
    slave = query.first()
    if not slave:
        raise HTTPException(status_code=404, detail="Slave account not found")

    if account_in.name is not None:
        slave.name = account_in.name
    if account_in.server is not None:
        slave.server = account_in.server
    if account_in.broker is not None:
        slave.broker = account_in.broker
    if account_in.is_active is not None:
        slave.is_active = account_in.is_active
    if account_in.password:
        slave.encrypted_password = encrypt_credential(account_in.password)

    db.commit()
    db.refresh(slave)
    return slave

@router.delete("/slave/{id}")
def delete_slave_account(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(SlaveAccount).filter(SlaveAccount.id == id)
    if not current_user.is_admin:
        query = query.filter(SlaveAccount.user_id == current_user.id)
    slave = query.first()
    if not slave:
        raise HTTPException(status_code=404, detail="Slave account not found")
    db.delete(slave)
    db.commit()
    return {"message": "Account removed successfully"}

@router.post("/slave/{id}/test")
def test_slave_account(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(SlaveAccount).filter(SlaveAccount.id == id)
    if not current_user.is_admin:
        query = query.filter(SlaveAccount.user_id == current_user.id)
    slave = query.first()
    if not slave:
        raise HTTPException(status_code=404, detail="Slave account not found")

    pwd = decrypt_credential(slave.encrypted_password)
    res = TerminalManager.test_connection(slave.login, pwd, slave.server)

    if res.get("success"):
        slave.status = "CONNECTED"
        slave.balance = res.get("balance", slave.balance)
        slave.equity = res.get("equity", slave.equity)
        slave.currency = res.get("currency", slave.currency)
        slave.last_ping = datetime.utcnow()
        slave.last_error = None
    else:
        slave.status = "ERROR"
        slave.last_error = res.get("error")

    db.commit()
    db.refresh(slave)
    return res

# ==================== COPIER SETTINGS ====================

@router.get("/slave/{id}/settings", response_model=CopierSettingResponse)
def get_slave_settings(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    setting = db.query(CopierSetting).filter(CopierSetting.slave_account_id == id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Settings not found")

    return CopierSettingResponse(
        id=setting.id,
        slave_account_id=setting.slave_account_id,
        master_account_id=setting.master_account_id,
        is_enabled=setting.is_enabled,
        risk_mode=setting.risk_mode,
        fixed_lot=setting.fixed_lot,
        lot_multiplier=setting.lot_multiplier,
        risk_percent=setting.risk_percent,
        min_lot=setting.min_lot,
        max_lot=setting.max_lot,
        max_slippage_pips=setting.max_slippage_pips,
        max_spread_pips=setting.max_spread_pips,
        copy_sl=setting.copy_sl,
        copy_tp=setting.copy_tp,
        invert_trade=setting.invert_trade,
        symbol_mapping=json.loads(setting.symbol_mapping) if setting.symbol_mapping else {},
        allowed_symbols=json.loads(setting.allowed_symbols) if setting.allowed_symbols else []
    )

@router.put("/slave/{id}/settings", response_model=CopierSettingResponse)
def update_slave_settings(
    id: int,
    settings_in: CopierSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    setting = db.query(CopierSetting).filter(CopierSetting.slave_account_id == id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Settings not found")

    for field, val in settings_in.dict(exclude_unset=True).items():
        if field == "symbol_mapping":
            setting.symbol_mapping = json.dumps(val)
        elif field == "allowed_symbols":
            setting.allowed_symbols = json.dumps(val)
        else:
            setattr(setting, field, val)

    db.commit()
    db.refresh(setting)

    return CopierSettingResponse(
        id=setting.id,
        slave_account_id=setting.slave_account_id,
        master_account_id=setting.master_account_id,
        is_enabled=setting.is_enabled,
        risk_mode=setting.risk_mode,
        fixed_lot=setting.fixed_lot,
        lot_multiplier=setting.lot_multiplier,
        risk_percent=setting.risk_percent,
        min_lot=setting.min_lot,
        max_lot=setting.max_lot,
        max_slippage_pips=setting.max_slippage_pips,
        max_spread_pips=setting.max_spread_pips,
        copy_sl=setting.copy_sl,
        copy_tp=setting.copy_tp,
        invert_trade=setting.invert_trade,
        symbol_mapping=json.loads(setting.symbol_mapping) if setting.symbol_mapping else {},
        allowed_symbols=json.loads(setting.allowed_symbols) if setting.allowed_symbols else []
    )

