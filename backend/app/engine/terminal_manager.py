import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from app.config import settings

logger = logging.getLogger("davidsonsfx.terminal")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.error("MetaTrader5 python package is not installed. MT5 operations will fail until installed.")

class TerminalManager:
    @classmethod
    def is_mt5_installed(cls) -> bool:
        return MT5_AVAILABLE

    @classmethod
    def _ensure_initialized(cls, path: Optional[str] = None) -> bool:
        """Ensure MetaTrader 5 is initialized."""
        if not MT5_AVAILABLE:
            return False
        
        # Check if already initialized
        terminal_info = mt5.terminal_info()
        if terminal_info is not None and terminal_info.connected:
            return True

        mt5_path = path or settings.DEFAULT_MT5_PATH
        if mt5_path:
            return mt5.initialize(path=mt5_path)
        return mt5.initialize()

    @classmethod
    def test_connection(
        cls, 
        login: int, 
        password: str, 
        server: str, 
        path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify login credentials against actual MT5 terminal and broker.
        Fetches live account balance, equity, currency, and broker details.
        """
        if not MT5_AVAILABLE:
            return {
                "success": False,
                "error": "MetaTrader5 Python library is not installed on this server."
            }

        mt5_path = path or settings.DEFAULT_MT5_PATH
        
        # Initialize terminal
        try:
            if mt5_path:
                init_ok = mt5.initialize(path=mt5_path, login=int(login), password=password, server=server)
            else:
                init_ok = mt5.initialize(login=int(login), password=password, server=server)
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize MT5: {str(e)}"}

        if not init_ok:
            err = mt5.last_error()
            return {"success": False, "error": f"MT5 initialization failed: {err}"}

        # Authenticate with the broker
        logged_in = mt5.login(login=int(login), password=password, server=server)
        if not logged_in:
            err = mt5.last_error()
            return {"success": False, "error": f"Authentication failed for MT5 account {login} on {server}: {err}"}

        acc_info = mt5.account_info()
        if acc_info is None:
            err = mt5.last_error()
            return {"success": False, "error": f"Could not retrieve account details from broker: {err}"}

        return {
            "success": True,
            "login": login,
            "server": server,
            "broker": getattr(acc_info, "company", server),
            "balance": float(getattr(acc_info, "balance", 0.0)),
            "equity": float(getattr(acc_info, "equity", 0.0)),
            "currency": getattr(acc_info, "currency", "USD"),
            "leverage": int(getattr(acc_info, "leverage", 100)),
            "error": None
        }

    @classmethod
    def get_symbol_quote(
        cls, 
        symbol: str, 
        login: Optional[int] = None, 
        password: Optional[str] = None, 
        server: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch actual real-time tick and market quote from broker."""
        if not MT5_AVAILABLE:
            return {"error": "MetaTrader5 library is not installed"}

        cls._ensure_initialized()

        if login and password and server:
            mt5.login(login=int(login), password=password, server=server)

        # Select symbol in Market Watch if not already active
        if not mt5.symbol_select(symbol, True):
            return {"error": f"Symbol {symbol} cannot be selected on broker terminal"}

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"error": f"Symbol {symbol} not found on broker"}

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"error": f"No active live tick data received for {symbol}"}

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": symbol_info.spread,
            "point": symbol_info.point,
            "digits": symbol_info.digits,
            "min_lot": getattr(symbol_info, "volume_min", 0.01),
            "max_lot": getattr(symbol_info, "volume_max", 100.0),
            "lot_step": getattr(symbol_info, "volume_step", 0.01)
        }

    @classmethod
    def get_available_symbols(cls, login: int, password: str, server: str) -> List[str]:
        """Fetch list of all tradeable symbols directly from the broker."""
        if not MT5_AVAILABLE:
            return []

        cls._ensure_initialized()
        mt5.login(login=int(login), password=password, server=server)
        symbols = mt5.symbols_get()
        if not symbols:
            return []
        return [s.name for s in symbols]

    @classmethod
    def open_position(
        cls,
        login: int,
        password: str,
        server: str,
        symbol: str,
        order_type: str,
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "DavidsonsFX",
        magic: int = 888999
    ) -> Dict[str, Any]:
        """
        Execute an actual live market order on the client MT5 terminal.
        """
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            return {
                "success": False,
                "error": "MetaTrader5 library is not available on this server",
                "execution_ms": 0.0
            }

        cls._ensure_initialized()

        if not mt5.login(login=int(login), password=password, server=server):
            return {
                "success": False,
                "error": f"Failed to login to MT5 account {login} on {server}: {mt5.last_error()}",
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        if not mt5.symbol_select(symbol, True):
            return {
                "success": False,
                "error": f"Failed to select symbol {symbol} in terminal market watch",
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {
                "success": False,
                "error": f"No tick price received for {symbol}",
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        action_type = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if action_type == mt5.ORDER_TYPE_BUY else tick.bid

        # Check broker filling mode
        sym_info = mt5.symbol_info(symbol)
        filling_mode = mt5.ORDER_FILLING_IOC
        if sym_info and hasattr(sym_info, "filling_mode"):
            if sym_info.filling_mode & 1:
                filling_mode = mt5.ORDER_FILLING_FOK
            elif sym_info.filling_mode & 2:
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": action_type,
            "price": float(price),
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": 20,
            "magic": int(magic),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = mt5.order_send(request)
        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            ret_desc = getattr(result, "comment", str(mt5.last_error()))
            return {
                "success": False,
                "error": f"Order rejected (retcode {getattr(result, 'retcode', 'None')}): {ret_desc}",
                "execution_ms": exec_ms
            }

        return {
            "success": True,
            "ticket": result.order,
            "price": result.price,
            "volume": result.volume,
            "symbol": symbol,
            "order_type": order_type.upper(),
            "execution_ms": exec_ms,
            "error": None
        }

    @classmethod
    def modify_position(
        cls,
        login: int,
        password: str,
        server: str,
        position_ticket: int,
        sl: float,
        tp: float
    ) -> Dict[str, Any]:
        """Modify existing open position Stop Loss and Take Profit."""
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            return {"success": False, "error": "MetaTrader5 library is not installed"}

        cls._ensure_initialized()
        mt5.login(login=int(login), password=password, server=server)

        positions = mt5.positions_get(ticket=int(position_ticket))
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position ticket {position_ticket} not found on MT5 terminal"}

        pos = positions[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position_ticket),
            "symbol": pos.symbol,
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
        }

        result = mt5.order_send(request)
        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "success": False,
                "error": f"Modify failed: {getattr(result, 'comment', mt5.last_error())}",
                "execution_ms": exec_ms
            }

        return {"success": True, "ticket": position_ticket, "sl": sl, "tp": tp, "execution_ms": exec_ms}

    @classmethod
    def close_position(
        cls,
        login: int,
        password: str,
        server: str,
        position_ticket: int,
        volume: Optional[float] = None
    ) -> Dict[str, Any]:
        """Close an actual live open position (full or partial volume)."""
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            return {"success": False, "error": "MetaTrader5 library is not installed"}

        cls._ensure_initialized()
        mt5.login(login=int(login), password=password, server=server)
        positions = mt5.positions_get(ticket=int(position_ticket))
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position ticket {position_ticket} not found on terminal"}

        pos = positions[0]
        close_vol = volume if volume and volume > 0 else pos.volume

        opposite_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return {"success": False, "error": f"No tick price received to close {pos.symbol}"}

        price = tick.bid if opposite_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(position_ticket),
            "symbol": pos.symbol,
            "volume": float(close_vol),
            "type": opposite_type,
            "price": float(price),
            "deviation": 20,
            "magic": pos.magic,
            "comment": "DavidsonsFX Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "success": False,
                "error": f"Close failed: {getattr(result, 'comment', mt5.last_error())}",
                "execution_ms": exec_ms
            }

        return {
            "success": True,
            "ticket": position_ticket,
            "closed_volume": close_vol,
            "close_price": result.price,
            "profit": getattr(result, "profit", 0.0),
            "execution_ms": exec_ms
        }
