from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import TradeLog, TicketMap, SlaveAccount, MasterAccount, User
from app.schemas import TradeLogResponse, DashboardStats
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/trades", tags=["Trades & Analytics"])

@router.get("/logs", response_model=List[TradeLogResponse])
def get_trade_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TradeLog)
    if not current_user.is_admin:
        user_slave_ids = [s.id for s in db.query(SlaveAccount.id).filter(SlaveAccount.user_id == current_user.id).all()]
        query = query.filter(TradeLog.slave_account_id.in_(user_slave_ids))

    if status:
        query = query.filter(TradeLog.status == status)

    return query.order_by(TradeLog.timestamp.desc()).offset(offset).limit(limit).all()

@router.get("/active")
def get_active_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TicketMap).filter(TicketMap.is_closed == False)
    if not current_user.is_admin:
        user_slave_ids = [s.id for s in db.query(SlaveAccount.id).filter(SlaveAccount.user_id == current_user.id).all()]
        query = query.filter(TicketMap.slave_account_id.in_(user_slave_ids))

    positions = query.order_by(TicketMap.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "master_ticket": p.master_ticket,
            "slave_ticket": p.slave_ticket,
            "slave_account_id": p.slave_account_id,
            "symbol": p.symbol,
            "order_type": p.order_type,
            "volume": p.volume,
            "open_price": p.open_price,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in positions
    ]

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    active_followers = db.query(SlaveAccount).filter(SlaveAccount.is_active == True).count()
    total_masters = db.query(MasterAccount).count()
    total_trades = db.query(TradeLog).count()
    success_trades = db.query(TradeLog).filter(TradeLog.status == "SUCCESS").count()
    failed_trades = db.query(TradeLog).filter(TradeLog.status == "FAILED").count()

    avg_latency = db.query(func.avg(TradeLog.execution_ms)).filter(TradeLog.status == "SUCCESS").scalar() or 0.0
    master_equity = db.query(func.sum(MasterAccount.equity)).scalar() or 0.0
    total_slave_equity = db.query(func.sum(SlaveAccount.equity)).filter(SlaveAccount.is_active == True).scalar() or 0.0

    return DashboardStats(
        total_users=total_users,
        active_followers=active_followers,
        total_master_accounts=total_masters,
        total_copied_trades=total_trades,
        successful_trades=success_trades,
        failed_trades=failed_trades,
        avg_latency_ms=round(float(avg_latency), 2),
        master_equity=round(float(master_equity), 2),
        total_slave_equity=round(float(total_slave_equity), 2)
    )

@router.get("/quotes")
def get_live_market_quotes():
    """Fetch live market quotes directly from MT5 terminal for key symbols."""
    from app.engine.terminal_manager import TerminalManager
    symbols = ["XAUUSD", "EURUSD", "US30", "BTCUSD"]
    quotes = {}
    for sym in symbols:
        quote = TerminalManager.get_symbol_quote(sym)
        if "error" not in quote:
            quotes[sym] = {
                "bid": quote.get("bid"),
                "ask": quote.get("ask"),
                "spread": quote.get("spread")
            }
        else:
            quotes[sym] = None
    return quotes

