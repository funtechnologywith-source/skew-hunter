"""Order execution engine for live and paper trading."""

import time
from typing import Tuple, Optional


class OrderExecutor:
    """Handles order placement, verification, and state management for live trading.

    Supports multiple brokers (Upstox, DHAN) through a common interface.
    """

    def __init__(self, broker, config: dict, broker_name: str = "UPSTOX"):
        """Initialize order executor.

        Args:
            broker: Broker API instance (UpstoxAPI or DhanAPI)
            config: Configuration dict
            broker_name: "UPSTOX" or "DHAN" for identification
        """
        self.broker = broker
        self.broker_name = broker_name
        self.config = config
        self.exec_config = config.get('EXECUTION', {})
        self.enabled = self.exec_config.get('enabled', False)
        self.paper_mode = self.exec_config.get('paper_trading', True)

    def is_live(self) -> bool:
        """Check if live execution is enabled (not paper trading)."""
        return self.enabled and not self.paper_mode

    def _get_product_type(self) -> str:
        """Get product type for current broker."""
        if self.broker_name == "DHAN":
            return "INTRADAY"
        return self.exec_config.get('product_type', 'I')

    def execute_entry(self, trade, expiry: str) -> Tuple[bool, str]:
        """Execute entry order for trade.

        Args:
            trade: Trade object with entry details
            expiry: Expiry date string (YYYY-MM-DD)

        Returns:
            Tuple[success, message]
        """
        if not self.enabled:
            return True, "Execution disabled - simulation only"

        if self.paper_mode:
            trade.execution_mode = "PAPER"
            msg = f"[PAPER] Entry: {trade.instrument} @ Rs{trade.entry_price:.2f}"
            print(msg)
            return True, msg

        # Live mode - place actual order
        trade.execution_mode = "LIVE"

        # Build instrument key
        opt_type = 'CE' if trade.trade_type == 'CALL' else 'PE'
        instrument_key = self.broker.build_instrument_key(trade.strike, opt_type, expiry)
        trade.instrument_key = instrument_key

        # Place order
        success, order_id, msg = self.broker.place_order(
            instrument_key=instrument_key,
            transaction_type='BUY',
            quantity=trade.qty,
            order_type=self.exec_config.get('order_type', 'MARKET'),
            product=self._get_product_type()
        )

        if not success:
            print(f"[{self.broker_name}] Order failed: {msg}")
            return False, msg

        trade.broker_order_id = order_id
        print(f"[{self.broker_name}] Order placed: {order_id}")

        # Wait for fill
        filled, fill_price, fill_qty = self._wait_for_fill(order_id)
        if filled:
            trade.actual_fill_price = fill_price
            trade.actual_fill_qty = fill_qty
            return True, f"Filled @ Rs{fill_price:.2f}"
        else:
            # Cancel unfilled order
            self.broker.cancel_order(order_id)
            return False, "Order not filled - cancelled"

    def execute_exit(self, trade) -> Tuple[bool, str]:
        """Execute exit order for trade.

        Returns:
            Tuple[success, message]
        """
        if not self.enabled:
            return True, "Execution disabled"

        if self.paper_mode:
            msg = f"[PAPER] Exit: {trade.instrument} @ Rs{trade.current_ltp:.2f}"
            print(msg)
            return True, msg

        if not trade.instrument_key:
            return False, "No instrument key - cannot exit"

        qty = trade.actual_fill_qty or trade.qty

        success, order_id, msg = self.broker.place_order(
            instrument_key=trade.instrument_key,
            transaction_type='SELL',
            quantity=qty,
            order_type='MARKET',  # Always market for exits
            product=self._get_product_type()
        )

        if not success:
            print(f"[{self.broker_name}] Exit order failed: {msg}")
            return False, msg

        trade.exit_order_id = order_id
        print(f"[{self.broker_name}] Exit order placed: {order_id}")

        # Wait for fill
        filled, fill_price, _ = self._wait_for_fill(order_id)
        if filled:
            trade.actual_exit_price = fill_price
            return True, f"Exit filled @ Rs{fill_price:.2f}"

        return False, "Exit order not filled - CHECK POSITIONS!"

    def _wait_for_fill(
        self,
        order_id: str,
        timeout: int = None
    ) -> Tuple[bool, float, int]:
        """Wait for order to fill with timeout.

        Returns:
            Tuple[filled, fill_price, fill_qty]
        """
        timeout = timeout or self.exec_config.get('order_timeout_seconds', 30)
        start = time.time()

        while time.time() - start < timeout:
            status = self.broker.get_order_status(order_id)
            if status:
                if status['status'] == 'complete':
                    return True, status['average_price'], status['filled_qty']
                elif status['status'] in ['rejected', 'cancelled']:
                    print(f"[{self.broker_name}] Order {status['status']}: {status.get('rejection_reason', '')}")
                    return False, 0, 0
            time.sleep(1)

        print(f"[{self.broker_name}] Order timeout after {timeout}s")
        return False, 0, 0
