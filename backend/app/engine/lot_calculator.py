import math

class LotCalculator:
    @staticmethod
    def calculate_lot(
        master_lot: float,
        risk_mode: str,
        fixed_lot: float = 0.01,
        lot_multiplier: float = 1.0,
        risk_percent: float = 1.0,
        master_equity: float = 1000.0,
        slave_equity: float = 1000.0,
        master_balance: float = 1000.0,
        slave_balance: float = 1000.0,
        min_lot: float = 0.01,
        max_lot: float = 50.0,
        lot_step: float = 0.01,
        sl_distance_pips: float = 0.0,
        pip_value_per_lot: float = 10.0
    ) -> float:
        """
        Calculate appropriate slave lot size according to risk settings.
        Supported modes:
        - FIXED_LOT: Uses static fixed lot
        - LOT_MULTIPLIER: Scaled directly by lot_multiplier (e.g. 1.0x, 0.5x, 2.0x)
        - EQUITY_RATIO: Proportional to equity ratio (SlaveEquity / MasterEquity)
        - BALANCE_RATIO: Proportional to balance ratio (SlaveBalance / MasterBalance)
        - RISK_PERCENT: Calculated based on risk percentage and SL distance
        """
        calculated_lot = min_lot

        if risk_mode == "FIXED_LOT":
            calculated_lot = fixed_lot

        elif risk_mode == "LOT_MULTIPLIER":
            calculated_lot = master_lot * lot_multiplier

        elif risk_mode == "EQUITY_RATIO":
            if master_equity > 0 and slave_equity > 0:
                ratio = slave_equity / master_equity
                calculated_lot = master_lot * ratio * lot_multiplier
            else:
                calculated_lot = master_lot * lot_multiplier

        elif risk_mode == "BALANCE_RATIO":
            if master_balance > 0 and slave_balance > 0:
                ratio = slave_balance / master_balance
                calculated_lot = master_lot * ratio * lot_multiplier
            else:
                calculated_lot = master_lot * lot_multiplier

        elif risk_mode == "RISK_PERCENT":
            if slave_equity > 0 and sl_distance_pips > 0 and pip_value_per_lot > 0:
                risk_amount = slave_equity * (risk_percent / 100.0)
                calculated_lot = risk_amount / (sl_distance_pips * pip_value_per_lot)
            else:
                calculated_lot = master_lot * lot_multiplier

        else:
            calculated_lot = master_lot * lot_multiplier

        # Round to broker lot step (e.g. 0.01)
        if lot_step > 0:
            steps = round(calculated_lot / lot_step)
            calculated_lot = round(steps * lot_step, 4)

        # Enforce boundaries
        calculated_lot = max(min_lot, min(max_lot, calculated_lot))
        return round(calculated_lot, 2)

