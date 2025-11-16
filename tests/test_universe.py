"""
Unit Tests for Universe Manager

Tests universe construction, filtering, and management functionality.

Test Coverage:
--------------
- Initialization and configuration
- Symbol list loading from files and exchanges
- Universe building and deduplication
- Price/volume filtering
- IB API integration for quote fetching
- Parquet persistence (save/load)
- Statistics generation
- Error handling and edge cases

Run:
----
pytest tests/test_universe.py -v --cov=src/screening/universe
"""

import json
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from src.screening.universe import UniverseManager, universe_manager


class TestUniverseManagerInitialization:
    """Test UniverseManager initialization."""

    def test_init_default_directory(self, tmp_path, monkeypatch):
        """Test initialization with default data directory."""
        # Mock config to return tmp_path
        mock_config = MagicMock()
        mock_config.get.return_value = str(tmp_path / "universe")
        mock_config.universe.min_price = 1.0
        mock_config.universe.max_price = 500.0
        mock_config.universe.min_avg_volume = 500000

        with patch('src.screening.universe.config', mock_config):
            manager = UniverseManager()

            assert manager.data_dir == Path(tmp_path / "universe")
            assert manager.data_dir.exists()
            assert manager.min_price == 1.0
            assert manager.max_price == 500.0
            assert manager.min_avg_volume == 500000
            assert isinstance(manager.symbol_lists, dict)
            assert isinstance(manager.cache, dict)
            assert len(manager.symbol_lists) == 0

    def test_init_custom_directory(self, tmp_path):
        """Test initialization with custom data directory."""
        custom_dir = tmp_path / "custom_universe"

        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "default")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            manager = UniverseManager(data_dir=str(custom_dir))

            assert manager.data_dir == custom_dir
            assert manager.data_dir.exists()

    def test_init_creates_directory_if_missing(self, tmp_path):
        """Test that initialization creates data directory if it doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent" / "nested" / "universe"

        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "default")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            manager = UniverseManager(data_dir=str(nonexistent_dir))

            assert manager.data_dir.exists()
            assert manager.data_dir.is_dir()


class TestLoadSymbolList:
    """Test symbol list loading from various sources."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_load_from_json_file(self, manager, tmp_path):
        """Test loading symbols from JSON file."""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        json_file = tmp_path / "test_symbols.json"

        with open(json_file, 'w') as f:
            json.dump(symbols, f)

        result = manager.load_symbol_list('custom', file_path=str(json_file))

        assert result == symbols
        assert manager.symbol_lists['custom'] == symbols

    def test_load_from_csv_file(self, manager, tmp_path):
        """Test loading symbols from CSV file."""
        df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'name': ['Apple', 'Microsoft', 'Google']
        })
        csv_file = tmp_path / "test_symbols.csv"
        df.to_csv(csv_file, index=False)

        result = manager.load_symbol_list('custom', file_path=str(csv_file))

        assert result == ['AAPL', 'MSFT', 'GOOGL']
        assert manager.symbol_lists['custom'] == result

    def test_load_from_unsupported_file_format(self, manager, tmp_path):
        """Test error handling for unsupported file format."""
        txt_file = tmp_path / "symbols.txt"
        txt_file.write_text("AAPL\nMSFT\nGOOGL")

        result = manager.load_symbol_list('custom', file_path=str(txt_file))

        assert result == []
        assert 'custom' not in manager.symbol_lists

    def test_load_from_nonexistent_file(self, manager, tmp_path):
        """Test error handling for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.json"

        result = manager.load_symbol_list('custom', file_path=str(nonexistent))

        assert result == []

    def test_load_from_exchange_nyse(self, manager):
        """Test loading symbols from NYSE via ticker_downloader."""
        mock_symbols = ['NYSE_1', 'NYSE_2', 'NYSE_3']

        with patch('src.screening.universe.ticker_downloader') as mock_downloader:
            mock_downloader.get_tickers.return_value = mock_symbols

            result = manager.load_symbol_list('NYSE')

            assert result == mock_symbols
            assert manager.symbol_lists['NYSE'] == mock_symbols
            mock_downloader.get_tickers.assert_called_once_with('NYSE')

    def test_load_from_exchange_nasdaq(self, manager):
        """Test loading symbols from NASDAQ via ticker_downloader."""
        mock_symbols = ['NASDAQ_1', 'NASDAQ_2']

        with patch('src.screening.universe.ticker_downloader') as mock_downloader:
            mock_downloader.get_tickers.return_value = mock_symbols

            result = manager.load_symbol_list('nasdaq')

            assert result == mock_symbols
            mock_downloader.get_tickers.assert_called_once_with('NASDAQ')

    def test_load_from_exchange_all(self, manager):
        """Test loading all symbols via ticker_downloader."""
        mock_symbols = ['SYM1', 'SYM2', 'SYM3', 'SYM4']

        with patch('src.screening.universe.ticker_downloader') as mock_downloader:
            mock_downloader.get_all_tickers.return_value = mock_symbols

            result = manager.load_symbol_list('ALL')

            assert result == mock_symbols
            assert manager.symbol_lists['ALL'] == mock_symbols
            mock_downloader.get_all_tickers.assert_called_once()

    def test_load_cached_symbol_list(self, manager):
        """Test loading already-cached symbol list."""
        cached_symbols = ['CACHED1', 'CACHED2']
        manager.symbol_lists['cached_source'] = cached_symbols

        result = manager.load_symbol_list('cached_source')

        assert result == cached_symbols

    def test_load_from_data_directory_json(self, manager, tmp_path):
        """Test loading from data directory JSON file."""
        symbols = ['LOCAL1', 'LOCAL2', 'LOCAL3']
        json_file = manager.data_dir / "sp500.json"

        with open(json_file, 'w') as f:
            json.dump(symbols, f)

        result = manager.load_symbol_list('sp500')

        assert result == symbols
        assert manager.symbol_lists['sp500'] == symbols

    def test_load_unknown_source(self, manager):
        """Test handling of unknown source."""
        result = manager.load_symbol_list('unknown_source')

        assert result == []
        assert 'unknown_source' not in manager.symbol_lists

    def test_load_malformed_json(self, manager, tmp_path):
        """Test error handling for malformed JSON."""
        json_file = tmp_path / "malformed.json"
        json_file.write_text("{ this is not valid json")

        result = manager.load_symbol_list('malformed', file_path=str(json_file))

        assert result == []

    def test_load_empty_csv(self, manager, tmp_path):
        """Test loading empty CSV file."""
        csv_file = tmp_path / "empty.csv"
        pd.DataFrame(columns=['symbol']).to_csv(csv_file, index=False)

        result = manager.load_symbol_list('empty', file_path=str(csv_file))

        assert result == []


class TestSaveSymbolList:
    """Test saving symbol lists to files."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_save_symbol_list(self, manager):
        """Test saving symbol list to JSON."""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        result = manager.save_symbol_list('test_list', symbols)

        assert result is True

        saved_file = manager.data_dir / "test_list.json"
        assert saved_file.exists()

        with open(saved_file, 'r') as f:
            loaded = json.load(f)
        assert loaded == symbols

    def test_save_empty_list(self, manager):
        """Test saving empty symbol list."""
        result = manager.save_symbol_list('empty_list', [])

        assert result is True

        saved_file = manager.data_dir / "empty_list.json"
        assert saved_file.exists()

        with open(saved_file, 'r') as f:
            loaded = json.load(f)
        assert loaded == []

    def test_save_with_permission_error(self, manager, monkeypatch):
        """Test error handling for file permission errors."""
        symbols = ['AAPL', 'MSFT']

        # Make directory read-only
        manager.data_dir.chmod(0o444)

        result = manager.save_symbol_list('test', symbols)

        # Restore permissions
        manager.data_dir.chmod(0o755)

        assert result is False


