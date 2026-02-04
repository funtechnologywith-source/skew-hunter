"""Trade dataclass and management functions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from trading.risk import get_vix_regime
from utils.cache import DataCache


@dataclass
class Trade:
    """Active trade data structure with VIX-adaptive trailing stops"""
    trade_id: int
    instrument: str
    trade_type: str  # 'CALL' or 'PUT'
    strike: int
    entry_price: float
    entry_time: datetime
    qty: int = 65  # NIFTY lot size

    current_ltp: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = field(default_factory=lambda: float('inf'))

    # VIX-adaptive trailing stop parameters (set at entry, never changed)
    entry_vix: float = 15.0                   # VIX at time of entry
    vix_regime: str = "normal"                # low/normal/elevated/high/extreme
    initial_sl_pct: float = 0.35              # Initial stop loss % (from VIX regime)
    trail_activation_pct: float = 0.25        # Profit % to activate trailing
    trail_distance_pct: float = 0.25          # Trail distance from peak

    # Premium-based trailing stop state (Golden Rule: only moves UP)
    highest_premium: float = 0.0              # Peak premium (only ratchets up)
    trailing_active: bool = False             # True once trail_activation_pct hit
    current_stop: float = 0.0                 # Current stop price (only moves up)

    # Entry metrics
    entry_alpha_1: float = 0.0
    entry_alpha_2: float = 0.0
    entry_pcr: float = 0.0
    entry_confidence: float = 0.0
    entry_quality: float = 0.0
    entry_trend: str = "NEUTRAL"

    # Exit data
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    reversal_detected: bool = False
    signal_path: str = "UNKNOWN"  # "BUYING" or "WRITING"

    # Broker execution fields (for live trading)
    broker_order_id: Optional[str] = None         # Upstox order ID
    instrument_key: Optional[str] = None          # Upstox instrument key
    actual_fill_price: Optional[float] = None     # Real fill price (vs simulated entry_price)
    actual_fill_qty: int = 0                      # Actual filled quantity
    execution_mode: str = "PAPER"                 # "PAPER" or "LIVE"
    exit_order_id: Optional[str] = None
    actual_exit_price: Optional[float] = None

    @property
    def entry_value(self) -> float:
        return self.entry_price * self.qty

    @property
    def current_value(self) -> float:
        return self.current_ltp * self.qty

    @property
    def exit_value(self) -> float:
        if self.exit_price:
            return self.exit_price * self.qty
        return 0

    @property
    def pnl_rupees(self) -> float:
        # Use actual prices if available (live trading), otherwise simulated
        entry = self.actual_fill_price or self.entry_price
        exit_p = self.actual_exit_price or self.exit_price or self.current_ltp
        qty = self.actual_fill_qty or self.qty
        return (exit_p - entry) * qty

    @property
    def pnl_percent(self) -> float:
        # Use actual prices if available (live trading), otherwise simulated
        entry = self.actual_fill_price or self.entry_price
        if entry == 0:
            return 0
        exit_p = self.actual_exit_price or self.exit_price or self.current_ltp
        return ((exit_p - entry) / entry) * 100

    @property
    def duration_seconds(self) -> float:
        end_time = self.exit_time or datetime.now()
        return (end_time - self.entry_time).total_seconds()

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60

    @property
    def mfe_percent(self) -> float:
        """Maximum Favorable Excursion"""
        if self.entry_price == 0:
            return 0
        return ((self.highest_price - self.entry_price) / self.entry_price) * 100

    @property
    def mae_percent(self) -> float:
        """Maximum Adverse Excursion"""
        if self.entry_price == 0 or self.lowest_price == float('inf'):
            return 0
        return ((self.entry_price - self.lowest_price) / self.entry_price) * 100

    def to_dict(self) -> dict:
        """Convert trade to dictionary for JSON serialization."""
        return {
            'trade_id': self.trade_id,
            'instrument': self.instrument,
            'trade_type': self.trade_type,
            'strike': self.strike,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'qty': self.qty,
            'current_ltp': self.current_ltp,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price if self.lowest_price != float('inf') else 0,
            'entry_vix': self.entry_vix,
            'vix_regime': self.vix_regime,
            'initial_sl_pct': self.initial_sl_pct,
            'trail_activation_pct': self.trail_activation_pct,
            'trail_distance_pct': self.trail_distance_pct,
            'highest_premium': self.highest_premium,
            'trailing_active': self.trailing_active,
            'current_stop': self.current_stop,
            'entry_alpha_1': self.entry_alpha_1,
            'entry_alpha_2': self.entry_alpha_2,
            'entry_pcr': self.entry_pcr,
            'entry_confidence': self.entry_confidence,
            'entry_quality': self.entry_quality,
            'entry_trend': self.entry_trend,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'reversal_detected': self.reversal_detected,
            'signal_path': self.signal_path,
            'pnl_rupees': self.pnl_rupees,
            'pnl_percent': self.pnl_percent,
            'duration_seconds': self.duration_seconds,
            'mfe_percent': self.mfe_percent,
            'mae_percent': self.mae_percent,
            'execution_mode': self.execution_mode
        }


def enter_trade(
    signal_type: str, strike: int, ltp: float,
    confidence: float, signal_path: str, data: dict, config: dict, trade_counter: int,
    india_vix: float = 15.0
) -> Trade:
    """Create new trade entry with VIX-adaptive trailing stop.

    VIX Regime determines:
    - Initial stop loss percentage (wider in high VIX)
    - Trail activation threshold (later in high VIX)
    - Trail distance from peak (looser in high VIX)

    These parameters are SET AT ENTRY and never changed mid-trade.
    """

    # Use auto-detected expiry if available, else fall back to config
    expiry_str = DataCache.current_expiry or config.get('EXPIRY', '')
    expiry = expiry_str.replace('-', '')
    if signal_type == 'CALL':
        instrument = f"NIFTY {expiry} {strike} CE"
    else:
        instrument = f"NIFTY {expiry} {strike} PE"

    qty = 65 * config['RISK']['position_size_lots']

    # Get VIX regime parameters (locked at entry time)
    vix_params = get_vix_regime(india_vix, config)

    # Calculate initial stop price based on VIX regime
    # e.g., VIX=18 (Elevated): initial_sl_pct=0.40 -> stop at 60% of entry
    initial_stop = ltp * (1 - vix_params['initial_sl_pct'])

    trade = Trade(
        trade_id=trade_counter,
        instrument=instrument,
        trade_type=signal_type,
        strike=strike,
        entry_price=ltp,
        entry_time=datetime.now(),
        qty=qty,
        current_ltp=ltp,
        highest_price=ltp,
        lowest_price=ltp,

        # VIX-adaptive parameters (set once, never changed)
        entry_vix=india_vix,
        vix_regime=vix_params['regime_name'],
        initial_sl_pct=vix_params['initial_sl_pct'],
        trail_activation_pct=vix_params['trail_activation'],
        trail_distance_pct=vix_params['trail_distance'],

        # Initialize trailing state
        highest_premium=ltp,
        trailing_active=False,
        current_stop=initial_stop,

        # Entry metrics
        entry_alpha_1=data.get(f'alpha_1_{signal_type.lower()}', 0),
        entry_alpha_2=data.get(f'alpha_2_{signal_type.lower()}', 0),
        entry_pcr=data.get('pcr', 1.0),
        entry_confidence=confidence,
        entry_quality=data.get(f'quality_score_{signal_type.lower()}', 0),
        entry_trend=data.get('trend', 'NEUTRAL'),
        signal_path=signal_path
    )

    return trade


def update_trade(trade: Trade, current_ltp: float, atr: float, config: dict):
    """Update trade with premium-based trailing stop.

    THE GOLDEN RULE: Trailing stop ONLY moves UP (for long positions), NEVER backwards.

    Flow:
    1. Track highest premium (only ratchets up on new highs)
    2. Calculate current profit percentage
    3. Check if trailing should activate (profit >= trail_activation_pct)
    4. Calculate potential new stop based on highest premium
    5. ONLY update stop if new value is HIGHER than current stop

    Example (Normal VIX regime - 25% activation, 25% trail distance):
        Entry: Rs100, Stop: Rs65 (35% SL)
        LTP rises to Rs130 (30% profit) -> Trail activates
        New stop = Rs130 * 0.75 = Rs97.50
        Rs97.50 > Rs65? YES -> Stop = Rs97.50

        LTP drops to Rs120
        Highest still Rs130, potential stop = Rs97.50
        Rs97.50 > Rs97.50? NO -> Stop stays at Rs97.50 (GOLDEN RULE)

        LTP rises to Rs150 (50% profit)
        New stop = Rs150 * 0.75 = Rs112.50
        Rs112.50 > Rs97.50? YES -> Stop = Rs112.50
    """

    # Update current LTP
    trade.current_ltp = current_ltp

    # Track highest/lowest for MFE/MAE stats
    trade.highest_price = max(trade.highest_price, current_ltp)
    trade.lowest_price = min(trade.lowest_price, current_ltp)

    # GOLDEN RULE: Track highest premium (only ratchets UP)
    if current_ltp > trade.highest_premium:
        trade.highest_premium = current_ltp

    # Calculate current profit percentage
    if trade.entry_price > 0:
        profit_pct = (current_ltp - trade.entry_price) / trade.entry_price
    else:
        profit_pct = 0

    # Check if trailing should activate
    if profit_pct >= trade.trail_activation_pct:
        trade.trailing_active = True

    # Calculate potential new stop
    if trade.trailing_active:
        # Trail from highest premium
        potential_stop = trade.highest_premium * (1 - trade.trail_distance_pct)
    else:
        # Initial stop based on entry price
        potential_stop = trade.entry_price * (1 - trade.initial_sl_pct)

    # GOLDEN RULE: Stop can ONLY move UP, never down
    if potential_stop > trade.current_stop:
        trade.current_stop = potential_stop
