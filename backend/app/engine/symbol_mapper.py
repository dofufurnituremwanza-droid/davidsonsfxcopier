import re
from typing import Dict, List, Optional

class SymbolMapper:
    COMMON_SYNONYMS = {
        "GOLD": "XAUUSD",
        "XAUUSD": "GOLD",
        "SILVER": "XAGUSD",
        "XAGUSD": "SILVER",
        "US30": "DJ30",
        "DJ30": "US30",
        "WS30": "US30",
        "NAS100": "USTEC",
        "USTEC": "NAS100",
        "NDX": "NAS100",
        "SPX500": "US500",
        "US500": "SPX500",
        "GER30": "DE30",
        "DE40": "GER40",
        "GER40": "DE40",
        "BTCUSD": "BTCUSD.m",
    }

    @classmethod
    def get_pip_size(cls, symbol: str, price: float = 1.0) -> float:
        """Calculate the pip size of a symbol (e.g. 0.0001 for EURUSD, 0.01 for USDJPY, 0.1/1.0 for indices/metals)."""
        sym = symbol.upper()
        if "JPY" in sym:
            return 0.01
        elif any(metal in sym for metal in ["XAU", "GOLD", "XAG", "SILVER"]):
            return 0.01 if price > 1000 else 0.1
        elif any(idx in sym for idx in ["US30", "NAS100", "US500", "GER", "DE40", "DJ30", "SPX"]):
            return 1.0
        elif any(crypto in sym for crypto in ["BTC", "ETH", "LTC"]):
            return 1.0
        # Standard Forex 5-digit / 4-digit
        return 0.0001

    @classmethod
    def map_symbol(
        cls,
        master_symbol: str,
        slave_available_symbols: Optional[List[str]] = None,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Translate a master symbol to the corresponding slave broker symbol.
        1. Checks custom mapping dictionary (e.g. {"GOLD": "XAUUSD.pro"})
        2. Checks common synonyms (GOLD -> XAUUSD)
        3. Matches base symbol against slave available symbols considering prefixes/suffixes (e.g. EURUSD -> EURUSDm or rEURUSD)
        """
        clean_master = master_symbol.strip()
        custom_mapping = custom_mapping or {}

        # 1. Custom explicit mapping
        if clean_master in custom_mapping:
            return custom_mapping[clean_master]
        
        # Upper case check
        if clean_master.upper() in custom_mapping:
            return custom_mapping[clean_master.upper()]

        # If slave symbols list is not provided, return clean_master or basic synonym
        if not slave_available_symbols:
            return cls.COMMON_SYNONYMS.get(clean_master.upper(), clean_master)

        # 2. Check if clean_master directly exists in slave list
        if clean_master in slave_available_symbols:
            return clean_master

        # 3. Strip common prefixes/suffixes to find core symbol
        # Regex to extract 6-char forex or common tickers
        core_symbol = cls._extract_core_symbol(clean_master)

        # Check direct core match
        if core_symbol in slave_available_symbols:
            return core_symbol

        # Check synonym core match
        synonym = cls.COMMON_SYNONYMS.get(core_symbol.upper())
        if synonym and synonym in slave_available_symbols:
            return synonym

        # Search slave symbols for any symbol containing the core symbol or synonym
        targets = [core_symbol]
        if synonym:
            targets.append(synonym)

        for target in targets:
            for slave_sym in slave_available_symbols:
                # Match e.g. "EURUSDm", "EURUSD.r", "EURUSD_i", "rEURUSD"
                pattern = rf"(^|[._\-\w]{{1,4}}){re.escape(target)}([._\-\w]{{1,6}})?$"
                if re.match(pattern, slave_sym, re.IGNORECASE):
                    return slave_sym

        return clean_master

    @classmethod
    def _extract_core_symbol(cls, symbol: str) -> str:
        s = symbol.upper()
        # Remove common delimiters
        s = s.replace(".", "").replace("_", "").replace("-", "")
        # Common 6-letter FX pairs
        fx_majors = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
                     "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "CADJPY", "EURAUD", "EURCAD"]
        for major in fx_majors:
            if major in s:
                return major

        # Metals & Crypto
        for asset in ["XAUUSD", "GOLD", "XAGUSD", "SILVER", "BTCUSD", "ETHUSD", "US30", "NAS100", "US500", "GER40"]:
            if asset in s:
                return asset

        return symbol

