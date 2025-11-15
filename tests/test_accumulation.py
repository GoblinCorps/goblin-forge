"""
Unit Tests for Accumulation Analysis (SABR20 Component 3)

Tests the novel Stoch/RSI signal frequency ratio for accumulation detection.

Test Coverage:
--------------
- Ratio calculation accuracy
- Phase classification logic
- Edge cases (zero signals, division by zero)
- Batch analysis
- Historical ratio series

Run:
----
pytest tests/test_accumulation.py -v --cov=src/indicators
"""

import pytest
import pandas as pd
import numpy as np

from src.indicators.accumulation_analysis import accumulation_analyzer
from src.indicators.indicator_engine import indicator_engine


@pytest.fixture
def sample_data_with_indicators():
    """
    Generate sample data with pre-calculated indicators.

    Creates realistic scenario with known accumulation pattern.
    """
    np.random.seed(42)

    dates = pd.date_range('2024-01-01', periods=200, freq='15min')

    # Generate price data
    close = 100 + np.random.randn(200).cumsum() * 0.5

    # OHLC
    high = close + np.abs(np.random.randn(200)) * 0.5
    low = close - np.abs(np.random.randn(200)) * 0.5
    open_price = close + (np.random.randn(200) * 0.2)
    volume = np.random.randint(100000, 1000000, 200)

    df = pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    # Calculate indicators
    df = indicator_engine.calculate_all(df, symbol='TEST')

    return df


@pytest.fixture
def early_accumulation_data():
    """
    Generate data exhibiting early accumulation pattern.

    High Stoch/RSI ratio (> 5.0) with RSI < 45.
    """
    np.random.seed(123)

    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    df = pd.DataFrame({'date': dates})

    # Create pattern: frequent Stoch oversold but RSI stays neutral
    # This simulates institutional buying on dips
    stoch_rsi = np.random.uniform(10, 25, 100)  # Frequently oversold
    rsi = np.random.uniform(35, 44, 100)  # Stays neutral (accumulation)

    df['stoch_rsi'] = stoch_rsi
    df['rsi'] = rsi

    return df


@pytest.fixture
def breakout_data():
    """
    Generate data exhibiting breakout pattern.

    Low Stoch/RSI ratio (< 1.5) with RSI > 50.
    """
    np.random.seed(456)

    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    df = pd.DataFrame({'date': dates})

    # Breakout: RSI strong, Stoch not oversold
    stoch_rsi = np.random.uniform(50, 80, 100)  # Not oversold
    rsi = np.random.uniform(55, 70, 100)  # Strong momentum

    df['stoch_rsi'] = stoch_rsi
    df['rsi'] = rsi

    return df


class TestRatioCalculation:
    """Test accumulation ratio calculation."""

    def test_calculate_ratio_series(self, sample_data_with_indicators):
        """Test that ratio series is calculated correctly."""
        df = accumulation_analyzer.calculate_ratio_series(
            sample_data_with_indicators.copy(),
            window=50
        )

        # Check that columns were added
        assert 'accumulation_ratio' in df.columns
        assert 'stoch_signals' in df.columns
        assert 'rsi_signals' in df.columns

    def test_ratio_non_negative(self, sample_data_with_indicators):
        """Test that ratio is always non-negative."""
        df = accumulation_analyzer.calculate_ratio_series(
            sample_data_with_indicators.copy()
        )

        valid_bars = df.dropna()
        assert (valid_bars['accumulation_ratio'] >= 0).all()

    def test_ratio_capped(self, sample_data_with_indicators):
        """Test that ratio is capped to prevent extreme values."""
        df = accumulation_analyzer.calculate_ratio_series(
            sample_data_with_indicators.copy()
        )

        # Ratio should be capped at 20 (see implementation)
        valid_bars = df.dropna()
        assert (valid_bars['accumulation_ratio'] <= 20).all()

    def test_zero_signals_handling(self):
        """Test handling of zero signals (edge case)."""
        # Create data with no oversold signals
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'stoch_rsi': [50] * 100,  # Never oversold
            'rsi': [50] * 100  # Never oversold
        })

        df_with_ratio = accumulation_analyzer.calculate_ratio_series(df, window=50)

        # When both are zero, ratio should be 0
        assert df_with_ratio['accumulation_ratio'].iloc[-1] == 0

    def test_custom_window(self, sample_data_with_indicators):
        """Test custom window parameter."""
        df_30 = accumulation_analyzer.calculate_ratio_series(
            sample_data_with_indicators.copy(),
            window=30
        )

        df_70 = accumulation_analyzer.calculate_ratio_series(
            sample_data_with_indicators.copy(),
            window=70
        )

        # Different windows should produce different results
        assert not df_30['accumulation_ratio'].equals(df_70['accumulation_ratio'])


