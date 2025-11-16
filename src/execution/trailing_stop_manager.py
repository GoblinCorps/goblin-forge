"""
Trailing Stop Management System

Manages automatic trailing stop adjustments for open positions to protect profits
while allowing winning trades to run.

Features:
---------
1. Dual Trailing Methods
   - Percentage-based: Fixed % below high water mark
   - ATR-based: Dynamic volatility-adjusted trailing

2. Activation Thresholds
   - Only trail after minimum profit achieved
   - Prevents premature stop tightening

3. Safety Guarantees
   - Stops ONLY move in profit direction (never against)
   - Respects minimum trail distance
   - Never moves stop below entry price (for longs)

4. Integration
   - Automatic updates every 1 minute during market hours
   - Database logging of all adjustments
   - OrderManager integration for stop modification

Usage:
------
from src.execution.trailing_stop_manager import trailing_stop_manager

# Enable trailing stop for a position
trailing_stop_manager.enable_trailing_stop(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0,  # 2% trail
    activation_profit_pct=1.5  # Activate after 1.5% profit
)

# Check and update all stops (called by scheduler)
adjustments = trailing_stop_manager.check_and_update_stops()

# Get trailing status
status = trailing_stop_manager.get_trailing_status('AAPL')
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import pandas as pd

from src.config import config


@dataclass
class TrailingConfig:
    """
    Trailing stop configuration for a symbol.

    Attributes:
    -----------
    symbol : str
        Stock symbol
    trailing_type : str
        'percentage' or 'atr'
    trailing_amount : float
        Trail distance (percentage or ATR multiplier)
    activation_profit_pct : float
        Profit % required before trailing starts
    min_trail_amount : float
        Minimum trail distance (percentage)
    enabled : bool
        Whether trailing is enabled
    activated : bool
        Whether profit threshold has been met
    activation_price : float, optional
        Price at which trailing was activated
    activation_time : datetime, optional
        Time at which trailing was activated
    adjustment_count : int
        Number of stop adjustments made
    last_adjustment_time : datetime, optional
        Time of last stop adjustment
    highest_price : float
        Highest price since activation (for longs)
    lowest_price : float
        Lowest price since activation (for shorts)
    """
    symbol: str
    trailing_type: str
    trailing_amount: float
    activation_profit_pct: float
    min_trail_amount: float
    enabled: bool = True
    activated: bool = False
    activation_price: Optional[float] = None
    activation_time: Optional[datetime] = None
    adjustment_count: int = 0
    last_adjustment_time: Optional[datetime] = None
    highest_price: float = 0.0
    lowest_price: float = float('inf')


@dataclass
class StopAdjustment:
    """
    Record of a stop adjustment.

    Attributes:
    -----------
    symbol : str
        Stock symbol
    timestamp : datetime
        Adjustment timestamp
    old_stop : float
        Previous stop price
    new_stop : float
        New stop price
    trigger_price : float
        Price that triggered adjustment
    trailing_type : str
        'percentage' or 'atr'
    trailing_amount : float
        Trail distance used
    profit_pct : float
        Current profit percentage
    """
    symbol: str
    timestamp: datetime
    old_stop: float
    new_stop: float
    trigger_price: float
    trailing_type: str
    trailing_amount: float
    profit_pct: float


class TrailingStopManager:
    """
    Manages trailing stop adjustments for open positions.

    Features:
    - Configurable trailing distance (percentage or ATR-based)
    - Automatic stop adjustment as price moves favorably
    - Never moves stop against position (only in profit direction)
    - Respects minimum profit threshold before activation
    - Logs all stop adjustments for audit trail

    Singleton Pattern:
    ------------------
    Only one instance should exist globally. Access via module-level singleton.

    Integration:
    ------------
    - Checks positions every 1 minute via trailing_stop_scheduler
    - Uses OrderManager to modify stops
    - Retrieves position data from OrderManager
    - Uses IndicatorEngine for ATR calculations

    Attributes:
    -----------
    trailing_configs : Dict[str, TrailingConfig]
        Active trailing configurations by symbol
    adjustment_history : List[StopAdjustment]
        History of all stop adjustments
    last_check_time : datetime, optional
        Timestamp of last update check
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize trailing stop manager."""
        if hasattr(self, '_initialized'):
            return

        # Active trailing configurations
        self.trailing_configs: Dict[str, TrailingConfig] = {}

        # Stop adjustment history
        self.adjustment_history: List[StopAdjustment] = []

        # Last check time
        self.last_check_time: Optional[datetime] = None

        # Load default config
        self._load_default_config()

        self._initialized = True
        logger.info("Trailing stop manager initialized")

    def _load_default_config(self) -> None:
        """
        Load default trailing stop configuration from config file.

        Loads default settings that will be used unless overridden per-symbol.
        """
        try:
            trailing_config = config.trading.execution.trailing

            self.default_enabled = trailing_config.get('enable', False)
            self.default_type = 'percentage'  # Default to percentage
            self.default_amount = trailing_config.get('trail_distance_pct', 2.0)
            self.default_activation = trailing_config.get('start_at_r', 1.0)
            self.default_min_trail = 0.5  # Default 0.5%

            logger.debug(
                f"Loaded default trailing config: type={self.default_type}, "
                f"amount={self.default_amount}%, activation={self.default_activation}R"
            )

        except Exception as e:
            logger.warning(f"Error loading trailing config, using hardcoded defaults: {e}")
            self.default_enabled = False
            self.default_type = 'percentage'
            self.default_amount = 2.0
            self.default_activation = 1.5
            self.default_min_trail = 0.5

    def enable_trailing_stop(
        self,
        symbol: str,
        trailing_type: str = 'percentage',
        trailing_amount: float = 2.0,
        activation_profit_pct: float = 1.5,
        min_trail_amount: float = 0.005
    ) -> None:
        """
        Enable trailing stop for a position.

        Parameters:
        -----------
        symbol : str
            Symbol to enable trailing stop for
        trailing_type : str, default='percentage'
            'percentage' (fixed %) or 'atr' (ATR multiplier)
        trailing_amount : float, default=2.0
            Trail distance (percentage or ATR multiplier)
        activation_profit_pct : float, default=1.5
            Profit % required before trailing starts
        min_trail_amount : float, default=0.005
            Minimum trail distance (0.5% as decimal)

        Notes:
        ------
        - Trailing will not start until position profit >= activation_profit_pct
        - Trail distance is measured from high water mark (LONG) or low (SHORT)
        - Stops ONLY move in favorable direction

        Examples:
        ---------
        >>> # Enable 2% percentage trail, activate after 1.5% profit
        >>> trailing_stop_manager.enable_trailing_stop(
        ...     symbol='AAPL',
        ...     trailing_type='percentage',
        ...     trailing_amount=2.0,
        ...     activation_profit_pct=1.5
        ... )

        >>> # Enable 3x ATR trail, activate after 2% profit
        >>> trailing_stop_manager.enable_trailing_stop(
        ...     symbol='TSLA',
        ...     trailing_type='atr',
        ...     trailing_amount=3.0,
        ...     activation_profit_pct=2.0
        ... )
        """
        # Validate trailing type
        if trailing_type not in ['percentage', 'atr']:
            logger.error(
                f"Invalid trailing_type '{trailing_type}' for {symbol}. "
                f"Must be 'percentage' or 'atr'"
            )
            return

        # Validate trailing amount
        if trailing_amount <= 0:
            logger.error(f"Invalid trailing_amount {trailing_amount} for {symbol}. Must be > 0")
            return

        # Create configuration
        config_obj = TrailingConfig(
            symbol=symbol,
            trailing_type=trailing_type,
            trailing_amount=trailing_amount,
            activation_profit_pct=activation_profit_pct,
            min_trail_amount=min_trail_amount,
            enabled=True,
            activated=False
        )

        self.trailing_configs[symbol] = config_obj

        logger.info(
            f"Enabled trailing stop for {symbol}: "
            f"type={trailing_type}, amount={trailing_amount}, "
            f"activation={activation_profit_pct}%"
        )

    def disable_trailing_stop(self, symbol: str) -> None:
        """
        Disable trailing stop for a symbol.

        Parameters:
        -----------
        symbol : str
            Symbol to disable trailing for

        Notes:
        ------
        - Removes configuration from active configs
        - Does not modify current stop price
        - Adjustment history is preserved
        """
        if symbol in self.trailing_configs:
            del self.trailing_configs[symbol]
            logger.info(f"Disabled trailing stop for {symbol}")
        else:
            logger.warning(f"No trailing config found for {symbol}")

    def check_and_update_stops(self) -> List[Dict[str, Any]]:
        """
        Check all positions and update trailing stops if needed.

        Called every 1 minute from pipeline scheduler during market hours.

        Returns:
        --------
        List[dict]
            List of stop adjustments made: [
                {
                    'symbol': 'AAPL',
                    'old_stop': 148.50,
                    'new_stop': 149.00,
                    'trigger_price': 152.00,
                    'profit_pct': 2.5,
                    'timestamp': datetime
                },
                ...
            ]

        Notes:
        ------
        - Only checks symbols with enabled trailing stops
        - Only adjusts stops if activation threshold met
        - Logs all adjustments
        - Returns empty list if no adjustments made
        """
        self.last_check_time = datetime.now()

        adjustments = []

        # Get order manager (avoid circular import)
        try:
            from src.execution.order_manager import order_manager
        except ImportError:
            logger.error("Cannot import order_manager for trailing stop check")
            return adjustments

        # Check each trailing config
        for symbol, config_obj in list(self.trailing_configs.items()):
            if not config_obj.enabled:
                continue

            # Get position
            if symbol not in order_manager.positions:
                logger.debug(f"Position {symbol} no longer open, disabling trailing")
                self.disable_trailing_stop(symbol)
                continue

            position = order_manager.positions[symbol]

            # Get current price
            current_price = position.current_price
            if current_price == 0.0:
                logger.debug(f"No current price for {symbol}, skipping")
                continue

            # Calculate new stop price
            new_stop = self._calculate_new_stop_price(
                symbol=symbol,
                current_price=current_price,
                position_side=position.side,
                entry_price=position.entry_price,
                current_stop=position.stop_price or 0.0
            )

            # No adjustment needed
            if new_stop is None:
                continue

            # Record adjustment
            profit_pct = position.unrealized_pnl_pct

            adjustment = StopAdjustment(
                symbol=symbol,
                timestamp=datetime.now(),
                old_stop=position.stop_price,
                new_stop=new_stop,
                trigger_price=current_price,
                trailing_type=config_obj.trailing_type,
                trailing_amount=config_obj.trailing_amount,
                profit_pct=profit_pct
            )

            self.adjustment_history.append(adjustment)
            config_obj.adjustment_count += 1
            config_obj.last_adjustment_time = datetime.now()

            # Add to return list
            adjustments.append({
                'symbol': symbol,
                'old_stop': position.stop_price,
                'new_stop': new_stop,
                'trigger_price': current_price,
                'profit_pct': profit_pct,
                'timestamp': datetime.now()
            })

            logger.debug(
                f"Trailing stop adjustment for {symbol}: "
                f"{position.stop_price:.2f} -> {new_stop:.2f} "
                f"(price: {current_price:.2f}, profit: {profit_pct:+.2f}%)"
            )

        return adjustments

    def _calculate_new_stop_price(
        self,
        symbol: str,
        current_price: float,
        position_side: str,
        entry_price: float,
        current_stop: float
    ) -> Optional[float]:
        """
        Calculate new trailing stop price.

        Logic:
        ------
        1. Check if activation profit threshold met
        2. Calculate trail distance based on type (% or ATR)
        3. Ensure new stop > old stop (LONG) or new stop < old stop (SHORT)
        4. Respect minimum trail amount
        5. Return None if no adjustment needed

        Parameters:
        -----------
        symbol : str
            Stock symbol
        current_price : float
            Current market price
        position_side : str
            'BUY' or 'SELL'
        entry_price : float
            Entry price
        current_stop : float
            Current stop price

        Returns:
        --------
        float or None
            New stop price, or None if no adjustment needed

        Notes:
        ------
        - Returns None if activation threshold not met
        - Returns None if new stop not better than old stop
        - Enforces minimum trail distance
        - Updates highest/lowest price tracking
        """
        if symbol not in self.trailing_configs:
            return None

        config_obj = self.trailing_configs[symbol]

        # Calculate current profit %
        if position_side == 'BUY':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL/SHORT
            profit_pct = ((entry_price - current_price) / entry_price) * 100

        # Check activation threshold
        if not config_obj.activated:
            if profit_pct >= config_obj.activation_profit_pct:
                config_obj.activated = True
                config_obj.activation_price = current_price
                config_obj.activation_time = datetime.now()
                config_obj.highest_price = current_price
                config_obj.lowest_price = current_price

                logger.info(
                    f"Trailing stop ACTIVATED for {symbol} at ${current_price:.2f} "
                    f"(profit: {profit_pct:+.2f}%)"
                )
            else:
                # Not activated yet
                return None

        # Update high water mark / low water mark
        if position_side == 'BUY':
            if current_price > config_obj.highest_price:
                config_obj.highest_price = current_price
        else:  # SHORT
            if current_price < config_obj.lowest_price:
                config_obj.lowest_price = current_price

        # Calculate trail distance
        if config_obj.trailing_type == 'percentage':
            trail_distance_pct = config_obj.trailing_amount / 100
        else:  # ATR
            atr_value = self._get_atr_value(symbol)
            if atr_value is None or atr_value == 0:
                logger.warning(
                    f"ATR value not available for {symbol}, "
                    f"falling back to {config_obj.trailing_amount}% percentage trail"
                )
                trail_distance_pct = config_obj.trailing_amount / 100
            else:
                trail_distance_pct = (atr_value * config_obj.trailing_amount) / current_price

        # Enforce minimum trail distance
        trail_distance_pct = max(trail_distance_pct, config_obj.min_trail_amount)

        # Calculate new stop based on side
        if position_side == 'BUY':
            # LONG: Trail below highest price
            new_stop = config_obj.highest_price * (1 - trail_distance_pct)

            # Only adjust if new stop is higher than current stop
            if current_stop > 0 and new_stop <= current_stop:
                return None

            # Validate improvement (skip very small improvements to reduce noise)
            if current_stop > 0:
                improvement_pct = ((new_stop - current_stop) / current_stop) * 100
                if improvement_pct < 0.01:  # Less than 0.01% improvement (1 basis point)
                    return None

        else:  # SELL/SHORT
            # SHORT: Trail above lowest price
            new_stop = config_obj.lowest_price * (1 + trail_distance_pct)

            # Only adjust if new stop is lower than current stop
            if current_stop > 0 and new_stop >= current_stop:
                return None

            # Validate improvement (skip very small improvements to reduce noise)
            if current_stop > 0:
                improvement_pct = ((current_stop - new_stop) / current_stop) * 100
                if improvement_pct < 0.01:  # Less than 0.01% improvement (1 basis point)
                    return None

        return new_stop

    def _get_atr_value(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Get ATR value for symbol.

        Uses cached historical data and indicator engine for calculation.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        period : int, default=14
            ATR period

        Returns:
        --------
        float or None
            ATR value, or None if calculation fails

        Notes:
        ------
        - Retrieves last 100 bars from historical_manager
        - Calculates ATR using indicator_engine
        - Returns most recent ATR value
        - Returns None if data unavailable
        """
        try:
            from src.data.historical_manager import historical_manager
            from src.indicators.indicator_engine import indicator_engine

            # Get recent bars (need enough for ATR calculation)
            df = historical_manager.load_symbol_data(
                symbol=symbol,
                timeframe='15 mins'
            )

            # Take last 100 bars if more are available
            if df is not None and not df.empty and len(df) > 100:
                df = df.tail(100)

            if df is None or df.empty:
                logger.debug(f"No historical data available for {symbol} ATR calculation")
                return None

            # Calculate ATR
            df = indicator_engine.calculate_atr(df)

            if 'atr' not in df.columns or df['atr'].isna().all():
                logger.debug(f"ATR calculation failed for {symbol}")
                return None

            # Get most recent ATR value
            atr_value = df['atr'].iloc[-1]

            if pd.isna(atr_value):
                return None

            return float(atr_value)

        except Exception as e:
            logger.warning(f"Error getting ATR for {symbol}: {e}")
            return None

    def get_trailing_status(self, symbol: str) -> Dict[str, Any]:
        """
        Get trailing stop status for a symbol.

        Parameters:
        -----------
        symbol : str
            Stock symbol

        Returns:
        --------
        dict
            {
                'enabled': True/False,
                'config': {...} or None,
                'activated': True/False,
                'current_profit_pct': 2.5 or None,
                'activation_threshold': 1.5,
                'last_adjustment': datetime or None,
                'adjustment_count': 3,
                'highest_price': 152.50 or None,
                'lowest_price': None (for longs)
            }

        Notes:
        ------
        - Returns minimal status if no config exists
        - Includes profit % if position exists
        """
        if symbol not in self.trailing_configs:
            return {
                'enabled': False,
                'config': None,
                'activated': False,
                'current_profit_pct': None,
                'activation_threshold': None,
                'last_adjustment': None,
                'adjustment_count': 0,
                'highest_price': None,
                'lowest_price': None
            }

        config_obj = self.trailing_configs[symbol]

        # Get current profit if position exists
        current_profit_pct = None
        try:
            from src.execution.order_manager import order_manager
            if symbol in order_manager.positions:
                position = order_manager.positions[symbol]
                current_profit_pct = position.unrealized_pnl_pct
        except:
            pass

        return {
            'enabled': config_obj.enabled,
            'config': {
                'trailing_type': config_obj.trailing_type,
                'trailing_amount': config_obj.trailing_amount,
                'activation_profit_pct': config_obj.activation_profit_pct,
                'min_trail_amount': config_obj.min_trail_amount
            },
            'activated': config_obj.activated,
            'current_profit_pct': current_profit_pct,
            'activation_threshold': config_obj.activation_profit_pct,
            'last_adjustment': config_obj.last_adjustment_time,
            'adjustment_count': config_obj.adjustment_count,
            'highest_price': config_obj.highest_price if config_obj.activated else None,
            'lowest_price': config_obj.lowest_price if config_obj.activated else None
        }

    def get_adjustment_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of stop adjustments with optional filters.

        Parameters:
        -----------
        symbol : str, optional
            Filter by symbol
        start_date : datetime, optional
            Filter by timestamp >= start_date
        end_date : datetime, optional
            Filter by timestamp <= end_date

        Returns:
        --------
        List[dict]
            List of adjustment records: [
                {
                    'symbol': 'AAPL',
                    'timestamp': datetime,
                    'old_stop': 148.50,
                    'new_stop': 149.00,
                    'trigger_price': 152.00,
                    'trailing_type': 'percentage',
                    'trailing_amount': 2.0,
                    'profit_pct': 2.5
                },
                ...
            ]

        Notes:
        ------
        - Returns all adjustments if no filters provided
        - Sorted by timestamp (newest first)
        """
        results = []

        for adj in self.adjustment_history:
            # Apply filters
            if symbol and adj.symbol != symbol:
                continue

            if start_date and adj.timestamp < start_date:
                continue

            if end_date and adj.timestamp > end_date:
                continue

            # Convert to dict
            results.append({
                'symbol': adj.symbol,
                'timestamp': adj.timestamp,
                'old_stop': adj.old_stop,
                'new_stop': adj.new_stop,
                'trigger_price': adj.trigger_price,
                'trailing_type': adj.trailing_type,
                'trailing_amount': adj.trailing_amount,
                'profit_pct': adj.profit_pct
            })

        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)

        return results


# Global singleton instance
trailing_stop_manager = TrailingStopManager()
