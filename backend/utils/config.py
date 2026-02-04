"""Configuration management for Skew Hunter."""

import os
import json


DEFAULT_CONFIG = {
    "ACTIVE_MODE": "BALANCED",
    "EXPIRY": "2026-01-20",

    "MODES": {
        "STRICT": {
            "alpha_1_call": 0.85,
            "alpha_1_put": 0.85,
            "alpha_2_call": 0.85,
            "alpha_2_put": 0.85,
            "min_confidence": 85,
            "min_quality_score": 85,
            "min_confluence": 5,
            "volume_ratio_threshold": 2.5,
            "oi_change_velocity": 12,
            "oi_persistence_bars": 3
        },
        "BALANCED": {
            "alpha_1_call": 0.80,
            "alpha_1_put": 0.80,
            "alpha_2_call": 0.82,
            "alpha_2_put": 0.82,
            "min_confidence": 80,
            "min_quality_score": 80,
            "min_confluence": 4,
            "volume_ratio_threshold": 2.3,
            "oi_change_velocity": 10,
            "oi_persistence_bars": 2
        },
        "RELAXED": {
            "alpha_1_call": 0.65,
            "alpha_1_put": 0.65,
            "alpha_2_call": 0.68,
            "alpha_2_put": 0.68,
            "min_confidence": 65,
            "min_quality_score": 65,
            "min_confluence": 2,
            "volume_ratio_threshold": 1.5,
            "oi_change_velocity": 5,
            "oi_persistence_bars": 1
        }
    },

    "RISK": {
        "position_size_lots": 1,
        "max_risk_per_trade_pct": 2.0,
        "daily_loss_limit_pct": 5.0,
        "max_trades_per_day": 5
    },

    "EXIT": {
        "profit_target_pct": 20.0,
        "time_exit": "15:15",
        "mtm_max_loss": -5000,
        "mtm_protect_trigger": 5000,
        "mtm_protect_pct": 0.5,
        "min_hold_seconds": 30,
        "vix_regimes": {
            "low": {"max_vix": 12, "initial_sl_pct": 0.25, "trail_activation": 0.20, "trail_distance": 0.25},
            "normal": {"max_vix": 15, "initial_sl_pct": 0.25, "trail_activation": 0.22, "trail_distance": 0.28},
            "elevated": {"max_vix": 20, "initial_sl_pct": 0.25, "trail_activation": 0.25, "trail_distance": 0.32},
            "high": {"max_vix": 25, "initial_sl_pct": 0.25, "trail_activation": 0.28, "trail_distance": 0.38},
            "extreme": {"max_vix": 100, "initial_sl_pct": 0.25, "trail_activation": 0.32, "trail_distance": 0.42}
        }
    },

    "FILTERS": {
        "min_option_price": 20,
        "max_option_price": 150,
        "min_volume": 25000,
        "max_spread_pct": 2.5,
        "min_atr_14": 80,
        "min_trend_strength": 0.6,
        "min_vix": 10,
        "min_oi_change_writing": 400000
    },

    "TIMING": {
        "trading_start": "09:45",
        "lunch_avoid_start": "12:00",
        "lunch_avoid_end": "12:45",
        "eod_squareoff": "15:15",
        "market_close": "15:30"
    },

    "REFRESH_INTERVAL_SECONDS": 3,

    "EXECUTION": {
        "enabled": False,
        "paper_trading": True,
        "order_type": "MARKET",
        "product_type": "I",
        "order_timeout_seconds": 30,
        "max_retry_attempts": 3
    }
}


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from file, create with defaults if missing"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_CONFIG.copy()
            deep_merge(merged, config)
            return merged
        except Exception as e:
            print(f"Warning: Error loading config: {e}. Using defaults.")

    # Create default config file
    save_config(DEFAULT_CONFIG, config_path)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict, config_path: str = "config.json"):
    """Save configuration to file"""
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def deep_merge(base: dict, override: dict):
    """Deep merge override into base dict"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
