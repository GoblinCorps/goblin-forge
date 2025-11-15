"""
Test Script: US-Stock-Symbols Ticker System

Tests the new ticker downloader and universe manager integration.

Tests:
------
1. Download ticker lists from GitHub
2. Validate data structure and counts
3. Test universe building with new sources
4. Verify caching mechanism
5. Test all exchanges (NYSE, NASDAQ, AMEX)

Run:
----
python scripts/test_ticker_system.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.ticker_downloader import ticker_downloader
from src.screening.universe import universe_manager

print("=" * 70)
print("TICKER SYSTEM TEST")
print("=" * 70)
print(f"Started: {datetime.now()}")
print()

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


# ===== TICKER DOWNLOADER TESTS =====
print("\n" + "=" * 70)
print("TICKER DOWNLOADER TESTS")
print("=" * 70)


@test_case("Download NYSE tickers")
def test_download_nyse():
    tickers = ticker_downloader.download_exchange('NYSE', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 0, "Should have tickers"
    assert all(isinstance(t, str) for t in tickers), "All tickers should be strings"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download NASDAQ tickers")
def test_download_nasdaq():
    tickers = ticker_downloader.download_exchange('NASDAQ', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 0, "Should have tickers"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download AMEX tickers")
def test_download_amex():
    tickers = ticker_downloader.download_exchange('AMEX', force=True)
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 0, "Should have tickers"
    print(f" ({len(tickers)} tickers)", end="")
    return tickers


@test_case("Download all exchanges")
def test_download_all():
    results = ticker_downloader.download_all_exchanges()
    assert isinstance(results, dict), "Should return a dictionary"
    assert 'NYSE' in results, "Should have NYSE"
    assert 'NASDAQ' in results, "Should have NASDAQ"
    assert 'AMEX' in results, "Should have AMEX"
    total = sum(len(tickers) for tickers in results.values())
    print(f" ({total} total tickers)", end="")
    return results


@test_case("Get all unique tickers")
def test_get_all_tickers():
    tickers = ticker_downloader.get_all_tickers()
    assert isinstance(tickers, list), "Should return a list"
    assert len(tickers) > 0, "Should have tickers"
    # Check for deduplication
    assert len(tickers) == len(set(tickers)), "Should have unique tickers only"
    print(f" ({len(tickers)} unique tickers)", end="")
    return tickers


@test_case("Cache validation")
def test_cache():
    # First download should create cache
    ticker_downloader.download_exchange('NYSE')
    # Second call should use cache
    assert ticker_downloader._is_cache_valid('NYSE'), "Cache should be valid"
    return True


@test_case("Get statistics")
def test_statistics():
    stats = ticker_downloader.get_statistics()
    assert isinstance(stats, dict), "Should return a dictionary"
    assert 'exchanges' in stats, "Should have exchanges"
    assert 'total_unique' in stats, "Should have total_unique"
    print(f" ({stats['total_unique']} unique tickers)", end="")
    return stats


# ===== UNIVERSE MANAGER TESTS =====
print("\n" + "=" * 70)
print("UNIVERSE MANAGER TESTS")
print("=" * 70)


@test_case("Load NYSE via universe manager")
def test_universe_nyse():
    symbols = universe_manager.load_symbol_list('NYSE')
    assert isinstance(symbols, list), "Should return a list"
    assert len(symbols) > 0, "Should have symbols"
    print(f" ({len(symbols)} symbols)", end="")
    return symbols


@test_case("Load NASDAQ via universe manager")
def test_universe_nasdaq():
    symbols = universe_manager.load_symbol_list('NASDAQ')
    assert isinstance(symbols, list), "Should return a list"
    assert len(symbols) > 0, "Should have symbols"
    print(f" ({len(symbols)} symbols)", end="")
    return symbols


@test_case("Load ALL via universe manager")
def test_universe_all():
    symbols = universe_manager.load_symbol_list('ALL')
    assert isinstance(symbols, list), "Should return a list"
    assert len(symbols) > 0, "Should have symbols"
    # Should be deduplicated
    assert len(symbols) == len(set(symbols)), "Should have unique symbols only"
    print(f" ({len(symbols)} symbols)", end="")
    return symbols


@test_case("Build universe from multiple sources")
def test_build_universe():
    universe = universe_manager.build_universe(['NYSE', 'NASDAQ'])
    assert isinstance(universe, list), "Should return a list"
    assert len(universe) > 0, "Should have symbols"
    # Should be sorted and deduplicated
    assert universe == sorted(universe), "Should be sorted"
    assert len(universe) == len(set(universe)), "Should have unique symbols only"
    print(f" ({len(universe)} symbols)", end="")
    return universe


@test_case("Verify common tickers in universe")
def test_common_tickers():
    universe = universe_manager.build_universe(['NYSE', 'NASDAQ'])
    common_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    found = [t for t in common_tickers if t in universe]
    assert len(found) > 0, f"Should find at least some common tickers, found: {found}"
    print(f" (found {len(found)}/{len(common_tickers)})", end="")
    return found


# ===== CONFIGURATION TESTS =====
print("\n" + "=" * 70)
print("CONFIGURATION TESTS")
print("=" * 70)


@test_case("Universe sources in config")
def test_config_sources():
    from src.config import config
    assert hasattr(config.universe, 'sources'), "Should have sources config"
    sources = config.universe.sources
    assert isinstance(sources, list), "Sources should be a list"
    assert len(sources) > 0, "Should have at least one source"
    print(f" ({sources})", end="")
    return sources


@test_case("Build universe from config")
def test_build_from_config():
    # Should use config.universe.sources by default
    universe = universe_manager.build_universe()
    assert isinstance(universe, list), "Should return a list"
    assert len(universe) > 0, "Should have symbols"
    print(f" ({len(universe)} symbols from config)", end="")
    return universe


# ===== RUN ALL TESTS =====
nyse_tickers = test_download_nyse()
nasdaq_tickers = test_download_nasdaq()
amex_tickers = test_download_amex()
all_exchanges = test_download_all()
all_tickers = test_get_all_tickers()
test_cache()
stats = test_statistics()

test_universe_nyse()
test_universe_nasdaq()
test_universe_all()
universe = test_build_universe()
test_common_tickers()

test_config_sources()
test_build_from_config()


# ===== DETAILED STATISTICS =====
print("\n" + "=" * 70)
print("TICKER STATISTICS")
print("=" * 70)

if stats:
    print(f"\nTotal unique tickers: {stats['total_unique']}")
    print(f"Cache directory: {stats['cache_dir']}\n")

    for exchange, data in stats['exchanges'].items():
        if data['count'] > 0:
            print(f"{exchange}:")
            print(f"  Count: {data['count']}")
            print(f"  Cache age: {data['cache_age_hours']:.1f} hours")
            print(f"  Cache valid: {data['cache_valid']}")


# ===== SAMPLE TICKERS =====
print("\n" + "=" * 70)
print("SAMPLE TICKERS")
print("=" * 70)

if universe and len(universe) > 0:
    print(f"\nFirst 20 tickers from built universe:")
    print(", ".join(universe[:20]))

    if len(universe) > 20:
        print(f"\nLast 20 tickers:")
        print(", ".join(universe[-20:]))


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
    print("✅ ALL TESTS PASSED - TICKER SYSTEM VALIDATED")
else:
    print(f"⚠️  {test_results['failed']} TESTS FAILED - SEE ERRORS ABOVE")
print("=" * 70)

print(f"\nCompleted: {datetime.now()}")

sys.exit(0 if test_results['failed'] == 0 else 1)
