"""
Trade Execution & Risk Management Layer

Handles order placement, position tracking, and risk controls:
- Pre-trade validation (risk limits, R:R requirements)
- Order execution via IB API (bracket orders)
- Position tracking (real-time P&L, risk exposure)
- Exit management (trailing stops, time-based exits)
- Performance analytics

Key Components:
---------------
validator : RiskValidator class for pre-trade checks
executor : OrderExecutor class for IB order placement
position_tracker : PositionTracker class for P&L and risk tracking

Risk Limits (CRITICAL):
-----------------------
- Max risk per trade: 1% of account equity
- Max total portfolio risk: 3% of account equity
- Max concurrent positions: 5
- Min R:R ratio: 1.5:1

Order Types:
------------
- Bracket orders (entry + stop + target)
- Market orders (emergency exits)
- Stop orders (trailing stops)
- Limit orders (entry optimization)

NEVER:
------
- Exceed risk limits
- Place orders without validation
- Skip pre-trade checks
- Trade without stops
"""

from .validator import (
    ExecutionValidator,
    TradeProposal,
    ValidationReport,
    ValidationResult,
    RejectionReason,
    create_validator,
)

__all__ = [
    'ExecutionValidator',
    'TradeProposal',
    'ValidationReport',
    'ValidationResult',
    'RejectionReason',
    'create_validator',
]
