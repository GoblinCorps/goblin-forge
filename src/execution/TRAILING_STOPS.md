# Trailing Stop Management System

Complete guide to the trailing stop management system for the Screener trading platform.

---

## Table of Contents

1. [Overview](#overview)
2. [How Trailing Stops Work](#how-trailing-stops-work)
3. [Configuration](#configuration)
4. [Trailing Types](#trailing-types)
5. [Activation Thresholds](#activation-thresholds)
6. [Integration](#integration)
7. [Best Practices](#best-practices)
8. [Examples](#examples)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The trailing stop management system automatically adjusts stop losses to protect profits while allowing winning trades to run. Key features:

- **Automatic Adjustments**: Stops trail price movements every 1 minute during market hours
- **Dual Methods**: Percentage-based or ATR-based trailing
- **Activation Thresholds**: Only trails after minimum profit achieved
- **Safety Guarantees**: Stops ONLY move in profit direction (never against)
- **Database Logging**: All adjustments logged for audit trail

**Safety**: Trailing stops NEVER move against your profit direction. For LONG positions, stops only move UP. For SHORT positions, stops only move DOWN.

---

## How Trailing Stops Work

### Basic Concept

A trailing stop is a stop loss that automatically moves in your favor as the trade becomes profitable:

```
LONG Position Example:
Entry:  $150.00
Stop:   $148.00 (initial)
Price:  $152.00 (2% profit)

Without trailing:
  Stop stays at $148.00

With 2% trailing (activated at 1.5% profit):
  Stop moves to $148.96 (152 * 0.98)
  Locks in some profit!

Price rises to $154.00:
  Stop moves to $150.92 (154 * 0.98)
  More profit locked in!

Price drops to $153.00:
  Stop stays at $150.92 (doesn't move down)
  Protects gains even if price retraces
```

### Lifecycle

1. **Position Opened** → Stop at initial level
2. **Profit Threshold Met** → Trailing activates
3. **Price Moves Favorably** → Stop trails behind
4. **Price Retraces** → Stop remains at best level
5. **Stop Hit** → Position closed with profit

---

## Configuration

### Global Default Settings

In `config/trading_params.yaml`:

```yaml
trailing_stops:
  # Default settings for all positions
  default:
    enabled: false              # Enable by default
    type: percentage            # 'percentage' or 'atr'
    amount: 2.0                 # 2% or 2x ATR
    activation_profit_pct: 1.5  # Activate after 1.5% profit
    min_trail_amount: 0.005     # Minimum 0.5% trail

  # Symbol-specific overrides
  symbol_overrides:
    # High volatility stocks - wider trail
    TSLA:
      type: atr
      amount: 3.0
      activation_profit_pct: 2.0

    # Low volatility stocks - tighter trail
    KO:
      type: percentage
      amount: 1.5
      activation_profit_pct: 1.0

  # Check frequency
  check_interval_seconds: 60  # Check every 1 minute
```

### Per-Position Configuration

Enable trailing for specific positions programmatically:

```python
from src.execution.order_manager import order_manager

# After opening a position
order_manager.enable_trailing_stop_for_position(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0,
    activation_profit_pct=1.5
)
```

Or directly via trailing stop manager:

```python
from src.execution.trailing_stop_manager import trailing_stop_manager

trailing_stop_manager.enable_trailing_stop(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0,
    activation_profit_pct=1.5,
    min_trail_amount=0.005
)
```

---

## Trailing Types

### 1. Percentage-Based Trailing

**How it works**: Stop trails at a fixed percentage below the high water mark (LONG) or above low water mark (SHORT).

**Formula (LONG)**:
```
new_stop = highest_price * (1 - trail_percentage)

Example:
  highest_price = $152.00
  trail_percentage = 2% (0.02)
  new_stop = $152.00 * 0.98 = $148.96
```

**Formula (SHORT)**:
```
new_stop = lowest_price * (1 + trail_percentage)

Example:
  lowest_price = $198.00
  trail_percentage = 2% (0.02)
  new_stop = $198.00 * 1.02 = $201.96
```

**Best for**:
- Stocks with consistent volatility
- Beginners (simple to understand)
- Automated systems with standard risk

**Configuration**:
```python
trailing_stop_manager.enable_trailing_stop(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0  # 2%
)
```

### 2. ATR-Based Trailing

**How it works**: Stop trails at a multiple of ATR (Average True Range) from the high/low water mark.

**Formula (LONG)**:
```
trail_distance_dollars = ATR * atr_multiplier
new_stop = highest_price - trail_distance_dollars

Example:
  highest_price = $152.00
  ATR = $3.00
  atr_multiplier = 2.0
  new_stop = $152.00 - ($3.00 * 2.0) = $146.00
```

**Formula (SHORT)**:
```
trail_distance_dollars = ATR * atr_multiplier
new_stop = lowest_price + trail_distance_dollars
```

**Best for**:
- High volatility stocks (TSLA, NVDA, crypto)
- Adapts to changing market conditions
- Swing traders

**Configuration**:
```python
trailing_stop_manager.enable_trailing_stop(
    symbol='TSLA',
    trailing_type='atr',
    trailing_amount=3.0  # 3x ATR
)
```

**ATR Details**:
- Uses 14-period ATR by default
- Calculated from recent 100 bars
- Falls back to percentage if ATR unavailable
- Cached for performance

---

## Activation Thresholds

### Why Use Activation Thresholds?

Activation thresholds prevent trailing stops from tightening too early:

**Without Activation** (bad):
```
Entry:  $150.00
Stop:   $148.00
Price:  $150.50 (0.33% profit)
Trail:  2%

New stop: $150.50 * 0.98 = $147.49
Risk if stopped: $150.00 - $147.49 = $2.51 (worse than initial $2.00!)
```

**With Activation at 1.5%** (good):
```
Entry:  $150.00
Stop:   $148.00
Price:  $150.50 (0.33% profit)
Trail:  Not activated yet

Price:  $152.50 (1.67% profit)
Trail:  NOW activated!

New stop: $152.50 * 0.98 = $149.45
Profit locked in: $149.45 - $150.00 = -$0.55 (small loss vs $2.00 risk)
```

### Recommended Thresholds

| Strategy | Activation Threshold | Reasoning |
|----------|---------------------|-----------|
| Scalp | 0.5% - 1.0% | Quick profits, tight trail |
| Day trade | 1.0% - 1.5% | Balance speed and profit |
| Swing trade | 1.5% - 2.5% | Room for daily volatility |
| Position trade | 2.0% - 5.0% | Long-term trend following |

**Rule of Thumb**: Activation threshold should be ≥ (initial stop distance / 2)

```python
entry = 150.00
initial_stop = 148.00
stop_distance = entry - initial_stop  # $2.00
stop_distance_pct = (stop_distance / entry) * 100  # 1.33%

activation_threshold = stop_distance_pct / 2  # 0.67%
# Use 1.0% for safety margin
```

---

## Integration

### System Architecture

```
RealtimeAggregator
      ↓ (new bar every 5s/15m/1h)
OrderManager.update_position_price()
      ↓ (current_price updated)
TrailingStopScheduler (every 1 minute)
      ↓
TrailingStopManager.check_and_update_stops()
      ↓ (calculates new stops)
OrderManager.modify_stop()
      ↓ (updates position & database)
IB Gateway (if connected)
      ↓
Stop order modified
```

### Pipeline Integration

The trailing stop scheduler runs as a background thread:

```python
# In main pipeline orchestrator
import threading
from src.pipeline.trailing_stop_scheduler import start_trailing_stop_scheduler

# Start trailing stop scheduler in background
scheduler_thread = threading.Thread(
    target=start_trailing_stop_scheduler,
    args=(60,),  # Check every 60 seconds
    daemon=True,
    name='TrailingStopScheduler'
)
scheduler_thread.start()
```

### Manual Integration

For testing or manual control:

```python
from src.pipeline.trailing_stop_scheduler import run_trailing_stop_check

# Single check
run_trailing_stop_check()

# Custom loop
import time
while True:
    run_trailing_stop_check()
    time.sleep(60)  # 1 minute
```

---

## Best Practices

### 1. Match Trail Distance to Strategy

**Scalping** (seconds to minutes):
```python
trailing_amount=1.0  # Tight 1% trail
activation_profit_pct=0.5  # Quick activation
```

**Day Trading** (minutes to hours):
```python
trailing_amount=2.0  # Standard 2% trail
activation_profit_pct=1.5  # Balanced activation
```

**Swing Trading** (days to weeks):
```python
trailing_type='atr'
trailing_amount=3.0  # Wide 3x ATR trail
activation_profit_pct=2.5  # Room to breathe
```

### 2. Use ATR for High Volatility

High volatility stocks need wider trails to avoid premature stops:

```python
# TSLA, NVDA, COIN, etc.
trailing_stop_manager.enable_trailing_stop(
    symbol='TSLA',
    trailing_type='atr',
    trailing_amount=3.0,  # 3x ATR = ~6% typical
    activation_profit_pct=2.0
)
```

### 3. Respect Minimum Trail Distance

Always set minimum trail to prevent whipsaws:

```python
trailing_stop_manager.enable_trailing_stop(
    symbol='AAPL',
    trailing_amount=0.3,  # Very tight 0.3%
    min_trail_amount=0.005  # But minimum 0.5%
)
# Actual trail will be 0.5% (minimum enforced)
```

### 4. Combine with Profit Targets

Use trailing stops for runners after partial exits:

```python
# Entry: $150, Stop: $148, Target: $154 (2R)

# At first target ($154), take 50% off
order_manager.close_position(
    symbol='AAPL',
    exit_price=154.00,
    quantity=50  # Half position
)

# Enable trailing for remaining 50%
order_manager.enable_trailing_stop_for_position(
    symbol='AAPL',
    trailing_amount=2.0,
    activation_profit_pct=0.0  # Already profitable
)
```

### 5. Monitor Adjustment History

Track how often stops are adjusting:

```python
from src.execution.trailing_stop_manager import trailing_stop_manager

# Get recent adjustments
history = trailing_stop_manager.get_adjustment_history(
    symbol='AAPL',
    start_date=datetime.now() - timedelta(days=1)
)

print(f"Adjustments in last 24h: {len(history)}")
for adj in history:
    print(f"  {adj['timestamp']}: ${adj['old_stop']:.2f} → ${adj['new_stop']:.2f}")
```

**Healthy Pattern**: 2-5 adjustments per winning trade
**Too Tight**: >10 adjustments (whipsaw risk)
**Too Loose**: 0-1 adjustments (not trailing enough)

### 6. Test Before Live Trading

Backtest trailing stop performance:

```python
# Simulate trailing stop behavior
from src.execution.trailing_stop_manager import TrailingStopManager

manager = TrailingStopManager()
manager.enable_trailing_stop(
    symbol='TEST',
    trailing_amount=2.0,
    activation_profit_pct=1.5
)

# Feed historical prices
for price in historical_prices:
    new_stop = manager._calculate_new_stop_price(
        symbol='TEST',
        current_price=price,
        position_side='BUY',
        entry_price=entry,
        current_stop=current_stop
    )

    if new_stop:
        print(f"Price ${price:.2f}: Stop adjusted to ${new_stop:.2f}")
        current_stop = new_stop
```

---

## Examples

### Example 1: Standard Day Trade (Percentage)

```python
from src.execution.order_manager import order_manager

# Open position
order_manager.open_position(
    symbol='AAPL',
    side='BUY',
    quantity=100,
    entry_price=150.00,
    stop_price=148.00,
    target_price=154.00,
    risk_amount=200.00
)

# Enable 2% trailing, activate after 1.5% profit
order_manager.enable_trailing_stop_for_position(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0,
    activation_profit_pct=1.5
)

# Price movement and stop adjustments:
# $150.00 → Entry
# $152.00 → 1.33% profit (not activated yet)
# $152.30 → 1.53% profit → ACTIVATED, stop = $149.25
# $153.00 → 2.00% profit → stop = $149.94
# $154.00 → 2.67% profit → stop = $150.92
# $153.00 → Retraces → stop stays at $150.92
# $150.92 → Stop hit → Exit with $0.92/share profit
```

### Example 2: High Volatility Swing Trade (ATR)

```python
# TSLA swing trade
order_manager.open_position(
    symbol='TSLA',
    side='BUY',
    quantity=50,
    entry_price=200.00,
    stop_price=195.00,
    target_price=220.00,
    risk_amount=250.00
)

# Enable 3x ATR trailing, activate after 2% profit
order_manager.enable_trailing_stop_for_position(
    symbol='TSLA',
    trailing_type='atr',
    trailing_amount=3.0,
    activation_profit_pct=2.0
)

# Assume ATR = $5.00
# Price movement:
# $200.00 → Entry
# $204.00 → 2.0% profit → ACTIVATED
#   Trail: 3 * $5.00 = $15.00
#   Stop = $204.00 - $15.00 = $189.00
# $210.00 → 5.0% profit
#   Stop = $210.00 - $15.00 = $195.00
# $215.00 → 7.5% profit
#   Stop = $215.00 - $15.00 = $200.00 (breakeven)
# $220.00 → 10% profit
#   Stop = $220.00 - $15.00 = $205.00 (locked in $5/share)
```

### Example 3: Short Position Trailing

```python
# Short TSLA
order_manager.open_position(
    symbol='TSLA',
    side='SELL',
    quantity=50,
    entry_price=200.00,
    stop_price=202.00,
    target_price=196.00,
    risk_amount=100.00
)

# Enable 2% trailing
order_manager.enable_trailing_stop_for_position(
    symbol='TSLA',
    trailing_type='percentage',
    trailing_amount=2.0,
    activation_profit_pct=1.0
)

# Price movement (SHORT):
# $200.00 → Entry
# $198.00 → 1.0% profit → ACTIVATED
#   Stop = $198.00 * 1.02 = $201.96
# $196.00 → 2.0% profit
#   Stop = $196.00 * 1.02 = $199.92
# $195.00 → 2.5% profit
#   Stop = $195.00 * 1.02 = $198.90
# $197.00 → Moves against us
#   Stop stays at $198.90 (doesn't move up)
# $198.90 → Stop hit → Exit with $1.10/share profit
```

### Example 4: Partial Exit with Trailing Runner

```python
# Open position
order_manager.open_position(
    symbol='AAPL',
    side='BUY',
    quantity=200,
    entry_price=150.00,
    stop_price=148.00,
    target_price=154.00,
    risk_amount=400.00
)

# Price hits first target
if current_price >= 154.00:
    # Take 50% off at target
    order_manager.close_position(
        symbol='AAPL',
        exit_price=154.00,
        exit_reason='TARGET',
        quantity=100  # Half
    )

    # Enable trailing for runner
    order_manager.enable_trailing_stop_for_position(
        symbol='AAPL',
        trailing_amount=2.0,
        activation_profit_pct=0.0  # Already profitable
    )

    # Let runner ride with trailing stop protection
```

---

## API Reference

### TrailingStopManager

#### `enable_trailing_stop(symbol, trailing_type, trailing_amount, activation_profit_pct, min_trail_amount)`

Enable trailing stop for a position.

**Parameters**:
- `symbol` (str): Stock symbol
- `trailing_type` (str): 'percentage' or 'atr'
- `trailing_amount` (float): Trail distance (percentage or ATR multiplier)
- `activation_profit_pct` (float): Profit % required before trailing starts
- `min_trail_amount` (float): Minimum trail distance (as decimal, e.g., 0.005 = 0.5%)

**Returns**: None

**Example**:
```python
trailing_stop_manager.enable_trailing_stop(
    symbol='AAPL',
    trailing_type='percentage',
    trailing_amount=2.0,
    activation_profit_pct=1.5,
    min_trail_amount=0.005
)
```

#### `disable_trailing_stop(symbol)`

Disable trailing stop for a symbol.

**Parameters**:
- `symbol` (str): Stock symbol

**Returns**: None

#### `check_and_update_stops()`

Check all positions and update trailing stops if needed.

**Returns**: List[dict] - List of adjustments made

**Example**:
```python
adjustments = trailing_stop_manager.check_and_update_stops()
for adj in adjustments:
    print(f"{adj['symbol']}: ${adj['old_stop']} → ${adj['new_stop']}")
```

#### `get_trailing_status(symbol)`

Get trailing stop status for a symbol.

**Parameters**:
- `symbol` (str): Stock symbol

**Returns**: dict with keys: enabled, config, activated, current_profit_pct, activation_threshold, last_adjustment, adjustment_count

**Example**:
```python
status = trailing_stop_manager.get_trailing_status('AAPL')
if status['enabled']:
    print(f"Trailing: {status['config']['trailing_amount']}%")
    print(f"Activated: {status['activated']}")
    print(f"Adjustments: {status['adjustment_count']}")
```

#### `get_adjustment_history(symbol, start_date, end_date)`

Get history of stop adjustments with optional filters.

**Parameters**:
- `symbol` (str, optional): Filter by symbol
- `start_date` (datetime, optional): Filter by timestamp >= start_date
- `end_date` (datetime, optional): Filter by timestamp <= end_date

**Returns**: List[dict] - Adjustment records

**Example**:
```python
from datetime import datetime, timedelta

history = trailing_stop_manager.get_adjustment_history(
    symbol='AAPL',
    start_date=datetime.now() - timedelta(days=1)
)
```

### OrderManager

#### `modify_stop(symbol, new_stop_price)`

Modify stop loss for an open position.

**Parameters**:
- `symbol` (str): Symbol to modify stop for
- `new_stop_price` (float): New stop price

**Returns**: bool - True if modification successful

#### `enable_trailing_stop_for_position(symbol, trailing_type, trailing_amount, activation_profit_pct)`

Enable trailing stop for an open position.

**Parameters**:
- `symbol` (str): Symbol to enable trailing for
- `trailing_type` (str): 'percentage' or 'atr'
- `trailing_amount` (float): Trail distance
- `activation_profit_pct` (float): Activation threshold

**Returns**: None

---

## Troubleshooting

### Problem: Trailing stops not adjusting

**Symptoms**: Position profit increasing but stop not moving

**Possible Causes**:
1. Activation threshold not met yet
2. Price hasn't moved enough to trigger adjustment
3. Scheduler not running

**Solutions**:
```python
# Check activation status
status = trailing_stop_manager.get_trailing_status('AAPL')
print(f"Activated: {status['activated']}")
print(f"Current profit: {status['current_profit_pct']}%")
print(f"Activation threshold: {status['activation_threshold']}%")

# Manually trigger check
from src.pipeline.trailing_stop_scheduler import run_trailing_stop_check
run_trailing_stop_check()
```

### Problem: Stops adjusting too frequently

**Symptoms**: >10 adjustments per trade, getting stopped out early

**Solution**: Widen trail distance or increase activation threshold

```python
# Before (too tight)
trailing_amount=1.0
activation_profit_pct=0.5

# After (wider)
trailing_amount=2.5
activation_profit_pct=1.5
```

### Problem: Stops not adjusting frequently enough

**Symptoms**: Large price moves with no stop adjustment

**Solution**: Check if ATR-based trail is too wide

```python
# Check ATR value
atr = trailing_stop_manager._get_atr_value('AAPL')
print(f"Current ATR: ${atr:.2f}")

# If ATR too large, reduce multiplier
trailing_amount=2.0  # Instead of 3.0
```

### Problem: Getting stopped out at breakeven

**Symptoms**: Trailing stop hits at or near entry price

**Cause**: Activation threshold too low, stop tightens before sufficient profit

**Solution**: Increase activation threshold

```python
# Before
activation_profit_pct=0.5  # Too low

# After
activation_profit_pct=2.0  # Room for volatility
```

### Problem: ATR fallback to percentage

**Symptoms**: Logs show "falling back to percentage trail"

**Causes**:
1. Insufficient historical data
2. Historical manager not initialized
3. Indicator engine error

**Solutions**:
```python
# Check historical data availability
from src.data.historical_manager import historical_manager

df = historical_manager.get_bars('AAPL', '15 mins', lookback_bars=100)
print(f"Bars available: {len(df)}")

# If insufficient, download more data
historical_manager.download_historical_bars('AAPL', '15 mins', '10 D')
```

### Problem: Database not updating

**Symptoms**: Stop adjustments happen but database shows old stop price

**Cause**: OrderManager not calling update_trade_stop()

**Solution**: Verify modify_stop() is being called

```python
# Enable debug logging
import logging
logging.getLogger('src.execution.order_manager').setLevel(logging.DEBUG)

# Check database directly
from src.data.trade_database import trade_database
trade = trade_database.get_trade(trade_id)
print(f"Database stop: ${trade['stop_price']:.2f}")
```

---

## Performance Considerations

### Check Frequency

Default 60-second interval balances responsiveness and CPU usage:

```python
# Default (recommended)
check_interval_seconds=60  # 1 minute

# High-frequency (scalping)
check_interval_seconds=10  # 10 seconds (higher CPU)

# Low-frequency (swing trading)
check_interval_seconds=300  # 5 minutes (lower CPU)
```

### ATR Calculation Overhead

ATR-based trailing requires indicator calculations:

- **Cache Period**: 15 minutes (uses `historical_manager` cache)
- **Calculation Time**: ~5-10ms per symbol
- **Fallback**: Automatic switch to percentage if ATR unavailable

### Database Performance

Each stop adjustment writes to database:

- **Write Time**: <10ms typical
- **Index**: stop_price not indexed (UPDATE only)
- **Batch Updates**: Not currently implemented

---

## Summary

**Key Takeaways**:

1. **Trailing stops protect profits** while letting winners run
2. **Use percentage** for stable stocks, **ATR** for volatile stocks
3. **Activation thresholds** prevent premature tightening
4. **Stops only move favorably** (never against profit)
5. **Match trail distance** to trading style (tight for scalping, wide for swinging)
6. **Monitor adjustment history** to tune parameters
7. **Test thoroughly** before live trading

**Golden Rules**:
- Activation threshold ≥ (initial stop distance / 2)
- Trail distance ≤ 2x initial stop distance
- High volatility → Use ATR
- Low volatility → Use percentage
- Scalping → Tight trail (1-1.5%)
- Swing trading → Wide trail (2-3%)

---

## Additional Resources

- **OrderManager Documentation**: `src/execution/order_manager.py`
- **TradeDatabase Documentation**: `src/data/trade_database.py`
- **Test Suite**: `tests/test_trailing_stops.py`
- **Configuration Reference**: `config/trading_params.yaml`
- **PRD Reference**: `PRD/09_execution_and_monitoring.md`

---

*Last Updated: 2025-11-15*
*Version: 1.0.0*
