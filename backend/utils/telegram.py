"""Telegram notification functions."""

import requests
from datetime import datetime


# Default settings - can be overridden via config
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_IDS = []
TELEGRAM_ENABLED = False


def configure_telegram(bot_token: str, chat_ids: list, enabled: bool = True):
    """Configure Telegram settings."""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, TELEGRAM_ENABLED
    TELEGRAM_BOT_TOKEN = bot_token
    TELEGRAM_CHAT_IDS = chat_ids
    TELEGRAM_ENABLED = enabled


def send_telegram_alert(signal_type: str, strike: int, ltp: float, confidence: float, signal_path: str = "UNKNOWN"):
    """Send signal alert to Telegram"""
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return

    opt_type = 'CE' if signal_type == 'CALL' else 'PE'
    path_emoji = "📈" if signal_path == "BUYING" else "📝"
    message = f"""🚨 *SKEW HUNTER SIGNAL*

📊 *{signal_type}* Signal Detected!
Strike: {strike} {opt_type}
Entry: ₹{ltp:.2f}
Confidence: {confidence:.0f}%
{path_emoji} Path: {signal_path}
Time: {datetime.now().strftime('%H:%M:%S')}"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=5)
        except Exception:
            pass  # Don't crash on notification failure


def send_telegram_ltp_update(trade):
    """Send LTP update with PNL to Telegram"""
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return

    opt_type = 'CE' if trade.trade_type == 'CALL' else 'PE'
    pnl_emoji = "🟢" if trade.pnl_rupees >= 0 else "🔴"
    pnl_sign = "+" if trade.pnl_rupees >= 0 else ""

    message = f"""📊 *LTP UPDATE*

{trade.trade_type} {trade.strike} {opt_type}
Entry: ₹{trade.entry_price:.2f}
Current: ₹{trade.current_ltp:.2f}

{pnl_emoji} *PNL: {pnl_sign}₹{trade.pnl_rupees:.2f} ({pnl_sign}{trade.pnl_percent:.1f}%)*

⏱ Duration: {int(trade.duration_seconds // 60)}m {int(trade.duration_seconds % 60)}s
Time: {datetime.now().strftime('%H:%M:%S')}"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=5)
        except Exception:
            pass


def send_telegram_exit_alert(trade, reason: str):
    """Send exit notification to Telegram"""
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return

    opt_type = 'CE' if trade.trade_type == 'CALL' else 'PE'
    pnl_emoji = "🟢" if trade.pnl_rupees >= 0 else "🔴"
    pnl_sign = "+" if trade.pnl_rupees >= 0 else ""

    reason_text = {
        'profit_target': '🎯 TARGET HIT',
        'stop_loss': '🛑 STOP LOSS',
        'initial_stop': '🛑 STOP LOSS',
        'trailing_stop': '📉 TRAILING STOP',
        'emergency_stop': '🚨 EMERGENCY STOP',
        'manual_exit': '👤 MANUAL EXIT',
        'session_end': '⏰ SESSION END',
        'time_exit': '⏰ TIME EXIT',
        'eod_squareoff': '⏰ EOD SQUAREOFF',
        'mtm_max_loss': '💥 MTM MAX LOSS',
        'mtm_profit_protection': '🔒 PROFIT PROTECTION',
    }.get(reason, f'EXIT: {reason.upper()}')

    message = f"""🔔 *TRADE CLOSED*

{reason_text}

{trade.trade_type} {trade.strike} {opt_type}
Entry: ₹{trade.entry_price:.2f}
Exit: ₹{trade.current_ltp:.2f}

{pnl_emoji} *FINAL PNL: {pnl_sign}₹{trade.pnl_rupees:.2f} ({pnl_sign}{trade.pnl_percent:.1f}%)*

⏱ Duration: {int(trade.duration_seconds // 60)}m {int(trade.duration_seconds % 60)}s
Time: {datetime.now().strftime('%H:%M:%S')}"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=5)
        except Exception:
            pass
