"""
Test Script: Ticker Downloader Only

Tests the ticker downloader without any external dependencies.

Run:
----
python scripts/test_ticker_downloader.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("TICKER DOWNLOADER TEST")
print("=" * 70)
print(f"Started: {datetime.now()}")
print()

# Import after path setup
from src.data.ticker_downloader import ticker_downloader

test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}


def test_case(name):
    """Decorator for test cases."""
    def decorator(func):
        def wrapper():
            try:
                print(f"Testing: {name}...", end=" ")
                result = func()
                print(f"✅ PASS")
                test_results['passed'] += 1
                return result
            except AssertionError as e:
                print(f"❌ FAIL: {e}")
                test_results['failed'] += 1
                test_results['errors'].append((name, str(e)))
                return None
            except Exception as e:
                print(f"❌ ERROR: {e}")
                test_results['failed'] += 1
                test_results['errors'].append((name, str(e)))
                return None
        return wrapper
    return decorator


print("\n" + "=" * 70)
print("DOWNLOADING TICKER LISTS FROM GITHUB")
print("=" * 70)


@test_case("Download NYSE tickers from GitHub")
def test_download_nyse():
    tickers = ticker_downloader.download_exchange('NYSE', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 100, f"Should have many tickers, got {len(tickers)}"
    assert all(isinstance(t, str) for t in tickers), "All tickers should be strings"
    # Check for some common NYSE stocks
    common_nyse = ['WMT', 'JPM', 'V', 'JNJ', 'PG']
    found = [t for t in common_nyse if t in tickers]
    assert len(found) > 0, f"Should find some common NYSE stocks, found: {found}"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download NASDAQ tickers from GitHub")
def test_download_nasdaq():
    tickers = ticker_downloader.download_exchange('NASDAQ', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 100, f"Should have many tickers, got {len(tickers)}"
    # Check for common NASDAQ stocks
    common_nasdaq = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    found = [t for t in common_nasdaq if t in tickers]
    assert len(found) > 0, f"Should find some common NASDAQ stocks, found: {found}"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download AMEX tickers from GitHub")
def test_download_amex():
    tickers = ticker_downloader.download_exchange('AMEX', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 0, "Should have tickers"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download all exchanges at once")
def test_download_all():
    results = ticker_downloader.download_all_exchanges(force=True)
    assert isinstance(results, dict), "Should return a dictionary"
    assert 'NYSE' in results, "Should have NYSE"
    assert 'NASDAQ' in results, "Should have NASDAQ"
    assert 'AMEX' in results, "Should have AMEX"
    assert len(results['NYSE']) > 0, "NYSE should have tickers"
    assert len(results['NASDAQ']) > 0, "NASDAQ should have tickers"
    total = sum(len(tickers) for tickers in results.values())
    print(f" ({total} total tickers)", end="")
    return results


print("\n" + "=" * 70)
print("TESTING CACHE MECHANISM")
print("=" * 70)


@test_case("Cache file creation")
def test_cache_files():
    # Download should create cache files
    ticker_downloader.download_exchange('NYSE')
    cache_file = ticker_downloader._get_cache_file('NYSE')
    assert cache_file.exists(), f"Cache file should exist: {cache_file}"
    return cache_file


@test_case("Cache validation")
def test_cache_valid():
    # After download, cache should be valid
    ticker_downloader.download_exchange('NASDAQ')
    assert ticker_downloader._is_cache_valid('NASDAQ'), "Cache should be valid"
    return True


@test_case("Using cached data")
def test_use_cache():
    # First call downloads
    tickers1 = ticker_downloader.get_tickers('NYSE', auto_download=True)
    # Second call should use cache
    tickers2 = ticker_downloader.get_tickers('NYSE', auto_download=False)
    assert tickers1 == tickers2, "Cached data should match downloaded data"
    print(f" ({len(tickers1)} tickers)", end="")
    return tickers1


print("\n" + "=" * 70)
print("TESTING DEDUPLICATION")
print("=" * 70)


@test_case("Get all unique tickers (deduplicated)")
def test_get_all_tickers():
    all_tickers = ticker_downloader.get_all_tickers()
    assert isinstance(all_tickers, list), "Should return a list"
    assert len(all_tickers) > 0, "Should have tickers"
    # Check for deduplication
    assert len(all_tickers) == len(set(all_tickers)), "Should have unique tickers only"
    # Should be sorted
    assert all_tickers == sorted(all_tickers), "Should be sorted alphabetically"
    print(f" ({len(all_tickers)} unique tickers)", end="")
    return all_tickers


@test_case("Verify common stocks in all tickers")
def test_common_stocks():
    all_tickers = ticker_downloader.get_all_tickers()
    common_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
                     'JPM', 'V', 'WMT', 'JNJ', 'PG']
    found = [t for t in common_stocks if t in all_tickers]
    assert len(found) >= 8, f"Should find most common stocks, found {len(found)}: {found}"
    print(f" (found {len(found)}/{len(common_stocks)})", end="")
    return found


print("\n" + "=" * 70)
print("TESTING STATISTICS")
print("=" * 70)


@test_case("Get ticker statistics")
def test_statistics():
    stats = ticker_downloader.get_statistics()
    assert isinstance(stats, dict), "Should return a dictionary"
    assert 'exchanges' in stats, "Should have exchanges"
    assert 'total_unique' in stats, "Should have total_unique"
    assert stats['total_unique'] > 0, "Should have unique tickers"
    print(f" ({stats['total_unique']} unique tickers)", end="")
    return stats


# ===== RUN ALL TESTS =====
nyse_tickers = test_download_nyse()
nasdaq_tickers = test_download_nasdaq()
amex_tickers = test_download_amex()
all_exchanges = test_download_all()

test_cache_files()
test_cache_valid()
cached_tickers = test_use_cache()

all_tickers = test_get_all_tickers()
common_stocks = test_common_stocks()

stats = test_statistics()


# ===== DETAILED STATISTICS =====
print("\n" + "=" * 70)
print("DETAILED STATISTICS")
print("=" * 70)

if stats:
    print(f"\nTotal unique tickers across all exchanges: {stats['total_unique']}")
    print(f"Cache directory: {stats['cache_dir']}\n")

    print("Per-Exchange Breakdown:")
    for exchange, data in stats['exchanges'].items():
        if data['count'] > 0:
            cache_status = "✅ Valid" if data['cache_valid'] else "⚠️  Expired"
            print(f"  {exchange:8s}: {data['count']:5d} tickers | "
                  f"Cache: {cache_status} ({data['cache_age_hours']:.1f}h old)")


# ===== SAMPLE TICKERS =====
print("\n" + "=" * 70)
print("SAMPLE TICKERS")
print("=" * 70)

if all_tickers and len(all_tickers) > 0:
    print(f"\nFirst 30 tickers (alphabetically sorted):")
    print(", ".join(all_tickers[:30]))

    if len(all_tickers) > 30:
        print(f"\nLast 30 tickers:")
        print(", ".join(all_tickers[-30:]))

if common_stocks:
    print(f"\nCommon stocks found in universe:")
    print(", ".join(common_stocks))


# ===== TEST SUMMARY =====
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

total = test_results['passed'] + test_results['failed']
pass_rate = (test_results['passed'] / total * 100) if total > 0 else 0

print(f"\nTotal Tests: {total}")
print(f"Passed: {test_results['passed']} ✅")
print(f"Failed: {test_results['failed']} ❌")
print(f"Pass Rate: {pass_rate:.1f}%")

if test_results['errors']:
    print(f"\n{'=' * 70}")
    print("ERRORS:")
    print("=" * 70)
    for name, error in test_results['errors']:
        print(f"\n{name}:")
        print(error)

print("\n" + "=" * 70)
if test_results['failed'] == 0:
    print("✅ ALL TESTS PASSED - TICKER DOWNLOADER VALIDATED")
    print("\nThe ticker downloader successfully:")
    print("  • Downloaded ticker lists from US-Stock-Symbols GitHub repo")
    print("  • Created local cache files")
    print("  • Deduplicated tickers across exchanges")
    print("  • Verified presence of common stocks")
    print(f"  • Found {stats['total_unique'] if stats else 'N/A'} unique tradeable symbols")
else:
    print(f"⚠️  {test_results['failed']} TESTS FAILED - SEE ERRORS ABOVE")
print("=" * 70)

print(f"\nCompleted: {datetime.now()}")

sys.exit(0 if test_results['failed'] == 0 else 1)
