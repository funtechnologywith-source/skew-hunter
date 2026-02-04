"""Entry signal detection for Skew Hunter."""

from datetime import datetime
from typing import Optional, Tuple

from utils.helpers import (
    is_trading_time_allowed,
    is_lunch_hour,
    get_days_to_expiry,
    get_optimal_strike,
    check_spread_acceptable,
    get_oi_flow_direction,
    check_oi_persistence,
    get_pcr_change
)
from utils.cache import DataCache


def check_entry_signal(
    data: dict, config: dict, session_stats: dict, india_vix: float = 15.0
) -> Tuple[Optional[str], Optional[int], Optional[float], Optional[float], Optional[str]]:
    """Check for entry signals, return (signal_type, strike, ltp, confidence, signal_path)

    ENHANCED (2026-01-30):
    - Added trend direction confirmation
    - Added RSI overbought/oversold checks
    - Added PCR change tracking
    - Added bid-ask spread filter
    - Added OI persistence check
    - Added signal cooldown after loss
    - Dynamic strike selection based on VIX/DTE
    """

    # Check daily limits
    if session_stats['trades_today'] >= config['RISK']['max_trades_per_day']:
        return None, None, None, None, None

    daily_loss_limit = session_stats['capital'] * (config['RISK']['daily_loss_limit_pct'] / 100)
    if session_stats['daily_pnl'] <= -daily_loss_limit:
        return None, None, None, None, None

    # NEW: Check signal cooldown (after losing trade)
    cooldown_until = session_stats.get('cooldown_until')
    if cooldown_until and datetime.now() < cooldown_until:
        return None, None, None, None, None

    # Check trading time
    if not is_trading_time_allowed(config):
        return None, None, None, None, None

    if is_lunch_hour(config):
        return None, None, None, None, None

    thresholds = config['MODES'][config['ACTIVE_MODE']]
    filters = config['FILTERS']

    # NEW: Skip signals in dead/low-volatility markets
    min_vix = filters.get('min_vix', 0)
    if min_vix > 0 and india_vix < min_vix:
        return None, None, None, None, None

    atm = data.get('atm_strike', 0)

    # NEW: Get days to expiry for dynamic strike selection
    expiry_str = DataCache.current_expiry or config.get('EXPIRY', '')
    dte = get_days_to_expiry(expiry_str) if expiry_str else 5

    # === OI FLOW DIRECTION CALCULATION ===
    ce_oi_change = data.get('ce_oi_change', 0)
    pe_oi_change = data.get('pe_oi_change', 0)
    total_oi_change = abs(ce_oi_change) + abs(pe_oi_change)

    if total_oi_change > 0:
        oi_flow_ratio = (ce_oi_change - pe_oi_change) / total_oi_change  # -1 to +1
    else:
        oi_flow_ratio = 0

    oi_velocity = data.get('oi_velocity', 0)

    # Get ATM option LTP for OI flow direction (buying vs writing detection)
    option_chain = data.get('option_chain', {})
    atm_ce_ltp = option_chain.get(atm, {}).get('CE', {}).get('ltp', 0)
    atm_pe_ltp = option_chain.get(atm, {}).get('PE', {}).get('ltp', 0)

    # NEW: Track OI flow direction with price direction (buying vs writing)
    oi_direction = get_oi_flow_direction(
        ce_oi_change, pe_oi_change,
        ce_ltp=atm_ce_ltp, pe_ltp=atm_pe_ltp,
        prev_ce_ltp=DataCache.prev_atm_ce_ltp,
        prev_pe_ltp=DataCache.prev_atm_pe_ltp
    )

    # Update previous LTP for next iteration
    if atm_ce_ltp > 0:
        DataCache.prev_atm_ce_ltp = atm_ce_ltp
    if atm_pe_ltp > 0:
        DataCache.prev_atm_pe_ltp = atm_pe_ltp

    DataCache.oi_flow_direction_history.append(oi_direction)
    # Keep only last 10 readings
    if len(DataCache.oi_flow_direction_history) > 10:
        DataCache.oi_flow_direction_history = DataCache.oi_flow_direction_history[-10:]

    # NEW: Track PCR for change calculation
    current_pcr = data.get('pcr', 1.0)
    DataCache.pcr_history.append(current_pcr)
    if len(DataCache.pcr_history) > 20:
        DataCache.pcr_history = DataCache.pcr_history[-20:]
    pcr_change = get_pcr_change(lookback_bars=5)

    # NEW: Check OI persistence
    oi_persistence_bars = thresholds.get('oi_persistence_bars', 2)
    oi_persistent, persistent_direction = check_oi_persistence(oi_persistence_bars)

    # === PATH 1: TRADITIONAL CALL SIGNAL (Buying Flow) ===
    # Full conditions - all must pass
    call_conditions = [
        data.get('alpha_1_call', 0) >= thresholds['alpha_1_call'],
        data.get('alpha_2_call', 0) >= thresholds['alpha_2_call'],
        data.get('pcr', 1.0) < 0.95,  # Call buying pushes PCR down, require low PCR
        data.get('volume_ratio_call', 0) >= thresholds['volume_ratio_threshold'],
        data.get('quality_score_call', 0) >= thresholds['min_quality_score'],
        data.get('confluence_call', 0) >= thresholds['min_confluence'],
        data.get('trend', 'NEUTRAL') in ['UPTREND', 'SIDEWAYS', 'NEUTRAL'],  # Not downtrend
        data.get('rsi', 50) < 75,  # RSI not overbought
    ]

    # === PATH 2: ALTERNATIVE CALL SIGNAL (Writing Flow - PE writing dominant) ===
    # Strong PE writing = bullish (support being built)
    oi_vel_threshold = thresholds.get('oi_change_velocity', 10)  # Config value
    min_oi_writing = filters.get('min_oi_change_writing', 400000)  # Config value
    call_writing_flow_conditions = [
        oi_flow_ratio < -0.35,  # PE writing significantly > CE writing
        oi_velocity >= oi_vel_threshold,  # FIX: Use config threshold
        data.get('alpha_1_call', 0) >= 0.50,  # Minimum alpha check (tightened)
        data.get('quality_score_call', 0) >= 70,  # Quality threshold (tightened from 55)
        data.get('pcr', 1.0) > 1.0,  # At least neutral-bullish PCR
        pe_oi_change > min_oi_writing,  # Significant PE writing (configurable)
        # Writing Flow: Allow any trend (reversal signals)
        True,  # FIX: Removed trend filter for Writing Flow
        # NEW: RSI not overbought
        data.get('rsi', 50) < 75,
    ]

    # NEW: OI persistence filter for CALL - skip if persistent bearish OI flow
    if oi_persistent and persistent_direction == 'BEARISH':
        call_conditions.append(False)  # Block CALL if OI is persistently bearish

    call_signal_triggered = all(call_conditions) or all(call_writing_flow_conditions)
    call_signal_type = "BUYING" if all(call_conditions) else "WRITING" if all(call_writing_flow_conditions) else None

    if call_signal_triggered:
        # UPDATED: Dynamic strike selection based on VIX and DTE
        strike = get_optimal_strike(atm, 'CALL', india_vix, dte)
        option_data = data.get('option_chain', {}).get(strike, {}).get('CE', {})
        ltp = option_data.get('ltp', 0)
        volume = option_data.get('volume', 0)

        if filters['min_option_price'] <= ltp <= filters['max_option_price']:
            if volume >= filters['min_volume']:
                # Check bid-ask spread - only generate signal if spread acceptable
                max_spread_pct = filters.get('max_spread_pct', 3.0)
                spread_ok = check_spread_acceptable(option_data, max_spread_pct)

                if spread_ok and call_signal_type == "BUYING":
                    confidence = min(
                        data.get('alpha_1_call', 0) * 50 +
                        data.get('alpha_2_call', 0) * 30 +
                        min(data.get('trend_strength', 0), 1) * 20,
                        100
                    )
                    return 'CALL', strike, ltp, confidence, "BUYING"
                elif spread_ok and call_signal_type == "WRITING":
                    confidence = min(
                        abs(oi_flow_ratio) * 40 +  # OI flow strength
                        min(oi_velocity / 100, 1) * 35 +  # OI velocity
                        min(data.get('quality_score_call', 0) / 100, 1) * 25,
                        100
                    )
                    return 'CALL', strike, ltp, confidence, "WRITING"

    # === PATH 1: TRADITIONAL PUT SIGNAL (Buying Flow) ===
    # Full conditions - same structure as CALL (symmetric)
    put_conditions = [
        data.get('alpha_1_put', 0) >= thresholds['alpha_1_put'],
        data.get('alpha_2_put', 0) >= thresholds['alpha_2_put'],
        data.get('pcr', 1.0) > 1.05,  # Put buying pushes PCR up, require high PCR
        data.get('volume_ratio_put', 0) >= thresholds['volume_ratio_threshold'],
        data.get('quality_score_put', 0) >= thresholds['min_quality_score'],
        data.get('confluence_put', 0) >= thresholds['min_confluence'],
        data.get('trend', 'NEUTRAL') in ['DOWNTREND', 'SIDEWAYS', 'NEUTRAL'],  # Not uptrend
        data.get('rsi', 50) > 25,  # RSI not oversold
    ]

    # === PATH 2: ALTERNATIVE PUT SIGNAL (Writing Flow - CE writing dominant) ===
    # Strong CE writing = bearish (resistance being built)
    put_writing_flow_conditions = [
        oi_flow_ratio > 0.35,  # CE writing significantly > PE writing
        oi_velocity >= oi_vel_threshold,
        data.get('alpha_1_put', 0) >= 0.50,
        data.get('quality_score_put', 0) >= 70,
        data.get('pcr', 1.0) < 1.0,  # CONTRARIAN: Low PCR for bearish writing flow
        ce_oi_change > min_oi_writing,  # Significant CE writing (configurable)
        True,  # Allow any trend for Writing Flow
        data.get('rsi', 50) > 25,
    ]

    # NEW: OI persistence filter for PUT - skip if persistent bullish OI flow
    if oi_persistent and persistent_direction == 'BULLISH':
        put_conditions.append(False)  # Block PUT if OI is persistently bullish

    put_signal_triggered = all(put_conditions) or all(put_writing_flow_conditions)
    put_signal_type = "BUYING" if all(put_conditions) else "WRITING" if all(put_writing_flow_conditions) else None

    if put_signal_triggered:
        # UPDATED: Dynamic strike selection based on VIX and DTE
        strike = get_optimal_strike(atm, 'PUT', india_vix, dte)
        option_data = data.get('option_chain', {}).get(strike, {}).get('PE', {})
        ltp = option_data.get('ltp', 0)
        volume = option_data.get('volume', 0)

        if filters['min_option_price'] <= ltp <= filters['max_option_price']:
            if volume >= filters['min_volume']:
                # Check bid-ask spread - only generate signal if spread acceptable
                max_spread_pct = filters.get('max_spread_pct', 3.0)
                spread_ok = check_spread_acceptable(option_data, max_spread_pct)

                if spread_ok and put_signal_type == "BUYING":
                    confidence = min(
                        data.get('alpha_1_put', 0) * 50 +
                        data.get('alpha_2_put', 0) * 30 +
                        min(1 - data.get('trend_strength', 0), 1) * 20,
                        100
                    )
                    return 'PUT', strike, ltp, confidence, "BUYING"
                elif spread_ok and put_signal_type == "WRITING":
                    confidence = min(
                        oi_flow_ratio * 40 +  # OI flow strength
                        min(oi_velocity / 100, 1) * 35 +  # OI velocity
                        min(data.get('quality_score_put', 0) / 100, 1) * 25,
                        100
                    )
                    return 'PUT', strike, ltp, confidence, "WRITING"

    return None, None, None, None, None
