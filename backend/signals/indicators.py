"""Technical indicators for signal generation."""

import numpy as np
from typing import List, Tuple


def get_atm_strike(spot: float, step: int = 50) -> int:
    """Get ATM strike price"""
    return round(spot / step) * step


def calculate_weighted_pcr(option_chain: dict, atm: int) -> float:
    """Calculate ATM-weighted Put-Call Ratio"""
    try:
        weights = {
            atm: 1.0,
            atm + 50: 0.8, atm - 50: 0.8,
            atm + 100: 0.6, atm - 100: 0.6,
            atm + 150: 0.4, atm - 150: 0.4,
            atm + 200: 0.2, atm - 200: 0.2
        }

        weighted_pe_oi = 0
        weighted_ce_oi = 0

        for strike, weight in weights.items():
            if strike in option_chain:
                pe_oi = option_chain[strike].get('PE', {}).get('oi', 0)
                ce_oi = option_chain[strike].get('CE', {}).get('oi', 0)
                weighted_pe_oi += pe_oi * weight
                weighted_ce_oi += ce_oi * weight

        if weighted_ce_oi == 0:
            return 1.0

        return weighted_pe_oi / weighted_ce_oi

    except Exception:
        return 1.0


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index using Wilder's smoothing method"""
    if len(prices) < period + 1:
        return 50.0

    try:
        prices_arr = np.array(prices)
        deltas = np.diff(prices_arr)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # FIX: Use Wilder's smoothing (EMA-like) instead of simple mean
        # First average is SMA
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        # Apply Wilder's smoothing for remaining values
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    except Exception:
        return 50.0


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate Average True Range as percentage"""
    if len(highs) < period + 1:
        return 1.0

    try:
        tr_list = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)

        atr = np.mean(tr_list[-period:])
        atr_pct = (atr / closes[-1]) * 100

        return float(atr_pct)

    except Exception:
        return 1.0


def calculate_trend_strength(prices: List[float], period: int = 20) -> float:
    """Calculate trend strength (0.0 to 1.0)"""
    if len(prices) < period:
        return 0.5

    try:
        recent = prices[-period:]

        # Linear regression slope
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]

        # Normalize by price level
        normalized_slope = slope / np.mean(recent)

        # Convert to 0-1 range using sigmoid
        strength = 1 / (1 + np.exp(-normalized_slope * 1000))

        return float(strength)

    except Exception:
        return 0.5


def calculate_vwap_position(spot: float, prices: List[float]) -> Tuple[str, float]:
    """Calculate position relative to moving average (proxy for VWAP without volume)

    NOTE: True VWAP requires volume data. This uses SMA as approximation.
    Threshold widened to 0.3% to reduce false signals.
    """
    if len(prices) < 5:
        return "NEUTRAL", 0.0

    try:
        # SMA approximation (true VWAP would need volume weighting)
        sma = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)

        diff_pct = ((spot - sma) / sma) * 100

        # FIX: Widened threshold from 0.1% to 0.3% to reduce noise
        if diff_pct > 0.3:
            return "ABOVE", diff_pct
        elif diff_pct < -0.3:
            return "BELOW", diff_pct
        return "AT", diff_pct

    except Exception:
        return "NEUTRAL", 0.0


def find_support_resistance(option_chain: dict, atm: int) -> dict:
    """Find support and resistance levels from OI"""
    try:
        # Look at strikes from ATM-500 to ATM+500
        strikes = sorted([s for s in option_chain.keys() if atm - 500 <= s <= atm + 500])

        max_pe_oi = 0
        max_ce_oi = 0
        support = atm - 100
        resistance = atm + 100

        for strike in strikes:
            pe_oi = option_chain[strike].get('PE', {}).get('oi', 0)
            ce_oi = option_chain[strike].get('CE', {}).get('oi', 0)

            if pe_oi > max_pe_oi and strike <= atm:
                max_pe_oi = pe_oi
                support = strike

            if ce_oi > max_ce_oi and strike >= atm:
                max_ce_oi = ce_oi
                resistance = strike

        return {
            'support': support,
            'support_oi': max_pe_oi,
            'resistance': resistance,
            'resistance_oi': max_ce_oi
        }

    except Exception:
        return {
            'support': atm - 100,
            'support_oi': 0,
            'resistance': atm + 100,
            'resistance_oi': 0
        }


def calculate_oi_changes(option_chain: dict, atm: int) -> dict:
    """Calculate total OI changes for CE and PE"""
    try:
        strikes = [atm - 100, atm - 50, atm, atm + 50, atm + 100]

        ce_oi_change = sum(
            option_chain.get(s, {}).get('CE', {}).get('oi_change', 0)
            for s in strikes if s in option_chain
        )

        pe_oi_change = sum(
            option_chain.get(s, {}).get('PE', {}).get('oi_change', 0)
            for s in strikes if s in option_chain
        )

        return {
            'ce_oi_change': ce_oi_change,
            'pe_oi_change': pe_oi_change
        }

    except Exception:
        return {'ce_oi_change': 0, 'pe_oi_change': 0}


def calculate_volume_ratio(option_chain: dict, atm: int, signal_type: str) -> float:
    """Calculate volume ratio for signal type (OTM vs ITM of SAME option type)"""
    try:
        if signal_type == 'CALL':
            # For CALL: Compare CE volume at OTM (above ATM) vs ITM (below ATM)
            otm_strikes = [atm + 50, atm + 100, atm + 150]
            itm_strikes = [atm - 50, atm - 100, atm - 150]

            otm_volume = sum(
                option_chain.get(s, {}).get('CE', {}).get('volume', 0)
                for s in otm_strikes if s in option_chain
            )
            itm_volume = sum(
                option_chain.get(s, {}).get('CE', {}).get('volume', 0)  # FIX: Was PE, now CE
                for s in itm_strikes if s in option_chain
            )
        else:
            # For PUT: Compare PE volume at OTM (below ATM) vs ITM (above ATM)
            otm_strikes = [atm - 50, atm - 100, atm - 150]
            itm_strikes = [atm + 50, atm + 100, atm + 150]

            otm_volume = sum(
                option_chain.get(s, {}).get('PE', {}).get('volume', 0)
                for s in otm_strikes if s in option_chain
            )
            itm_volume = sum(
                option_chain.get(s, {}).get('PE', {}).get('volume', 0)  # FIX: Was CE, now PE
                for s in itm_strikes if s in option_chain
            )

        return otm_volume / max(itm_volume, 1)

    except Exception:
        return 1.0


def calculate_quality_score(
    alpha_1: float, alpha_2: float, volume_ratio: float,
    oi_velocity: float, trend_strength: float
) -> float:
    """Calculate overall quality score (0-100)"""
    try:
        # Weighted combination
        score = (
            alpha_1 * 25 +           # 25% weight
            alpha_2 * 25 +           # 25% weight
            min(volume_ratio / 3, 1) * 20 +  # 20% weight
            min(oi_velocity / 15, 1) * 15 +  # 15% weight
            trend_strength * 15      # 15% weight
        )

        return min(100, max(0, score))

    except Exception:
        return 50.0


def count_confluence(data: dict, thresholds: dict, signal_type: str) -> Tuple[int, List[str]]:
    """Count confluence factors and return list of met conditions"""
    met_conditions = []

    try:
        if signal_type == 'CALL':
            # Alpha 1 check
            if data.get('alpha_1_call', 0) >= thresholds.get('alpha_1_call', 0.8):
                met_conditions.append("Alpha1")

            # Alpha 2 check
            if data.get('alpha_2_call', 0) >= thresholds.get('alpha_2_call', 0.8):
                met_conditions.append("Alpha2")

            # PCR check - CONTRARIAN: High PCR = fear = bullish
            if data.get('pcr', 1.0) > 1.1:
                met_conditions.append("PCR")

            # Volume ratio
            if data.get('volume_ratio', 0) >= thresholds.get('volume_ratio_threshold', 2.3):
                met_conditions.append("Volume")

            # Trend strength
            if data.get('trend_strength', 0) >= 0.6:
                met_conditions.append("Trend")

            # OI velocity
            if data.get('oi_velocity', 0) >= thresholds.get('oi_change_velocity', 10):
                met_conditions.append("OI_Vel")

        else:  # PUT
            # FIX: Use direct threshold comparison (same as CALL)
            if data.get('alpha_1_put', 0) >= thresholds.get('alpha_1_put', 0.8):
                met_conditions.append("Alpha1")

            if data.get('alpha_2_put', 0) >= thresholds.get('alpha_2_put', 0.8):
                met_conditions.append("Alpha2")

            # PCR bearish OR OI flow bearish (CE writing > PE writing)
            ce_oi_chg = data.get('ce_oi_change', 0)
            pe_oi_chg = data.get('pe_oi_change', 0)
            if data.get('pcr', 1.0) < 0.9:
                met_conditions.append("PCR")
            elif ce_oi_chg > pe_oi_chg and ce_oi_chg > 0:
                met_conditions.append("OI_Flow")  # Bearish OI flow

            if data.get('volume_ratio', 0) >= thresholds.get('volume_ratio_threshold', 2.3):
                met_conditions.append("Volume")

            if data.get('trend_strength', 0) <= 0.4:
                met_conditions.append("Trend")

            if data.get('oi_velocity', 0) >= thresholds.get('oi_change_velocity', 10):
                met_conditions.append("OI_Vel")

        return len(met_conditions), met_conditions

    except Exception:
        return 0, []
