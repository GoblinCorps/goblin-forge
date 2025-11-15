"""
Unit Tests for Historical Data Manager

Tests Parquet-based storage and retrieval of historical bar data.

Test Coverage:
--------------
- Save/load Parquet files
- Data validation
- Merge and deduplication
- Metadata retrieval
- File operations (delete, list)
- Edge cases and error handling

Run:
----
pytest tests/test_historical_manager.py -v --cov=src/data
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.data.historical_manager import HistoricalDataManager


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def historical_manager_test(temp_data_dir):
    """Create historical manager instance with temporary directory."""
    return HistoricalDataManager(data_dir=temp_data_dir)


@pytest.fixture
def sample_bars():
    """Generate sample OHLCV bar data."""
    np.random.seed(42)

    dates = pd.date_range('2024-01-01 09:30', periods=100, freq='15min')
    close = 100 + np.random.randn(100).cumsum() * 0.5

    df = pd.DataFrame({
        'date': dates,
        'open': close + (np.random.randn(100) * 0.2),
        'high': close + np.abs(np.random.randn(100)) * 0.5,
        'low': close - np.abs(np.random.randn(100)) * 0.5,
        'close': close,
        'volume': np.random.randint(100000, 1000000, 100)
    })

    return df


@pytest.fixture
def additional_bars():
    """Generate additional bars for testing updates."""
    np.random.seed(123)

    # Start after sample_bars end date
    dates = pd.date_range('2024-01-03 09:30', periods=50, freq='15min')
    close = 105 + np.random.randn(50).cumsum() * 0.5

    df = pd.DataFrame({
        'date': dates,
        'open': close + (np.random.randn(50) * 0.2),
        'high': close + np.abs(np.random.randn(50)) * 0.5,
        'low': close - np.abs(np.random.randn(50)) * 0.5,
        'close': close,
        'volume': np.random.randint(100000, 1000000, 50)
    })

    return df


class TestSaveLoad:
    """Test basic save and load functionality."""

    def test_save_success(self, historical_manager_test, sample_bars):
        """Test successful save of historical data."""
        result = historical_manager_test.save(
            symbol='AAPL',
            timeframe='15 mins',
            data=sample_bars
        )

        assert result is True

    def test_load_success(self, historical_manager_test, sample_bars):
        """Test successful load of historical data."""
        # Save first
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Load
        loaded_df = historical_manager_test.load('AAPL', '15 mins')

        assert loaded_df is not None
        assert len(loaded_df) == len(sample_bars)

    def test_load_nonexistent(self, historical_manager_test):
        """Test load of nonexistent file returns None."""
        loaded_df = historical_manager_test.load('NONEXISTENT', '15 mins')

        assert loaded_df is None

    def test_save_overwrites(self, historical_manager_test, sample_bars, additional_bars):
        """Test that save with overwrite=True replaces data."""
        # Save initial data
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Overwrite with new data
        historical_manager_test.save(
            'AAPL',
            '15 mins',
            additional_bars,
            overwrite=True
        )

        # Load and verify
        loaded_df = historical_manager_test.load('AAPL', '15 mins')
        assert len(loaded_df) == len(additional_bars)


class TestDataValidation:
    """Test data validation functionality."""

    def test_empty_dataframe_rejected(self, historical_manager_test):
        """Test that empty DataFrame is rejected."""
        with pytest.raises(ValueError):
            historical_manager_test.save(
                'AAPL',
                '15 mins',
                pd.DataFrame()
            )

    def test_missing_columns_rejected(self, historical_manager_test, sample_bars):
        """Test that missing required columns are rejected."""
        # Remove 'close' column
        df_incomplete = sample_bars.drop(columns=['close'])

        with pytest.raises(ValueError):
            historical_manager_test.save('AAPL', '15 mins', df_incomplete)

    def test_invalid_date_type_rejected(self, historical_manager_test, sample_bars):
        """Test that non-datetime date column is rejected."""
        df_invalid = sample_bars.copy()
        df_invalid['date'] = df_invalid['date'].astype(str)  # Convert to string

        with pytest.raises(ValueError):
            historical_manager_test.save('AAPL', '15 mins', df_invalid)


class TestMergeDeduplication:
    """Test merge and deduplication logic."""

    def test_update_merges_data(self, historical_manager_test, sample_bars, additional_bars):
        """Test that update merges new data with existing."""
        # Save initial data
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Update with additional data
        historical_manager_test.update('AAPL', '15 mins', additional_bars)

        # Load and verify
        loaded_df = historical_manager_test.load('AAPL', '15 mins')
        expected_length = len(sample_bars) + len(additional_bars)

        assert len(loaded_df) == expected_length

    def test_duplicates_removed(self, historical_manager_test, sample_bars):
        """Test that duplicate timestamps are removed."""
        # Save data
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Save same data again (should deduplicate)
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Load and verify
        loaded_df = historical_manager_test.load('AAPL', '15 mins')

        # Should still have same length (duplicates removed)
        assert len(loaded_df) == len(sample_bars)

    def test_data_sorted_by_date(self, historical_manager_test, sample_bars):
        """Test that saved data is sorted by date."""
        # Shuffle data
        shuffled = sample_bars.sample(frac=1).reset_index(drop=True)

        # Save shuffled data
        historical_manager_test.save('AAPL', '15 mins', shuffled)

        # Load
        loaded_df = historical_manager_test.load('AAPL', '15 mins')

        # Verify sorted
        assert loaded_df['date'].is_monotonic_increasing


class TestDateFiltering:
    """Test date filtering on load."""

    def test_load_with_start_date(self, historical_manager_test, sample_bars):
        """Test loading with start_date filter."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Get midpoint date
        midpoint = sample_bars['date'].iloc[50]

        # Load from midpoint
        loaded_df = historical_manager_test.load(
            'AAPL',
            '15 mins',
            start_date=midpoint
        )

        assert len(loaded_df) < len(sample_bars)
        assert loaded_df['date'].min() >= midpoint

    def test_load_with_end_date(self, historical_manager_test, sample_bars):
        """Test loading with end_date filter."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        # Get midpoint date
        midpoint = sample_bars['date'].iloc[50]

        # Load up to midpoint
        loaded_df = historical_manager_test.load(
            'AAPL',
            '15 mins',
            end_date=midpoint
        )

        assert len(loaded_df) < len(sample_bars)
        assert loaded_df['date'].max() <= midpoint

    def test_load_with_date_range(self, historical_manager_test, sample_bars):
        """Test loading with both start and end dates."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        start = sample_bars['date'].iloc[25]
        end = sample_bars['date'].iloc[75]

        loaded_df = historical_manager_test.load(
            'AAPL',
            '15 mins',
            start_date=start,
            end_date=end
        )

        assert loaded_df['date'].min() >= start
        assert loaded_df['date'].max() <= end


