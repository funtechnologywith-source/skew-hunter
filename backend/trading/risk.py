"""VIX regime and risk management functions."""


def get_vix_regime(india_vix: float, config: dict) -> dict:
    """Get VIX-based regime parameters for trailing stops.

    Returns dict with:
    - regime_name: str (low/normal/elevated/high/extreme)
    - initial_sl_pct: float (0.30-0.50)
    - trail_activation: float (0.20-0.40)
    - trail_distance: float (0.20-0.40)
    """
    vix_regimes = config.get('EXIT', {}).get('vix_regimes', {})

    # Default to normal regime if config missing
    if not vix_regimes:
        return {
            'regime_name': 'normal',
            'initial_sl_pct': 0.35,
            'trail_activation': 0.25,
            'trail_distance': 0.25
        }

    # Check regimes in order: low -> normal -> elevated -> high -> extreme
    regime_order = ['low', 'normal', 'elevated', 'high', 'extreme']

    for regime_name in regime_order:
        regime = vix_regimes.get(regime_name, {})
        max_vix = regime.get('max_vix', 100)

        if india_vix <= max_vix:
            return {
                'regime_name': regime_name,
                'initial_sl_pct': regime.get('initial_sl_pct', 0.35),
                'trail_activation': regime.get('trail_activation', 0.25),
                'trail_distance': regime.get('trail_distance', 0.25)
            }

    # Fallback to extreme if VIX is very high
    extreme = vix_regimes.get('extreme', {})
    return {
        'regime_name': 'extreme',
        'initial_sl_pct': extreme.get('initial_sl_pct', 0.50),
        'trail_activation': extreme.get('trail_activation', 0.40),
        'trail_distance': extreme.get('trail_distance', 0.40)
    }