class TestPhaseClassification:
    """Test accumulation phase classification logic."""

    def test_early_accumulation_classification(self):
        """Test that early accumulation is classified correctly."""
        # High ratio (> 5.0), low RSI (< 45)
        result = accumulation_analyzer.classify_phase(ratio=6.0, rsi=42)

        assert result['phase'] == 'early'
        assert result['points'] == 18  # Maximum points

    def test_mid_accumulation_classification(self):
        """Test that mid accumulation is classified correctly."""
        # Medium ratio (3.0-5.0), RSI < 50
        result = accumulation_analyzer.classify_phase(ratio=4.0, rsi=48)

        assert result['phase'] == 'mid'
        assert result['points'] == 14

    def test_late_accumulation_classification(self):
        """Test that late accumulation is classified correctly."""
        # Lower ratio (1.5-3.0), RSI 40-55
        result = accumulation_analyzer.classify_phase(ratio=2.0, rsi=52)

        assert result['phase'] == 'late'
        assert result['points'] == 10

    def test_breakout_classification(self):
        """Test that breakout is classified correctly."""
        # Low ratio (0.8-1.5), high RSI (> 50)
        result = accumulation_analyzer.classify_phase(ratio=1.0, rsi=60)

        assert result['phase'] == 'breakout'
        assert result['points'] == 6

    def test_none_classification(self):
        """Test that no accumulation is classified correctly."""
        # Doesn't match any phase criteria
        result = accumulation_analyzer.classify_phase(ratio=0.5, rsi=40)

        assert result['phase'] == 'none'
        assert result['points'] == 0


class TestAnalyze:
    """Test full accumulation analysis."""

    def test_analyze_success(self, sample_data_with_indicators):
        """Test that analyze returns complete result."""
        result = accumulation_analyzer.analyze(
            sample_data_with_indicators,
            symbol='TEST'
        )

        # Check that all required keys exist
        required_keys = [
            'phase', 'ratio', 'points', 'description',
            'stoch_signals', 'rsi_signals', 'rsi', 'history'
        ]

        for key in required_keys:
            assert key in result

    def test_analyze_early_accumulation(self, early_accumulation_data):
        """Test analyze detects early accumulation."""
        result = accumulation_analyzer.analyze(
            early_accumulation_data,
            symbol='TEST'
        )

        # Should detect early or mid accumulation (high ratio, low RSI)
        assert result['phase'] in ['early', 'mid']
        assert result['points'] >= 14

    def test_analyze_breakout(self, breakout_data):
        """Test analyze detects breakout."""
        result = accumulation_analyzer.analyze(
            breakout_data,
            symbol='TEST'
        )

        # Should detect breakout or none (low ratio, high RSI)
        assert result['phase'] in ['breakout', 'none', 'late']

    def test_analyze_empty_data(self):
        """Test analyze handles empty DataFrame."""
        result = accumulation_analyzer.analyze(
            pd.DataFrame(),
            symbol='TEST'
        )

        assert result['phase'] == 'none'
        assert result['points'] == 0

    def test_analyze_missing_indicators(self):
        """Test analyze handles missing indicators."""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'close': [100] * 100
            # Missing stoch_rsi and rsi
        })

        result = accumulation_analyzer.analyze(df, symbol='TEST')

        assert result['phase'] == 'none'
        assert result['points'] == 0

    def test_analyze_history_length(self, sample_data_with_indicators):
        """Test that history contains last 10 values."""
        result = accumulation_analyzer.analyze(
            sample_data_with_indicators,
            symbol='TEST'
        )

        assert len(result['history']) == 10


class TestBatchAnalyze:
    """Test batch analysis of multiple symbols."""

    def test_batch_analyze(self, sample_data_with_indicators):
        """Test batch analysis of multiple symbols."""
        data_dict = {
            'AAPL': sample_data_with_indicators.copy(),
            'MSFT': sample_data_with_indicators.copy(),
            'GOOGL': sample_data_with_indicators.copy()
        }

        results = accumulation_analyzer.batch_analyze(data_dict)

        # Check all symbols analyzed
        assert len(results) == 3
        assert 'AAPL' in results
        assert 'MSFT' in results
        assert 'GOOGL' in results

        # Check result structure
        for symbol, result in results.items():
            assert 'phase' in result
            assert 'points' in result

    def test_batch_analyze_handles_errors(self):
        """Test that batch analyze handles individual errors."""
        data_dict = {
            'GOOD': pd.DataFrame({
                'stoch_rsi': [20] * 100,
                'rsi': [40] * 100
            }),
            'BAD': pd.DataFrame()  # Empty - will error
        }

        results = accumulation_analyzer.batch_analyze(data_dict)

        # Should have results for both (BAD gets default)
        assert len(results) == 2
        assert results['BAD']['phase'] == 'none'


class TestPhaseSummary:
    """Test phase summary retrieval."""

    def test_get_phase_summary(self):
        """Test that phase summary is returned correctly."""
        summary = accumulation_analyzer.get_phase_summary()

        # Should have all phases
        assert 'early' in summary
        assert 'mid' in summary
        assert 'late' in summary
        assert 'breakout' in summary

        # Each phase should have required fields
        for phase, info in summary.items():
            assert 'points' in info
            assert 'description' in info


class TestConfiguration:
    """Test that analyzer uses configuration correctly."""

    def test_window_from_config(self):
        """Test that window comes from configuration."""
        assert accumulation_analyzer.window > 0
        assert isinstance(accumulation_analyzer.window, int)

    def test_thresholds_from_config(self):
        """Test that thresholds come from configuration."""
        assert accumulation_analyzer.stoch_oversold > 0
        assert accumulation_analyzer.rsi_oversold > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/indicators', '--cov-report=term-missing'])
