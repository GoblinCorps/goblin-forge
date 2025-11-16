"""
Trade Execution and Order Management

Handles order validation, submission, and tracking with strict risk controls.

Safety Controls:
----------------
1. Global kill switch (allow_execution in config)
2. Paper trading enforcement
3. Position size limits (1% risk per trade, 3% total)
4. Order validation before submission
5. Duplicate order prevention

Order Flow:
-----------
1. Validate setup (SABR20 score, regime compatibility)
2. Calculate position size based on risk
3. Validate against risk limits
4. Submit order to IB
5. Track position

Usage:
------
from src.execution.order_manager import order_manager

# Validate and submit order
order = order_manager.create_order_from_setup(
    setup=sabr20_score,
    account_value=100000
)

if order:
    result = order_manager.submit_order(order)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd
from loguru import logger
from ib_insync import Stock, Order, Trade

from src.config import config
from src.data.ib_manager import ib_manager
from src.screening.sabr20_engine import SABR20Score
from src.regime.regime_detector import regime_detector


@dataclass
class Position:
    """
    Position tracking with real-time P&L.

    Attributes:
    -----------
    symbol : str
        Stock symbol
    side : str
        'BUY' or 'SELL'
    quantity : int
        Number of shares
    entry_price : float
        Entry price per share
    entry_time : datetime
        Position entry timestamp
    stop_price : float, optional
        Stop loss price
    target_price : float, optional
        Take profit price
    current_price : float
        Current market price (updated from realtime bars)
    last_update : datetime, optional
        Timestamp of last price update
    order_id : int, optional
        IB order ID
    risk_amount : float
        Initial risk in dollars
    mae : float
        Maximum Adverse Excursion (worst drawdown)
    mfe : float
        Maximum Favorable Excursion (best gain)
    """
    symbol: str
    side: str
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    current_price: float = 0.0
    last_update: Optional[datetime] = None
    order_id: Optional[int] = None
    risk_amount: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        """
        Calculate unrealized P&L based on current price.

        Returns:
        --------
        float
            Unrealized profit/loss in dollars
        """
        if self.current_price == 0.0:
            return 0.0

        if self.side == 'BUY':
            pnl = (self.current_price - self.entry_price) * self.quantity
        else:  # SELL/SHORT
            pnl = (self.entry_price - self.current_price) * self.quantity

        return pnl

    @property
    def unrealized_pnl_pct(self) -> float:
        """
        Calculate unrealized P&L as percentage of entry value.

        Returns:
        --------
        float
            Unrealized P&L percentage
        """
        if self.entry_price == 0:
            return 0.0
        return (self.unrealized_pnl / (self.entry_price * self.quantity)) * 100

    @property
    def current_risk(self) -> float:
        """
        Current distance from stop loss in dollars.

        Returns:
        --------
        float
            Current risk in dollars
        """
        if not self.stop_price:
            return 0.0

        if self.side == 'BUY':
            return (self.current_price - self.stop_price) * self.quantity
        else:
            return (self.stop_price - self.current_price) * self.quantity


@dataclass
class ClosedTrade:
    """Record of a closed trade."""
    symbol: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    order_id: Optional[int] = None


class OrderStatus(Enum):
    """Order status types."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class TradeOrder:
    """
    Trade order representation.

    Attributes:
    -----------
    symbol : str
        Stock symbol
    action : str
        'BUY' or 'SELL'
    quantity : int
        Number of shares
    entry_price : float
        Target entry price
    stop_loss : float
        Stop loss price
    take_profit : float
        Take profit price
    risk_amount : float
        Dollar risk amount
    position_size_pct : float
        Position size as % of account
    sabr20_score : float
        SABR20 score that triggered this order
    timestamp : datetime
        Order creation time
    order_id : int or None
        IB order ID (after submission)
    status : OrderStatus
        Current status
    """
    symbol: str
    action: str
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    position_size_pct: float
    sabr20_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING


