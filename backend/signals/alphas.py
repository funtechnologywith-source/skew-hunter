"""Alpha 1 and Alpha 2 calculations for signal generation."""

import numpy as np


def calculate_alpha_1_call(option_chain: dict, atm: int) -> float:
    """Calculate Alpha 1 (Volume/OI Flow) for CALL signal.

    FIXED: Now uses symmetric OTM comparison instead of flawed OTM vs "ITM" logic.
    Measures bullish activity:
    - OTM CE volume/OI increase = call buying = bullish directional bets
    - OTM PE OI increase = put writing = support building (also bullish)

    Normalization uses ATM total OI instead of magic number 100000.
    """
    try:
        # OTM call strikes (upside bets)
        otm_ce_strikes = [atm + 50, atm + 100, atm + 150]
        # OTM put strikes (downside protection / support)
        otm_pe_strikes = [atm - 50, atm - 100, atm - 150]

        # OTM CE buying = bullish directional bets
        otm_ce_volume = sum(
            option_chain.get(s, {}).get('CE', {}).get('volume', 0)
            for s in otm_ce_strikes if s in option_chain
        )
        otm_ce_oi_change = sum(
            option_chain.get(s, {}).get('CE', {}).get('oi_change', 0)
            for s in otm_ce_strikes if s in option_chain
        )

        # OTM PE writing (positive OI change) = support building (bullish)
        otm_pe_oi_change = sum(
            option_chain.get(s, {}).get('PE', {}).get('oi_change', 0)
            for s in otm_pe_strikes if s in option_chain
        )

        # Dynamic normalization based on ATM total OI (not magic number)
        atm_ce_oi = option_chain.get(atm, {}).get('CE', {}).get('oi', 0)
        atm_pe_oi = option_chain.get(atm, {}).get('PE', {}).get('oi', 0)
        atm_total_oi = atm_ce_oi + atm_pe_oi
        norm_factor = max(atm_total_oi * 0.01, 10000)  # 1% of ATM OI, min 10k

        # Volume score (50% weight) - compare OTM CE volume against average
        avg_volume = sum(
            option_chain.get(s, {}).get('CE', {}).get('volume', 0)
            for s in [atm - 50, atm, atm + 50] if s in option_chain
        ) / 3
        volume_ratio = otm_ce_volume / max(avg_volume, 1)
        volume_score = min(volume_ratio / 3.0, 1.0) * 0.5

        # OI flow score (50% weight)
        # Bullish: CE OI increasing (buying) OR PE OI increasing (writing = support)
        # FIX: Symmetric handling - only count positive OI changes for both
        bullish_flow = max(0, otm_ce_oi_change) + max(0, otm_pe_oi_change)
        oi_score = min(bullish_flow / norm_factor, 1.0) * 0.5

        alpha_1 = volume_score + oi_score
        return max(0.0, min(1.0, alpha_1))

    except Exception:
        return 0.5


def calculate_alpha_1_put(option_chain: dict, atm: int) -> float:
    """Calculate Alpha 1 (Volume/OI Flow) for PUT signal.

    FIXED: Now uses symmetric OTM comparison instead of flawed OTM vs "ITM" logic.
    Measures bearish activity:
    - OTM PE volume/OI increase = put buying = bearish directional bets
    - OTM CE OI increase = call writing = resistance building (also bearish)

    Normalization uses ATM total OI instead of magic number 100000.
    """
    try:
        # OTM put strikes (downside bets)
        otm_pe_strikes = [atm - 50, atm - 100, atm - 150]
        # OTM call strikes (resistance / upside cap)
        otm_ce_strikes = [atm + 50, atm + 100, atm + 150]

        # OTM PE buying = bearish directional bets
        otm_pe_volume = sum(
            option_chain.get(s, {}).get('PE', {}).get('volume', 0)
            for s in otm_pe_strikes if s in option_chain
        )
        otm_pe_oi_change = sum(
            option_chain.get(s, {}).get('PE', {}).get('oi_change', 0)
            for s in otm_pe_strikes if s in option_chain
        )

        # OTM CE writing (positive OI change) = resistance building (bearish)
        otm_ce_oi_change = sum(
            option_chain.get(s, {}).get('CE', {}).get('oi_change', 0)
            for s in otm_ce_strikes if s in option_chain
        )

        # Dynamic normalization based on ATM total OI (not magic number)
        atm_ce_oi = option_chain.get(atm, {}).get('CE', {}).get('oi', 0)
        atm_pe_oi = option_chain.get(atm, {}).get('PE', {}).get('oi', 0)
        atm_total_oi = atm_ce_oi + atm_pe_oi
        norm_factor = max(atm_total_oi * 0.01, 10000)  # 1% of ATM OI, min 10k

        # Volume score (50% weight) - compare OTM PE volume against average
        avg_volume = sum(
            option_chain.get(s, {}).get('PE', {}).get('volume', 0)
            for s in [atm - 50, atm, atm + 50] if s in option_chain
        ) / 3
        volume_ratio = otm_pe_volume / max(avg_volume, 1)
        volume_score = min(volume_ratio / 3.0, 1.0) * 0.5

        # OI flow score (50% weight)
        # Bearish: PE OI increasing (buying) OR CE OI increasing (writing = resistance)
        # Only count CE writing (positive OI change), not unwinding
        bearish_flow = otm_pe_oi_change + max(0, otm_ce_oi_change)
        oi_score = min(max(0, bearish_flow) / norm_factor, 1.0) * 0.5

        alpha_1 = volume_score + oi_score
        return max(0.0, min(1.0, alpha_1))

    except Exception:
        return 0.5


