from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Master Account Schemas
class MasterAccountBase(BaseModel):
    name: str = "DavidsonsFX Main"
    login: int
    server: str
    broker: Optional[str] = None

class MasterAccountCreate(MasterAccountBase):
    password: Optional[str] = None

class MasterAccountResponse(MasterAccountBase):
    id: int
    is_active: bool
    balance: float
    equity: float
    currency: str
    last_seen: datetime

    class Config:
        from_attributes = True

# Slave Account Schemas
class SlaveAccountBase(BaseModel):
    name: str = "Client MT5 Account"
    login: int
    server: str
    broker: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_method: Optional[str] = None
    telegram_handle: Optional[str] = None

class SlaveAccountCreate(SlaveAccountBase):
    password: str

class SlaveAccountUpdate(BaseModel):
    name: Optional[str] = None
    server: Optional[str] = None
    broker: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    approval_status: Optional[str] = None

class SlaveAccountResponse(SlaveAccountBase):
    id: int
    user_id: int
    is_active: bool
    is_approved: bool
    approval_status: str
    status: str
    balance: float
    equity: float
    currency: str
    last_ping: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class SlaveApprovalRequest(BaseModel):
    approved: bool
    master_account_id: Optional[int] = None
    notes: Optional[str] = None

# Copier Settings Schemas
class CopierSettingUpdate(BaseModel):
    is_enabled: Optional[bool] = True
    risk_mode: Optional[str] = "EQUITY_RATIO"  # FIXED_LOT, LOT_MULTIPLIER, EQUITY_RATIO, BALANCE_RATIO, RISK_PERCENT
    fixed_lot: Optional[float] = 0.01
    lot_multiplier: Optional[float] = 1.0
    risk_percent: Optional[float] = 1.0
    min_lot: Optional[float] = 0.01
    max_lot: Optional[float] = 50.0
    max_slippage_pips: Optional[float] = 3.0
    max_spread_pips: Optional[float] = 5.0
    copy_sl: Optional[bool] = True
    copy_tp: Optional[bool] = True
    invert_trade: Optional[bool] = False
    symbol_mapping: Optional[Dict[str, str]] = {}
    allowed_symbols: Optional[List[str]] = []

class CopierSettingResponse(BaseModel):
    id: int
    slave_account_id: int
    master_account_id: Optional[int]
    is_enabled: bool
    risk_mode: str
    fixed_lot: float
    lot_multiplier: float
    risk_percent: float
    min_lot: float
    max_lot: float
    max_slippage_pips: float
    max_spread_pips: float
    copy_sl: bool
    copy_tp: bool
    invert_trade: bool
    symbol_mapping: Dict[str, str]
    allowed_symbols: List[str]

    class Config:
        from_attributes = True

# Trade Signal (from Master EA / Webhook / Terminal Watcher)
class TradeSignal(BaseModel):
    action: str  # OPEN, MODIFY, CLOSE, PARTIAL_CLOSE
    master_ticket: int
    master_login: Optional[int] = None
    symbol: str
    order_type: str  # BUY, SELL
    volume: float
    price: float
    sl: Optional[float] = 0.0
    tp: Optional[float] = 0.0
    close_price: Optional[float] = None
    close_volume: Optional[float] = None
    magic: Optional[int] = 0
    comment: Optional[str] = "DavidsonsFX Copier"

# Trade Log Schemas
class TradeLogResponse(BaseModel):
    id: int
    master_account_id: Optional[int]
    slave_account_id: int
    master_ticket: Optional[int]
    slave_ticket: Optional[int]
    symbol: str
    action: str
    order_type: Optional[str]
    master_price: Optional[float]
    slave_price: Optional[float]
    slippage_pips: float
    master_lot: Optional[float]
    slave_lot: Optional[float]
    execution_ms: float
    status: str
    error_message: Optional[str]
    profit: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True

# Dashboard Stats
class DashboardStats(BaseModel):
    total_users: int
    active_followers: int
    total_master_accounts: int
    total_copied_trades: int
    successful_trades: int
    failed_trades: int
    avg_latency_ms: float
    master_equity: float
    total_slave_equity: float

