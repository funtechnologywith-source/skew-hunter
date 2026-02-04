"""DHAN API client for order execution only.

Used as an alternate broker while Upstox handles all market data.
Requires static IP whitelisting in DHAN dashboard for order placement.
"""

import io
import csv as csv_module
import re
import requests
from datetime import datetime
from typing import Optional, Tuple, List


class DhanAPI:
    """DHAN API client for order execution only.

    Used as an alternate broker while Upstox handles all market data.
    Requires static IP whitelisting in DHAN dashboard for order placement.
    """

    BASE_URL = "https://api.dhan.co/v2"

    def __init__(self, access_token: str, client_id: str):
        self.token = access_token
        self.client_id = client_id
        self.headers = {
            'Content-Type': 'application/json',
            'access-token': access_token
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._security_cache = {}  # Cache: "strike_CE/PE" -> security_id
        self._expiry_loaded = None  # Track which expiry is loaded

    def load_security_ids(self, expiry: str) -> bool:
        """Load NIFTY option security IDs from DHAN instrument master.

        Args:
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            True if loaded successfully
        """
        if self._expiry_loaded == expiry and self._security_cache:
            return True  # Already loaded

        try:
            # Download DHAN instrument master CSV (compact version)
            print(f"DHAN: Downloading instrument master...")
            response = requests.get(
                "https://images.dhan.co/api-data/api-scrip-master.csv",
                timeout=60
            )

            if response.status_code != 200:
                print(f"DHAN: Failed to download instrument master (HTTP {response.status_code})")
                return False

            reader = csv_module.DictReader(io.StringIO(response.text))

            # Convert expiry to match instrument format (YYYY-MM-DD)
            exp_dt = datetime.strptime(expiry, '%Y-%m-%d')

            count = 0
            for row in reader:
                try:
                    # Filter for NSE F&O segment (D = Derivatives)
                    segment = row.get('SEM_SEGMENT', '')
                    exchange = row.get('SEM_EXM_EXCH_ID', '')
                    if segment != 'D' or exchange != 'NSE':
                        continue

                    # Filter for NIFTY options only
                    symbol = row.get('SEM_TRADING_SYMBOL', '')
                    if not symbol.startswith('NIFTY'):
                        continue

                    # Skip futures (only want options)
                    instrument = row.get('SEM_INSTRUMENT_NAME', '')
                    if 'FUT' in instrument:
                        continue

                    # Get security ID
                    security_id = row.get('SEM_SMST_SECURITY_ID', '')
                    if not security_id:
                        continue

                    # Check expiry date matches
                    row_expiry = row.get('SEM_EXPIRY_DATE', '')
                    if not row_expiry or row_expiry == 'N/A':
                        continue

                    # Parse row expiry (format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                    try:
                        row_exp_dt = datetime.strptime(row_expiry.split(' ')[0], '%Y-%m-%d')
                    except:
                        continue

                    if row_exp_dt.date() != exp_dt.date():
                        continue

                    # Get strike price directly from column
                    strike_str = row.get('SEM_STRIKE_PRICE', '')
                    if not strike_str or strike_str == 'N/A':
                        # Fallback: extract from symbol
                        match = re.search(r'(\d{5})[\s\-]?(CE|PE)$', symbol)
                        if match:
                            strike = int(match.group(1))
                        else:
                            continue
                    else:
                        try:
                            strike = int(float(strike_str))
                        except:
                            continue

                    # Get option type directly from column or symbol
                    opt_type = row.get('SEM_OPTION_TYPE', '')
                    if not opt_type or opt_type == 'N/A':
                        if symbol.endswith('CE'):
                            opt_type = 'CE'
                        elif symbol.endswith('PE'):
                            opt_type = 'PE'
                        else:
                            continue

                    # Store in cache
                    self._security_cache[f"{strike}_{opt_type}"] = security_id
                    count += 1

                except Exception:
                    continue

            self._expiry_loaded = expiry
            print(f"DHAN: Loaded {count} NIFTY option security IDs for {expiry}")
            return count > 0

        except Exception as e:
            print(f"DHAN security ID load error: {e}")
            return False

    def get_security_id(self, strike: int, opt_type: str) -> Optional[str]:
        """Get DHAN security ID for a NIFTY option.

        Args:
            strike: Strike price (e.g., 24850)
            opt_type: 'CE' or 'PE'

        Returns:
            Security ID string or None
        """
        key = f"{strike}_{opt_type}"
        return self._security_cache.get(key)

    def build_instrument_key(self, strike: int, opt_type: str, expiry: str) -> str:
        """Build instrument info for DHAN.

        Note: For DHAN, this returns the security_id directly.
        The expiry parameter is used to ensure cache is loaded.
        """
        # Ensure security IDs are loaded
        if self._expiry_loaded != expiry:
            self.load_security_ids(expiry)

        return self.get_security_id(strike, opt_type) or ""

    def place_order(
        self,
        instrument_key: str,  # For DHAN this is actually security_id
        transaction_type: str,  # 'BUY' or 'SELL'
        quantity: int,
        order_type: str = 'MARKET',
        price: float = 0,
        product: str = 'INTRADAY',
        validity: str = 'DAY'
    ) -> Tuple[bool, Optional[str], str]:
        """Place order via DHAN API.

        Args:
            instrument_key: DHAN security_id (numeric string)
            transaction_type: 'BUY' or 'SELL'
            quantity: Number of contracts
            order_type: 'MARKET' or 'LIMIT'
            price: Limit price (0 for market orders)
            product: 'INTRADAY' or 'CNC'
            validity: 'DAY' or 'IOC'

        Returns:
            Tuple[success, order_id, message]
        """
        if not instrument_key:
            return False, None, "Missing security ID - run load_security_ids first"

        try:
            payload = {
                'dhanClientId': self.client_id,
                'transactionType': transaction_type,
                'exchangeSegment': 'NSE_FNO',
                'productType': product,
                'orderType': order_type,
                'validity': validity,
                'securityId': instrument_key,
                'quantity': quantity,
                'price': price if order_type == 'LIMIT' else 0,
                'disclosedQuantity': 0,
                'triggerPrice': 0
            }

            response = self.session.post(
                f"{self.BASE_URL}/orders",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                order_id = data.get('orderId')
                if order_id:
                    return True, str(order_id), "Order placed successfully"
                return False, None, data.get('message', 'No order ID returned')

            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', f"HTTP {response.status_code}")
            return False, None, f"Order failed: {error_msg}"

        except requests.exceptions.Timeout:
            return False, None, "Order timeout - check positions manually"
        except Exception as e:
            return False, None, f"Order error: {str(e)}"

    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get order status from DHAN.

        Returns:
            Dict with status, filled_qty, average_price, or None on error
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/orders/{order_id}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Map DHAN status to common format
                dhan_status = data.get('orderStatus', '').upper()
                status_map = {
                    'TRADED': 'complete',
                    'PENDING': 'pending',
                    'REJECTED': 'rejected',
                    'CANCELLED': 'cancelled',
                    'TRANSIT': 'pending',
                    'EXPIRED': 'cancelled'
                }

                return {
                    'status': status_map.get(dhan_status, 'pending'),
                    'filled_qty': data.get('filledQty', 0),
                    'average_price': data.get('price', 0),
                    'pending_qty': data.get('pendingQty', 0),
                    'rejection_reason': data.get('omsErrorDescription', '')
                }

            return None

        except Exception as e:
            print(f"DHAN order status error: {e}")
            return None

    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel pending order on DHAN.

        Returns:
            Tuple[success, message]
        """
        try:
            response = self.session.delete(
                f"{self.BASE_URL}/orders/{order_id}",
                timeout=10
            )

            if response.status_code in [200, 202]:
                return True, "Order cancelled"

            error_msg = response.json().get('message', 'Cancel failed') if response.text else 'Cancel failed'
            return False, error_msg

        except Exception as e:
            return False, f"Cancel error: {str(e)}"

    def get_positions(self) -> Optional[List[dict]]:
        """Get current day positions from DHAN.

        Returns:
            List of position dicts or None on error
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/positions",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            return None

        except Exception as e:
            print(f"DHAN position fetch error: {e}")
            return None