class TestBuildUniverse:
    """Test universe building from multiple sources."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000
            mock_config.universe.sources = ['NYSE', 'NASDAQ']

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_build_from_single_source(self, manager):
        """Test building universe from single source."""
        mock_symbols = ['AAPL', 'MSFT', 'GOOGL']

        with patch.object(manager, 'load_symbol_list', return_value=mock_symbols):
            universe = manager.build_universe(['NYSE'])

            assert universe == sorted(mock_symbols)

    def test_build_from_multiple_sources(self, manager):
        """Test building universe from multiple sources with deduplication."""
        def mock_load(source):
            if source == 'NYSE':
                return ['AAPL', 'IBM', 'JPM']
            elif source == 'NASDAQ':
                return ['AAPL', 'MSFT', 'GOOGL']
            return []

        with patch.object(manager, 'load_symbol_list', side_effect=mock_load):
            universe = manager.build_universe(['NYSE', 'NASDAQ'])

            # Should deduplicate AAPL
            expected = sorted(['AAPL', 'IBM', 'JPM', 'MSFT', 'GOOGL'])
            assert universe == expected

    def test_build_with_empty_source(self, manager):
        """Test building universe when source returns empty list."""
        with patch.object(manager, 'load_symbol_list', return_value=[]):
            universe = manager.build_universe(['NYSE'])

            assert universe == []

    def test_build_with_default_sources(self, manager):
        """Test building universe using config default sources."""
        mock_symbols = ['AAPL', 'MSFT']

        with patch.object(manager, 'load_symbol_list', return_value=mock_symbols):
            universe = manager.build_universe()  # No sources specified

            assert len(universe) > 0

    def test_build_removes_duplicates(self, manager):
        """Test that duplicates are removed."""
        def mock_load(source):
            return ['AAPL', 'AAPL', 'MSFT', 'MSFT', 'GOOGL']

        with patch.object(manager, 'load_symbol_list', side_effect=mock_load):
            universe = manager.build_universe(['NYSE'])

            assert universe == ['AAPL', 'GOOGL', 'MSFT']  # Sorted, unique

    def test_build_sorts_alphabetically(self, manager):
        """Test that universe is sorted alphabetically."""
        mock_symbols = ['ZZZZ', 'AAAA', 'MMMM', 'BBBB']

        with patch.object(manager, 'load_symbol_list', return_value=mock_symbols):
            universe = manager.build_universe(['NYSE'])

            assert universe == ['AAAA', 'BBBB', 'MMMM', 'ZZZZ']


class TestGetUniverseQuotes:
    """Test fetching market quotes for universe symbols."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_get_quotes_success(self, manager):
        """Test successful quote fetching."""
        symbols = ['AAPL', 'MSFT']

        # Mock IB manager
        mock_ib = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.last = 150.0
        mock_ticker.bid = 149.95
        mock_ticker.ask = 150.05
        mock_ticker.volume = 1000000
        mock_ticker.close = 149.5
        mock_ticker.high = 151.0
        mock_ticker.low = 149.0

        mock_ib.reqTicker.return_value = mock_ticker
        mock_ib.sleep = MagicMock()

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True
            mock_manager.ib = mock_ib

            df = manager.get_universe_quotes(symbols)

            assert not df.empty
            assert len(df) == 2
            assert list(df.columns) == [
                'symbol', 'last', 'bid', 'ask', 'volume',
                'close', 'high', 'low', 'timestamp'
            ]
            assert df['symbol'].tolist() == symbols

    def test_get_quotes_ib_not_connected(self, manager):
        """Test quote fetching when IB is not connected."""
        symbols = ['AAPL', 'MSFT']

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = False

            df = manager.get_universe_quotes(symbols)

            assert df.empty

    def test_get_quotes_with_nan_values(self, manager):
        """Test handling of NaN values in ticker data."""
        symbols = ['AAPL']

        mock_ib = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.last = float('nan')
        mock_ticker.bid = 149.95
        mock_ticker.ask = float('nan')
        mock_ticker.volume = 1000000
        mock_ticker.close = 149.5
        mock_ticker.high = 151.0
        mock_ticker.low = 149.0

        mock_ib.reqTicker.return_value = mock_ticker
        mock_ib.sleep = MagicMock()

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True
            mock_manager.ib = mock_ib

            df = manager.get_universe_quotes(symbols)

            assert not df.empty
            assert pd.isna(df.loc[0, 'last'])
            assert pd.isna(df.loc[0, 'ask'])
            assert not pd.isna(df.loc[0, 'bid'])

    def test_get_quotes_with_errors(self, manager):
        """Test quote fetching when some symbols fail."""
        symbols = ['AAPL', 'INVALID', 'MSFT']

        mock_ib = MagicMock()

        def mock_req_ticker(contract):
            if 'INVALID' in str(contract):
                raise Exception("Invalid symbol")
            ticker = MagicMock()
            ticker.last = 150.0
            ticker.bid = 149.95
            ticker.ask = 150.05
            ticker.volume = 1000000
            ticker.close = 149.5
            ticker.high = 151.0
            ticker.low = 149.0
            return ticker

        mock_ib.reqTicker.side_effect = mock_req_ticker
        mock_ib.sleep = MagicMock()

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True
            mock_manager.ib = mock_ib

            df = manager.get_universe_quotes(symbols)

            # Should return quotes for 2 valid symbols
            assert len(df) == 2
            assert 'INVALID' not in df['symbol'].values

    def test_get_quotes_empty_symbol_list(self, manager):
        """Test quote fetching with empty symbol list."""
        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True

            df = manager.get_universe_quotes([])

            assert df.empty

    def test_get_quotes_rate_limiting(self, manager):
        """Test that rate limiting is applied between requests."""
        symbols = ['AAPL', 'MSFT', 'GOOGL']

        mock_ib = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.last = 150.0
        mock_ticker.bid = 149.95
        mock_ticker.ask = 150.05
        mock_ticker.volume = 1000000
        mock_ticker.close = 149.5
        mock_ticker.high = 151.0
        mock_ticker.low = 149.0

        mock_ib.reqTicker.return_value = mock_ticker
        mock_ib.sleep = MagicMock()

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True
            mock_manager.ib = mock_ib

            df = manager.get_universe_quotes(symbols)

            # Verify sleep was called for rate limiting
            assert mock_ib.sleep.call_count == len(symbols)
            mock_ib.sleep.assert_called_with(0.1)

    def test_get_quotes_exception_handling(self, manager):
        """Test overall exception handling in get_universe_quotes."""
        symbols = ['AAPL']

        with patch('src.screening.universe.ib_manager') as mock_manager:
            mock_manager.is_connected.return_value = True
            mock_manager.ib.reqTicker.side_effect = Exception("Fatal error")

            df = manager.get_universe_quotes(symbols)

            assert df.empty