def calculate_alpha_2_call(option_chain: dict, atm: int) -> float:
    """Calculate Alpha 2 (IV Skew) for CALL signal"""
    try:
        # Get IVs
        otm_call_strikes = [atm + 50, atm + 100, atm + 150]
        otm_put_strikes = [atm - 50, atm - 100, atm - 150]

        otm_call_ivs = [
            option_chain.get(s, {}).get('CE', {}).get('iv', 0)
            for s in otm_call_strikes if s in option_chain
        ]

        otm_put_ivs = [
            option_chain.get(s, {}).get('PE', {}).get('iv', 0)
            for s in otm_put_strikes if s in option_chain
        ]

        atm_iv = option_chain.get(atm, {}).get('CE', {}).get('iv', 15)

        # Filter out zero IVs
        otm_call_ivs = [iv for iv in otm_call_ivs if iv > 0]
        otm_put_ivs = [iv for iv in otm_put_ivs if iv > 0]

        if not otm_call_ivs or not otm_put_ivs or atm_iv <= 0:
            return 0.5

        avg_otm_call_iv = np.mean(otm_call_ivs)
        avg_otm_put_iv = np.mean(otm_put_ivs)

        # IV skew (positive = calls more expensive = bearish expectation reducing)
        iv_skew = (avg_otm_call_iv - avg_otm_put_iv) / atm_iv

        # Sigmoid normalization
        alpha_2 = 1 / (1 + np.exp(-iv_skew * 10))
        return float(alpha_2)

    except Exception:
        return 0.5


def calculate_alpha_2_put(option_chain: dict, atm: int) -> float:
    """Calculate Alpha 2 (IV Skew) for PUT signal"""
    try:
        otm_call_strikes = [atm + 50, atm + 100, atm + 150]
        otm_put_strikes = [atm - 50, atm - 100, atm - 150]

        otm_call_ivs = [
            option_chain.get(s, {}).get('CE', {}).get('iv', 0)
            for s in otm_call_strikes if s in option_chain
        ]

        otm_put_ivs = [
            option_chain.get(s, {}).get('PE', {}).get('iv', 0)
            for s in otm_put_strikes if s in option_chain
        ]

        atm_iv = option_chain.get(atm, {}).get('PE', {}).get('iv', 15)

        otm_call_ivs = [iv for iv in otm_call_ivs if iv > 0]
        otm_put_ivs = [iv for iv in otm_put_ivs if iv > 0]

        if not otm_call_ivs or not otm_put_ivs or atm_iv <= 0:
            return 0.5

        avg_otm_call_iv = np.mean(otm_call_ivs)
        avg_otm_put_iv = np.mean(otm_put_ivs)

        # For puts, higher put IV relative to call IV is bullish for puts
        iv_skew = (avg_otm_put_iv - avg_otm_call_iv) / atm_iv

        alpha_2 = 1 / (1 + np.exp(-iv_skew * 10))
        return float(alpha_2)

    except Exception:
        return 0.5
