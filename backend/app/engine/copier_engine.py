import asyncio
import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import MasterAccount, SlaveAccount, CopierSetting, TicketMap, TradeLog
from app.schemas import TradeSignal
from app.security import decrypt_credential
from app.engine.terminal_manager import TerminalManager
from app.engine.lot_calculator import LotCalculator
from app.engine.symbol_mapper import SymbolMapper
from app.engine.risk_manager import RiskManager
from app.ws.connection_manager import ws_manager

logger = logging.getLogger("davidsonsfx.copier")

class CopierEngine:
    @classmethod
    async def process_signal(cls, signal: TradeSignal) -> Dict[str, Any]:
        """
        Main signal processing pipeline.
        Dispatches incoming master trade event to all active followers.
        """
        logger.info(f"Signal received: {signal.action} #{signal.master_ticket} {signal.symbol} {signal.volume} lots")
        
        db: Session = SessionLocal()
        try:
            # 1. Locate master account
            master = None
            if signal.master_login:
                master = db.query(MasterAccount).filter(MasterAccount.login == signal.master_login).first()
            if not master:
                master = db.query(MasterAccount).filter(MasterAccount.is_active == True).first()

            master_id = master.id if master else None
            master_equity = master.equity if master and master.equity > 0 else 1000.0
            master_balance = master.balance if master and master.balance > 0 else 1000.0

            # 2. Find all active slave accounts configured to copy
            active_slaves = (
                db.query(SlaveAccount)
                .join(CopierSetting, CopierSetting.slave_account_id == SlaveAccount.id)
                .filter(SlaveAccount.is_active == True, CopierSetting.is_enabled == True)
                .all()
            )

            if not active_slaves:
                logger.info("No active slave accounts found for copying.")
                return {"status": "SKIPPED", "message": "No active followers", "followers_count": 0}

            # 3. Parallel asynchronous dispatch
            tasks = [
                cls._dispatch_to_slave(slave.id, signal, master_id, master_equity, master_balance)
                for slave in active_slaves
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Broadcast summary event to WebSockets
            await ws_manager.broadcast({
                "type": "SIGNAL_PROCESSED",
                "action": signal.action,
                "symbol": signal.symbol,
                "master_ticket": signal.master_ticket,
                "timestamp": datetime.utcnow().isoformat(),
                "followers_targeted": len(active_slaves),
            })

            return {
                "status": "COMPLETED",
                "action": signal.action,
                "master_ticket": signal.master_ticket,
                "followers_count": len(active_slaves),
                "results": [r if not isinstance(r, Exception) else str(r) for r in results]
            }

        finally:
            db.close()

    @classmethod
    async def _dispatch_to_slave(
        cls,
        slave_id: int,
        signal: TradeSignal,
        master_id: int,
        master_equity: float,
        master_balance: float
    ) -> Dict[str, Any]:
        """Process execution for a single follower account."""
        db: Session = SessionLocal()
        try:
            slave = db.query(SlaveAccount).filter(SlaveAccount.id == slave_id).first()
            if not slave:
                return {"slave_id": slave_id, "status": "FAILED", "error": "Slave account not found"}

            setting = db.query(CopierSetting).filter(CopierSetting.slave_account_id == slave.id).first()
            if not setting or not setting.is_enabled:
                return {"slave_id": slave_id, "status": "SKIPPED", "reason": "Copier disabled for slave"}

            password = decrypt_credential(slave.encrypted_password)

            # Custom symbol mapping parse
            try:
                custom_mapping = json.loads(setting.symbol_mapping) if setting.symbol_mapping else {}
            except Exception:
                custom_mapping = {}

            try:
                allowed_symbols = json.loads(setting.allowed_symbols) if setting.allowed_symbols else []
            except Exception:
                allowed_symbols = []

            # Determine slave symbol
            slave_symbol = SymbolMapper.map_symbol(
                master_symbol=signal.symbol,
                slave_available_symbols=None,
                custom_mapping=custom_mapping
            )

            # ======================== ACTION: OPEN ========================
            if signal.action == "OPEN":
                # Check for existing mapping (avoid double opening)
                existing_map = db.query(TicketMap).filter(
                    TicketMap.slave_account_id == slave.id,
                    TicketMap.master_ticket == signal.master_ticket,
                    TicketMap.is_closed == False
                ).first()

                if existing_map:
                    return {"slave_id": slave_id, "status": "SKIPPED", "reason": "Already copied"}

                # Get slave quote
                quote = TerminalManager.get_symbol_quote(slave_symbol, slave.login, password, slave.server)
                slave_bid = quote.get("bid", 0.0)
                slave_ask = quote.get("ask", 0.0)

                # Validate pre-trade risk
                is_valid, reason, final_type, slippage = RiskManager.validate_pre_trade(
                    symbol=slave_symbol,
                    order_type=signal.order_type,
                    master_price=signal.price,
                    slave_bid=slave_bid,
                    slave_ask=slave_ask,
                    allowed_symbols=allowed_symbols,
                    max_slippage_pips=setting.max_slippage_pips,
                    max_spread_pips=setting.max_spread_pips,
                    invert_trade=setting.invert_trade
                )

                if not is_valid:
                    # Log rejection
                    log = TradeLog(
                        master_account_id=master_id,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        symbol=slave_symbol,
                        action="REJECTED",
                        order_type=signal.order_type,
                        master_price=signal.price,
                        slippage_pips=slippage,
                        master_lot=signal.volume,
                        status="SKIPPED",
                        error_message=reason
                    )
                    db.add(log)
                    db.commit()
                    return {"slave_id": slave_id, "status": "REJECTED", "reason": reason}

                # Calculate lot size
                sl_distance = 0.0
                if signal.sl and signal.sl > 0:
                    sl_distance = abs(signal.price - signal.sl) / SymbolMapper.get_pip_size(slave_symbol, signal.price)

                # Retrieve live slave equity and balance if uninitialized
                slave_equity = slave.equity
                slave_balance = slave.balance
                if slave_equity <= 0 or slave_balance <= 0:
                    conn_info = TerminalManager.test_connection(slave.login, password, slave.server)
                    if conn_info.get("success"):
                        slave.balance = conn_info.get("balance", slave.balance)
                        slave.equity = conn_info.get("equity", slave.equity)
                        slave.currency = conn_info.get("currency", slave.currency)
                        slave_equity = slave.equity
                        slave_balance = slave.balance
                        db.commit()

                slave_lot = LotCalculator.calculate_lot(
                    master_lot=signal.volume,
                    risk_mode=setting.risk_mode,
                    fixed_lot=setting.fixed_lot,
                    lot_multiplier=setting.lot_multiplier,
                    risk_percent=setting.risk_percent,
                    master_equity=master_equity if master_equity > 0 else slave_equity,
                    slave_equity=slave_equity,
                    master_balance=master_balance if master_balance > 0 else slave_balance,
                    slave_balance=slave_balance,
                    min_lot=setting.min_lot,
                    max_lot=setting.max_lot,
                    sl_distance_pips=sl_distance
                )

                # Calculate slave SL / TP
                slave_sl = signal.sl if setting.copy_sl else 0.0
                slave_tp = signal.tp if setting.copy_tp else 0.0

                # Send order to slave MT5
                res = TerminalManager.open_position(
                    login=slave.login,
                    password=password,
                    server=slave.server,
                    symbol=slave_symbol,
                    order_type=final_type,
                    volume=slave_lot,
                    sl=slave_sl,
                    tp=slave_tp,
                    comment=f"DFX-M#{signal.master_ticket}"
                )

                if res.get("success"):
                    # Record ticket mapping
                    ticket_map = TicketMap(
                        master_account_id=master_id or 1,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        slave_ticket=res["ticket"],
                        symbol=slave_symbol,
                        order_type=final_type,
                        open_price=res["price"],
                        volume=res["volume"],
                        is_closed=False
                    )
                    db.add(ticket_map)

                    # Record trade log
                    log = TradeLog(
                        master_account_id=master_id,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        slave_ticket=res["ticket"],
                        symbol=slave_symbol,
                        action="OPEN",
                        order_type=final_type,
                        master_price=signal.price,
                        slave_price=res["price"],
                        slippage_pips=slippage,
                        master_lot=signal.volume,
                        slave_lot=res["volume"],
                        execution_ms=res["execution_ms"],
                        status="SUCCESS"
                    )
                    db.add(log)
                    db.commit()

                    # Broadcast WS update
                    await ws_manager.broadcast({
                        "type": "TRADE_OPENED",
                        "slave_id": slave.id,
                        "slave_name": slave.name,
                        "symbol": slave_symbol,
                        "order_type": final_type,
                        "lot": res["volume"],
                        "ticket": res["ticket"],
                        "latency_ms": res["execution_ms"]
                    })

                    return {"slave_id": slave.id, "status": "SUCCESS", "ticket": res["ticket"]}
                else:
                    log = TradeLog(
                        master_account_id=master_id,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        symbol=slave_symbol,
                        action="OPEN",
                        order_type=final_type,
                        master_lot=signal.volume,
                        slave_lot=slave_lot,
                        status="FAILED",
                        error_message=res.get("error", "Unknown MT5 error")
                    )
                    db.add(log)
                    db.commit()
                    return {"slave_id": slave.id, "status": "FAILED", "error": res.get("error")}

            # ======================== ACTION: MODIFY ========================
            elif signal.action == "MODIFY":
                ticket_map = db.query(TicketMap).filter(
                    TicketMap.slave_account_id == slave.id,
                    TicketMap.master_ticket == signal.master_ticket,
                    TicketMap.is_closed == False
                ).first()

                if not ticket_map:
                    return {"slave_id": slave.id, "status": "SKIPPED", "reason": "No mapped position found"}

                res = TerminalManager.modify_position(
                    login=slave.login,
                    password=password,
                    server=slave.server,
                    position_ticket=ticket_map.slave_ticket,
                    sl=signal.sl if setting.copy_sl else 0.0,
                    tp=signal.tp if setting.copy_tp else 0.0
                )

                log = TradeLog(
                    master_account_id=master_id,
                    slave_account_id=slave.id,
                    master_ticket=signal.master_ticket,
                    slave_ticket=ticket_map.slave_ticket,
                    symbol=ticket_map.symbol,
                    action="MODIFY",
                    status="SUCCESS" if res.get("success") else "FAILED",
                    execution_ms=res.get("execution_ms", 0.0),
                    error_message=res.get("error")
                )
                db.add(log)
                db.commit()
                return {"slave_id": slave.id, "status": "MODIFIED"}

            # ======================== ACTION: CLOSE / PARTIAL CLOSE ========================
            elif signal.action in ["CLOSE", "PARTIAL_CLOSE"]:
                ticket_map = db.query(TicketMap).filter(
                    TicketMap.slave_account_id == slave.id,
                    TicketMap.master_ticket == signal.master_ticket,
                    TicketMap.is_closed == False
                ).first()

                if not ticket_map:
                    return {"slave_id": slave.id, "status": "SKIPPED", "reason": "No mapped open position found"}

                close_vol = None
                if signal.action == "PARTIAL_CLOSE" and signal.close_volume:
                    # Calculate proportional partial close volume
                    if signal.volume > 0:
                        close_ratio = signal.close_volume / signal.volume
                        close_vol = round(ticket_map.volume * close_ratio, 2)

                res = TerminalManager.close_position(
                    login=slave.login,
                    password=password,
                    server=slave.server,
                    position_ticket=ticket_map.slave_ticket,
                    volume=close_vol
                )

                if res.get("success"):
                    if signal.action == "CLOSE" or not close_vol or close_vol >= ticket_map.volume:
                        ticket_map.is_closed = True
                        ticket_map.closed_at = datetime.utcnow()
                    else:
                        ticket_map.volume = round(ticket_map.volume - close_vol, 2)

                    log = TradeLog(
                        master_account_id=master_id,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        slave_ticket=ticket_map.slave_ticket,
                        symbol=ticket_map.symbol,
                        action=signal.action,
                        slave_price=res.get("close_price"),
                        execution_ms=res.get("execution_ms", 0.0),
                        profit=res.get("profit", 0.0),
                        status="SUCCESS"
                    )
                    db.add(log)
                    db.commit()

                    await ws_manager.broadcast({
                        "type": "TRADE_CLOSED",
                        "slave_id": slave.id,
                        "ticket": ticket_map.slave_ticket,
                        "profit": res.get("profit", 0.0)
                    })

                    return {"slave_id": slave.id, "status": "CLOSED", "profit": res.get("profit")}
                else:
                    log = TradeLog(
                        master_account_id=master_id,
                        slave_account_id=slave.id,
                        master_ticket=signal.master_ticket,
                        slave_ticket=ticket_map.slave_ticket,
                        symbol=ticket_map.symbol,
                        action=signal.action,
                        status="FAILED",
                        error_message=res.get("error")
                    )
                    db.add(log)
                    db.commit()
                    return {"slave_id": slave.id, "status": "FAILED", "error": res.get("error")}

            return {"slave_id": slave.id, "status": "UNKNOWN_ACTION"}

        except Exception as e:
            logger.error(f"Error copying to slave {slave_id}: {e}", exc_info=True)
            return {"slave_id": slave_id, "status": "ERROR", "error": str(e)}
        finally:
            db.close()

