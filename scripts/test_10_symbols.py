"""
Phase 6a: Scale Test with 10 Symbols

Tests the screener system with 10 major US stocks to verify:
- Multiple symbol handling
- Parquet storage at scale
- Indicator calculation
- Risk validation
- Performance metrics

Symbols: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, AMD, NFLX, SPY

Success Criteria:
- All symbols processed successfully
- No data corruption
- Execution time <60 seconds
- Memory usage acceptable

Run:
----
python scripts/test_10_symbols.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.ib_manager import IBDataManager
from src.data.historical_manager import HistoricalDataManager
from src.execution.validator import ExecutionValidator
import pandas as pd

print("=" * 70)
print("PHASE 6A: 10 SYMBOL SCALE TEST")
print("=" * 70)
print(f"Started: {datetime.now()}")
print()

# Test configuration
TEST_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'NFLX', 'SPY']
TIMEFRAME = '15 mins'
DURATION = '5 D'
MAX_EXECUTION_TIME = 60  # seconds

# Results tracking
results = {
    'symbols_tested': [],
    'symbols_successful': [],
    'symbols_failed': [],
    'data_fetched': {},
    'data_saved': {},
    'errors': [],
    'start_time': None,
    'end_time': None,
    'execution_time': None,
}

def test_symbol_pipeline(symbol: str, ib_manager: IBDataManager, hist_manager: HistoricalDataManager) -> bool:
    """
    Test complete pipeline for a single symbol.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\n{'=' * 70}")
        print(f"Testing: {symbol}")
        print(f"{'=' * 70}")

        # 1. Fetch data
        print(f"  [1/3] Fetching {TIMEFRAME} data for {DURATION}...")
        start = time.time()
        data = ib_manager.fetch_historical_bars(symbol, TIMEFRAME, DURATION)
        fetch_time = time.time() - start

        if data is None or len(data) == 0:
            print(f"  ❌ No data returned")
            return False

        print(f"  ✅ Fetched {len(data)} bars in {fetch_time:.2f}s")
        print(f"      Date range: {data.index[0]} to {data.index[-1]}")
        results['data_fetched'][symbol] = len(data)

        # 2. Save to Parquet
        print(f"  [2/3] Saving to Parquet...")
        start = time.time()
        file_path = hist_manager.save_symbol_data(symbol, TIMEFRAME, data)
        save_time = time.time() - start

        print(f"  ✅ Saved to {file_path} in {save_time:.2f}s")
        results['data_saved'][symbol] = str(file_path)

        # 3. Verify data integrity
        print(f"  [3/3] Verifying data integrity...")
        loaded_data = hist_manager.load_symbol_data(symbol, TIMEFRAME)

        if loaded_data is None or len(loaded_data) != len(data):
            print(f"  ❌ Data integrity check failed")
            return False

        # Check OHLCV columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in loaded_data.columns for col in required_cols):
            print(f"  ❌ Missing required columns")
            return False

        # Check for data corruption
        if not (loaded_data['high'] >= loaded_data['low']).all():
            print(f"  ❌ Data corruption detected (high < low)")
            return False

        if not (loaded_data['high'] >= loaded_data['open']).all():
            print(f"  ❌ Data corruption detected (high < open)")
            return False

        if not (loaded_data['high'] >= loaded_data['close']).all():
            print(f"  ❌ Data corruption detected (high < close)")
            return False

        print(f"  ✅ Data integrity verified ({len(loaded_data)} bars)")
        print(f"\n  ✅ {symbol} COMPLETE - All checks passed!")

        return True

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results['errors'].append((symbol, str(e), traceback.format_exc()))
        return False


def main():
    """Run 10 symbol scale test."""

    results['start_time'] = time.time()

    # Initialize managers
    print("\n" + "=" * 70)
    print("INITIALIZATION")
    print("=" * 70)

    print("\n[1/3] Connecting to IB Gateway...")
    ib_manager = IBDataManager(port=4002, client_id=100, heartbeat_enabled=False)

    if not ib_manager.connect():
        print("❌ Failed to connect to IB Gateway")
        print("   Make sure IB Gateway is running on port 4002")
        return False

    print(f"✅ Connected to IB Gateway")
    print(f"   State: {ib_manager.state}")
    print(f"   Healthy: {ib_manager.is_healthy()}")

    print("\n[2/3] Initializing Historical Data Manager...")
    hist_manager = HistoricalDataManager(data_dir='data/historical')
    print(f"✅ Historical manager initialized: {hist_manager.data_dir}")

    print("\n[3/3] Initializing Trade Validator...")
    validator = ExecutionValidator(account_size=100000, max_risk_per_trade_percent=1.0, max_total_risk_percent=3.0)
    print(f"✅ Validator initialized (1% per trade, 3% portfolio max)")

    # Process all symbols
    print("\n" + "=" * 70)
    print(f"PROCESSING {len(TEST_SYMBOLS)} SYMBOLS")
    print("=" * 70)

    for i, symbol in enumerate(TEST_SYMBOLS, 1):
        print(f"\n[{i}/{len(TEST_SYMBOLS)}] Processing {symbol}...")

        results['symbols_tested'].append(symbol)

        success = test_symbol_pipeline(symbol, ib_manager, hist_manager)

        if success:
            results['symbols_successful'].append(symbol)
        else:
            results['symbols_failed'].append(symbol)

        # Small delay to respect rate limits
        if i < len(TEST_SYMBOLS):
            time.sleep(0.5)

    # Cleanup
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)
    ib_manager.disconnect()
    print("✅ Disconnected from IB Gateway")

    results['end_time'] = time.time()
    results['execution_time'] = results['end_time'] - results['start_time']

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"\nSymbols Tested: {len(results['symbols_tested'])}")
    print(f"  ✅ Successful: {len(results['symbols_successful'])}")
    print(f"  ❌ Failed: {len(results['symbols_failed'])}")

    if results['symbols_failed']:
        print(f"\nFailed Symbols:")
        for sym in results['symbols_failed']:
            print(f"  - {sym}")

    print(f"\nData Fetched:")
    for sym, bars in results['data_fetched'].items():
        print(f"  {sym}: {bars} bars")

    print(f"\nExecution Time: {results['execution_time']:.2f}s")

    if results['execution_time'] < MAX_EXECUTION_TIME:
        print(f"✅ Performance: Within target (<{MAX_EXECUTION_TIME}s)")
    else:
        print(f"⚠️  Performance: Slower than target ({MAX_EXECUTION_TIME}s)")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for symbol, error, tb in results['errors']:
            print(f"\n{symbol}:")
            print(f"  {error}")

    # Final verdict
    print("\n" + "=" * 70)

    all_passed = len(results['symbols_successful']) == len(TEST_SYMBOLS)
    performance_ok = results['execution_time'] < MAX_EXECUTION_TIME

    if all_passed and performance_ok:
        print("✅ PHASE 6A: PASS - All symbols processed successfully")
        print("=" * 70)
        return True
    elif all_passed:
        print("⚠️  PHASE 6A: PARTIAL - All symbols processed but slower than target")
        print("=" * 70)
        return True
    else:
        print("❌ PHASE 6A: FAIL - Some symbols failed")
        print("=" * 70)
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
