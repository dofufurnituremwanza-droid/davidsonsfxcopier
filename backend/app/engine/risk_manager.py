from typing import List, Tuple, Optional
from app.engine.symbol_mapper import SymbolMapper

class RiskManager:
    @staticmethod
    def validate_pre_trade(
        symbol: str,
        order_type: str,
        master_price: float,
        slave_bid: float,
        slave_ask: float,
        allowed_symbols: Optional[List[str]] = None,
        max_slippage_pips: float = 3.0,
        max_spread_pips: float = 5.0,
        invert_trade: bool = False
    ) -> Tuple[bool, str, str, float]:
        """
        Validate trade against risk rules.
        Returns:
            is_valid (bool)
            reason (str)
            final_order_type (str, e.g. BUY/SELL, inverted if configured)
            slippage_pips (float)
        """
        # 1. Allowed symbols check
        if allowed_symbols and len(allowed_symbols) > 0:
            if symbol.upper() not in [s.upper() for s in allowed_symbols]:
                return False, f"Symbol {symbol} is not in the allowed symbols list", order_type, 0.0

        pip_size = SymbolMapper.get_pip_size(symbol, master_price)

        # 2. Check spread
        if slave_ask > 0 and slave_bid > 0:
            spread_pips = (slave_ask - slave_bid) / pip_size
            if spread_pips > max_spread_pips:
                return False, f"Current spread ({spread_pips:.1f} pips) exceeds maximum allowed ({max_spread_pips:.1f} pips)", order_type, 0.0

        # Invert order type if configured
        final_order_type = order_type.upper()
        if invert_trade:
            final_order_type = "SELL" if final_order_type == "BUY" else "BUY"

        # 3. Check slippage
        slave_current_price = slave_ask if final_order_type == "BUY" else slave_bid
        if master_price > 0 and slave_current_price > 0:
            diff = abs(slave_current_price - master_price)
            slippage_pips = diff / pip_size
            if slippage_pips > max_slippage_pips:
                return False, f"Slippage ({slippage_pips:.1f} pips) exceeds maximum allowed ({max_slippage_pips:.1f} pips)", final_order_type, slippage_pips
        else:
            slippage_pips = 0.0

        return True, "Passed all risk filters", final_order_type, round(slippage_pips, 2)

