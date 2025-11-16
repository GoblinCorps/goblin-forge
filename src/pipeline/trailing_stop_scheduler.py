"""
Trailing Stop Scheduler

Scheduled task to check and update trailing stops during market hours.

Features:
---------
1. Periodic Checking
   - Runs every 1 minute during market hours
   - Skips during pre-market and after-hours

2. Automatic Stop Adjustments
   - Checks all positions with enabled trailing stops
   - Calculates new stop prices based on config
   - Submits modifications via OrderManager

3. Market Hours Detection
   - Validates current time within 9:30 AM - 4:00 PM ET
   - Pauses automatically outside market hours

Usage:
------
# Start scheduler (infinite loop)
python -m src.pipeline.trailing_stop_scheduler

# Or integrate with main pipeline
from src.pipeline.trailing_stop_scheduler import start_trailing_stop_scheduler
import threading

scheduler_thread = threading.Thread(
    target=start_trailing_stop_scheduler,
    args=(60,),  # Check every 60 seconds
    daemon=True
)
scheduler_thread.start()
"""

import time
from datetime import datetime, time as dt_time
from loguru import logger

from src.execution.trailing_stop_manager import trailing_stop_manager
from src.execution.order_manager import order_manager


def is_market_hours() -> bool:
    """
    Check if current time is during market hours (9:30 AM - 4:00 PM ET).

    Returns:
    --------
    bool
        True if within market hours, False otherwise

    Notes:
    ------
    - Uses local system time (assumes system timezone is ET)
    - In production, use proper timezone handling with pytz
    - Market hours: Monday-Friday 9:30 AM - 4:00 PM ET
    - Does not check for market holidays

    TODO:
    -----
    - Add timezone conversion from system time to ET
    - Check for market holidays via calendar
    - Validate weekdays (skip weekends)
    """
    now = datetime.now()

    # Check if weekday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False

    # Market hours: 9:30 AM - 4:00 PM
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)

    current_time = now.time()

    return market_open <= current_time <= market_close


def run_trailing_stop_check() -> None:
    """
    Main function to check and update trailing stops.

    Called every minute during market hours.

    Process:
    --------
    1. Verify market hours
    2. Call trailing_stop_manager.check_and_update_stops()
    3. Apply adjustments via order_manager.modify_stop()
    4. Log results

    Notes:
    ------
    - No-op if outside market hours
    - Logs all adjustments
    - Handles errors gracefully
    - Safe to call repeatedly
    """
    if not is_market_hours():
        logger.debug("Market closed, skipping trailing stop check")
        return

    try:
        # Get all trailing stop adjustments
        adjustments = trailing_stop_manager.check_and_update_stops()

        if not adjustments:
            logger.debug("No trailing stop adjustments needed")
            return

        # Apply each adjustment
        success_count = 0
        failure_count = 0

        for adj in adjustments:
            symbol = adj['symbol']
            new_stop = adj['new_stop']
            old_stop = adj['old_stop']
            trigger_price = adj['trigger_price']
            profit_pct = adj['profit_pct']

            # Modify stop via order manager
            success = order_manager.modify_stop(symbol, new_stop)

            if success:
                success_count += 1
                logger.info(
                    f"Trailing stop adjusted: {symbol} "
                    f"${old_stop:.2f} -> ${new_stop:.2f} "
                    f"(price: ${trigger_price:.2f}, profit: {profit_pct:+.2f}%)"
                )
            else:
                failure_count += 1
                logger.error(f"Failed to adjust trailing stop for {symbol}")

        # Summary log
        logger.info(
            f"Trailing stop check complete: {success_count} adjustments, "
            f"{failure_count} failures"
        )

    except Exception as e:
        logger.error(f"Error during trailing stop check: {e}", exc_info=True)


def start_trailing_stop_scheduler(interval_seconds: int = 60) -> None:
    """
    Start infinite loop checking trailing stops.

    Parameters:
    -----------
    interval_seconds : int, default=60
        Check interval in seconds (default 60 = 1 minute)

    Notes:
    ------
    - Runs indefinitely until interrupted (Ctrl+C)
    - Only checks during market hours
    - Logs all adjustments
    - Can be run in background thread

    Examples:
    ---------
    >>> # Run in main thread (blocking)
    >>> start_trailing_stop_scheduler(interval_seconds=60)

    >>> # Run in background thread
    >>> import threading
    >>> scheduler_thread = threading.Thread(
    ...     target=start_trailing_stop_scheduler,
    ...     args=(60,),
    ...     daemon=True
    ... )
    >>> scheduler_thread.start()
    """
    logger.info(f"Starting trailing stop scheduler (interval={interval_seconds}s)")

    try:
        while True:
            run_trailing_stop_check()
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        logger.info("Trailing stop scheduler stopped by user")

    except Exception as e:
        logger.error(f"Trailing stop scheduler crashed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    """
    Run trailing stop scheduler as standalone script.

    Usage:
        python -m src.pipeline.trailing_stop_scheduler
    """
    logger.info("Trailing stop scheduler starting...")

    # Start scheduler (blocking)
    start_trailing_stop_scheduler(interval_seconds=60)
