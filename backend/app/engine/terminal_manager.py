import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from app.config import settings

logger = logging.getLogger("davidsonsfx.terminal")

# Try to import MetaTrader5; if unavailable, mock mode is activated
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 python package not detected. Running in Simulation/Safe Mode.")

class TerminalManager:
    _simulated_tickets = 1000000

    @classmethod
    def is_mt5_installed(cls) -> bool:
        return MT5_AVAILABLE

    @classmethod
    def test_connection(
        cls, 
        login: int, 
        password: str, 
        server: str, 
        path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify login credentials with MT5 terminal.
        Returns dict with success status, balance, equity, currency, broker, error.
        """
        if not MT5_AVAILABLE:
            # Simulation response for development/testing
            return {
                "success": True,
                "simulated": True,
                "login": login,
                "server": server,
                "broker": f"Simulated Broker ({server})",
                "balance": 10000.0,
                "equity": 10000.0,
                "currency": "USD",
                "leverage": 100,
                "error": None
            }

        mt5_path = path or settings.DEFAULT_MT5_PATH
        
        # Initialize terminal connection
        init_ok = False
        try:
            if mt5_path:
                init_ok = mt5.initialize(path=mt5_path, login=login, password=password, server=server)
            else:
                init_ok = mt5.initialize(login=login, password=password, server=server)
        except Exception as e:
            return {"success": False, "error": f"Failed to launch MT5 terminal: {str(e)}"}

        if not init_ok:
            err = mt5.last_error()
            return {"success": False, "error": f"MT5 initialization failed: {err}"}

        # Attempt explicit login
        logged_in = mt5.login(login=login, password=password, server=server)
        if not logged_in:
            err = mt5.last_error()
            return {"success": False, "error": f"Login failed for account {login} on {server}: {err}"}

        acc_info = mt5.account_info()
        if acc_info is None:
            err = mt5.last_error()
            return {"success": False, "error": f"Failed to retrieve account info: {err}"}

        return {
            "success": True,
            "simulated": False,
            "login": login,
            "server": server,
            "broker": getattr(acc_info, "company", server),
            "balance": getattr(acc_info, "balance", 0.0),
            "equity": getattr(acc_info, "equity", 0.0),
            "currency": getattr(acc_info, "currency", "USD"),
            "leverage": getattr(acc_info, "leverage", 100),
            "error": None
        }

    @classmethod
    def get_symbol_quote(
        cls, 
        symbol: str, 
        login: int, 
        password: str, 
        server: str
    ) -> Dict[str, Any]:
        """Fetch real-time tick/quote (bid, ask, spread)."""
        if not MT5_AVAILABLE:
            return {
                "symbol": symbol,
                "bid": 1.0850,
                "ask": 1.0852,
                "spread": 2,
                "point": 0.0001,
                "digits": 5,
                "min_lot": 0.01,
                "max_lot": 100.0,
                "lot_step": 0.01
            }

        mt5.login(login=login, password=password, server=server)
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            mt5.symbol_select(symbol, True)
            symbol_info = mt5.symbol_info(symbol)

        if symbol_info is None:
            return {"error": f"Symbol {symbol} not found on broker {server}"}

        tick = mt5.symbol_info_tick(symbol)
        bid = tick.bid if tick else symbol_info.bid
        ask = tick.ask if tick else symbol_info.ask

        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "spread": symbol_info.spread,
            "point": symbol_info.point,
            "digits": symbol_info.digits,
            "min_lot": getattr(symbol_info, "volume_min", 0.01),
            "max_lot": getattr(symbol_info, "volume_max", 100.0),
            "lot_step": getattr(symbol_info, "volume_step", 0.01)
        }

    @classmethod
    def get_available_symbols(cls, login: int, password: str, server: str) -> List[str]:
        """Fetch list of all tradeable symbols from the connected broker."""
        if not MT5_AVAILABLE:
            return ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "GOLD", "US30", "NAS100", "BTCUSD"]

        mt5.login(login=login, password=password, server=server)
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
        comment: str = "DavidsonsFX Copier",
        magic: int = 888999
    ) -> Dict[str, Any]:
        """
        Execute an instant market order on MT5.
        Returns ticket number, execution price, error if any.
        """
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            cls._simulated_tickets += 1
            exec_price = 1.0852 if order_type.upper() == "BUY" else 1.0850
            return {
                "success": True,
                "ticket": cls._simulated_tickets,
                "price": exec_price,
                "volume": volume,
                "symbol": symbol,
                "order_type": order_type.upper(),
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "error": None
            }

        if not mt5.login(login=login, password=password, server=server):
            return {
                "success": False,
                "error": f"Failed to login to MT5 account {login} on {server}: {mt5.last_error()}"
            }

        # Ensure symbol is active in Market Watch
        if not mt5.symbol_select(symbol, True):
            return {
                "success": False,
                "error": f"Failed to select symbol {symbol} in terminal market watch"
            }

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"success": False, "error": f"No tick data available for {symbol}"}

        action_type = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if action_type == mt5.ORDER_TYPE_BUY else tick.bid

        # Determine filling mode supported by broker symbol
        sym_info = mt5.symbol_info(symbol)
        filling_mode = mt5.ORDER_FILLING_IOC
        if sym_info and hasattr(sym_info, "filling_mode"):
            if sym_info.filling_mode & 1:  # FOK
                filling_mode = mt5.ORDER_FILLING_FOK
            elif sym_info.filling_mode & 2:  # IOC
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
            ret_desc = result.comment if result else str(mt5.last_error())
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
        """Modify existing position Stop Loss and Take Profit."""
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            return {
                "success": True,
                "ticket": position_ticket,
                "sl": sl,
                "tp": tp,
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "error": None
            }

        mt5.login(login=login, password=password, server=server)

        # Retrieve position info
        positions = mt5.positions_get(ticket=position_ticket)
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position ticket {position_ticket} not found"}

        pos = positions[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position_ticket,
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
        """Close an open position (supports full or partial lot size)."""
        start_time = time.perf_counter()

        if not MT5_AVAILABLE:
            return {
                "success": True,
                "ticket": position_ticket,
                "closed_volume": volume or 0.1,
                "close_price": 1.0860,
                "profit": 15.0,
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "error": None
            }

        mt5.login(login=login, password=password, server=server)
        positions = mt5.positions_get(ticket=position_ticket)
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position ticket {position_ticket} not found on terminal"}

        pos = positions[0]
        close_vol = volume if volume and volume > 0 else pos.volume

        # Determine opposite order type
        opposite_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return {"success": False, "error": f"No tick quote to close {pos.symbol}"}

        price = tick.bid if opposite_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position_ticket,
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

