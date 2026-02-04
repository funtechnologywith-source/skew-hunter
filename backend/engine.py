"""Async engine wrapper for Skew Hunter trading logic."""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from brokers import UpstoxAPI, DhanAPI
from execution import OrderExecutor
from signals import (
    calculate_alpha_1_call, calculate_alpha_1_put,
    calculate_alpha_2_call, calculate_alpha_2_put,
    calculate_weighted_pcr, calculate_rsi, calculate_atr,
    calculate_trend_strength, calculate_vwap_position,
    find_support_resistance, calculate_oi_changes,
    calculate_volume_ratio, calculate_quality_score,
    count_confluence, get_atm_strike, check_entry_signal
)
from trading import (
    Trade, enter_trade, update_trade,
    check_exit_conditions, detect_reversal, exit_trade,
    get_vix_regime
)
from utils import (
    DataCache, fetch_spot_price, fetch_option_chain,
    is_market_open, is_trading_time_allowed, is_lunch_hour,
    get_market_status, load_session_state, save_session_state
)
from signals.indicators import get_atm_strike
from utils.telegram import (
    send_telegram_alert, send_telegram_exit_alert,
    configure_telegram
)
from websocket_manager import WebSocketManager


class SkewHunterEngine:
    """Async trading engine that broadcasts state via WebSocket."""

    def __init__(
        self,
        config: dict,
        upstox_api: UpstoxAPI,
        capital: float = 100000.0,
        execution_mode: str = "OFF",
        broker: str = "UPSTOX",
        dhan_api: Optional[DhanAPI] = None,
        ws_manager: Optional[WebSocketManager] = None
    ):
        self.config = config
        self.upstox_api = upstox_api
        self.capital = capital
        self.execution_mode = execution_mode
        self.broker = broker
        self.dhan_api = dhan_api
        self.ws_manager = ws_manager

        # Engine state
        self.running = False
        self.active_trade: Optional[Trade] = None
        self.closed_trades: List[Trade] = []
        self.exit_requested: Optional[str] = None

        # Session stats
        self.session_stats = load_session_state()
        self.session_stats['capital'] = capital

        # Trade counter
        self.trade_counter = self.session_stats.get('last_trade_id', 0)

        # Order executor
        if execution_mode != "OFF":
            broker_api = dhan_api if broker == "DHAN" else upstox_api
            self.executor = OrderExecutor(broker_api, config, broker)
            # Enable execution based on mode
            self.executor.enabled = True
            self.executor.paper_mode = execution_mode == "PAPER"
        else:
            self.executor = None

        # Data state
        self.spot_price = 0.0
        self.spot_change_pct = 0.0
        self.india_vix = 15.0
        self.option_chain: Optional[dict] = None
        self.indicators: dict = {}

        # Refresh interval - optimized for low latency
        # LIVE: 0.3s, PAPER: 1s, OFF: 1.5s
        if execution_mode == "LIVE":
            self.refresh_interval = 0.3
        elif execution_mode == "PAPER":
            self.refresh_interval = 1.0
        else:
            self.refresh_interval = 1.5

        # Configure Telegram if set
        telegram_config = config.get('TELEGRAM', {})
        if telegram_config.get('enabled'):
            configure_telegram(
                telegram_config.get('bot_token', ''),
                telegram_config.get('chat_ids', []),
                True
            )

        # Auto-detect expiry
        expiry = upstox_api.get_current_weekly_expiry(config.get('EXPIRY', ''))
        DataCache.current_expiry = expiry

    async def run(self):
        """Main trading loop as async task."""
        self.running = True
        print(f"Engine started - Mode: {self.config['ACTIVE_MODE']}, Execution: {self.execution_mode}")

        while self.running:
            try:
                await self._loop_iteration()
                await asyncio.sleep(self.refresh_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Engine error: {e}")
                await asyncio.sleep(5)  # Wait before retry

        print("Engine stopped")

    async def _loop_iteration(self):
        """Single iteration of the trading loop."""
        # Fetch market data
        await self._fetch_data()

        # Calculate indicators
        self._calculate_indicators()

        # Check for exits if in trade
        if self.active_trade:
            await self._manage_trade()
        else:
            # Check for entry signals
            await self._check_signals()

        # Broadcast state
        await self._broadcast_state()

        # Save session state periodically
        self._save_session()

    async def _fetch_data(self):
        """Fetch market data from API."""
        # Run blocking API calls in thread pool
        loop = asyncio.get_event_loop()

        # Fetch spot price
        spot_data = await loop.run_in_executor(
            None, fetch_spot_price, self.upstox_api
        )
        if spot_data['price']:
            self.spot_price = spot_data['price']
            self.spot_change_pct = spot_data.get('change_pct', 0)

        # Fetch VIX
        vix = await loop.run_in_executor(
            None, self.upstox_api.get_india_vix
        )
        if vix:
            self.india_vix = vix

        # Fetch option chain
        expiry = DataCache.current_expiry or self.config.get('EXPIRY', '')
        chain = await loop.run_in_executor(
            None, fetch_option_chain, self.upstox_api, expiry
        )
        if chain:
            self.option_chain = chain

        # Fetch candles for ATR
        candles = await loop.run_in_executor(
            None, self.upstox_api.get_intraday_candles, "5minute"
        )
        if candles:
            DataCache.high_history = [c['high'] for c in candles[-50:]]
            DataCache.low_history = [c['low'] for c in candles[-50:]]
            DataCache.close_history = [c['close'] for c in candles[-50:]]

        # Update VIX and ATM in cache
        DataCache.last_vix = self.india_vix
        if self.spot_price > 0:
            DataCache.last_atm_strike = get_atm_strike(self.spot_price)

        # Save cache to disk periodically
        DataCache.save_to_disk()

    def _calculate_indicators(self):
        """Calculate all technical indicators."""
        if not self.option_chain or not self.spot_price:
            return

        atm = get_atm_strike(self.spot_price)

        # Alpha values
        alpha_1_call = calculate_alpha_1_call(self.option_chain, atm)
        alpha_1_put = calculate_alpha_1_put(self.option_chain, atm)
        alpha_2_call = calculate_alpha_2_call(self.option_chain, atm)
        alpha_2_put = calculate_alpha_2_put(self.option_chain, atm)

        # PCR
        pcr = calculate_weighted_pcr(self.option_chain, atm)

        # OI changes
        oi_changes = calculate_oi_changes(self.option_chain, atm)
        ce_oi_change = oi_changes['ce_oi_change']
        pe_oi_change = oi_changes['pe_oi_change']

        # OI flow ratio
        total_oi = abs(ce_oi_change) + abs(pe_oi_change)
        oi_flow_ratio = (ce_oi_change - pe_oi_change) / total_oi if total_oi > 0 else 0

        # OI velocity
        oi_velocity = total_oi / 10000 if total_oi > 0 else 0

        # Volume ratios
        volume_ratio_call = calculate_volume_ratio(self.option_chain, atm, 'CALL')
        volume_ratio_put = calculate_volume_ratio(self.option_chain, atm, 'PUT')

        # RSI from price history
        rsi = calculate_rsi(DataCache.price_history) if DataCache.price_history else 50.0

        # ATR
        atr_pct = 0.0
        if DataCache.high_history and DataCache.low_history and DataCache.close_history:
            atr_pct = calculate_atr(
                DataCache.high_history,
                DataCache.low_history,
                DataCache.close_history
            )

        # Trend
        trend_strength = calculate_trend_strength(DataCache.price_history) if DataCache.price_history else 0.5
        if trend_strength > 0.6:
            trend = "UPTREND"
        elif trend_strength < 0.4:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        # Support/Resistance
        sr = find_support_resistance(self.option_chain, atm)

        # Quality scores
        thresholds = self.config['MODES'][self.config['ACTIVE_MODE']]

        quality_call = calculate_quality_score(
            alpha_1_call, alpha_2_call, volume_ratio_call, oi_velocity, trend_strength
        )
        quality_put = calculate_quality_score(
            alpha_1_put, alpha_2_put, volume_ratio_put, oi_velocity, trend_strength
        )

        # Build data dict for confluence
        data = {
            'alpha_1_call': alpha_1_call,
            'alpha_1_put': alpha_1_put,
            'alpha_2_call': alpha_2_call,
            'alpha_2_put': alpha_2_put,
            'pcr': pcr,
            'volume_ratio': volume_ratio_call,
            'trend_strength': trend_strength,
            'oi_velocity': oi_velocity,
            'ce_oi_change': ce_oi_change,
            'pe_oi_change': pe_oi_change
        }

        confluence_call, conditions_call = count_confluence(data, thresholds, 'CALL')
        confluence_put, conditions_put = count_confluence(data, thresholds, 'PUT')

        # PCR trend
        if len(DataCache.pcr_history) >= 5:
            pcr_change = pcr - DataCache.pcr_history[-5] if len(DataCache.pcr_history) >= 5 else 0
            if pcr_change > 0.03:
                pcr_trend = "RISING"
            elif pcr_change < -0.03:
                pcr_trend = "FALLING"
            else:
                pcr_trend = "STABLE"
        else:
            pcr_trend = "STABLE"

        # OI flow direction
        oi_direction = DataCache.oi_flow_direction_history[-1] if DataCache.oi_flow_direction_history else "NEUTRAL"

        # Store all indicators
        self.indicators = {
            'atm_strike': atm,
            'alpha_1_call': alpha_1_call,
            'alpha_1_put': alpha_1_put,
            'alpha_2_call': alpha_2_call,
            'alpha_2_put': alpha_2_put,
            'pcr': pcr,
            'pcr_trend': pcr_trend,
            'ce_oi_change': ce_oi_change,
            'pe_oi_change': pe_oi_change,
            'oi_flow_ratio': oi_flow_ratio,
            'oi_flow_direction': oi_direction,
            'oi_velocity': oi_velocity,
            'volume_ratio_call': volume_ratio_call,
            'volume_ratio_put': volume_ratio_put,
            'rsi': rsi,
            'atr_pct': atr_pct,
            'trend': trend,
            'trend_strength': trend_strength,
            'support': sr['support'],
            'resistance': sr['resistance'],
            'quality_score_call': quality_call,
            'quality_score_put': quality_put,
            'confluence_call': confluence_call,
            'confluence_put': confluence_put,
            'confluence_conditions_call': conditions_call,
            'confluence_conditions_put': conditions_put,
            'option_chain': self.option_chain
        }

    async def _check_signals(self):
        """Check for entry signals."""
        if not self.indicators or not self.option_chain:
            return

        # Don't check if max trades reached
        if self.session_stats['trades_today'] >= self.config['RISK']['max_trades_per_day']:
            return

        signal_type, strike, ltp, confidence, signal_path = check_entry_signal(
            self.indicators,
            self.config,
            self.session_stats,
            self.india_vix
        )

        if signal_type:
            await self._enter_trade(signal_type, strike, ltp, confidence, signal_path)

    async def _enter_trade(self, signal_type: str, strike: int, ltp: float, confidence: float, signal_path: str):
        """Enter a new trade."""
        self.trade_counter += 1

        self.active_trade = enter_trade(
            signal_type, strike, ltp, confidence, signal_path,
            self.indicators, self.config, self.trade_counter,
            self.india_vix
        )

        # Execute entry order if enabled
        if self.executor:
            expiry = DataCache.current_expiry or self.config.get('EXPIRY', '')
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(
                None, self.executor.execute_entry, self.active_trade, expiry
            )
            if not success:
                print(f"Entry failed: {msg}")
                self.active_trade = None
                return

        # Update session stats
        self.session_stats['trades_today'] += 1
        self.session_stats['last_trade_id'] = self.trade_counter

        # Send Telegram alert
        send_telegram_alert(signal_type, strike, ltp, confidence, signal_path)

        print(f"ENTERED: {self.active_trade.instrument} @ {ltp:.2f} ({signal_path})")

    async def _manage_trade(self):
        """Manage active trade - update and check exits."""
        if not self.active_trade:
            return

        # Get current LTP
        opt_type = 'CE' if self.active_trade.trade_type == 'CALL' else 'PE'
        option_data = self.option_chain.get(self.active_trade.strike, {}).get(opt_type, {})
        current_ltp = option_data.get('ltp', self.active_trade.current_ltp)

        # Update trade state
        atr = self.indicators.get('atr_pct', 1.0)
        update_trade(self.active_trade, current_ltp, atr, self.config)

        # Check for reversal
        reversal, warnings = detect_reversal(self.indicators, self.active_trade)
        self.active_trade.reversal_detected = reversal

        # Check for manual exit request
        if self.exit_requested:
            await self._exit_trade(self.exit_requested)
            self.exit_requested = None
            return

        # Check exit conditions
        current_pnl = self.session_stats['daily_pnl'] + self.active_trade.pnl_rupees
        peak_mtm = max(self.session_stats['peak_session_mtm'], current_pnl)

        should_exit, reason = check_exit_conditions(
            self.active_trade,
            datetime.now(),
            self.config,
            current_pnl,
            peak_mtm
        )

        if should_exit:
            await self._exit_trade(reason)

    async def _exit_trade(self, reason: str):
        """Exit the active trade."""
        if not self.active_trade:
            return

        exit_price = self.active_trade.current_ltp
        exit_trade(self.active_trade, exit_price, reason)

        # Execute exit order if enabled
        if self.executor:
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(
                None, self.executor.execute_exit, self.active_trade
            )
            if not success:
                print(f"Exit execution warning: {msg}")

        # Update session stats
        self.session_stats['daily_pnl'] += self.active_trade.pnl_rupees
        self.session_stats['peak_session_mtm'] = max(
            self.session_stats['peak_session_mtm'],
            self.session_stats['daily_pnl']
        )

        # Send Telegram alert
        send_telegram_exit_alert(self.active_trade, reason)

        print(f"EXITED: {self.active_trade.instrument} @ {exit_price:.2f} ({reason}) P&L: {self.active_trade.pnl_rupees:.2f}")

        # Move to closed trades
        self.closed_trades.append(self.active_trade)
        self.active_trade = None

    async def _broadcast_state(self):
        """Broadcast current state via WebSocket."""
        if not self.ws_manager:
            return

        state = self.get_state()
        await self.ws_manager.broadcast(state)

    def get_state(self) -> Dict[str, Any]:
        """Get current engine state for API/WebSocket."""
        market_status, next_action = get_market_status()
        thresholds = self.config['MODES'][self.config['ACTIVE_MODE']]

        # Determine status
        if not self.running:
            status = "STOPPED"
        elif self.active_trade:
            status = "TRADING"
        else:
            status = "SCANNING"

        # Active trade data
        active_trade_data = None
        reversal_warnings = []
        if self.active_trade:
            active_trade_data = self.active_trade.to_dict()
            if self.active_trade.reversal_detected:
                _, warnings = detect_reversal(self.indicators, self.active_trade)
                reversal_warnings = warnings

        return {
            # Engine status
            "status": status,
            "mode": self.config['ACTIVE_MODE'],
            "execution_mode": self.execution_mode,
            "broker": self.broker,

            # Market data (use cache if current is 0)
            "spot_price": self.spot_price if self.spot_price > 0 else (DataCache.last_spot_price or 0),
            "spot_change_pct": self.spot_change_pct if self.spot_price > 0 else (DataCache.last_spot_change or 0),
            "india_vix": self.india_vix if self.india_vix > 0 else (DataCache.last_vix or 15.0),
            "atm_strike": self.indicators.get('atm_strike', 0) or DataCache.last_atm_strike or 0,
            "data_live": is_market_open(),

            # Session stats
            "trades_today": self.session_stats['trades_today'],
            "max_trades_per_day": self.config['RISK']['max_trades_per_day'],
            "daily_pnl": self.session_stats['daily_pnl'],
            "peak_session_mtm": self.session_stats['peak_session_mtm'],
            "capital": self.capital,

            # Indicators
            "pcr": self.indicators.get('pcr', 1.0),
            "pcr_trend": self.indicators.get('pcr_trend', 'STABLE'),
            "ce_oi_change": self.indicators.get('ce_oi_change', 0),
            "pe_oi_change": self.indicators.get('pe_oi_change', 0),
            "oi_flow_ratio": self.indicators.get('oi_flow_ratio', 0),
            "oi_flow_direction": self.indicators.get('oi_flow_direction', 'NEUTRAL'),
            "oi_velocity": self.indicators.get('oi_velocity', 0),

            # Alpha values
            "alpha_1_call": self.indicators.get('alpha_1_call', 0),
            "alpha_1_put": self.indicators.get('alpha_1_put', 0),
            "alpha_2_call": self.indicators.get('alpha_2_call', 0),
            "alpha_2_put": self.indicators.get('alpha_2_put', 0),

            # Quality scores
            "quality_score_call": self.indicators.get('quality_score_call', 0),
            "quality_score_put": self.indicators.get('quality_score_put', 0),
            "confluence_call": self.indicators.get('confluence_call', 0),
            "confluence_put": self.indicators.get('confluence_put', 0),
            "confluence_conditions_call": self.indicators.get('confluence_conditions_call', []),
            "confluence_conditions_put": self.indicators.get('confluence_conditions_put', []),

            # Trend
            "trend": self.indicators.get('trend', 'NEUTRAL'),
            "trend_strength": self.indicators.get('trend_strength', 0.5),
            "rsi": self.indicators.get('rsi', 50),
            "atr_pct": self.indicators.get('atr_pct', 0),

            # Support/Resistance
            "support": self.indicators.get('support', 0),
            "resistance": self.indicators.get('resistance', 0),

            # Volume ratios
            "volume_ratio_call": self.indicators.get('volume_ratio_call', 0),
            "volume_ratio_put": self.indicators.get('volume_ratio_put', 0),

            # Active trade
            "active_trade": active_trade_data,
            "reversal_warnings": reversal_warnings,

            # Timing
            "timestamp": datetime.now().isoformat(),
            "market_status": market_status,
            "next_action": next_action,
            "trading_allowed": is_trading_time_allowed(self.config),
            "is_lunch_hour": is_lunch_hour(self.config),

            # Thresholds
            "thresholds": thresholds
        }

    def _save_session(self):
        """Save session state to file."""
        # Save active trade for crash recovery
        if self.active_trade:
            self.session_stats['active_trade'] = self.active_trade.to_dict()
        else:
            self.session_stats['active_trade'] = None

        save_session_state(self.session_stats)

    def request_exit(self, reason: str):
        """Request trade exit (called from API)."""
        self.exit_requested = reason

    def recover_trade(self, trade_data: Dict[str, Any]):
        """Recover trade from saved data."""
        # Reconstruct Trade object from dict
        from trading.trade import Trade
        self.active_trade = Trade(
            trade_id=trade_data['trade_id'],
            instrument=trade_data['instrument'],
            trade_type=trade_data['trade_type'],
            strike=trade_data['strike'],
            entry_price=trade_data['entry_price'],
            entry_time=datetime.fromisoformat(trade_data['entry_time']),
            qty=trade_data['qty'],
            current_ltp=trade_data['current_ltp'],
            highest_price=trade_data['highest_price'],
            lowest_price=trade_data.get('lowest_price', float('inf')),
            entry_vix=trade_data.get('entry_vix', 15.0),
            vix_regime=trade_data.get('vix_regime', 'normal'),
            initial_sl_pct=trade_data.get('initial_sl_pct', 0.25),
            trail_activation_pct=trade_data.get('trail_activation_pct', 0.22),
            trail_distance_pct=trade_data.get('trail_distance_pct', 0.28),
            highest_premium=trade_data.get('highest_premium', trade_data['entry_price']),
            trailing_active=trade_data.get('trailing_active', False),
            current_stop=trade_data.get('current_stop', trade_data['entry_price'] * 0.75),
            signal_path=trade_data.get('signal_path', 'UNKNOWN')
        )
        print(f"Recovered trade: {self.active_trade.instrument}")

    def exit_orphan(self, trade_data: Dict[str, Any]):
        """Exit orphaned position via market order."""
        if not self.executor or not self.executor.is_live():
            print("Cannot exit orphan - execution not enabled")
            return

        # Build minimal trade object for exit
        self.recover_trade(trade_data)
        if self.active_trade:
            # Get current LTP
            opt_type = 'CE' if self.active_trade.trade_type == 'CALL' else 'PE'
            if self.option_chain:
                option_data = self.option_chain.get(self.active_trade.strike, {}).get(opt_type, {})
                self.active_trade.current_ltp = option_data.get('ltp', 0)

            # Execute exit
            asyncio.create_task(self._exit_trade("orphan_exit"))

    async def stop(self):
        """Stop the engine gracefully."""
        self.running = False

        # Exit active trade if any
        if self.active_trade:
            await self._exit_trade("engine_stop")

        # Save final session state
        self._save_session()
