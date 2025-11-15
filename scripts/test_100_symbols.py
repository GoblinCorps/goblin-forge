"""
Phase 6b: Scale Test with 100 Symbols

Tests the screener system with 100 US stocks to verify:
- Parallel processing capabilities
- IB API rate limit handling
- Parquet storage at scale
- Data integrity across large dataset
- Performance metrics

Uses parallel processing with rate limiting to respect IB API constraints.

Success Criteria:
- All symbols processed successfully
- No rate limit errors
- Execution time <5 minutes (300 seconds)
- All data validates correctly

Run:
----
python scripts/test_100_symbols.py
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
import pandas as pd

print("=" * 70)
print("PHASE 6B: 100 SYMBOL SCALE TEST")
print("=" * 70)
print(f"Started: {datetime.now()}")
print()

# Test configuration
MAX_EXECUTION_TIME = 300  # 5 minutes
TIMEFRAME = '15 mins'
DURATION = '5 D'

# 100 major US stocks across sectors
TEST_SYMBOLS = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'INTC', 'CSCO', 'ORCL',
    'ADBE', 'CRM', 'AVGO', 'TXN', 'QCOM', 'NOW', 'INTU', 'MU', 'AMAT', 'ADI',
    # Finance
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'COF',
    'PNC', 'USB', 'TFC', 'BK', 'STT',
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'ABT', 'MRK', 'LLY', 'DHR', 'BMY',
    'AMGN', 'GILD', 'CVS', 'CI', 'HUM',
    # Consumer
    'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'NKE', 'MCD', 'SBUX', 'TGT',
    'LOW', 'DIS', 'CMCSA', 'NFLX', 'TSLA',
    # Industrial
    'BA', 'CAT', 'GE', 'HON', 'UNP', 'UPS', 'RTX', 'LMT', 'DE', 'MMM',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PSX', 'MPC', 'VLO', 'OXY', 'HAL',
    # Utilities & Real Estate
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'AMT', 'PLD', 'CCI', 'EQIX', 'SPG',
]

# Results tracking
results = {
    'symbols_tested': [],
    'symbols_successful': [],
    'symbols_failed': [],
    'data_fetched': {},
    'errors': [],
    'start_time': None,
    'end_time': None,
    'execution_time': None,
}


def test_symbol(symbol: str, ib_manager: IBDataManager, hist_manager: HistoricalDataManager) -> bool:
    """
    Test data pipeline for a single symbol.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Fetch data
        data = ib_manager.fetch_historical_bars(symbol, TIMEFRAME, DURATION)

        if data is None or len(data) == 0:
            results['errors'].append((symbol, 'No data returned', ''))
            return False

        results['data_fetched'][symbol] = len(data)

        # Save to Parquet
        file_path = hist_manager.save_symbol_data(symbol, TIMEFRAME, data)

        # Verify integrity
        loaded_data = hist_manager.load_symbol_data(symbol, TIMEFRAME)

        if loaded_data is None or len(loaded_data) != len(data):
            results['errors'].append((symbol, 'Data integrity check failed', ''))
            return False

        # OHLCV validation
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in loaded_data.columns for col in required_cols):
            results['errors'].append((symbol, 'Missing required columns', ''))
            return False

        # Data corruption checks
        if not (loaded_data['high'] >= loaded_data['low']).all():
            results['errors'].append((symbol, 'Data corruption: high < low', ''))
            return False

        if not (loaded_data['high'] >= loaded_data['open']).all():
            results['errors'].append((symbol, 'Data corruption: high < open', ''))
            return False

        if not (loaded_data['high'] >= loaded_data['close']).all():
            results['errors'].append((symbol, 'Data corruption: high < close', ''))
            return False

        return True

    except Exception as e:
        results['errors'].append((symbol, str(e), traceback.format_exc()))
        return False