class TestMetadata:
    """Test metadata retrieval."""

    def test_get_metadata(self, historical_manager_test, sample_bars):
        """Test metadata retrieval."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)

        metadata = historical_manager_test.get_metadata('AAPL', '15 mins')

        assert metadata is not None
        assert metadata['symbol'] == 'AAPL'
        assert metadata['timeframe'] == '15 mins'
        assert metadata['bar_count'] == len(sample_bars)
        assert 'start_date' in metadata
        assert 'end_date' in metadata
        assert 'file_size_mb' in metadata

    def test_get_metadata_nonexistent(self, historical_manager_test):
        """Test metadata for nonexistent file returns None."""
        metadata = historical_manager_test.get_metadata('NONEXISTENT', '15 mins')
        assert metadata is None


class TestFileOperations:
    """Test file operations (delete, list)."""

    def test_delete_specific_timeframe(self, historical_manager_test, sample_bars):
        """Test deletion of specific timeframe."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)
        historical_manager_test.save('AAPL', '1 hour', sample_bars)

        # Delete 15 mins
        result = historical_manager_test.delete('AAPL', '15 mins')
        assert result is True

        # 15 mins should be gone
        assert historical_manager_test.load('AAPL', '15 mins') is None

        # 1 hour should still exist
        assert historical_manager_test.load('AAPL', '1 hour') is not None

    def test_delete_all_symbol_data(self, historical_manager_test, sample_bars):
        """Test deletion of all data for a symbol."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)
        historical_manager_test.save('AAPL', '1 hour', sample_bars)

        # Delete all AAPL data
        result = historical_manager_test.delete('AAPL')
        assert result is True

        # All data should be gone
        assert historical_manager_test.load('AAPL', '15 mins') is None
        assert historical_manager_test.load('AAPL', '1 hour') is None

    def test_list_symbols(self, historical_manager_test, sample_bars):
        """Test listing all symbols."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)
        historical_manager_test.save('MSFT', '15 mins', sample_bars)
        historical_manager_test.save('GOOGL', '15 mins', sample_bars)

        symbols = historical_manager_test.list_symbols()

        assert len(symbols) == 3
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'GOOGL' in symbols

    def test_list_timeframes(self, historical_manager_test, sample_bars):
        """Test listing timeframes for a symbol."""
        historical_manager_test.save('AAPL', '5 mins', sample_bars)
        historical_manager_test.save('AAPL', '15 mins', sample_bars)
        historical_manager_test.save('AAPL', '1 hour', sample_bars)

        timeframes = historical_manager_test.list_timeframes('AAPL')

        assert len(timeframes) == 3
        assert '5mins' in timeframes
        assert '15mins' in timeframes
        assert '1hour' in timeframes


class TestStorageSummary:
    """Test storage summary functionality."""

    def test_get_storage_summary(self, historical_manager_test, sample_bars):
        """Test storage summary generation."""
        historical_manager_test.save('AAPL', '15 mins', sample_bars)
        historical_manager_test.save('MSFT', '15 mins', sample_bars)

        summary = historical_manager_test.get_storage_summary()

        assert summary['symbol_count'] == 2
        assert summary['total_files'] == 2
        assert summary['total_size_mb'] > 0
        assert len(summary['symbols']) == 2


class TestTimeframeNormalization:
    """Test timeframe normalization."""

    def test_normalize_timeframe(self, historical_manager_test):
        """Test that timeframe strings are normalized correctly."""
        # These should all map correctly
        assert historical_manager_test._normalize_timeframe('5 mins') == '5mins'
        assert historical_manager_test._normalize_timeframe('15 mins') == '15mins'
        assert historical_manager_test._normalize_timeframe('1 hour') == '1hour'
        assert historical_manager_test._normalize_timeframe('4 hours') == '4hours'
        assert historical_manager_test._normalize_timeframe('1 day') == '1day'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/data', '--cov-report=term-missing'])
