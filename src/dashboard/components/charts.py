"""
Multi-timeframe chart components for dashboard.

Provides Plotly-based candlestick charts with technical indicators
across 15-minute, 1-hour, and 4-hour timeframes.

Features:
---------
- 4-panel layout (Price, Stochastic RSI, MACD, Volume)
- Candlestick charts with Bollinger Bands and EMAs
- Interactive zoom/pan with Plotly
- Responsive design with timeframe tabs
- Real-time data integration
- Error handling for missing data

Components:
-----------
1. Price Panel: Candlesticks + BB + EMAs (8, 21, 50)
2. Stochastic RSI Panel: Oscillator with 80/20 levels
3. MACD Panel: MACD line, signal, histogram
4. Volume Panel: Color-coded volume bars

Usage:
------
from src.dashboard.components.charts import create_multitimeframe_chart

fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

Author: Screener Trading System
Date: 2025-11-15
"""

from typing import Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from loguru import logger

from src.data.historical_manager import historical_manager
from src.indicators.indicator_engine import indicator_engine


def create_multitimeframe_chart(
    symbol: str,
    timeframe: str = '1 hour',
    bars: int = 100
) -> go.Figure:
    """
    Create multi-panel chart for a symbol at specified timeframe.

    This is the primary chart generation function. It loads historical data,
    calculates indicators, and creates a 4-panel Plotly figure with:
    1. Price + Bollinger Bands + EMAs
    2. Stochastic RSI
    3. MACD
    4. Volume

    Parameters:
    -----------
    symbol : str
        Stock symbol to chart (e.g., 'AAPL', 'GOOGL')
    timeframe : str, default='1 hour'
        Timeframe identifier matching historical_manager format:
        - '15 mins' for 15-minute bars
        - '1 hour' for 1-hour bars
        - '4 hours' for 4-hour bars
    bars : int, default=100
        Number of bars to display (takes last N bars)

    Returns:
    --------
    go.Figure
        Plotly figure with 4 panels and interactive features:
        - Height: 800px
        - Template: plotly_dark
        - Hover mode: x unified
        - Range slider: disabled

    Examples:
    ---------
    >>> # Create 1-hour chart for AAPL with 100 bars
    >>> fig = create_multitimeframe_chart('AAPL', '1 hour', 100)
    >>> fig.show()

    >>> # Create 15-minute chart for GOOGL with 200 bars
    >>> fig = create_multitimeframe_chart('GOOGL', '15 mins', 200)
    >>> fig.write_html('googl_15m.html')

    Notes:
    ------
    - Returns empty chart with error message if data unavailable
    - Automatically calculates all required indicators
    - Handles missing indicator columns gracefully
    - Color scheme optimized for dark theme
    """
    try:
        # Map common timeframe formats
        timeframe_map = {
            '15m': '15 mins',
            '15min': '15 mins',
            '1h': '1 hour',
            '1hr': '1 hour',
            '4h': '4 hours',
            '4hr': '4 hours',
        }
        timeframe = timeframe_map.get(timeframe, timeframe)

        # Load data from historical manager
        logger.info(f"Loading {timeframe} data for {symbol}")
        df = historical_manager.load_symbol_data(symbol, timeframe)

        if df is None or len(df) == 0:
            logger.warning(f"No data available for {symbol} {timeframe}")
            return _create_empty_chart(symbol, timeframe, "No data available")

        # Take last N bars
        df = df.tail(bars).copy()
        logger.debug(f"Chart data: {len(df)} bars for {symbol} {timeframe}")

        # Calculate indicators
        logger.debug(f"Calculating indicators for {symbol}")
        df = indicator_engine.calculate_all(df, symbol=symbol)

        if df is None or len(df) == 0:
            logger.error(f"Indicator calculation failed for {symbol}")
            return _create_empty_chart(
                symbol, timeframe,
                "Indicator calculation failed - insufficient data"
            )

    except Exception as e:
        logger.error(f"Failed to load data for {symbol} {timeframe}: {e}")
        return _create_empty_chart(symbol, timeframe, f"Error: {str(e)}")

    # Create subplot figure (4 rows)
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(
            f'{symbol} - {timeframe}',
            'Stochastic RSI',
            'MACD',
            'Volume'
        ),
        row_heights=[0.5, 0.15, 0.15, 0.20]
    )

    # === Panel 1: Candlestick + Bollinger Bands + EMAs ===
    _add_price_panel(fig, df, symbol, timeframe)

    # === Panel 2: Stochastic RSI ===
    _add_stochastic_rsi_panel(fig, df)

    # === Panel 3: MACD ===
    _add_macd_panel(fig, df)

    # === Panel 4: Volume ===
    _add_volume_panel(fig, df)

    # Update layout
    fig.update_layout(
        height=800,
        template='plotly_dark',
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # Update axes
    fig.update_xaxes(title_text="Time", row=4, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Stoch RSI", range=[0, 100], row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)

    logger.info(f"Successfully created chart for {symbol} {timeframe}")
    return fig


def _add_price_panel(
    fig: go.Figure,
    df: pd.DataFrame,
    symbol: str,
    timeframe: str
) -> None:
    """
    Add price panel with candlesticks, Bollinger Bands, and EMAs.

    Parameters:
    -----------
    fig : go.Figure
        Figure to add traces to
    df : pd.DataFrame
        OHLCV data with indicators
    symbol : str
        Symbol name
    timeframe : str
        Timeframe identifier
    """
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#00cc00',  # Green
            decreasing_line_color='#ff3333',  # Red
            increasing_fillcolor='#00cc00',
            decreasing_fillcolor='#ff3333'
        ),
        row=1, col=1
    )

    # Bollinger Bands
    if all(col in df.columns for col in ['bb_upper', 'bb_lower']):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_upper'],
                name='BB Upper',
                line=dict(color='#888888', width=1, dash='dash'),
                showlegend=True,
                hovertemplate='BB Upper: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_lower'],
                name='BB Lower',
                line=dict(color='#888888', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)',
                showlegend=True,
                hovertemplate='BB Lower: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )

    # EMAs (8, 21, 50) - calculate if not present
    ema_configs = [
        ('ema_8', 8, '#3366ff', 'EMA 8'),
        ('ema_21', 21, '#ff9900', 'EMA 21'),
        ('ema_50', 50, '#cc00cc', 'EMA 50')
    ]

    for ema_col, period, color, name in ema_configs:
        if ema_col not in df.columns:
            # Calculate EMA if not present
            import talib
            df[ema_col] = talib.EMA(df['close'].values, timeperiod=period)

        if ema_col in df.columns and not df[ema_col].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[ema_col],
                    name=name,
                    line=dict(color=color, width=1.5),
                    showlegend=True,
                    hovertemplate=f'{name}: %{{y:.2f}}<extra></extra>'
                ),
                row=1, col=1
            )


