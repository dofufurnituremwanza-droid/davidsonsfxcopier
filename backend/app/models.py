import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    slave_accounts = relationship("SlaveAccount", back_populates="owner", cascade="all, delete-orphan")

class MasterAccount(Base):
    __tablename__ = "master_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Master Account")
    login = Column(Integer, unique=True, index=True, nullable=False)
    server = Column(String(100), nullable=False)
    broker = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    settings = relationship("CopierSetting", back_populates="master", cascade="all, delete-orphan")
    ticket_maps = relationship("TicketMap", back_populates="master", cascade="all, delete-orphan")

class SlaveAccount(Base):
    __tablename__ = "slave_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False, default="Client Account")
    login = Column(Integer, nullable=False)
    encrypted_password = Column(String(500), nullable=False)
    server = Column(String(100), nullable=False)
    broker = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="DISCONNECTED")  # CONNECTED, DISCONNECTED, ERROR
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    last_ping = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="slave_accounts")
    setting = relationship("CopierSetting", back_populates="slave", uselist=False, cascade="all, delete-orphan")
    ticket_maps = relationship("TicketMap", back_populates="slave", cascade="all, delete-orphan")
    logs = relationship("TradeLog", back_populates="slave", cascade="all, delete-orphan")

class CopierSetting(Base):
    __tablename__ = "copier_settings"

    id = Column(Integer, primary_key=True, index=True)
    slave_account_id = Column(Integer, ForeignKey("slave_accounts.id"), unique=True, nullable=False)
    master_account_id = Column(Integer, ForeignKey("master_accounts.id"), nullable=True)
    
    is_enabled = Column(Boolean, default=True)
    # Risk modes: FIXED_LOT, LOT_MULTIPLIER, EQUITY_RATIO, BALANCE_RATIO, RISK_PERCENT
    risk_mode = Column(String(50), default="EQUITY_RATIO")
    fixed_lot = Column(Float, default=0.01)
    lot_multiplier = Column(Float, default=1.0)
    risk_percent = Column(Float, default=1.0)
    min_lot = Column(Float, default=0.01)
    max_lot = Column(Float, default=50.0)
    
    max_slippage_pips = Column(Float, default=3.0)
    max_spread_pips = Column(Float, default=5.0)
    copy_sl = Column(Boolean, default=True)
    copy_tp = Column(Boolean, default=True)
    invert_trade = Column(Boolean, default=False)
    
    symbol_mapping = Column(Text, default="{}")     # JSON string e.g. {"GOLD": "XAUUSD"}
    allowed_symbols = Column(Text, default="[]")    # JSON string e.g. ["EURUSD", "XAUUSD"] - empty means ALL
    
    slave = relationship("SlaveAccount", back_populates="setting")
    master = relationship("MasterAccount", back_populates="settings")

class TicketMap(Base):
    __tablename__ = "ticket_maps"

    id = Column(Integer, primary_key=True, index=True)
    master_account_id = Column(Integer, ForeignKey("master_accounts.id"), nullable=False)
    slave_account_id = Column(Integer, ForeignKey("slave_accounts.id"), nullable=False)
    master_ticket = Column(Integer, nullable=False, index=True)
    slave_ticket = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    order_type = Column(String(20), nullable=False)  # BUY, SELL
    open_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    master = relationship("MasterAccount", back_populates="ticket_maps")
    slave = relationship("SlaveAccount", back_populates="ticket_maps")

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, index=True)
    master_account_id = Column(Integer, nullable=True)
    slave_account_id = Column(Integer, ForeignKey("slave_accounts.id"), nullable=False)
    master_ticket = Column(Integer, nullable=True)
    slave_ticket = Column(Integer, nullable=True)
    symbol = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)       # OPEN, MODIFY, CLOSE, REJECTED
    order_type = Column(String(20), nullable=True)    # BUY, SELL
    master_price = Column(Float, nullable=True)
    slave_price = Column(Float, nullable=True)
    slippage_pips = Column(Float, default=0.0)
    master_lot = Column(Float, nullable=True)
    slave_lot = Column(Float, nullable=True)
    execution_ms = Column(Float, default=0.0)
    status = Column(String(20), default="SUCCESS")    # SUCCESS, FAILED, SKIPPED
    error_message = Column(Text, nullable=True)
    profit = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    slave = relationship("SlaveAccount", back_populates="logs")

