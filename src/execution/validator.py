"""
Trade execution validation with comprehensive risk controls.

This module provides validation for trade execution with strict risk management:
- Maximum 1% risk per trade
- Maximum 3% total portfolio risk
- Position size calculation
- Stop loss validation
- Account balance checks

Features:
- Risk-based position sizing
- Portfolio exposure tracking
- Multi-level validation (symbol, price, quantity, risk)
- Detailed rejection reasons
- Thread-safe operations

Author: Screener Trading System
Date: 2025-11-15
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

from loguru import logger


class ValidationResult(Enum):
    """Validation result status."""

    APPROVED = 'approved'
    REJECTED = 'rejected'
    WARNING = 'warning'


class RejectionReason(Enum):
    """Reasons for trade rejection."""

    # Risk-based rejections
    RISK_PER_TRADE_EXCEEDED = 'risk_per_trade_exceeded'  # > 1%
    TOTAL_PORTFOLIO_RISK_EXCEEDED = 'total_portfolio_risk_exceeded'  # > 3%
    INSUFFICIENT_ACCOUNT_BALANCE = 'insufficient_account_balance'

    # Position-based rejections
    POSITION_SIZE_TOO_SMALL = 'position_size_too_small'
    POSITION_SIZE_TOO_LARGE = 'position_size_too_large'
    MAX_POSITION_COUNT_EXCEEDED = 'max_position_count_exceeded'

    # Price-based rejections
    PRICE_OUT_OF_RANGE = 'price_out_of_range'
    STOP_LOSS_INVALID = 'stop_loss_invalid'
    STOP_LOSS_TOO_WIDE = 'stop_loss_too_wide'
    STOP_LOSS_TOO_TIGHT = 'stop_loss_too_tight'

    # Symbol-based rejections
    SYMBOL_INVALID = 'symbol_invalid'
    SYMBOL_NOT_ALLOWED = 'symbol_not_allowed'

    # Order-based rejections
    ORDER_TYPE_INVALID = 'order_type_invalid'
    QUANTITY_INVALID = 'quantity_invalid'
    SIDE_INVALID = 'side_invalid'


@dataclass
class TradeProposal:
    """Proposed trade for validation."""

    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    order_type: str = 'LIMIT'
    time_in_force: str = 'DAY'
    account_size: float = 0.0  # Set by validator if not provided

    def __post_init__(self):
        """Validate basic fields."""
        if self.side not in ('BUY', 'SELL'):
            raise ValueError(f"Invalid side: {self.side}")
        if self.quantity <= 0:
            raise ValueError(f"Invalid quantity: {self.quantity}")
        if self.entry_price <= 0:
            raise ValueError(f"Invalid entry price: {self.entry_price}")
        if self.stop_loss <= 0:
            raise ValueError(f"Invalid stop loss: {self.stop_loss}")

    @property
    def risk_per_share(self) -> float:
        """Calculate risk per share."""
        if self.side == 'BUY':
            return abs(self.entry_price - self.stop_loss)
        else:  # SELL
            return abs(self.stop_loss - self.entry_price)

    @property
    def total_risk(self) -> float:
        """Calculate total dollar risk for the trade."""
        return self.risk_per_share * self.quantity

    @property
    def position_value(self) -> float:
        """Calculate total position value."""
        return self.entry_price * self.quantity

    @property
    def risk_percent(self) -> float:
        """Calculate risk as percentage of account (if account_size set)."""
        if self.account_size > 0:
            return (self.total_risk / self.account_size) * 100.0
        return 0.0


@dataclass
class ValidationReport:
    """Result of trade validation."""

    result: ValidationResult
    approved: bool
    symbol: str
    proposal: TradeProposal
    rejections: List[RejectionReason] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_metrics: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def rejection_messages(self) -> List[str]:
        """Get human-readable rejection messages."""
        messages = {
            RejectionReason.RISK_PER_TRADE_EXCEEDED: (
                f"Trade risk ({self.risk_metrics.get('risk_percent', 0):.2f}%) "
                f"exceeds 1% maximum"
            ),
            RejectionReason.TOTAL_PORTFOLIO_RISK_EXCEEDED: (
                f"Total portfolio risk ({self.risk_metrics.get('total_portfolio_risk', 0):.2f}%) "
                f"would exceed 3% maximum"
            ),
            RejectionReason.INSUFFICIENT_ACCOUNT_BALANCE: (
                f"Insufficient balance: need ${self.proposal.position_value:,.2f}, "
                f"have ${self.risk_metrics.get('available_balance', 0):,.2f}"
            ),
            RejectionReason.POSITION_SIZE_TOO_SMALL: (
                f"Position size {self.proposal.quantity} shares is too small (min: "
                f"{self.risk_metrics.get('min_position_size', 1)})"
            ),
            RejectionReason.POSITION_SIZE_TOO_LARGE: (
                f"Position size {self.proposal.quantity} shares is too large (max: "
                f"{self.risk_metrics.get('max_position_size', 'N/A')})"
            ),
            RejectionReason.STOP_LOSS_TOO_WIDE: (
                f"Stop loss distance ({self.risk_metrics.get('stop_distance_percent', 0):.2f}%) "
                f"is too wide (max: {self.risk_metrics.get('max_stop_distance', 10):.2f}%)"
            ),
            RejectionReason.STOP_LOSS_TOO_TIGHT: (
                f"Stop loss distance ({self.risk_metrics.get('stop_distance_percent', 0):.2f}%) "
                f"is too tight (min: {self.risk_metrics.get('min_stop_distance', 0.5):.2f}%)"
            ),
            RejectionReason.SYMBOL_INVALID: f"Invalid symbol: {self.symbol}",
            RejectionReason.SYMBOL_NOT_ALLOWED: f"Symbol {self.symbol} is not in allowed list",
        }

        return [messages.get(r, str(r)) for r in self.rejections]


class ExecutionValidator:
    """
    Validate trades with comprehensive risk management.

    This class enforces strict risk controls on all trades:
    - Maximum 1% risk per trade
    - Maximum 3% total portfolio risk
    - Position size limits
    - Stop loss validation
    - Account balance checks

    Parameters:
    -----------
    account_size : float
        Total account size in dollars
    max_risk_per_trade_percent : float, default=1.0
        Maximum risk per trade as percentage (default 1%)
    max_total_risk_percent : float, default=3.0
        Maximum total portfolio risk as percentage (default 3%)
    max_positions : int, default=10
        Maximum number of concurrent positions
    min_position_size : int, default=1
        Minimum position size in shares
    max_position_size : Optional[int], default=None
        Maximum position size in shares
    min_stop_distance_percent : float, default=0.5
        Minimum stop loss distance as percentage
    max_stop_distance_percent : float, default=10.0
        Maximum stop loss distance as percentage
    allowed_symbols : Optional[List[str]], default=None
        List of allowed symbols (None = all allowed)

    Examples:
    ---------
    >>> validator = ExecutionValidator(account_size=100000)
    >>> proposal = TradeProposal(
    ...     symbol='AAPL',
    ...     side='BUY',
    ...     quantity=100,
    ...     entry_price=150.00,
    ...     stop_loss=148.00
    ... )
    >>> report = validator.validate(proposal)
    >>> if report.approved:
    ...     print("Trade approved!")
    """

    def __init__(
        self,
        account_size: float,
        max_risk_per_trade_percent: float = 1.0,
        max_total_risk_percent: float = 3.0,
        max_positions: int = 10,
        min_position_size: int = 1,
        max_position_size: Optional[int] = None,
        min_stop_distance_percent: float = 0.5,
        max_stop_distance_percent: float = 10.0,
        allowed_symbols: Optional[List[str]] = None,
    ):
        """Initialize execution validator."""
        self.account_size = account_size
        self.max_risk_per_trade_percent = max_risk_per_trade_percent
        self.max_total_risk_percent = max_total_risk_percent
        self.max_positions = max_positions
        self.min_position_size = min_position_size
        self.max_position_size = max_position_size
        self.min_stop_distance_percent = min_stop_distance_percent
        self.max_stop_distance_percent = max_stop_distance_percent
        self.allowed_symbols = allowed_symbols

        # Track current positions: {symbol: risk_amount}
        self._current_positions: Dict[str, float] = {}

        # Thread safety
        self._lock = threading.RLock()

        logger.info(
            f"ExecutionValidator initialized: "
            f"Account=${account_size:,.2f}, "
            f"Max risk per trade={max_risk_per_trade_percent}%, "
            f"Max total risk={max_total_risk_percent}%"
        )

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        risk_amount: Optional[float] = None,
    ) -> int:
        """
        Calculate position size based on risk.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        risk_amount : float, optional
            Dollar amount to risk (default: 1% of account)

        Returns:
        --------
        int
            Number of shares to buy
        """
        if risk_amount is None:
            risk_amount = self.account_size * (self.max_risk_per_trade_percent / 100.0)

        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            logger.warning(f"Zero risk per share for {symbol}, cannot calculate position size")
            return 0

        position_size = int(risk_amount / risk_per_share)

        # Apply limits
        if self.max_position_size:
            position_size = min(position_size, self.max_position_size)

        position_size = max(position_size, self.min_position_size)

        logger.debug(
            f"Calculated position size for {symbol}: {position_size} shares "
            f"(risk=${risk_amount:,.2f}, risk/share=${risk_per_share:.2f})"
        )

        return position_size

    def validate(self, proposal: TradeProposal) -> ValidationReport:
        """
        Validate trade proposal with comprehensive risk checks.

        Parameters:
        -----------
        proposal : TradeProposal
            Trade proposal to validate

        Returns:
        --------
        ValidationReport
            Validation result with detailed feedback
        """
        with self._lock:
            # Set account size in proposal if not set
            if proposal.account_size == 0:
                proposal.account_size = self.account_size

            rejections = []
            warnings = []
            risk_metrics = {}

            # Calculate risk metrics
            risk_per_share = proposal.risk_per_share
            total_risk = proposal.total_risk
            risk_percent = proposal.risk_percent
            position_value = proposal.position_value

            risk_metrics['risk_per_share'] = risk_per_share
            risk_metrics['total_risk'] = total_risk
            risk_metrics['risk_percent'] = risk_percent
            risk_metrics['position_value'] = position_value

            # 1. Symbol validation
            if not proposal.symbol or len(proposal.symbol) == 0:
                rejections.append(RejectionReason.SYMBOL_INVALID)

            if self.allowed_symbols and proposal.symbol not in self.allowed_symbols:
                rejections.append(RejectionReason.SYMBOL_NOT_ALLOWED)

            # 2. Quantity validation
            if proposal.quantity < self.min_position_size:
                rejections.append(RejectionReason.POSITION_SIZE_TOO_SMALL)
                risk_metrics['min_position_size'] = self.min_position_size

            if self.max_position_size and proposal.quantity > self.max_position_size:
                rejections.append(RejectionReason.POSITION_SIZE_TOO_LARGE)
                risk_metrics['max_position_size'] = self.max_position_size

            # 3. Stop loss validation
            stop_distance_percent = (risk_per_share / proposal.entry_price) * 100.0
            risk_metrics['stop_distance_percent'] = stop_distance_percent

            if stop_distance_percent < self.min_stop_distance_percent:
                rejections.append(RejectionReason.STOP_LOSS_TOO_TIGHT)
                risk_metrics['min_stop_distance'] = self.min_stop_distance_percent

            if stop_distance_percent > self.max_stop_distance_percent:
                rejections.append(RejectionReason.STOP_LOSS_TOO_WIDE)
                risk_metrics['max_stop_distance'] = self.max_stop_distance_percent

            # Validate stop loss direction
            if proposal.side == 'BUY' and proposal.stop_loss >= proposal.entry_price:
                rejections.append(RejectionReason.STOP_LOSS_INVALID)
                warnings.append("Stop loss must be below entry price for BUY orders")

            if proposal.side == 'SELL' and proposal.stop_loss <= proposal.entry_price:
                rejections.append(RejectionReason.STOP_LOSS_INVALID)
                warnings.append("Stop loss must be above entry price for SELL orders")

            # 4. Risk per trade validation (CRITICAL - 1% max)
            if risk_percent > self.max_risk_per_trade_percent:
                rejections.append(RejectionReason.RISK_PER_TRADE_EXCEEDED)
                logger.warning(
                    f"Trade rejected: risk {risk_percent:.2f}% exceeds "
                    f"{self.max_risk_per_trade_percent}% maximum for {proposal.symbol}"
                )

            # 5. Total portfolio risk validation (CRITICAL - 3% max)
            current_total_risk = sum(self._current_positions.values())
            new_total_risk = current_total_risk + total_risk
            total_portfolio_risk_percent = (new_total_risk / self.account_size) * 100.0

            risk_metrics['current_portfolio_risk'] = current_total_risk
            risk_metrics['total_portfolio_risk'] = total_portfolio_risk_percent

            if total_portfolio_risk_percent > self.max_total_risk_percent:
                rejections.append(RejectionReason.TOTAL_PORTFOLIO_RISK_EXCEEDED)
                logger.warning(
                    f"Trade rejected: total portfolio risk {total_portfolio_risk_percent:.2f}% "
                    f"would exceed {self.max_total_risk_percent}% maximum"
                )

            # 6. Account balance validation
            available_balance = self.account_size - current_total_risk
            risk_metrics['available_balance'] = available_balance

            if position_value > available_balance:
                rejections.append(RejectionReason.INSUFFICIENT_ACCOUNT_BALANCE)

            # 7. Position count validation
            if len(self._current_positions) >= self.max_positions:
                if proposal.symbol not in self._current_positions:
                    rejections.append(RejectionReason.MAX_POSITION_COUNT_EXCEEDED)
                    warnings.append(
                        f"Already have {len(self._current_positions)} positions "
                        f"(max: {self.max_positions})"
                    )

            # Determine result
            if len(rejections) > 0:
                result = ValidationResult.REJECTED
                approved = False
            elif len(warnings) > 0:
                result = ValidationResult.WARNING
                approved = True
            else:
                result = ValidationResult.APPROVED
                approved = True

            report = ValidationReport(
                result=result,
                approved=approved,
                symbol=proposal.symbol,
                proposal=proposal,
                rejections=rejections,
                warnings=warnings,
                risk_metrics=risk_metrics,
            )

            if approved:
                logger.info(
                    f"Trade APPROVED: {proposal.symbol} {proposal.side} "
                    f"{proposal.quantity} @ ${proposal.entry_price:.2f} "
                    f"(risk: {risk_percent:.2f}%)"
                )
            else:
                logger.warning(
                    f"Trade REJECTED: {proposal.symbol} - "
                    f"{[str(r) for r in rejections]}"
                )

            return report

    def add_position(self, symbol: str, risk_amount: float):
        """
        Add position to tracking.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        risk_amount : float
            Dollar amount at risk
        """
        with self._lock:
            self._current_positions[symbol] = risk_amount
            logger.info(
                f"Added position: {symbol} with risk ${risk_amount:,.2f} "
                f"(total positions: {len(self._current_positions)})"
            )

    def remove_position(self, symbol: str):
        """
        Remove position from tracking.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        """
        with self._lock:
            if symbol in self._current_positions:
                risk = self._current_positions.pop(symbol)
                logger.info(
                    f"Removed position: {symbol} (freed ${risk:,.2f} risk)"
                )

    def update_position_risk(self, symbol: str, new_risk: float):
        """
        Update risk amount for existing position.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        new_risk : float
            New risk amount
        """
        with self._lock:
            if symbol in self._current_positions:
                old_risk = self._current_positions[symbol]
                self._current_positions[symbol] = new_risk
                logger.info(
                    f"Updated {symbol} risk: ${old_risk:,.2f} → ${new_risk:,.2f}"
                )

    def get_current_positions(self) -> Dict[str, float]:
        """
        Get current positions and risk amounts.

        Returns:
        --------
        dict
            Dictionary of {symbol: risk_amount}
        """
        with self._lock:
            return self._current_positions.copy()

    def get_portfolio_stats(self) -> Dict:
        """
        Get portfolio risk statistics.

        Returns:
        --------
        dict
            Statistics including total risk, available risk, etc.
        """
        with self._lock:
            total_risk = sum(self._current_positions.values())
            total_risk_percent = (total_risk / self.account_size) * 100.0
            available_risk = (
                self.account_size * (self.max_total_risk_percent / 100.0) - total_risk
            )
            available_risk_percent = (available_risk / self.account_size) * 100.0

            return {
                'account_size': self.account_size,
                'total_risk': total_risk,
                'total_risk_percent': total_risk_percent,
                'available_risk': available_risk,
                'available_risk_percent': available_risk_percent,
                'num_positions': len(self._current_positions),
                'max_positions': self.max_positions,
                'positions': self._current_positions.copy(),
            }

    def reset(self):
        """Reset all positions (for testing/emergency)."""
        with self._lock:
            self._current_positions.clear()
            logger.warning("ExecutionValidator reset - all positions cleared")


def create_validator(
    account_size: float,
    **kwargs
) -> ExecutionValidator:
    """
    Factory function to create ExecutionValidator.

    Parameters:
    -----------
    account_size : float
        Total account size in dollars
    **kwargs
        Additional arguments passed to ExecutionValidator

    Returns:
    --------
    ExecutionValidator
        Configured validator instance
    """
    return ExecutionValidator(account_size=account_size, **kwargs)