def _add_stochastic_rsi_panel(fig: go.Figure, df: pd.DataFrame) -> None:
    """
    Add Stochastic RSI panel with 80/20 levels.

    Parameters:
    -----------
    fig : go.Figure
        Figure to add traces to
    df : pd.DataFrame
        Data with stoch_rsi indicators
    """
    if 'stoch_rsi_k' in df.columns:
        # %K line (fast)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['stoch_rsi_k'],
                name='Stoch RSI %K',
                line=dict(color='#9966ff', width=2),
                showlegend=True,
                hovertemplate='%K: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

    if 'stoch_rsi_d' in df.columns:
        # %D line (slow/signal)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['stoch_rsi_d'],
                name='Stoch RSI %D',
                line=dict(color='#ff9900', width=1.5),
                showlegend=True,
                hovertemplate='%D: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

    # Overbought/Oversold horizontal lines
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="#ff3333",
        line_width=1,
        row=2, col=1,
        annotation_text="Overbought (80)",
        annotation_position="right"
    )
    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color="#00cc00",
        line_width=1,
        row=2, col=1,
        annotation_text="Oversold (20)",
        annotation_position="right"
    )


def _add_macd_panel(fig: go.Figure, df: pd.DataFrame) -> None:
    """
    Add MACD panel with MACD line, signal line, and histogram.

    Parameters:
    -----------
    fig : go.Figure
        Figure to add traces to
    df : pd.DataFrame
        Data with MACD indicators
    """
    if 'macd' in df.columns:
        # MACD line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['macd'],
                name='MACD',
                line=dict(color='#3366ff', width=2),
                showlegend=True,
                hovertemplate='MACD: %{y:.3f}<extra></extra>'
            ),
            row=3, col=1
        )

    if 'macd_signal' in df.columns:
        # Signal line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['macd_signal'],
                name='Signal',
                line=dict(color='#ff9900', width=1.5),
                showlegend=True,
                hovertemplate='Signal: %{y:.3f}<extra></extra>'
            ),
            row=3, col=1
        )

    if 'macd_hist' in df.columns:
        # Histogram (color-coded: green if positive, red if negative)
        colors = ['#00cc00' if val >= 0 else '#ff3333' for val in df['macd_hist']]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['macd_hist'],
                name='Histogram',
                marker_color=colors,
                showlegend=True,
                hovertemplate='Histogram: %{y:.3f}<extra></extra>'
            ),
            row=3, col=1
        )

    # Zero line
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="#666666",
        line_width=1,
        row=3, col=1
    )