class OrderManager:
    """
    Order management and execution system.

    Manages order creation, position tracking, and live P&L updates.

    Features:
    - Real-time position price updates from realtime_aggregator
    - Unrealized P&L calculation for open positions
    - Portfolio-level P&L aggregation
    - Risk monitoring (distance from stops)

    Integration:
    - RealtimeAggregator calls update_position_price() on each new bar
    - Dashboard reads position data for P&L display
    - Trailing stop manager uses current_risk for stop adjustments

    Attributes:
    -----------
    max_risk_per_trade : float
        Maximum risk per trade as % of account
    max_total_risk : float
        Maximum total risk across all positions
    max_positions : int
        Maximum concurrent positions
    allow_execution : bool
        Master kill switch for live trading
    positions : Dict[str, Position]
        Active positions with live P&L tracking
    closed_trades : List[ClosedTrade]
        History of closed trades
    """

    def __init__(self):
        """Initialize order manager with configuration."""
        # Load execution configuration
        exec_config = config.trading.execution

        self.allow_execution = exec_config.allow_execution
        self.require_paper_trading = exec_config.require_paper_trading_mode
        self.max_risk_per_trade = exec_config.max_risk_per_trade_pct / 100
        self.max_total_risk = exec_config.max_total_risk_pct / 100
        self.max_positions = exec_config.max_concurrent_positions

        # Position tracking with live P&L
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[ClosedTrade] = []

        # Legacy support
        self.active_positions: Dict[str, TradeOrder] = {}
        self.order_history: List[TradeOrder] = []

        # Trade database integration
        from src.data.trade_database import trade_database
        self.trade_database = trade_database
        self.position_to_trade_id: Dict[str, int] = {}

        # Safety check
        if self.allow_execution:
            logger.warning("⚠️  LIVE EXECUTION ENABLED - Orders will be submitted!")
        else:
            logger.info("✅ Execution disabled (SCREENER-ONLY mode)")

        logger.info(
            f"Order manager initialized: "
            f"max_risk={self.max_risk_per_trade:.1%}, "
            f"max_total={self.max_total_risk:.1%}, "
            f"max_positions={self.max_positions}"
        )

    def validate_execution_allowed(self) -> bool:
        """
        Validate that execution is allowed.

        Checks:
        1. allow_execution flag
        2. IB connection status
        3. Paper trading requirement

        Returns:
        --------
        bool
            True if execution allowed
        """
        if not self.allow_execution:
            logger.warning("Execution blocked: allow_execution=False in config")
            return False

        if not ib_manager.is_connected():
            logger.error("Execution blocked: IB not connected")
            return False

        # Check paper trading requirement
        if self.require_paper_trading:
            # Get account info
            try:
                account_values = ib_manager.ib.accountValues()
                account_type = ib_manager.ib.accountSummary()

                # This is a simplification - in reality, you'd check port number
                # Port 7497 = TWS Paper, 7496 = TWS Live
                if ib_manager.profile.port not in [7497, 4002]:  # Paper trading ports
                    logger.error(
                        "Execution blocked: Paper trading required but connected to live port"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error checking account type: {e}")
                return False

        return True

    def calculate_position_size(
        self,
        account_value: float,
        entry_price: float,
        stop_loss: float,
        regime_adjustment: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate position size based on risk parameters.

        Uses fixed fractional position sizing:
        Position Size = (Account × Risk %) / (Entry - Stop)

        Parameters:
        -----------
        account_value : float
            Total account value
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        regime_adjustment : float, default=1.0
            Risk adjustment factor from regime detector (0.0-1.0)

        Returns:
        --------
        dict
            {'quantity': int, 'risk_amount': float, 'position_value': float, 'position_pct': float}
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share <= 0:
            logger.error("Invalid stop loss: must be below entry for longs")
            return {'quantity': 0, 'risk_amount': 0, 'position_value': 0, 'position_pct': 0}

        # Adjusted risk percentage
        adjusted_risk_pct = self.max_risk_per_trade * regime_adjustment

        # Calculate risk amount
        risk_amount = account_value * adjusted_risk_pct

        # Calculate quantity
        quantity = int(risk_amount / risk_per_share)

        # Calculate actual position value and percentage
        position_value = quantity * entry_price
        position_pct = position_value / account_value

        logger.debug(
            f"Position sizing: qty={quantity}, value=${position_value:.2f} "
            f"({position_pct:.1%}), risk=${risk_amount:.2f}"
        )

        return {
            'quantity': quantity,
            'risk_amount': risk_amount,
            'position_value': position_value,
            'position_pct': position_pct
        }

    def validate_risk_limits(
        self,
        new_risk_amount: float,
        account_value: float
    ) -> bool:
        """
        Validate that new order doesn't exceed risk limits.

        Checks:
        1. Individual trade risk <= max_risk_per_trade
        2. Total portfolio risk <= max_total_risk
        3. Position count <= max_positions

        Parameters:
        -----------
        new_risk_amount : float
            Risk amount for new order
        account_value : float
            Total account value

        Returns:
        --------
        bool
            True if within limits
        """
        # Check individual trade risk
        new_trade_risk_pct = new_risk_amount / account_value
        if new_trade_risk_pct > self.max_risk_per_trade:
            logger.warning(
                f"Order rejected: trade risk {new_trade_risk_pct:.1%} "
                f"exceeds limit {self.max_risk_per_trade:.1%}"
            )
            return False

        # Calculate current total risk
        current_total_risk = sum(
            pos.risk_amount for pos in self.active_positions.values()
        )
        new_total_risk = current_total_risk + new_risk_amount
        new_total_risk_pct = new_total_risk / account_value

        if new_total_risk_pct > self.max_total_risk:
            logger.warning(
                f"Order rejected: total risk {new_total_risk_pct:.1%} "
                f"exceeds limit {self.max_total_risk:.1%}"
            )
            return False

        # Check position count
        if len(self.active_positions) >= self.max_positions:
            logger.warning(
                f"Order rejected: {len(self.active_positions)} positions "
                f"(max {self.max_positions})"
            )
            return False

        return True

    def create_order_from_setup(
        self,
        setup: SABR20Score,
        account_value: float
    ) -> Optional[TradeOrder]:
        """
        Create order from SABR20 setup.

        Parameters:
        -----------
        setup : SABR20Score
            Scored setup
        account_value : float
            Account value for position sizing

        Returns:
        --------
        TradeOrder or None
            Created order, or None if validation failed
        """
        try:
            # Extract entry/stop/target from setup
            rr_details = setup.details.get('risk_reward', {})
            entry_price = rr_details.get('entry')
            stop_loss = rr_details.get('stop')
            take_profit = rr_details.get('target')

            if not all([entry_price, stop_loss, take_profit]):
                logger.warning(f"Incomplete price data for {setup.symbol}")
                return None

            # Get regime adjustment
            regime_adjustment = regime_detector.get_risk_adjustment_factor()

            # Calculate position size
            sizing = self.calculate_position_size(
                account_value=account_value,
                entry_price=entry_price,
                stop_loss=stop_loss,
                regime_adjustment=regime_adjustment
            )

            if sizing['quantity'] == 0:
                logger.warning(f"Position size = 0 for {setup.symbol}")
                return None

            # Validate risk limits
            if not self.validate_risk_limits(sizing['risk_amount'], account_value):
                return None

            # Create order
            order = TradeOrder(
                symbol=setup.symbol,
                action='BUY',
                quantity=sizing['quantity'],
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=sizing['risk_amount'],
                position_size_pct=sizing['position_pct'],
                sabr20_score=setup.total_points
            )

            logger.info(
                f"Created order: {order.symbol} {order.action} {order.quantity} shares "
                f"@ ${order.entry_price:.2f} (risk: ${order.risk_amount:.2f})"
            )

            return order

        except Exception as e:
            logger.error(f"Error creating order from setup {setup.symbol}: {e}")
            return None

    def submit_order(
        self,
        trade_order: TradeOrder,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Submit order to Interactive Brokers.

        Parameters:
        -----------
        trade_order : TradeOrder
            Order to submit
        dry_run : bool, default=False
            If True, validates but doesn't submit

        Returns:
        --------
        dict
            {'success': bool, 'order_id': int or None, 'message': str, 'trade': Trade or None}
        """
        try:
            # Validate execution allowed
            if not self.validate_execution_allowed() and not dry_run:
                return {
                    'success': False,
                    'order_id': None,
                    'message': 'Execution not allowed',
                    'trade': None
                }

            # Check for duplicate
            if trade_order.symbol in self.active_positions:
                return {
                    'success': False,
                    'order_id': None,
                    'message': f'Position already exists for {trade_order.symbol}',
                    'trade': None
                }

            # Create IB contract
            contract = Stock(trade_order.symbol, 'SMART', 'USD')

            # Create IB order (market order)
            ib_order = Order()
            ib_order.action = trade_order.action
            ib_order.totalQuantity = trade_order.quantity
            ib_order.orderType = 'MKT'  # Market order for immediate fill

            # Dry run - just validate
            if dry_run:
                logger.info(
                    f"DRY RUN: Would submit {trade_order.symbol} "
                    f"{trade_order.action} {trade_order.quantity}"
                )
                return {
                    'success': True,
                    'order_id': None,
                    'message': 'Dry run - order validated',
                    'trade': None
                }

            # Submit order
            trade = ib_manager.ib.placeOrder(contract, ib_order)
            ib_manager.ib.sleep(1)  # Wait for order acknowledgment

            # Update trade order
            trade_order.order_id = ib_order.orderId
            trade_order.status = OrderStatus.SUBMITTED

            # Track position
            self.active_positions[trade_order.symbol] = trade_order
            self.order_history.append(trade_order)

            logger.info(
                f"✅ Order submitted: {trade_order.symbol} {trade_order.action} "
                f"{trade_order.quantity} @ ${trade_order.entry_price:.2f} "
                f"(Order ID: {ib_order.orderId})"
            )

            return {
                'success': True,
                'order_id': ib_order.orderId,
                'message': 'Order submitted successfully',
                'trade': trade
            }

        except Exception as e:
            logger.error(f"Error submitting order for {trade_order.symbol}: {e}")
            trade_order.status = OrderStatus.REJECTED
            return {
                'success': False,
                'order_id': None,
                'message': str(e),
                'trade': None
            }

    def get_active_positions(self) -> List[TradeOrder]:
        """Get list of active positions."""
        return list(self.active_positions.values())

    def get_total_risk(self) -> float:
        """Get total risk across all positions."""
        return sum(pos.risk_amount for pos in self.active_positions.values())

    def get_position_summary(self) -> pd.DataFrame:
        """Get summary of active positions as DataFrame."""
        if not self.active_positions:
            return pd.DataFrame()

        rows = []
        for pos in self.active_positions.values():
            rows.append({
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'entry': pos.entry_price,
                'stop': pos.stop_loss,
                'target': pos.take_profit,
                'risk': pos.risk_amount,
                'sabr20': pos.sabr20_score,
                'status': pos.status.value,
                'timestamp': pos.timestamp
            })

        return pd.DataFrame(rows)

    def update_position_price(self, symbol: str, current_price: float) -> None:
        """
        Update position current price and MAE/MFE from real-time bar data.

        Called by realtime_aggregator on each new bar to update live P&L.

        Parameters:
        -----------
        symbol : str
            Symbol to update
        current_price : float
            Latest price from realtime bar

        Notes:
        ------
        - Updates position.current_price and position.last_update
        - Tracks MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)
        - Updates trade database with current MAE/MFE
        - Logs unrealized P&L for monitoring
        - Safe to call for non-existent positions (no-op)
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        position.current_price = current_price
        position.last_update = datetime.now()

        # Update MAE/MFE
        unrealized_pnl = position.unrealized_pnl

        if position.side == 'BUY':
            # MAE = most negative unrealized P&L
            if unrealized_pnl < position.mae:
                position.mae = unrealized_pnl
            # MFE = most positive unrealized P&L
            if unrealized_pnl > position.mfe:
                position.mfe = unrealized_pnl
        else:  # SHORT
            if unrealized_pnl < position.mae:
                position.mae = unrealized_pnl
            if unrealized_pnl > position.mfe:
                position.mfe = unrealized_pnl

        # Update database MAE/MFE if trade exists
        if symbol in self.position_to_trade_id:
            trade_id = self.position_to_trade_id[symbol]
            self.trade_database.update_trade_mae_mfe(trade_id, current_price)

        logger.debug(
            f"Updated {symbol} position price: ${current_price:.2f}, "
            f"Unrealized P&L: ${position.unrealized_pnl:+.2f} "
            f"({position.unrealized_pnl_pct:+.2f}%), "
            f"MAE: ${position.mae:.2f}, MFE: ${position.mfe:.2f}"
        )

    def get_portfolio_pnl(self) -> Dict[str, Any]:
        """
        Get total portfolio P&L (realized + unrealized).

        Returns:
        --------
        dict
            {
                'realized_pnl': float,
                'unrealized_pnl': float,
                'total_pnl': float,
                'positions_count': int,
                'winning_positions': int,
                'losing_positions': int,
                'closed_trades_count': int,
                'winning_trades': int,
                'losing_trades': int
            }

        Examples:
        ---------
        >>> pnl = order_manager.get_portfolio_pnl()
        >>> print(f"Total P&L: ${pnl['total_pnl']:.2f}")
        >>> print(f"Win rate: {pnl['winning_positions'] / pnl['positions_count']:.1%}")
        """
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        realized_pnl = sum(trade.pnl for trade in self.closed_trades)

        winning = sum(1 for pos in self.positions.values() if pos.unrealized_pnl > 0)
        losing = sum(1 for pos in self.positions.values() if pos.unrealized_pnl < 0)

        winning_trades = sum(1 for trade in self.closed_trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in self.closed_trades if trade.pnl < 0)

        return {
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': realized_pnl + unrealized_pnl,
            'positions_count': len(self.positions),
            'winning_positions': winning,
            'losing_positions': losing,
            'closed_trades_count': len(self.closed_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades
        }

    def get_positions_dataframe(self) -> pd.DataFrame:
        """
        Get positions with live P&L as DataFrame.

        Returns:
        --------
        pd.DataFrame
            Columns: symbol, side, quantity, entry_price, current_price,
                    stop_price, target_price, unrealized_pnl, unrealized_pnl_pct,
                    current_risk, last_update

        Examples:
        ---------
        >>> df = order_manager.get_positions_dataframe()
        >>> print(df[['symbol', 'unrealized_pnl', 'unrealized_pnl_pct']])
        """
        if not self.positions:
            return pd.DataFrame()

        rows = []
        for pos in self.positions.values():
            rows.append({
                'symbol': pos.symbol,
                'side': pos.side,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'stop_price': pos.stop_price,
                'target_price': pos.target_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                'current_risk': pos.current_risk,
                'entry_time': pos.entry_time,
                'last_update': pos.last_update
            })

        return pd.DataFrame(rows)

    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_price: float,
        target_price: float,
        risk_amount: float,
        order_id: Optional[int] = None
    ) -> None:
        """
        Open new position and record in database.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        side : str
            'BUY' or 'SELL'
        quantity : int
            Number of shares
        entry_price : float
            Entry price
        stop_price : float
            Stop loss price
        target_price : float
            Take profit price
        risk_amount : float
            Initial risk amount
        order_id : int, optional
            IB order ID

        Notes:
        ------
        Automatically records trade entry in database with SABR20 score and regime.
        """
        # Create position
        position = Position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(),
            stop_price=stop_price,
            target_price=target_price,
            current_price=entry_price,
            risk_amount=risk_amount,
            order_id=order_id,
            mae=0.0,
            mfe=0.0
        )

        self.positions[symbol] = position

        # Record in database
        self._on_position_opened(symbol)

        logger.info(
            f"Opened position: {symbol} {side} {quantity}@${entry_price:.2f}, "
            f"stop=${stop_price:.2f}, target=${target_price:.2f}"
        )

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        commission: float = 0.0,
        notes: Optional[str] = None
    ) -> None:
        """
        Close position and record in database.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        exit_price : float
            Exit price
        exit_reason : str
            'STOP', 'TARGET', 'MANUAL', 'TRAILING_STOP'
        commission : float, default=0.0
            Total commission
        notes : str, optional
            Exit notes

        Notes:
        ------
        Automatically records trade exit in database with final MAE/MFE.
        """
        if symbol not in self.positions:
            logger.warning(f"Cannot close position - {symbol} not found")
            return

        position = self.positions[symbol]

        # Calculate realized P&L
        if position.side == 'BUY':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity

        realized_pnl = pnl - commission
        pnl_pct = (realized_pnl / (position.entry_price * position.quantity)) * 100

        # Create closed trade record
        closed_trade = ClosedTrade(
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=realized_pnl,
            pnl_pct=pnl_pct,
            order_id=position.order_id
        )

        self.closed_trades.append(closed_trade)

        # Record exit in database
        self._on_position_closed(
            symbol=symbol,
            exit_price=exit_price,
            exit_reason=exit_reason,
            commission=commission,
            notes=notes
        )

        # Remove from active positions
        del self.positions[symbol]

        logger.info(
            f"Closed position: {symbol} @ ${exit_price:.2f}, "
            f"P&L: ${realized_pnl:+.2f} ({pnl_pct:+.2f}%), "
            f"reason: {exit_reason}"
        )

    def _on_position_opened(self, symbol: str) -> None:
        """
        Record trade entry in database when position opened.

        Parameters:
        -----------
        symbol : str
            Stock symbol

        Notes:
        ------
        - Retrieves SABR20 score from watchlist if available
        - Retrieves market regime from regime analyzer if available
        - Stores trade_id for future updates
        """
        if symbol not in self.positions:
            logger.warning(f"Position {symbol} not found for database recording")
            return

        position = self.positions[symbol]

        # Get SABR20 score from latest watchlist
        sabr20_score = None
        try:
            from src.screening.watchlist import watchlist_manager
            watchlist = watchlist_manager.get_current_watchlist()
            score_entry = next((s for s in watchlist if s['symbol'] == symbol), None)
            if score_entry:
                sabr20_score = score_entry.get('total_score')
        except Exception as e:
            logger.debug(f"Could not retrieve SABR20 score for {symbol}: {e}")

        # Get market regime
        regime = None
        try:
            current_regime = regime_detector.get_current_regime()
            if current_regime:
                regime = current_regime.get('regime_name')
        except Exception as e:
            logger.debug(f"Could not retrieve regime for {symbol}: {e}")

        # Record in database
        trade_id = self.trade_database.record_trade_entry(
            symbol=symbol,
            side=position.side,
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            quantity=position.quantity,
            stop_price=position.stop_price or 0.0,
            target_price=position.target_price or 0.0,
            risk_amount=position.risk_amount,
            sabr20_score=sabr20_score,
            regime=regime
        )

        self.position_to_trade_id[symbol] = trade_id
        logger.info(f"Recorded trade entry for {symbol}, trade_id={trade_id}")

    def modify_stop(self, symbol: str, new_stop_price: float) -> bool:
        """
        Modify stop loss for an open position.

        Parameters:
        -----------
        symbol : str
            Symbol to modify stop for
        new_stop_price : float
            New stop price

        Returns:
        --------
        bool
            True if modification successful

        Notes:
        ------
        - Validates new stop is better than old stop
        - Updates position stop_price
        - Submits order modification to IB (if connected)
        - Updates database
        - Logs modification
        """
        if symbol not in self.positions:
            logger.error(f"Cannot modify stop for {symbol}: no open position")
            return False

        position = self.positions[symbol]

        # Validate new stop is improvement
        if position.side == 'BUY':
            if new_stop_price <= position.stop_price:
                logger.warning(
                    f"New stop {new_stop_price:.2f} not higher than "
                    f"current {position.stop_price:.2f} for LONG {symbol}"
                )
                return False
        else:  # SHORT
            if new_stop_price >= position.stop_price:
                logger.warning(
                    f"New stop {new_stop_price:.2f} not lower than "
                    f"current {position.stop_price:.2f} for SHORT {symbol}"
                )
                return False

        old_stop = position.stop_price
        position.stop_price = new_stop_price

        # Update in database
        if symbol in self.position_to_trade_id:
            trade_id = self.position_to_trade_id[symbol]
            self.trade_database.update_trade_stop(trade_id, new_stop_price)

        # Submit order modification to IB (if connected)
        try:
            if ib_manager.is_connected():
                # In production, you'd modify the actual stop order via IB API
                # This is a placeholder for the IB integration
                # Actual implementation would use ib_manager.ib.placeOrder()
                # to modify the existing stop order
                logger.debug(f"Would modify IB stop order for {symbol} to {new_stop_price:.2f}")
                pass
        except Exception as e:
            logger.warning(f"Could not modify IB stop order for {symbol}: {e}")

        logger.info(
            f"Modified stop for {symbol}: ${old_stop:.2f} -> ${new_stop_price:.2f}"
        )
        return True

    def enable_trailing_stop_for_position(
        self,
        symbol: str,
        trailing_type: str = 'percentage',
        trailing_amount: float = 2.0,
        activation_profit_pct: float = 1.5
    ) -> None:
        """
        Enable trailing stop for an open position.

        Parameters:
        -----------
        symbol : str
            Symbol to enable trailing for
        trailing_type : str, default='percentage'
            'percentage' (fixed %) or 'atr' (ATR multiplier)
        trailing_amount : float, default=2.0
            Trail distance (percentage or ATR multiplier)
        activation_profit_pct : float, default=1.5
            Profit % required before trailing starts

        Notes:
        ------
        - Position must exist
        - Trailing managed by trailing_stop_manager
        - Automatic updates via scheduler
        """
        if symbol not in self.positions:
            logger.error(f"Cannot enable trailing stop for {symbol}: no open position")
            return

        from src.execution.trailing_stop_manager import trailing_stop_manager

        trailing_stop_manager.enable_trailing_stop(
            symbol=symbol,
            trailing_type=trailing_type,
            trailing_amount=trailing_amount,
            activation_profit_pct=activation_profit_pct
        )

        logger.info(
            f"Enabled trailing stop for {symbol}: {trailing_amount}% trail, "
            f"activate at {activation_profit_pct}% profit"
        )

    def _on_position_closed(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        commission: float = 0.0,
        notes: Optional[str] = None
    ) -> None:
        """
        Record trade exit in database when position closed.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        exit_price : float
            Exit price
        exit_reason : str
            'STOP', 'TARGET', 'MANUAL', 'TRAILING_STOP'
        commission : float, default=0.0
            Total commission
        notes : str, optional
            Exit notes
        """
        if symbol not in self.position_to_trade_id:
            logger.warning(f"No trade_id found for {symbol}, cannot record exit")
            return

        trade_id = self.position_to_trade_id[symbol]

        # Get position for MAE/MFE (before it's deleted)
        if symbol in self.positions:
            position = self.positions[symbol]
            mae = position.mae
            mfe = position.mfe
        else:
            # Already deleted - use from closed_trades
            if self.closed_trades:
                mae = None
                mfe = None
            else:
                mae = None
                mfe = None

        # Determine actual stop/target hit
        actual_stop = None
        actual_target = None

        if exit_reason == 'STOP':
            actual_stop = exit_price
        elif exit_reason == 'TARGET':
            actual_target = exit_price

        # Record exit
        self.trade_database.record_trade_exit(
            trade_id=trade_id,
            exit_time=datetime.now(),
            exit_price=exit_price,
            exit_reason=exit_reason,
            commission=commission,
            actual_stop=actual_stop,
            actual_target=actual_target,
            mae=mae,
            mfe=mfe,
            notes=notes
        )

        del self.position_to_trade_id[symbol]
        logger.info(
            f"Recorded trade exit for {symbol}, trade_id={trade_id}, "
            f"reason={exit_reason}"
        )


# Global singleton instance
order_manager = OrderManager()
