"""Session state persistence for trade counts and P&L."""

import os
import json
from datetime import datetime
from typing import Optional


SESSION_STATE_FILE = "session_state.json"


def load_session_state(filepath: str = SESSION_STATE_FILE) -> dict:
    """Load session state from file.

    Returns dict with:
    - trades_today: int
    - daily_pnl: float
    - peak_session_mtm: float
    - max_trades_reached: bool
    - last_trade_id: int
    - date: str (YYYY-MM-DD)
    """
    default_state = {
        'trades_today': 0,
        'daily_pnl': 0.0,
        'peak_session_mtm': 0.0,
        'max_trades_reached': False,
        'last_trade_id': 0,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'active_trade': None,  # Serialized active trade for crash recovery
        'cooldown_until': None
    }

    if not os.path.exists(filepath):
        return default_state

    try:
        with open(filepath, 'r') as f:
            state = json.load(f)

        # Check if state is from today
        if state.get('date') != datetime.now().strftime('%Y-%m-%d'):
            # New day - reset state
            print("New trading day detected, resetting session state")
            return default_state

        # Merge with defaults to ensure all keys exist
        for key, value in default_state.items():
            if key not in state:
                state[key] = value

        return state

    except Exception as e:
        print(f"Error loading session state: {e}")
        return default_state


def save_session_state(state: dict, filepath: str = SESSION_STATE_FILE):
    """Save session state to file."""
    try:
        # Ensure date is set
        state['date'] = datetime.now().strftime('%Y-%m-%d')

        # Handle datetime serialization for cooldown_until
        if state.get('cooldown_until') and isinstance(state['cooldown_until'], datetime):
            state['cooldown_until'] = state['cooldown_until'].isoformat()

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    except Exception as e:
        print(f"Error saving session state: {e}")


def clear_session_state(filepath: str = SESSION_STATE_FILE):
    """Clear session state file."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error clearing session state: {e}")
