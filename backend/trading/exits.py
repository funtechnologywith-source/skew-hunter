"""Exit condition checking and trade exit logic."""

from datetime import datetime
from typing import Optional, Tuple, List


def check_exit_conditions(
    trade, current_time: datetime, config: dict,
    session_mtm: float = 0.0, peak_session_mtm: float = 0.0
) -> Tuple[bool, Optional[str]]:
    """Check if trade should be exited with priority-based exit system.

    EXIT PRIORITY (first trigger wins):
    1. TIME EXIT        -> 3:15 PM mandatory exit
    2. MTM MAX LOSS     -> Portfolio-level max loss hit
    3. MTM PROFIT PROT  -> Protect locked profits at portfolio level
    4. PROFIT TARGET    -> Fixed target hit
    5. PREMIUM STOP     -> Option premium trailing stop (Golden Rule)
    6. MIN HOLD         -> Minimum hold time protection

    Args:
        trade: Active Trade object
        current_time: Current datetime
        config: Configuration dict
        session_mtm: Current session MTM (total P&L including this trade)
        peak_session_mtm: Highest session MTM achieved

    Returns:
        Tuple[bool, str]: (should_exit, exit_reason)
    """

    exit_cfg = config['EXIT']
    min_hold = exit_cfg.get('min_hold_seconds', 30)
    trade_duration = (current_time - trade.entry_time).total_seconds()

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 1: TIME EXIT (3:15 PM mandatory)
    # ═══════════════════════════════════════════════════════════════════════
    time_exit = exit_cfg.get('time_exit', '15:15')
    exit_time = datetime.strptime(time_exit, "%H:%M").time()
    if current_time.time() >= exit_time:
        return True, "time_exit"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 2: MTM MAX LOSS (Portfolio protection)
    # ═══════════════════════════════════════════════════════════════════════
    mtm_max_loss = exit_cfg.get('mtm_max_loss', -5000)
    if session_mtm <= mtm_max_loss:
        return True, "mtm_max_loss"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 3: MTM PROFIT PROTECTION (Lock in portfolio gains)
    # ═══════════════════════════════════════════════════════════════════════
    mtm_protect_trigger = exit_cfg.get('mtm_protect_trigger', 5000)
    mtm_protect_pct = exit_cfg.get('mtm_protect_pct', 0.5)

    if peak_session_mtm >= mtm_protect_trigger:
        # Calculate floor: lock in 50% of peak MTM
        mtm_floor = peak_session_mtm * mtm_protect_pct
        if session_mtm <= mtm_floor:
            return True, "mtm_profit_protection"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 4: PROFIT TARGET (Fixed target - take profits!)
    # ═══════════════════════════════════════════════════════════════════════
    profit_target_pct = exit_cfg.get('profit_target_pct', 20.0)
    if trade.pnl_percent >= profit_target_pct:
        return True, "profit_target"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 5: PREMIUM TRAILING STOP (Golden Rule)
    # ═══════════════════════════════════════════════════════════════════════
    # Check if current LTP is below the trailing stop
    if trade.current_ltp <= trade.current_stop:
        if trade.trailing_active:
            return True, "trailing_stop"
        else:
            return True, "initial_stop"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 6: MIN HOLD PROTECTION
    # ═══════════════════════════════════════════════════════════════════════
    # Don't exit for minor fluctuations within min_hold period
    # (Stops already checked above - they always apply)
    if trade_duration < min_hold:
        return False, None

    return False, None


def detect_reversal(current_data: dict, trade) -> Tuple[bool, List[str]]:
    """Detect potential reversal signals"""
    warnings = []

    try:
        if trade.trade_type == 'CALL':
            # RSI overbought
            rsi = current_data.get('rsi', 50)
            if rsi > 70:
                warnings.append(f"RSI Overbought ({rsi:.1f} > 70)")

            # OI flow reversing
            ce_oi_change = current_data.get('ce_oi_change', 0)
            pe_oi_change = current_data.get('pe_oi_change', 0)
            if ce_oi_change > 5000 and pe_oi_change < 0:
                warnings.append("OI Flow Reversing")

            # Near resistance
            spot = current_data.get('spot', 0)
            resistance = current_data.get('resistance', spot + 100)
            if spot >= resistance * 0.995:
                warnings.append(f"Near Resistance ({spot:.0f} vs {resistance})")

            # Alpha deteriorating
            current_alpha = current_data.get('alpha_1_call', 0)
            if current_alpha < trade.entry_alpha_1 * 0.75:
                warnings.append(f"Alpha Deteriorating ({current_alpha:.2f} vs {trade.entry_alpha_1:.2f})")

            # Below VWAP
            vwap_pos = current_data.get('vwap_position', 'ABOVE')
            if vwap_pos == 'BELOW':
                warnings.append("Crossed Below VWAP")

        else:  # PUT
            rsi = current_data.get('rsi', 50)
            if rsi < 30:
                warnings.append(f"RSI Oversold ({rsi:.1f} < 30)")

            ce_oi_change = current_data.get('ce_oi_change', 0)
            pe_oi_change = current_data.get('pe_oi_change', 0)
            if pe_oi_change > 5000 and ce_oi_change < 0:
                warnings.append("OI Flow Reversing")

            spot = current_data.get('spot', 0)
            support = current_data.get('support', spot - 100)
            if spot <= support * 1.005:
                warnings.append(f"Near Support ({spot:.0f} vs {support})")

            current_alpha = current_data.get('alpha_1_put', 0)
            if current_alpha < trade.entry_alpha_1 * 0.75:
                warnings.append("Alpha Deteriorating")

            vwap_pos = current_data.get('vwap_position', 'BELOW')
            if vwap_pos == 'ABOVE':
                warnings.append("Crossed Above VWAP")

        # Reversal if 2+ warnings
        is_reversal = len(warnings) >= 2
        return is_reversal, warnings

    except Exception:
        return False, []


def exit_trade(trade, exit_price: float, reason: str):
    """Close trade and record exit"""
    trade.exit_price = exit_price
    trade.exit_time = datetime.now()
    trade.exit_reason = reason
    trade.current_ltp = exit_price
