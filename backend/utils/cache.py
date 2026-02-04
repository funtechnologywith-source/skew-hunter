"""Data cache for market data and historical values."""

import json
import os
from datetime import datetime
from typing import List, Optional

CACHE_FILE = "cache_data.json"


class DataCache:
    """Cache for market data when market is closed"""
    last_spot_price: float = None
    last_spot_timestamp: datetime = None
    last_option_chain: dict = None
    last_chain_timestamp: datetime = None
    last_spot_change: float = 0.0
    last_vix: float = 15.0
    last_atm_strike: int = 0
    price_history: List[float] = []
    high_history: List[float] = []
    low_history: List[float] = []
    close_history: List[float] = []
    oi_history: List[dict] = []
    # OI flow direction history for persistence check
    oi_flow_direction_history: List[str] = []  # ['BULLISH', 'BEARISH', 'NEUTRAL']
    # PCR history for change tracking
    pcr_history: List[float] = []
    # Current weekly expiry (auto-detected)
    current_expiry: str = None
    # Previous ATM LTP for OI flow direction (buying vs writing)
    prev_atm_ce_ltp: float = 0.0
    prev_atm_pe_ltp: float = 0.0

    @classmethod
    def reset(cls):
        """Reset all cache values"""
        cls.last_spot_price = None
        cls.last_spot_timestamp = None
        cls.last_option_chain = None
        cls.last_chain_timestamp = None
        cls.last_spot_change = 0.0
        cls.last_vix = 15.0
        cls.last_atm_strike = 0
        cls.price_history = []
        cls.high_history = []
        cls.low_history = []
        cls.close_history = []
        cls.oi_history = []
        cls.oi_flow_direction_history = []
        cls.pcr_history = []
        cls.current_expiry = None
        cls.prev_atm_ce_ltp = 0.0
        cls.prev_atm_pe_ltp = 0.0

    @classmethod
    def save_to_disk(cls):
        """Save essential cache data to disk for persistence across restarts"""
        try:
            data = {
                'last_spot_price': cls.last_spot_price,
                'last_spot_change': cls.last_spot_change,
                'last_spot_timestamp': cls.last_spot_timestamp.isoformat() if cls.last_spot_timestamp else None,
                'last_vix': cls.last_vix,
                'last_atm_strike': cls.last_atm_strike,
                'current_expiry': cls.current_expiry,
                'pcr_history': cls.pcr_history[-10:] if cls.pcr_history else [],
                'price_history': cls.price_history[-20:] if cls.price_history else [],
            }
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    @classmethod
    def load_from_disk(cls):
        """Load cached data from disk on startup"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)

                cls.last_spot_price = data.get('last_spot_price')
                cls.last_spot_change = data.get('last_spot_change', 0.0)
                cls.last_vix = data.get('last_vix', 15.0)
                cls.last_atm_strike = data.get('last_atm_strike', 0)
                cls.current_expiry = data.get('current_expiry')
                cls.pcr_history = data.get('pcr_history', [])
                cls.price_history = data.get('price_history', [])

                ts = data.get('last_spot_timestamp')
                if ts:
                    cls.last_spot_timestamp = datetime.fromisoformat(ts)

                print(f"Loaded cache: Spot={cls.last_spot_price}, VIX={cls.last_vix}")
        except Exception as e:
            print(f"Failed to load cache: {e}")