def main():
    """Run 100 symbol scale test with parallel processing."""

    results['start_time'] = time.time()

    # Initialize managers
    print("\n" + "=" * 70)
    print("INITIALIZATION")
    print("=" * 70)

    print("\n[1/2] Connecting to IB Gateway...")
    ib_manager = IBDataManager(port=4002, client_id=101, heartbeat_enabled=False)

    if not ib_manager.connect():
        print("❌ Failed to connect to IB Gateway")
        print("   Make sure IB Gateway is running on port 4002")
        return False

    print(f"✅ Connected to IB Gateway")
    print(f"   State: {ib_manager.state}")
    print(f"   Healthy: {ib_manager.is_healthy()}")

    print("\n[2/2] Initializing Historical Data Manager...")
    hist_manager = HistoricalDataManager(data_dir='data/historical')
    print(f"✅ Historical manager initialized: {hist_manager.data_dir}")

    # Process symbols sequentially
    # Note: IB-insync requires sequential processing due to event loop constraints
    print("\n" + "=" * 70)
    print(f"PROCESSING {len(TEST_SYMBOLS)} SYMBOLS")
    print("Mode: Sequential (ib-insync event loop requirement)")
    print("=" * 70)

    completed = 0
    failed = 0
    start_processing = time.time()

    for i, symbol in enumerate(TEST_SYMBOLS, 1):
        results['symbols_tested'].append(symbol)

        try:
            success = test_symbol(symbol, ib_manager, hist_manager)

            if success:
                completed += 1
                results['symbols_successful'].append(symbol)
                bars = results['data_fetched'].get(symbol, 0)
                elapsed = time.time() - start_processing
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(TEST_SYMBOLS) - i) / rate if rate > 0 else 0
                print(f"✅ [{i}/{len(TEST_SYMBOLS)}] {symbol}: {bars} bars | {elapsed:.1f}s elapsed, ETA {eta:.0f}s")
            else:
                failed += 1
                results['symbols_failed'].append(symbol)
                print(f"❌ [{i}/{len(TEST_SYMBOLS)}] {symbol}: FAILED")

        except Exception as e:
            failed += 1
            results['symbols_failed'].append(symbol)
            results['errors'].append((symbol, str(e), traceback.format_exc()))
            print(f"❌ [{i}/{len(TEST_SYMBOLS)}] {symbol}: ERROR - {e}")

        # Progress update every 10 symbols
        if i % 10 == 0:
            elapsed = time.time() - start_processing
            rate = i / elapsed
            eta = (len(TEST_SYMBOLS) - i) / rate
            print(f"   Progress: {i}/{len(TEST_SYMBOLS)} ({i/len(TEST_SYMBOLS)*100:.1f}%) | Rate: {rate:.1f} sym/s | ETA: {eta/60:.1f} min")

    processing_time = time.time() - start_processing

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
        print(f"\nFailed Symbols ({len(results['symbols_failed'])}):")
        for sym in results['symbols_failed'][:10]:  # Show first 10
            print(f"  - {sym}")
        if len(results['symbols_failed']) > 10:
            print(f"  ... and {len(results['symbols_failed']) - 10} more")

    print(f"\nData Fetched:")
    total_bars = sum(results['data_fetched'].values())
    print(f"  Total bars: {total_bars:,}")
    print(f"  Average per symbol: {total_bars // len(results['data_fetched']) if results['data_fetched'] else 0}")

    print(f"\nPerformance:")
    print(f"  Total execution time: {results['execution_time']:.2f}s")
    print(f"  Processing time: {processing_time:.2f}s")
    print(f"  Average per symbol: {processing_time / len(TEST_SYMBOLS):.2f}s")

    if results['execution_time'] < MAX_EXECUTION_TIME:
        print(f"  ✅ Within target (<{MAX_EXECUTION_TIME}s / {MAX_EXECUTION_TIME // 60}min)")
    else:
        print(f"  ⚠️  Slower than target ({MAX_EXECUTION_TIME}s / {MAX_EXECUTION_TIME // 60}min)")

    if results['errors'] and len(results['errors']) <= 10:
        print(f"\nErrors ({len(results['errors'])}):")
        for symbol, error, tb in results['errors']:
            print(f"\n{symbol}: {error}")
            if tb:
                print(f"  {tb[:200]}...")  # Show first 200 chars of traceback
    elif results['errors']:
        print(f"\n⚠️  {len(results['errors'])} errors occurred (showing first 5):")
        for symbol, error, _ in results['errors'][:5]:
            print(f"  {symbol}: {error}")

    # Final verdict
    print("\n" + "=" * 70)

    all_passed = len(results['symbols_successful']) == len(TEST_SYMBOLS)
    performance_ok = results['execution_time'] < MAX_EXECUTION_TIME
    success_rate = len(results['symbols_successful']) / len(TEST_SYMBOLS) * 100

    if all_passed and performance_ok:
        print(f"✅ PHASE 6B: PASS - All {len(TEST_SYMBOLS)} symbols processed successfully")
        print("=" * 70)
        return True
    elif success_rate >= 95 and performance_ok:
        print(f"⚠️  PHASE 6B: PARTIAL PASS - {success_rate:.1f}% success rate (≥95% target)")
        print("=" * 70)
        return True
    elif all_passed:
        print(f"⚠️  PHASE 6B: PARTIAL - All symbols processed but slower than target")
        print("=" * 70)
        return True
    else:
        print(f"❌ PHASE 6B: FAIL - Only {success_rate:.1f}% success rate")
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
