"""Upstox API client for market data and order execution."""

import requests
from datetime import datetime
from typing import Optional, Tuple, List


class UpstoxAPI:
    """Upstox API client for market data"""

    BASE_URL = "https://api.upstox.com/v2"

    def __init__(self, access_token: str):
        self.token = access_token
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def validate_token(self) -> Tuple[bool, str]:
        """Validate access token by fetching user profile"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/user/profile",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    user_name = data.get('data', {}).get('user_name', 'User')
                    return True, user_name

            return False, response.json().get('message', 'Unknown error')

        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    def get_spot_price(self) -> Optional[dict]:
        """Get NIFTY 50 spot price"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/market-quote/ltp",
                params={'instrument_key': 'NSE_INDEX|Nifty 50'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    # Try both possible key formats
                    api_data = data.get('data', {})
                    ltp_data = api_data.get('NSE_INDEX:Nifty 50', {}) or api_data.get('NSE_INDEX|Nifty 50', {})

                    # If still empty, try to get first value from response
                    if not ltp_data and api_data:
                        ltp_data = next(iter(api_data.values()), {})

                    price = ltp_data.get('last_price', 0)
                    if price > 0:
                        return {
                            'price': price,
                            'change': ltp_data.get('change', 0),
                            'change_pct': ltp_data.get('change_percent', 0)
                        }
                    else:
                        print(f"Spot API response: {api_data.keys() if api_data else 'empty'}")
            else:
                print(f"Spot API status: {response.status_code}")
            return None

        except Exception as e:
            print(f"API Error (spot): {e}")
            return None

    def get_intraday_candles(self, interval: str = "5minute") -> Optional[List[dict]]:
        """Get NIFTY intraday candles for ATR calculation

        Args:
            interval: 1minute, 5minute, 15minute, 30minute, 1hour

        Returns:
            List of candles with open, high, low, close, volume
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/historical-candle/intraday/NSE_INDEX%7CNifty%2050/{interval}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    candles = data.get('data', {}).get('candles', [])
                    # Candles format: [timestamp, open, high, low, close, volume, oi]
                    parsed = []
                    for c in candles:
                        if len(c) >= 5:
                            parsed.append({
                                'timestamp': c[0],
                                'open': c[1],
                                'high': c[2],
                                'low': c[3],
                                'close': c[4],
                                'volume': c[5] if len(c) > 5 else 0
                            })
                    return parsed
            return None

        except Exception as e:
            print(f"API Error (candles): {e}")
            return None

    def get_india_vix(self) -> Optional[float]:
        """Fetch India VIX for volatility regime detection"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/market-quote/ltp",
                params={'instrument_key': 'NSE_INDEX|India VIX'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    vix_data = data.get('data', {}).get('NSE_INDEX:India VIX', {})
                    return vix_data.get('last_price', 15.0)  # Default to normal VIX
            return 15.0  # Default on failure

        except Exception as e:
            print(f"API Error (VIX): {e}")
            return 15.0  # Default to normal VIX on error

    def get_current_weekly_expiry(self, fallback_expiry: str = "") -> str:
        """Auto-detect current weekly NIFTY expiry from Upstox API.

        Args:
            fallback_expiry: Expiry to use if API fails (from config)

        Returns:
            Expiry date string in YYYY-MM-DD format
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/option/contract",
                params={'instrument_key': 'NSE_INDEX|Nifty 50'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    # Get list of available expiries
                    expiries = data.get('data', {}).get('expiry', [])
                    if expiries:
                        # Sort and get nearest expiry (first one)
                        expiries.sort()
                        nearest_expiry = expiries[0]
                        print(f"Auto-detected expiry: {nearest_expiry}")
                        return nearest_expiry

            # Fallback to config
            print(f"Using config expiry: {fallback_expiry}")
            return fallback_expiry

        except Exception as e:
            print(f"Expiry fetch error: {e}, using config")
            return fallback_expiry

    def get_option_chain(self, expiry: str) -> Optional[dict]:
        """Get NIFTY option chain for given expiry"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/option/chain",
                params={
                    'instrument_key': 'NSE_INDEX|Nifty 50',
                    'expiry_date': expiry
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return self._parse_option_chain(data.get('data', []))
            return None

        except Exception as e:
            print(f"API Error (chain): {e}")
            return None

    def _parse_option_chain(self, chain_data: list) -> dict:
        """Parse option chain data into structured format"""
        parsed = {}

        for item in chain_data:
            strike = item.get('strike_price', 0)

            if strike not in parsed:
                parsed[strike] = {'CE': None, 'PE': None}

            # Call option data
            if 'call_options' in item and item['call_options']:
                ce = item['call_options'].get('market_data', {})
                ce_oi = ce.get('oi', 0)
                ce_prev_oi = ce.get('prev_oi', 0)
                parsed[strike]['CE'] = {
                    'ltp': ce.get('ltp', 0),
                    'volume': ce.get('volume', 0),
                    'oi': ce_oi,
                    'oi_change': ce_oi - ce_prev_oi,  # Calculate from oi and prev_oi
                    'iv': item['call_options'].get('option_greeks', {}).get('iv', 0),
                    'delta': item['call_options'].get('option_greeks', {}).get('delta', 0),
                    'bid': ce.get('bid_price', 0),
                    'ask': ce.get('ask_price', 0)
                }

            # Put option data
            if 'put_options' in item and item['put_options']:
                pe = item['put_options'].get('market_data', {})
                pe_oi = pe.get('oi', 0)
                pe_prev_oi = pe.get('prev_oi', 0)
                parsed[strike]['PE'] = {
                    'ltp': pe.get('ltp', 0),
                    'volume': pe.get('volume', 0),
                    'oi': pe_oi,
                    'oi_change': pe_oi - pe_prev_oi,  # Calculate from oi and prev_oi
                    'iv': item['put_options'].get('option_greeks', {}).get('iv', 0),
                    'delta': item['put_options'].get('option_greeks', {}).get('delta', 0),
                    'bid': pe.get('bid_price', 0),
                    'ask': pe.get('ask_price', 0)
                }

        return parsed

    # ═══════════════════════════════════════════════════════════════════════════
    # ORDER EXECUTION METHODS (for live trading)
    # ═══════════════════════════════════════════════════════════════════════════

    def build_instrument_key(self, strike: int, opt_type: str, expiry: str) -> str:
        """Build Upstox instrument key for NIFTY options.

        Args:
            strike: Option strike price (e.g., 24850)
            opt_type: 'CE' or 'PE'
            expiry: Expiry date string 'YYYY-MM-DD'

        Returns:
            Instrument key like 'NSE_FO|NIFTY24850CE'
        """
        # Convert expiry YYYY-MM-DD to Upstox format
        dt = datetime.strptime(expiry, '%Y-%m-%d')
        exp_str = dt.strftime('%y%b').upper()
        return f"NSE_FO|NIFTY{exp_str}{strike}{opt_type}"

    def place_order(
        self,
        instrument_key: str,
        transaction_type: str,  # 'BUY' or 'SELL'
        quantity: int,
        order_type: str = 'MARKET',
        price: float = 0,
        product: str = 'I',  # Intraday
        validity: str = 'DAY'
    ) -> Tuple[bool, Optional[str], str]:
        """Place order via Upstox API.

        Returns:
            Tuple[success, order_id, message]
        """
        try:
            payload = {
                'quantity': quantity,
                'product': product,
                'validity': validity,
                'price': price,
                'instrument_token': instrument_key,
                'order_type': order_type,
                'transaction_type': transaction_type,
                'disclosed_quantity': 0,
                'trigger_price': 0,
                'is_amo': False
            }

            response = self.session.post(
                f"{self.BASE_URL}/order/place",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    order_id = data.get('data', {}).get('order_id')
                    return True, order_id, "Order placed successfully"

            error_msg = response.json().get('message', 'Unknown error')
            return False, None, f"Order failed: {error_msg}"

        except requests.exceptions.Timeout:
            return False, None, "Order timeout - check positions manually"
        except Exception as e:
            return False, None, f"Order error: {str(e)}"

    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get order status and fill details.

        Returns:
            Dict with status, filled_qty, average_price, or None on error
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/order/retrieve-all",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    orders = data.get('data', [])
                    for order in orders:
                        if order.get('order_id') == order_id:
                            return {
                                'status': order.get('status'),
                                'filled_qty': order.get('filled_quantity', 0),
                                'average_price': order.get('average_price', 0),
                                'pending_qty': order.get('pending_quantity', 0),
                                'rejection_reason': order.get('status_message', '')
                            }
            return None

        except Exception as e:
            print(f"Order status error: {e}")
            return None

    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel pending order.

        Returns:
            Tuple[success, message]
        """
        try:
            response = self.session.delete(
                f"{self.BASE_URL}/order/cancel",
                params={'order_id': order_id},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return True, "Order cancelled"

            return False, response.json().get('message', 'Cancel failed')

        except Exception as e:
            return False, f"Cancel error: {str(e)}"

    def get_positions(self) -> Optional[List[dict]]:
        """Get current day positions to verify fills.

        Returns:
            List of position dicts or None on error
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/portfolio/short-term-positions",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data.get('data', [])
            return None

        except Exception as e:
            print(f"Position fetch error: {e}")
            return None