class TestFilterUniverse:
    """Test universe filtering by price and volume."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 5.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    @pytest.fixture
    def sample_quotes(self):
        """Create sample quote data."""
        return pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'PENNY', 'EXPENSIVE', 'LOW_VOL'],
            'last': [150.0, 300.0, 2.0, 1000.0, 50.0],
            'volume': [10000000, 5000000, 100000, 1000000, 100000],
            'bid': [149.95, 299.95, 1.99, 999.0, 49.95],
            'ask': [150.05, 300.05, 2.01, 1001.0, 50.05],
            'close': [149.5, 299.5, 1.98, 998.0, 49.8],
            'high': [151.0, 301.0, 2.05, 1005.0, 51.0],
            'low': [149.0, 299.0, 1.95, 995.0, 49.0],
            'timestamp': [datetime.now()] * 5
        })

    def test_filter_with_defaults(self, manager, sample_quotes):
        """Test filtering with default parameters."""
        symbols = sample_quotes['symbol'].tolist()

        with patch.object(manager, 'get_universe_quotes', return_value=sample_quotes):
            filtered = manager.filter_universe(symbols)

            # PENNY (price < 5), EXPENSIVE (price > 500), LOW_VOL (volume < 500k) filtered out
            assert set(filtered) == {'AAPL', 'MSFT'}

    def test_filter_custom_min_price(self, manager, sample_quotes):
        """Test filtering with custom minimum price."""
        symbols = sample_quotes['symbol'].tolist()

        with patch.object(manager, 'get_universe_quotes', return_value=sample_quotes):
            filtered = manager.filter_universe(symbols, min_price=100.0, max_price=1000.0, min_volume=100000)

            # Only AAPL and MSFT meet min_price >= 100
            assert set(filtered) == {'AAPL', 'MSFT', 'EXPENSIVE'}

    def test_filter_custom_volume(self, manager, sample_quotes):
        """Test filtering with custom minimum volume."""
        symbols = sample_quotes['symbol'].tolist()

        with patch.object(manager, 'get_universe_quotes', return_value=sample_quotes):
            filtered = manager.filter_universe(symbols, min_price=1.0, max_price=2000.0, min_volume=5000000)

            # AAPL (10M) and MSFT (5M) have volume >= 5M
            assert set(filtered) == {'AAPL', 'MSFT'}

    def test_filter_all_filtered_out(self, manager):
        """Test filtering when all symbols are filtered out."""
        quotes = pd.DataFrame({
            'symbol': ['PENNY1', 'PENNY2'],
            'last': [1.0, 2.0],
            'volume': [100, 200],
            'bid': [0.99, 1.99],
            'ask': [1.01, 2.01],
            'close': [0.98, 1.98],
            'high': [1.05, 2.05],
            'low': [0.95, 1.95],
            'timestamp': [datetime.now()] * 2
        })

        with patch.object(manager, 'get_universe_quotes', return_value=quotes):
            filtered = manager.filter_universe(['PENNY1', 'PENNY2'], min_price=10.0)

            assert filtered == []

    def test_filter_empty_quotes(self, manager):
        """Test filtering when quote data is empty."""
        symbols = ['AAPL', 'MSFT']

        with patch.object(manager, 'get_universe_quotes', return_value=pd.DataFrame()):
            filtered = manager.filter_universe(symbols)

            # Returns unfiltered when no quote data
            assert filtered == symbols

    def test_filter_with_cached_quotes(self, manager, sample_quotes):
        """Test filtering using cached quotes."""
        symbols = sample_quotes['symbol'].tolist()
        manager.cache['quotes'] = sample_quotes
        manager.cache['quotes_timestamp'] = datetime.now()

        with patch.object(manager, 'get_universe_quotes') as mock_quotes:
            filtered = manager.filter_universe(symbols, use_cached_quotes=True)

            # Should not call get_universe_quotes
            mock_quotes.assert_not_called()
            assert len(filtered) > 0

    def test_filter_fetches_fresh_quotes(self, manager, sample_quotes):
        """Test filtering fetches fresh quotes when not using cache."""
        symbols = sample_quotes['symbol'].tolist()

        with patch.object(manager, 'get_universe_quotes', return_value=sample_quotes) as mock_quotes:
            filtered = manager.filter_universe(symbols, use_cached_quotes=False)

            # Should call get_universe_quotes
            mock_quotes.assert_called_once_with(symbols)
            assert 'quotes' in manager.cache

    def test_filter_updates_cache(self, manager, sample_quotes):
        """Test that filtering updates the cache."""
        symbols = sample_quotes['symbol'].tolist()

        with patch.object(manager, 'get_universe_quotes', return_value=sample_quotes):
            manager.filter_universe(symbols)

            assert 'quotes' in manager.cache
            assert 'quotes_timestamp' in manager.cache
            pd.testing.assert_frame_equal(manager.cache['quotes'], sample_quotes)


class TestGetUniverseSummary:
    """Test universe summary statistics generation."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000
            mock_config.universe.sources = ['NYSE']

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_summary_with_quotes(self, manager):
        """Test summary generation with valid quote data."""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        quotes = pd.DataFrame({
            'symbol': symbols,
            'last': [150.0, 300.0, 2500.0],
            'volume': [10000000, 5000000, 1000000],
            'bid': [149.95, 299.95, 2499.0],
            'ask': [150.05, 300.05, 2501.0],
            'close': [149.5, 299.5, 2499.0],
            'high': [151.0, 301.0, 2510.0],
            'low': [149.0, 299.0, 2490.0],
            'timestamp': [datetime.now()] * 3
        })

        with patch.object(manager, 'get_universe_quotes', return_value=quotes):
            summary = manager.get_universe_summary(symbols)

            assert summary['symbol_count'] == 3
            assert summary['price_range'] == (150.0, 2500.0)
            assert summary['volume_range'] == (1000000, 10000000)
            assert summary['avg_price'] == pytest.approx(983.33, rel=0.01)
            assert summary['avg_volume'] == 5333333
            assert 'timestamp' in summary

    def test_summary_without_quotes(self, manager):
        """Test summary generation when quotes are not available."""
        symbols = ['AAPL', 'MSFT']

        with patch.object(manager, 'get_universe_quotes', return_value=pd.DataFrame()):
            summary = manager.get_universe_summary(symbols)

            assert summary['symbol_count'] == 2
            assert 'price_range' not in summary
            assert 'volume_range' not in summary
            assert 'timestamp' in summary

    def test_summary_builds_universe_if_none_provided(self, manager):
        """Test that summary builds universe if symbols not provided."""
        with patch.object(manager, 'build_universe', return_value=['AAPL', 'MSFT']) as mock_build:
            with patch.object(manager, 'get_universe_quotes', return_value=pd.DataFrame()):
                summary = manager.get_universe_summary()

                mock_build.assert_called_once()
                assert summary['symbol_count'] == 2

    def test_summary_empty_universe(self, manager):
        """Test summary with empty universe."""
        with patch.object(manager, 'get_universe_quotes', return_value=pd.DataFrame()):
            summary = manager.get_universe_summary([])

            assert summary['symbol_count'] == 0
            assert 'timestamp' in summary


