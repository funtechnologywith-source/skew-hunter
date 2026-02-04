"""Helper functions for market hours, data fetching, and calculations."""

import copy
from datetime import datetime, time as dt_time
from typing import Optional, Tuple

from utils.cache import DataCache


def is_market_open() -> bool:
    """Check if Indian stock market is currently open"""
    now = datetime.now()

    # NOTE: Weekend check removed - market opens on special days (Budget, etc.)
    # The API will return stale data if market is actually closed

    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)

    return market_open <= now.time() <= market_close


def is_trading_time_allowed(config: dict) -> bool:
    """Check if current time is within allowed trading window"""
    now = datetime.now()

    if not is_market_open():
        return False

    # Parse trading start time
    trading_start = datetime.strptime(config['TIMING']['trading_start'], "%H:%M").time()
    eod_squareoff = datetime.strptime(config['TIMING']['eod_squareoff'], "%H:%M").time()

    return trading_start <= now.time() <= eod_squareoff


def is_lunch_hour(config: dict) -> bool:
    """Check if current time is in lunch avoidance period"""
    now = datetime.now()

    lunch_start = datetime.strptime(config['TIMING']['lunch_avoid_start'], "%H:%M").time()
    lunch_end = datetime.strptime(config['TIMING']['lunch_avoid_end'], "%H:%M").time()

    return lunch_start <= now.time() <= lunch_end


def get_market_status() -> Tuple[str, str]:
    """Get market status and next action time"""
    now = datetime.now()

    if now.weekday() >= 5:
        days_until_monday = 7 - now.weekday()
        return "CLOSED (Weekend)", f"Opens Monday 9:15 AM"

    if now.time() < dt_time(9, 15):
        return "PRE-MARKET", "Opens at 9:15 AM"
    elif now.time() > dt_time(15, 30):
        return "CLOSED", "Opens tomorrow 9:15 AM"
    else:
        return "OPEN", "Closes at 3:30 PM"


def get_days_to_expiry(expiry_str: str) -> int:
    """Calculate days to expiry from expiry string (YYYY-MM-DD format)"""
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
        return max(0, (expiry.date() - datetime.now().date()).days)
    except Exception:
        return 5  # Default to mid-week if parsing fails


def get_optimal_strike(atm: int, signal_type: str, india_vix: float, dte: int) -> int:
    """Select optimal strike based on VIX and days to expiry.

    Logic:
    - Expiry day (dte=0-1): Use ATM - gamma is concentrated, need higher delta
    - Low VIX (<13): Use closer strikes (ATM+50) - need better delta for moves
    - Normal VIX (13-18): Standard ATM+100
    - High VIX (>18): Use closer strikes - capture volatility with better delta

    Returns:
        Strike price (integer)
    """
    if signal_type == 'CALL':
        if dte <= 1:  # Expiry day
            offset = 0  # ATM only - gamma concentrated
        elif india_vix < 13:  # Low VIX
            offset = 50  # Closer to money for better delta
        elif india_vix < 18:  # Normal VIX
            offset = 100  # Standard
        else:  # High VIX (>=18)
            offset = 50  # Better delta capture in volatile market
        return atm + offset
    else:  # PUT
        if dte <= 1:
            offset = 0
        elif india_vix < 13:
            offset = 50
        elif india_vix < 18:
            offset = 100
        else:
            offset = 50
        return atm - offset


def check_spread_acceptable(option_data: dict, max_spread_pct: float = 2.0) -> bool:
    """Check if bid-ask spread is acceptable (not too wide).

    Wide spreads indicate illiquidity and lead to slippage on entry/exit.

    Args:
        option_data: Dict with 'bid' and 'ask' keys
        max_spread_pct: Maximum acceptable spread as percentage (default 2%)

    Returns:
        True if spread is acceptable, False otherwise
    """
    bid = option_data.get('bid', 0)
    ask = option_data.get('ask', 0)

    if bid <= 0 or ask <= 0:
        return False  # Invalid data

    mid = (bid + ask) / 2
    if mid <= 0:
        return False

    spread_pct = (ask - bid) / mid * 100
    return spread_pct <= max_spread_pct


