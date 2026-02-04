"""Pydantic models for API request/response validation."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class TokenValidationRequest(BaseModel):
    """Request to validate Upstox token"""
    token: str


class DhanValidationRequest(BaseModel):
    """Request to validate DHAN credentials"""
    access_token: str
    client_id: str
    expiry: str  # YYYY-MM-DD format for loading security IDs


class EngineStartRequest(BaseModel):
    """Request to start the trading engine"""
    token: str
    capital: float = 100000.0
    execution_mode: str = "OFF"  # OFF, PAPER, LIVE
    broker: str = "UPSTOX"  # UPSTOX or DHAN
    dhan_token: Optional[str] = None
    dhan_client_id: Optional[str] = None


class ModeChangeRequest(BaseModel):
    """Request to change trading mode"""
    mode: str  # STRICT, BALANCED, RELAXED


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    config: Dict[str, Any]


class OrphanActionRequest(BaseModel):
    """Request to handle orphaned position"""
    action: str  # RECOVER, EXIT, IGNORE
    trade_data: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class TokenValidationResponse(BaseModel):
    """Response from token validation"""
    valid: bool
    user_name: Optional[str] = None
    message: str


class EngineStatusResponse(BaseModel):
    """Response with engine status"""
    running: bool
    mode: str
    execution_mode: str
    broker: str
    trades_today: int
    daily_pnl: float


class TradeResponse(BaseModel):
    """Trade data for API responses"""
    trade_id: int
    instrument: str
    trade_type: str
    strike: int
    entry_price: float
    entry_time: str
    qty: int
    current_ltp: float
    pnl_rupees: float
    pnl_percent: float
    duration_seconds: float
    trailing_active: bool
    current_stop: float
    vix_regime: str
    signal_path: str
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_reason: Optional[str] = None


class SessionStatsResponse(BaseModel):
    """Session statistics"""
    trades_today: int
    daily_pnl: float
    peak_session_mtm: float
    max_trades_reached: bool
    capital: float
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None


class OrphanCheckResponse(BaseModel):
    """Response from orphan position check"""
    has_orphan: bool
    trade_data: Optional[Dict[str, Any]] = None
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket State Model
# ═══════════════════════════════════════════════════════════════════════════════

class EngineState(BaseModel):
    """Complete engine state for WebSocket broadcast"""
    # Engine status
    status: str  # SCANNING, TRADING, STOPPED, ERROR
    mode: str  # STRICT, BALANCED, RELAXED
    execution_mode: str  # OFF, PAPER, LIVE
    broker: str  # UPSTOX, DHAN

    # Market data
    spot_price: float
    spot_change_pct: float
    india_vix: float
    atm_strike: int
    data_live: bool

    # Session stats
    trades_today: int
    max_trades_per_day: int
    daily_pnl: float
    peak_session_mtm: float
    capital: float

    # Indicators
    pcr: float
    pcr_trend: str  # RISING, FALLING, STABLE
    ce_oi_change: int
    pe_oi_change: int
    oi_flow_ratio: float
    oi_flow_direction: str  # BULLISH, BEARISH, NEUTRAL
    oi_velocity: float

    # Alpha values
    alpha_1_call: float
    alpha_1_put: float
    alpha_2_call: float
    alpha_2_put: float

    # Quality scores
    quality_score_call: float
    quality_score_put: float
    confluence_call: int
    confluence_put: int
    confluence_conditions_call: List[str]
    confluence_conditions_put: List[str]

    # Trend
    trend: str  # UPTREND, DOWNTREND, SIDEWAYS, NEUTRAL
    trend_strength: float
    rsi: float
    atr_pct: float

    # Support/Resistance
    support: int
    resistance: int

    # Volume ratios
    volume_ratio_call: float
    volume_ratio_put: float

    # Active trade (if any)
    active_trade: Optional[Dict[str, Any]] = None
    reversal_warnings: List[str] = []

    # Timing
    timestamp: str
    market_status: str  # OPEN, CLOSED, PRE-MARKET
    next_action: str
    trading_allowed: bool
    is_lunch_hour: bool

    # Thresholds (for UI comparison)
    thresholds: Dict[str, Any]