class TestRefreshUniverse:
    """Test universe refresh workflow."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_refresh_builds_and_filters(self, manager):
        """Test that refresh builds raw universe and applies filters."""
        raw_symbols = ['AAPL', 'MSFT', 'PENNY', 'GOOGL']
        filtered_symbols = ['AAPL', 'MSFT', 'GOOGL']

        with patch.object(manager, 'build_universe', return_value=raw_symbols) as mock_build:
            with patch.object(manager, 'filter_universe', return_value=filtered_symbols) as mock_filter:
                result = manager.refresh_universe()

                mock_build.assert_called_once()
                mock_filter.assert_called_once_with(raw_symbols)
                assert result == filtered_symbols

    def test_refresh_updates_cache(self, manager):
        """Test that refresh updates the cache."""
        filtered_symbols = ['AAPL', 'MSFT']

        with patch.object(manager, 'build_universe', return_value=['AAPL', 'MSFT', 'PENNY']):
            with patch.object(manager, 'filter_universe', return_value=filtered_symbols):
                manager.refresh_universe()

                assert 'universe' in manager.cache
                assert manager.cache['universe'] == filtered_symbols
                assert 'universe_timestamp' in manager.cache
                assert isinstance(manager.cache['universe_timestamp'], datetime)

    def test_refresh_returns_filtered_universe(self, manager):
        """Test that refresh returns the filtered universe."""
        expected = ['AAPL', 'MSFT', 'GOOGL']

        with patch.object(manager, 'build_universe', return_value=['AAPL', 'MSFT', 'GOOGL', 'PENNY']):
            with patch.object(manager, 'filter_universe', return_value=expected):
                result = manager.refresh_universe()

                assert result == expected


class TestUniverseManagerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UniverseManager with temp directory."""
        with patch('src.screening.universe.config') as mock_config:
            mock_config.get.return_value = str(tmp_path / "universe")
            mock_config.universe.min_price = 1.0
            mock_config.universe.max_price = 500.0
            mock_config.universe.min_avg_volume = 500000

            return UniverseManager(data_dir=str(tmp_path / "universe"))

    def test_empty_universe_operations(self, manager):
        """Test operations on empty universe."""
        with patch.object(manager, 'get_universe_quotes', return_value=pd.DataFrame()):
            quotes = manager.get_universe_quotes([])
            assert quotes.empty

            filtered = manager.filter_universe([])
            assert filtered == []

            summary = manager.get_universe_summary([])
            assert summary['symbol_count'] == 0

    def test_duplicate_symbols_in_filter(self, manager):
        """Test filtering with duplicate symbols in input."""
        symbols = ['AAPL', 'AAPL', 'MSFT', 'MSFT']
        quotes = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'last': [150.0, 300.0],
            'volume': [10000000, 5000000],
            'bid': [149.95, 299.95],
            'ask': [150.05, 300.05],
            'close': [149.5, 299.5],
            'high': [151.0, 301.0],
            'low': [149.0, 299.0],
            'timestamp': [datetime.now()] * 2
        })

        with patch.object(manager, 'get_universe_quotes', return_value=quotes):
            filtered = manager.filter_universe(symbols, min_price=100.0, min_volume=1000000)

            assert set(filtered) == {'AAPL', 'MSFT'}

    def test_very_large_universe(self, manager):
        """Test handling of very large universe (performance check)."""
        large_universe = [f'SYM{i:04d}' for i in range(5000)]

        with patch.object(manager, 'load_symbol_list', return_value=large_universe):
            universe = manager.build_universe(['LARGE'])

            assert len(universe) == 5000
            assert universe == sorted(large_universe)

    def test_special_characters_in_symbols(self, manager):
        """Test handling of symbols with special characters."""
        symbols = ['BRK.B', 'BF.A', 'TEST-WT', 'SYMBOL_R']

        with patch.object(manager, 'load_symbol_list', return_value=symbols):
            universe = manager.build_universe(['special'])

            assert set(universe) == set(symbols)

    def test_cache_persistence_across_operations(self, manager):
        """Test that cache persists across multiple operations."""
        quotes = pd.DataFrame({
            'symbol': ['AAPL'],
            'last': [150.0],
            'volume': [10000000],
            'bid': [149.95],
            'ask': [150.05],
            'close': [149.5],
            'high': [151.0],
            'low': [149.0],
            'timestamp': [datetime.now()]
        })

        with patch.object(manager, 'get_universe_quotes', return_value=quotes):
            # First filter operation - populates cache
            manager.filter_universe(['AAPL'])

            # Cache should exist
            assert 'quotes' in manager.cache
            assert 'quotes_timestamp' in manager.cache

            # Second operation using cached quotes
            filtered = manager.filter_universe(['AAPL'], use_cached_quotes=True)

            assert filtered == ['AAPL']


class TestGlobalSingleton:
    """Test global singleton instance."""

    def test_singleton_exists(self):
        """Test that global universe_manager singleton is created."""
        assert universe_manager is not None
        assert isinstance(universe_manager, UniverseManager)

    def test_singleton_is_functional(self):
        """Test that singleton instance is functional."""
        with patch.object(universe_manager, 'load_symbol_list', return_value=['AAPL', 'MSFT']):
            symbols = universe_manager.load_symbol_list('test')

            assert symbols == ['AAPL', 'MSFT']