def _add_volume_panel(fig: go.Figure, df: pd.DataFrame) -> None:
    """
    Add volume panel with color-coded bars.

    Parameters:
    -----------
    fig : go.Figure
        Figure to add traces to
    df : pd.DataFrame
        Data with volume column
    """
    if 'volume' not in df.columns:
        logger.warning("Volume column not found in data")
        return

    # Color-code volume: green if close > open (bullish), red otherwise
    colors = [
        '#00cc00' if close >= open_ else '#ff3333'
        for close, open_ in zip(df['close'], df['open'])
    ]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=True,
            hovertemplate='Volume: %{y:,.0f}<extra></extra>'
        ),
        row=4, col=1
    )


def _create_empty_chart(
    symbol: str,
    timeframe: str,
    message: str
) -> go.Figure:
    """
    Create empty chart with error message.

    Used when data is unavailable or an error occurs.

    Parameters:
    -----------
    symbol : str
        Symbol name
    timeframe : str
        Timeframe identifier
    message : str
        Error/info message to display

    Returns:
    --------
    go.Figure
        Empty figure with centered message
    """
    fig = go.Figure()
    fig.add_annotation(
        text=f"<b>{symbol} - {timeframe}</b><br>{message}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=18, color='#888888'),
        align='center'
    )
    fig.update_layout(
        height=800,
        template='plotly_dark',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False)
    )
    logger.warning(f"Created empty chart for {symbol} {timeframe}: {message}")
    return fig


def get_available_timeframes() -> list:
    """
    Get list of available timeframes.

    Returns:
    --------
    list of str
        Available timeframe identifiers
    """
    return ['15 mins', '1 hour', '4 hours']


def validate_symbol_data(symbol: str, timeframe: str) -> bool:
    """
    Validate that data exists for symbol and timeframe.

    Parameters:
    -----------
    symbol : str
        Stock symbol
    timeframe : str
        Timeframe identifier

    Returns:
    --------
    bool
        True if data exists and is valid, False otherwise
    """
    try:
        df = historical_manager.load_symbol_data(symbol, timeframe)
        return df is not None and len(df) > 0
    except Exception as e:
        logger.error(f"Error validating data for {symbol} {timeframe}: {e}")
        return False
