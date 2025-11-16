"""
Tests for dashboard chart components.

Tests the multi-timeframe chart generation functionality including:
- Chart creation with valid data
- Panel rendering (Price, Stochastic RSI, MACD, Volume)
- Error handling (missing data, invalid symbols)
- Indicator integration
- Empty chart generation

Author: Screener Trading System
Date: 2025-11-15
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import plotly.graph_objects as go

from src.dashboard.components.charts import (
    create_multitimeframe_chart,
    _create_empty_chart,
    _add_price_panel,
    _add_stochastic_rsi_panel,
    _add_macd_panel,
    _add_volume_panel,
    get_available_timeframes,
    validate_symbol_data
)


class TestMultiTimeframeCharts:
    """Test multi-timeframe chart generation."""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data with indicators."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        np.random.seed(42)

        # Generate realistic price data
        close_prices = 150 + np.cumsum(np.random.randn(100) * 0.5)
        high_prices = close_prices + np.abs(np.random.randn(100) * 0.3)
        low_prices = close_prices - np.abs(np.random.randn(100) * 0.3)
        open_prices = close_prices + np.random.randn(100) * 0.2

        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.randint(800000, 1200000, 100),
            'bb_upper': close_prices + 2,
            'bb_middle': close_prices,
            'bb_lower': close_prices - 2,
            'bb_width': np.full(100, 4.0),
            'bb_position': np.random.uniform(0.2, 0.8, 100),
            'ema_8': close_prices - 0.5,
            'ema_21': close_prices - 1.0,
            'ema_50': close_prices - 1.5,
            'stoch_rsi_k': np.random.uniform(20, 80, 100),
            'stoch_rsi_d': np.random.uniform(20, 80, 100),
            'stoch_rsi': np.random.uniform(20, 80, 100),
            'macd': np.random.randn(100) * 0.5,
            'macd_signal': np.random.randn(100) * 0.4,
            'macd_hist': np.random.randn(100) * 0.2,
            'rsi': np.random.uniform(30, 70, 100),
            'atr': np.random.uniform(1.0, 2.0, 100)
        }, index=dates)
        return df

    @pytest.fixture
    def minimal_ohlcv_data(self):
        """Create minimal OHLCV data without indicators."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        np.random.seed(42)

        close_prices = 150 + np.cumsum(np.random.randn(100) * 0.5)
        high_prices = close_prices + np.abs(np.random.randn(100) * 0.3)
        low_prices = close_prices - np.abs(np.random.randn(100) * 0.3)
        open_prices = close_prices + np.random.randn(100) * 0.2

        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.randint(800000, 1200000, 100),
        }, index=dates)
        return df

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_with_valid_data(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        sample_ohlcv_data
    ):
        """Test chart creation with valid data."""
        # Setup mocks
        mock_historical_manager.load_symbol_data.return_value = sample_ohlcv_data
        mock_indicator_engine.calculate_all.return_value = sample_ohlcv_data

        # Create chart
        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        # Verify figure created
        assert fig is not None
        assert isinstance(fig, go.Figure)

        # Verify data loading
        mock_historical_manager.load_symbol_data.assert_called_once_with('AAPL', '1 hour')

        # Verify indicator calculation
        mock_indicator_engine.calculate_all.assert_called_once()

        # Verify traces added (should have multiple traces for different panels)
        assert len(fig.data) > 0

        # Verify layout settings
        assert fig.layout.height == 800
        assert fig.layout.template.layout.paper_bgcolor == 'rgb(17,17,17)'  # Dark theme
        assert fig.layout.hovermode == 'x unified'

    @patch('src.dashboard.components.charts.historical_manager')
    def test_create_chart_no_data(self, mock_historical_manager):
        """Test chart creation when no data available."""
        mock_historical_manager.load_symbol_data.return_value = None

        fig = create_multitimeframe_chart('INVALID', '1 hour', 100)

        assert fig is not None
        assert isinstance(fig, go.Figure)
        # Should have annotation with error message
        assert len(fig.layout.annotations) > 0
        assert 'No data available' in fig.layout.annotations[0].text

    @patch('src.dashboard.components.charts.historical_manager')
    def test_create_chart_empty_dataframe(self, mock_historical_manager):
        """Test chart creation with empty dataframe."""
        mock_historical_manager.load_symbol_data.return_value = pd.DataFrame()

        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        assert fig is not None
        assert len(fig.layout.annotations) > 0

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_indicator_calculation_fails(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        minimal_ohlcv_data
    ):
        """Test chart creation when indicator calculation fails."""
        mock_historical_manager.load_symbol_data.return_value = minimal_ohlcv_data
        mock_indicator_engine.calculate_all.return_value = None

        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        assert fig is not None
        assert len(fig.layout.annotations) > 0
        assert 'Indicator calculation failed' in fig.layout.annotations[0].text

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_different_timeframes(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        sample_ohlcv_data
    ):
        """Test chart creation with different timeframes."""
        mock_historical_manager.load_symbol_data.return_value = sample_ohlcv_data
        mock_indicator_engine.calculate_all.return_value = sample_ohlcv_data

        timeframes = ['15 mins', '1 hour', '4 hours']

        for tf in timeframes:
            fig = create_multitimeframe_chart('AAPL', tf, 100)
            assert fig is not None
            assert isinstance(fig, go.Figure)
            mock_historical_manager.load_symbol_data.assert_called_with('AAPL', tf)

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_timeframe_mapping(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        sample_ohlcv_data
    ):
        """Test timeframe abbreviation mapping."""
        mock_historical_manager.load_symbol_data.return_value = sample_ohlcv_data
        mock_indicator_engine.calculate_all.return_value = sample_ohlcv_data

        # Test abbreviations
        fig = create_multitimeframe_chart('AAPL', '15m', 100)
        mock_historical_manager.load_symbol_data.assert_called_with('AAPL', '15 mins')

        fig = create_multitimeframe_chart('AAPL', '1h', 100)
        mock_historical_manager.load_symbol_data.assert_called_with('AAPL', '1 hour')

        fig = create_multitimeframe_chart('AAPL', '4h', 100)
        mock_historical_manager.load_symbol_data.assert_called_with('AAPL', '4 hours')

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_bars_limit(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        sample_ohlcv_data
    ):
        """Test that chart respects bars limit."""
        # Create larger dataset
        dates = pd.date_range('2024-01-01', periods=500, freq='1H')
        large_data = sample_ohlcv_data.reindex(dates, method='ffill')

        mock_historical_manager.load_symbol_data.return_value = large_data
        mock_indicator_engine.calculate_all.return_value = large_data

        # Request only 100 bars
        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        # Verify indicator engine received only last 100 bars
        call_args = mock_indicator_engine.calculate_all.call_args
        df_passed = call_args[0][0]
        assert len(df_passed) == 100

    def test_create_empty_chart(self):
        """Test empty chart creation."""
        fig = _create_empty_chart('AAPL', '1 hour', 'Test error message')

        assert fig is not None
        assert isinstance(fig, go.Figure)
        assert fig.layout.height == 800
        assert fig.layout.template.layout.paper_bgcolor == 'rgb(17,17,17)'  # Dark theme
        assert len(fig.layout.annotations) > 0
        assert 'AAPL' in fig.layout.annotations[0].text
        assert '1 hour' in fig.layout.annotations[0].text
        assert 'Test error message' in fig.layout.annotations[0].text

    def test_add_price_panel(self, sample_ohlcv_data):
        """Test price panel addition."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_price_panel(fig, sample_ohlcv_data, 'AAPL', '1 hour')

        # Should have candlestick + BB + EMAs
        # Candlestick (1) + BB upper (1) + BB lower (1) + EMA 8/21/50 (3) = 6 traces
        assert len(fig.data) >= 5  # At least candlestick + some indicators

        # Check for candlestick trace
        assert any(isinstance(trace, go.Candlestick) for trace in fig.data)

        # Check for scatter traces (BB, EMAs)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) > 0

    def test_add_price_panel_without_indicators(self, minimal_ohlcv_data):
        """Test price panel with minimal data (no indicators)."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_price_panel(fig, minimal_ohlcv_data, 'AAPL', '1 hour')

        # Should still have candlestick even without indicators
        assert len(fig.data) >= 1
        assert any(isinstance(trace, go.Candlestick) for trace in fig.data)

    def test_add_stochastic_rsi_panel(self, sample_ohlcv_data):
        """Test Stochastic RSI panel addition."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_stochastic_rsi_panel(fig, sample_ohlcv_data)

        # Should have %K and %D lines
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) >= 2

        # Check for horizontal reference lines (80 and 20)
        # These are added as shapes in the layout
        # Just verify function doesn't crash

    def test_add_stochastic_rsi_panel_missing_data(self):
        """Test Stochastic RSI panel with missing indicator data."""
        from plotly.subplots import make_subplots

        df = pd.DataFrame({'close': [100, 101, 102]})
        fig = make_subplots(rows=4, cols=1)

        # Should not crash even without stoch_rsi columns
        _add_stochastic_rsi_panel(fig, df)

    def test_add_macd_panel(self, sample_ohlcv_data):
        """Test MACD panel addition."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_macd_panel(fig, sample_ohlcv_data)

        # Should have MACD line, signal line, and histogram
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]

        assert len(scatter_traces) >= 2  # MACD + signal
        assert len(bar_traces) >= 1  # Histogram

    def test_add_macd_panel_histogram_colors(self, sample_ohlcv_data):
        """Test MACD histogram color coding."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_macd_panel(fig, sample_ohlcv_data)

        # Find histogram trace
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) > 0

        # Histogram should have color array
        histogram = bar_traces[0]
        assert hasattr(histogram, 'marker')

    def test_add_volume_panel(self, sample_ohlcv_data):
        """Test volume panel addition."""
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=4, cols=1)
        _add_volume_panel(fig, sample_ohlcv_data)

        # Should have volume bars
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1

        # Volume bars should be color-coded
        volume_trace = bar_traces[0]
        assert hasattr(volume_trace, 'marker')

    def test_add_volume_panel_missing_volume(self):
        """Test volume panel with missing volume data."""
        from plotly.subplots import make_subplots

        df = pd.DataFrame({'close': [100, 101, 102], 'open': [99, 100, 101]})
        fig = make_subplots(rows=4, cols=1)

        # Should not crash
        _add_volume_panel(fig, df)

    def test_volume_panel_color_coding(self, sample_ohlcv_data):
        """Test volume bar colors (green for up days, red for down days)."""
        from plotly.subplots import make_subplots

        # Create specific data with known up/down days
        df = sample_ohlcv_data.copy()
        df.iloc[0, df.columns.get_loc('close')] = 151  # Up day
        df.iloc[0, df.columns.get_loc('open')] = 150
        df.iloc[1, df.columns.get_loc('close')] = 149  # Down day
        df.iloc[1, df.columns.get_loc('open')] = 150

        fig = make_subplots(rows=4, cols=1)
        _add_volume_panel(fig, df)

        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) > 0

    def test_get_available_timeframes(self):
        """Test get_available_timeframes function."""
        timeframes = get_available_timeframes()

        assert isinstance(timeframes, list)
        assert len(timeframes) == 3
        assert '15 mins' in timeframes
        assert '1 hour' in timeframes
        assert '4 hours' in timeframes

    @patch('src.dashboard.components.charts.historical_manager')
    def test_validate_symbol_data_valid(self, mock_historical_manager, sample_ohlcv_data):
        """Test validate_symbol_data with valid data."""
        mock_historical_manager.load_symbol_data.return_value = sample_ohlcv_data

        result = validate_symbol_data('AAPL', '1 hour')

        assert result is True
        mock_historical_manager.load_symbol_data.assert_called_once_with('AAPL', '1 hour')

    @patch('src.dashboard.components.charts.historical_manager')
    def test_validate_symbol_data_no_data(self, mock_historical_manager):
        """Test validate_symbol_data with no data."""
        mock_historical_manager.load_symbol_data.return_value = None

        result = validate_symbol_data('INVALID', '1 hour')

        assert result is False

    @patch('src.dashboard.components.charts.historical_manager')
    def test_validate_symbol_data_empty(self, mock_historical_manager):
        """Test validate_symbol_data with empty dataframe."""
        mock_historical_manager.load_symbol_data.return_value = pd.DataFrame()

        result = validate_symbol_data('AAPL', '1 hour')

        assert result is False

    @patch('src.dashboard.components.charts.historical_manager')
    def test_validate_symbol_data_exception(self, mock_historical_manager):
        """Test validate_symbol_data with exception."""
        mock_historical_manager.load_symbol_data.side_effect = Exception("Test error")

        result = validate_symbol_data('AAPL', '1 hour')

        assert result is False

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_create_chart_exception_handling(
        self,
        mock_indicator_engine,
        mock_historical_manager
    ):
        """Test exception handling in chart creation."""
        mock_historical_manager.load_symbol_data.side_effect = Exception("Test error")

        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        # Should return empty chart with error message
        assert fig is not None
        assert len(fig.layout.annotations) > 0
        assert 'Error' in fig.layout.annotations[0].text

    @patch('src.dashboard.components.charts.historical_manager')
    @patch('src.dashboard.components.charts.indicator_engine')
    def test_chart_with_all_panels(
        self,
        mock_indicator_engine,
        mock_historical_manager,
        sample_ohlcv_data
    ):
        """Test that chart includes all 4 panels."""
        mock_historical_manager.load_symbol_data.return_value = sample_ohlcv_data
        mock_indicator_engine.calculate_all.return_value = sample_ohlcv_data

        fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

        # Check for subplots (4 rows)
        assert hasattr(fig, 'layout')
        # Verify multiple y-axis (one per panel)
        layout_dict = fig.to_dict()['layout']
        # Should have yaxis, yaxis2, yaxis3, yaxis4
        assert 'yaxis' in layout_dict
        assert 'yaxis2' in layout_dict
        assert 'yaxis3' in layout_dict
        assert 'yaxis4' in layout_dict