def get_oi_flow_direction(
    ce_oi_change: int, pe_oi_change: int,
    ce_ltp: float = 0, pe_ltp: float = 0,
    prev_ce_ltp: float = 0, prev_pe_ltp: float = 0
) -> str:
    """Determine OI flow direction from CE/PE changes AND price direction.

    IMPROVED: Cross-references OI change with price direction to distinguish
    buying from writing:
    - OI ↑ + Price ↑ = Buying (long positions opening)
    - OI ↑ + Price ↓ = Writing (short positions opening)

    Returns:
        'BEARISH' if net bearish flow (CE buying or PE writing)
        'BULLISH' if net bullish flow (PE buying or CE writing)
        'NEUTRAL' if no clear dominance
    """
    # Calculate price direction
    ce_price_up = ce_ltp > prev_ce_ltp if prev_ce_ltp > 0 else False
    pe_price_up = pe_ltp > prev_pe_ltp if prev_pe_ltp > 0 else False

    bullish_score = 0
    bearish_score = 0

    # CE OI increasing
    if ce_oi_change > 100000:  # Significant CE OI change
        if ce_price_up:
            # CE OI up + CE price up = Call BUYING = BULLISH
            bullish_score += 1
        else:
            # CE OI up + CE price down = Call WRITING = BEARISH
            bearish_score += 1

    # PE OI increasing
    if pe_oi_change > 100000:  # Significant PE OI change
        if pe_price_up:
            # PE OI up + PE price up = Put BUYING = BEARISH
            bearish_score += 1
        else:
            # PE OI up + PE price down = Put WRITING = BULLISH
            bullish_score += 1

    # Fallback to old logic if no price data
    if bullish_score == 0 and bearish_score == 0:
        if ce_oi_change > pe_oi_change * 1.2:
            return 'BEARISH'
        elif pe_oi_change > ce_oi_change * 1.2:
            return 'BULLISH'
        return 'NEUTRAL'

    if bullish_score > bearish_score:
        return 'BULLISH'
    elif bearish_score > bullish_score:
        return 'BEARISH'
    return 'NEUTRAL'


def check_oi_persistence(required_bars: int = 2) -> Tuple[bool, str]:
    """Check if OI flow has been consistent for N bars.

    Args:
        required_bars: Number of consecutive bars required for persistence

    Returns:
        (is_persistent, direction): Tuple of persistence flag and dominant direction
    """
    recent = DataCache.oi_flow_direction_history[-required_bars:] if DataCache.oi_flow_direction_history else []

    if len(recent) < required_bars:
        return False, 'NEUTRAL'

    # Check if all recent bars have same non-neutral direction
    if len(set(recent)) == 1 and recent[0] != 'NEUTRAL':
        return True, recent[0]

    return False, 'NEUTRAL'


def get_pcr_change(lookback_bars: int = 5) -> float:
    """Calculate PCR change from lookback_bars ago to now.

    Returns:
        PCR change (current - past), positive if PCR increased
    """
    if len(DataCache.pcr_history) < lookback_bars + 1:
        return 0.0

    current_pcr = DataCache.pcr_history[-1]
    past_pcr = DataCache.pcr_history[-(lookback_bars + 1)]

    return current_pcr - past_pcr


def adjust_config_for_expiry(config: dict, dte: int) -> dict:
    """Adjust config parameters based on days to expiry.

    Near expiry, options behave differently:
    - Higher gamma means faster moves
    - Time decay accelerates
    - Need tighter stops and earlier trail activation

    Args:
        config: Original config dict
        dte: Days to expiry

    Returns:
        Modified config dict (deep copy)
    """
    adjusted = copy.deepcopy(config)

    if dte <= 1:  # Expiry day
        adjusted['FILTERS']['max_option_price'] = 80
        for regime in adjusted['EXIT']['vix_regimes'].values():
            regime['initial_sl_pct'] = min(regime['initial_sl_pct'], 0.20)
            regime['trail_activation'] = min(regime['trail_activation'], 0.12)
    elif dte <= 3:  # Expiry week
        adjusted['FILTERS']['max_option_price'] = 100
        for regime in adjusted['EXIT']['vix_regimes'].values():
            regime['initial_sl_pct'] = min(regime['initial_sl_pct'], 0.25)
            regime['trail_activation'] = min(regime['trail_activation'], 0.15)

    return adjusted


def fetch_spot_price(api) -> dict:
    """Fetch spot price with market closed fallback"""
    result = {
        'price': None,
        'change': 0,
        'change_pct': 0,
        'is_live': False,
        'data_age_seconds': 0,
        'timestamp': None
    }

    # Always try to fetch - API returns last closing price even when closed
    data = api.get_spot_price()
    if data and data.get('price'):
        DataCache.last_spot_price = data['price']
        DataCache.last_spot_change = data.get('change_pct', 0)
        DataCache.last_spot_timestamp = datetime.now()

        # Update price history only during market hours
        if is_market_open():
            DataCache.price_history.append(data['price'])
            if len(DataCache.price_history) > 100:
                DataCache.price_history = DataCache.price_history[-100:]

        return {
            'price': data['price'],
            'change': data.get('change', 0),
            'change_pct': data.get('change_pct', 0),
            'is_live': is_market_open(),
            'data_age_seconds': 0,
            'timestamp': datetime.now()
        }

    # Fallback to cache
    if DataCache.last_spot_price is not None:
        age = (datetime.now() - DataCache.last_spot_timestamp).total_seconds()
        return {
            'price': DataCache.last_spot_price,
            'change': 0,
            'change_pct': DataCache.last_spot_change,
            'is_live': False,
            'data_age_seconds': age,
            'timestamp': DataCache.last_spot_timestamp
        }

    return result


def fetch_option_chain(api, expiry: str) -> Optional[dict]:
    """Fetch option chain with market closed fallback"""
    # Always try to fetch - API may return last known data
    chain = api.get_option_chain(expiry)
    if chain:
        DataCache.last_option_chain = chain
        DataCache.last_chain_timestamp = datetime.now()
        return chain

    # Fallback to cache
    return DataCache.last_option_chain
