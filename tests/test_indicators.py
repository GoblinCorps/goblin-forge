"""
Unit Tests for Indicator Calculation Engine

Tests all technical indicators for accuracy, edge cases, and error handling.

Test Coverage:
--------------
- Bollinger Bands calculation and edge cases
- Stochastic RSI calculation
- MACD calculation
- RSI calculation
- ATR calculation
- Batch calculation (calculate_all)
- Data validation
- NaN handling
- Insufficient data handling

Run:
----
pytest tests/test_indicators.py -v --cov=src/indicators
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators.indicator_engine import indicator_engine


@pytest.fixture
def sample_ohlcv_data():
    """
    Generate sample OHLCV data for testing.

    Returns 200 bars of synthetic price data with realistic characteristics.
    """
    np.random.seed(42)  # Reproducible results

    dates = pd.date_range('2024-01-01', periods=200, freq='15min')

    # Generate realistic price data (trending with noise)
    base_price = 100.0
    trend = np.linspace(0, 10, 200)  # Upward trend
    noise = np.random.randn(200).cumsum() * 0.5

    close = base_price + trend + noise

    # OHLC derived from close
    high = close + np.abs(np.random.randn(200)) * 0.5
    low = close - np.abs(np.random.randn(200)) * 0.5
    open_price = close + (np.random.randn(200) * 0.2)

    # Volume
    volume = np.random.randint(100000, 1000000, 200)

    df = pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    return df


@pytest.fixture
def insufficient_data():
    """Generate insufficient data (< min_bars_required)."""
    np.random.seed(42)

    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=20, freq='15min'),
        'open': np.random.randn(20).cumsum() + 100,
        'high': np.random.randn(20).cumsum() + 101,
        'low': np.random.randn(20).cumsum() + 99,
        'close': np.random.randn(20).cumsum() + 100,
        'volume': np.random.randint(100000, 1000000, 20)
    })

    return df


@pytest.fixture
def data_with_nan():
    """Generate data with NaN values."""
    np.random.seed(42)

    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=200, freq='15min'),
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 101,
        'low': np.random.randn(200).cumsum() + 99,
        'close': np.random.randn(200).cumsum() + 100,
        'volume': np.random.randint(100000, 1000000, 200)
    })

    # Introduce NaN values
    df.loc[50:55, 'close'] = np.nan

    return df


class TestDataValidation:
    """Test data validation functionality."""

    def test_valid_data(self, sample_ohlcv_data):
        """Test that valid data passes validation."""
        result = indicator_engine.validate_data(sample_ohlcv_data, symbol='TEST')
        assert result is True

    def test_insufficient_bars(self, insufficient_data):
        """Test that insufficient bars fail validation."""
        result = indicator_engine.validate_data(insufficient_data, symbol='TEST')
        assert result is False

    def test_empty_dataframe(self):
        """Test that empty DataFrame fails validation."""
        df = pd.DataFrame()
        result = indicator_engine.validate_data(df, symbol='TEST')
        assert result is False

    def test_missing_columns(self, sample_ohlcv_data):
        """Test that missing columns fail validation."""
        df = sample_ohlcv_data.drop(columns=['close'])
        result = indicator_engine.validate_data(df, symbol='TEST')
        assert result is False

    def test_none_input(self):
        """Test that None input fails validation."""
        result = indicator_engine.validate_data(None, symbol='TEST')
        assert result is False


class TestBollingerBands:
    """Test Bollinger Bands calculation."""

    def test_bollinger_bands_calculation(self, sample_ohlcv_data):
        """Test that Bollinger Bands are calculated correctly."""
        df = indicator_engine.calculate_bollinger_bands(sample_ohlcv_data.copy())

        # Check that columns were added
        assert 'bb_upper' in df.columns
        assert 'bb_middle' in df.columns
        assert 'bb_lower' in df.columns
        assert 'bb_width' in df.columns
        assert 'bb_position' in df.columns

        # Check that upper > middle > lower (for most bars)
        valid_bars = df.dropna()
        assert (valid_bars['bb_upper'] >= valid_bars['bb_middle']).sum() > len(valid_bars) * 0.95
        assert (valid_bars['bb_middle'] >= valid_bars['bb_lower']).sum() > len(valid_bars) * 0.95

    def test_bb_position_range(self, sample_ohlcv_data):
        """Test that BB position is within 0-1 range."""
        df = indicator_engine.calculate_bollinger_bands(sample_ohlcv_data.copy())

        # Check that position is clipped to 0-1
        valid_bars = df.dropna()
        assert (valid_bars['bb_position'] >= 0).all()
        assert (valid_bars['bb_position'] <= 1).all()

    def test_bb_width_positive(self, sample_ohlcv_data):
        """Test that BB width is always positive."""
        df = indicator_engine.calculate_bollinger_bands(sample_ohlcv_data.copy())

        valid_bars = df.dropna()
        assert (valid_bars['bb_width'] > 0).all()


class TestStochasticRSI:
    """Test Stochastic RSI calculation."""

    def test_stochastic_rsi_calculation(self, sample_ohlcv_data):
        """Test that Stochastic RSI is calculated correctly."""
        df = indicator_engine.calculate_stochastic_rsi(sample_ohlcv_data.copy())

        # Check that columns were added
        assert 'stoch_rsi_k' in df.columns
        assert 'stoch_rsi_d' in df.columns
        assert 'stoch_rsi' in df.columns

    def test_stochastic_rsi_range(self, sample_ohlcv_data):
        """Test that Stochastic RSI is within 0-100 range."""
        df = indicator_engine.calculate_stochastic_rsi(sample_ohlcv_data.copy())

        valid_bars = df.dropna()
        assert (valid_bars['stoch_rsi_k'] >= 0).all()
        assert (valid_bars['stoch_rsi_k'] <= 100).all()
        assert (valid_bars['stoch_rsi_d'] >= 0).all()
        assert (valid_bars['stoch_rsi_d'] <= 100).all()


class TestMACD:
    """Test MACD calculation."""

    def test_macd_calculation(self, sample_ohlcv_data):
        """Test that MACD is calculated correctly."""
        df = indicator_engine.calculate_macd(sample_ohlcv_data.copy())

        # Check that columns were added
        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_hist' in df.columns

    def test_macd_histogram_relationship(self, sample_ohlcv_data):
        """Test that MACD histogram = MACD - Signal."""
        df = indicator_engine.calculate_macd(sample_ohlcv_data.copy())

        valid_bars = df.dropna()
        # MACD histogram should equal MACD - Signal
        calculated_hist = valid_bars['macd'] - valid_bars['macd_signal']
        np.testing.assert_array_almost_equal(
            valid_bars['macd_hist'].values,
            calculated_hist.values,
            decimal=5
        )


class TestRSI:
    """Test RSI calculation."""

    def test_rsi_calculation(self, sample_ohlcv_data):
        """Test that RSI is calculated correctly."""
        df = indicator_engine.calculate_rsi(sample_ohlcv_data.copy())

        # Check that column was added
        assert 'rsi' in df.columns

    def test_rsi_range(self, sample_ohlcv_data):
        """Test that RSI is within 0-100 range."""
        df = indicator_engine.calculate_rsi(sample_ohlcv_data.copy())

        valid_bars = df.dropna()
        assert (valid_bars['rsi'] >= 0).all()
        assert (valid_bars['rsi'] <= 100).all()


class TestATR:
    """Test ATR calculation."""

    def test_atr_calculation(self, sample_ohlcv_data):
        """Test that ATR is calculated correctly."""
        df = indicator_engine.calculate_atr(sample_ohlcv_data.copy())

        # Check that column was added
        assert 'atr' in df.columns

    def test_atr_positive(self, sample_ohlcv_data):
        """Test that ATR is always positive."""
        df = indicator_engine.calculate_atr(sample_ohlcv_data.copy())

        valid_bars = df.dropna()
        assert (valid_bars['atr'] > 0).all()


class TestCalculateAll:
    """Test batch calculation of all indicators."""

    def test_calculate_all_success(self, sample_ohlcv_data):
        """Test that all indicators are calculated in batch."""
        df = indicator_engine.calculate_all(sample_ohlcv_data.copy(), symbol='TEST')

        assert df is not None

        # Check that all expected columns exist
        expected_cols = [
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
            'macd', 'macd_signal', 'macd_hist',
            'rsi', 'atr'
        ]

        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_calculate_all_insufficient_data(self, insufficient_data):
        """Test that calculate_all returns None for insufficient data."""
        df = indicator_engine.calculate_all(insufficient_data.copy(), symbol='TEST')
        assert df is None

    def test_calculate_all_preserves_original_columns(self, sample_ohlcv_data):
        """Test that original columns are preserved."""
        original_cols = sample_ohlcv_data.columns.tolist()
        df = indicator_engine.calculate_all(sample_ohlcv_data.copy(), symbol='TEST')

        for col in original_cols:
            assert col in df.columns

    def test_calculate_all_handles_nan(self, data_with_nan):
        """Test that calculate_all handles NaN values gracefully."""
        # This should still work despite NaN values
        df = indicator_engine.calculate_all(data_with_nan.copy(), symbol='TEST')

        # Should return DataFrame (TA-Lib handles NaN)
        assert df is not None


class TestIndicatorList:
    """Test indicator list retrieval."""

    def test_get_indicator_list(self):
        """Test that get_indicator_list returns correct list."""
        indicator_list = indicator_engine.get_indicator_list()

        expected = [
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
            'macd', 'macd_signal', 'macd_hist',
            'rsi', 'atr'
        ]

        assert indicator_list == expected


class TestMinBarsRequired:
    """Test minimum bars requirement."""

    def test_min_bars_required_attribute(self):
        """Test that min_bars_required is set correctly."""
        assert indicator_engine.min_bars_required > 0
        assert isinstance(indicator_engine.min_bars_required, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/indicators', '--cov-report=term-missing'])
