"""
Real-Time Screening Dashboard

Dash-based web application for monitoring screening results and market regime.

Features:
---------
- Real-time watchlist table with SABR20 scores
- Market regime indicator
- Component score breakdown
- Multi-timeframe charts
- Auto-refresh every 5 minutes
- Entry/target/stop visualization

Pages:
------
1. Watchlist: Top setups ranked by SABR20 score
2. Setup Details: Individual symbol analysis
3. Market Regime: Current market conditions

Run:
----
python src/dashboard/app.py

Then navigate to http://localhost:8050
"""

import os
from datetime import datetime
from typing import List, Dict, Any

import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from loguru import logger

from src.config import config
from src.screening.watchlist import watchlist_generator
from src.regime.regime_detector import regime_detector, RegimeType
from src.data.historical_manager import historical_manager
from src.dashboard.components.charts import create_multitimeframe_chart
from src.dashboard.components.positions import create_positions_panel, update_positions_callback
from src.dashboard.components.branding import (
    create_kymera_header,
    create_metric_card,
    create_section_header,
    create_badge
)
from src.execution.order_manager import order_manager


# Initialize Dash app with Kymera theme
# Note: Kymera theme CSS automatically loaded from assets/ folder
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],  # Dark base theme for Bootstrap components
    suppress_callback_exceptions=True,
    assets_folder='assets'  # Loads kymera_theme.css automatically
)

app.title = "Desktop Kymera - Trading Dashboard"

# Global state
watchlist_cache = {
    'data': [],
    'timestamp': None
}


def create_header():
    """
    Create branded Desktop Kymera header.

    Returns:
    --------
    dbc.Navbar
        Kymera-themed navbar with logo, status, and live clock

    Features:
    ---------
    - Glass-morphism background with blur
    - Desktop Kymera branding with gradient
    - System online status indicator (pulsing green dot)
    - Live clock updated every second
    - Sticky positioning (stays visible on scroll)
    """
    return create_kymera_header(
        show_clock=True,
        show_status=True,
        system_status="online"
    )


def create_regime_card(regime_data: Dict[str, Any]) -> dbc.Card:
    """
    Create market regime indicator card with Kymera styling.

    Parameters:
    -----------
    regime_data : Dict[str, Any]
        Regime detection results from regime_detector

    Returns:
    --------
    dbc.Card
        Styled card showing market regime, confidence, and recommendations

    Visual Design:
    --------------
    - Glass-morphism card background
    - Color-coded regime badge
    - Confidence percentage with monospace font
    - Strategy recommendations
    """
    regime_type = regime_data.get('type_str', 'unknown')
    confidence = regime_data.get('confidence', 0)
    recommendation = regime_data.get('recommendation', {})

    # Badge variant based on regime
    regime_badges = {
        'ranging': 'success',
        'trending_bullish': 'info',
        'trending_bearish': 'warning',
        'volatile': 'danger',
        'unknown': 'primary'
    }
    badge_variant = regime_badges.get(regime_type, 'primary')

    return dbc.Card([
        dbc.CardHeader(html.H5("Market Regime", className="mb-0")),
        dbc.CardBody([
            # Regime type with badge
            html.Div([
                create_badge(
                    regime_type.replace('_', ' ').title(),
                    badge_variant
                )
            ], className="mb-3"),

            # Confidence metric
            html.Div([
                html.Div("CONFIDENCE", className="kymera-metric-label"),
                html.Div(f"{confidence:.0%}", className="kymera-metric-value",
                        style={'fontSize': 'var(--kymera-font-size-2xl)'})
            ], className="mb-3"),

            html.Hr(style={'borderTop': '1px solid var(--kymera-border-subtle)'}),

            # Recommendations
            html.P([
                html.Strong("Strategy Fit: ", className="text-muted"),
                html.Span(recommendation.get('strategy_suitability', 'unknown').title())
            ], className="mb-2"),
            html.P([
                html.Strong("Position Sizing: ", className="text-muted"),
                html.Span(recommendation.get('position_sizing', 'unknown').title())
            ], className="mb-2"),
            html.P(
                recommendation.get('notes', ''),
                className="text-muted small"
            )
        ])
    ], className="mb-4 kymera-card")


def create_watchlist_table(watchlist: List) -> dash_table.DataTable:
    """Create watchlist data table."""
    if not watchlist:
        return html.Div("No setups found", className="text-muted")

    # Convert to DataFrame
    df = watchlist_generator.get_watchlist_summary(watchlist)

    # Format for display
    df['score'] = df['score'].round(1)
    if 'entry' in df.columns:
        df['entry'] = df['entry'].round(2)
    if 'target' in df.columns:
        df['target'] = df['target'].round(2)
    if 'stop' in df.columns:
        df['stop'] = df['stop'].round(2)
    if 'rr_ratio' in df.columns:
        df['rr_ratio'] = df['rr_ratio'].round(2)

    columns = [
        {'name': 'Symbol', 'id': 'symbol'},
        {'name': 'Score', 'id': 'score'},
        {'name': 'Grade', 'id': 'grade'},
        {'name': 'Setup', 'id': 'setup_strength'},
        {'name': 'Bottom', 'id': 'bottom_phase'},
        {'name': 'Accum', 'id': 'accumulation'},
        {'name': 'Momentum', 'id': 'trend_momentum'},
        {'name': 'R:R', 'id': 'risk_reward'},
        {'name': 'Macro', 'id': 'macro'},
        {'name': 'Entry', 'id': 'entry'},
        {'name': 'Target', 'id': 'target'},
        {'name': 'Stop', 'id': 'stop'},
        {'name': 'R:R Ratio', 'id': 'rr_ratio'},
    ]

    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=columns,
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': '#343a40',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{grade} = "Excellent"'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'filter_query': '{grade} = "Strong"'},
                'backgroundColor': '#d1ecf1',
                'color': '#0c5460'
            },
            {
                'if': {'filter_query': '{grade} = "Good"'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            }
        ],
        sort_action='native',
        filter_action='native',
        page_size=20
    )


# Layout with Kymera theme
app.layout = html.Div([
    create_header(),

    dbc.Container([
        # Control row with Kymera buttons
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Refresh Watchlist",
                    id="refresh-button",
                    color="primary",
                    className="me-2 kymera-button"
                ),
                dbc.Button(
                    "Settings",
                    id="settings-button",
                    color="secondary",
                    className="me-2 kymera-button-secondary"
                ),
                html.Span(id="last-update", className="text-muted ms-3",
                         style={'fontFamily': 'var(--kymera-font-mono)',
                                'fontSize': 'var(--kymera-font-size-sm)'})
            ], width=12, className="mb-3")
        ]),

        # Positions panel (new)
        dbc.Row([
            dbc.Col([
                create_positions_panel()
            ], width=12)
        ]),

        # Main content row with Kymera styling
        dbc.Row([
            # Left column: Regime + Stats
            dbc.Col([
                html.Div(id='regime-card'),
                dbc.Card([
                    dbc.CardHeader(html.H5("Statistics", className="mb-0")),
                    dbc.CardBody(id='stats-content')
                ], className="kymera-card")
            ], width=3),

            # Right column: Watchlist
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Watchlist", className="mb-0")),
                    dbc.CardBody(id='watchlist-content')
                ], className="kymera-card")
            ], width=9)
        ]),

        # Charts section with Kymera styling
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Symbol Analysis", className="mb-0")),
                    dbc.CardBody([
                        # Timeframe tabs (Bootstrap tabs auto-styled by CSS)
                        dbc.Tabs([
                            dbc.Tab(label="15 Min", tab_id="15m"),
                            dbc.Tab(label="1 Hour", tab_id="1h"),
                            dbc.Tab(label="4 Hour", tab_id="4h"),
                        ], id="timeframe-tabs", active_tab="1h", className="mb-3"),

                        # Symbol input and load button
                        html.Div([
                            dbc.Input(
                                id="symbol-input",
                                placeholder="Enter symbol (e.g., AAPL)",
                                type="text",
                                value="AAPL",
                                className="kymera-input",
                                style={"width": "250px"}
                            ),
                            dbc.Button(
                                "Load Chart",
                                id="load-chart-btn",
                                color="primary",
                                size="sm",
                                className="kymera-button ms-2"
                            )
                        ], className="d-flex align-items-center mb-3"),

                        # Chart display with loading spinner
                        dcc.Loading(
                            id="chart-loading",
                            type="default",
                            children=html.Div([
                                dcc.Graph(
                                    id="symbol-chart",
                                    style={"height": "800px"},
                                    config={
                                        'displayModeBar': True,
                                        'displaylogo': False,
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                                    }
                                )
                            ], className="kymera-chart-container")
                        )
                    ])
                ], className="mt-3 kymera-card")
            ], width=12)
        ]),

        # Hidden interval for auto-refresh (5 seconds for positions, 5 minutes for watchlist)
        dcc.Interval(
            id='interval-component',
            interval=5*1000,  # 5 seconds in milliseconds
            n_intervals=0
        ),
        # Separate interval for watchlist (5 minutes)
        dcc.Interval(
            id='watchlist-interval',
            interval=5*60*1000,  # 5 minutes in milliseconds
            n_intervals=0
        ),

        # Hidden interval for clock
        dcc.Interval(
            id='clock-interval',
            interval=1000,  # 1 second
            n_intervals=0
        )
    ], fluid=True)
], className="kymera-dashboard")


@app.callback(
    Output('live-clock', 'children'),
    Input('clock-interval', 'n_intervals')
)
def update_clock(n):
    """Update live clock."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.callback(
    [Output('regime-card', 'children'),
     Output('watchlist-content', 'children'),
     Output('stats-content', 'children'),
     Output('last-update', 'children')],
    [Input('refresh-button', 'n_clicks'),
     Input('watchlist-interval', 'n_intervals')]
)
def update_dashboard(n_clicks, n_intervals):
    """Update dashboard with fresh data."""
    try:
        logger.info("Updating dashboard...")

        # Detect regime
        regime_data = regime_detector.detect_regime()
        regime_card = create_regime_card(regime_data)

        # Generate watchlist
        watchlist = watchlist_generator.generate(
            max_symbols=20,
            min_score=50.0
        )

        # Update cache
        watchlist_cache['data'] = watchlist
        watchlist_cache['timestamp'] = datetime.now()

        # Create watchlist table
        watchlist_table = create_watchlist_table(watchlist)

        # Statistics
        stats = html.Div([
            html.P([
                html.Strong("Setups Found: "),
                str(len(watchlist))
            ], className="mb-2"),
            html.P([
                html.Strong("Avg Score: "),
                f"{sum(s.total_points for s in watchlist) / len(watchlist):.1f}" if watchlist else "N/A"
            ], className="mb-2"),
            html.P([
                html.Strong("Top Grade: "),
                watchlist[0].setup_grade if watchlist else "N/A"
            ], className="mb-2")
        ])

        last_update = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"

        return regime_card, watchlist_table, stats, last_update

    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        error_msg = html.Div(f"Error: {str(e)}", className="text-danger")
        return error_msg, error_msg, error_msg, "Error"


@app.callback(
    [
        Output('positions-table', 'data'),
        Output('total-pnl', 'children'),
        Output('total-pnl', 'className'),
        Output('unrealized-pnl', 'children'),
        Output('unrealized-pnl', 'className'),
        Output('positions-count', 'children'),
        Output('winning-positions', 'children'),
        Output('losing-positions', 'children')
    ],
    Input('interval-component', 'n_intervals')
)
def update_positions(n):
    """
    Update positions panel with live P&L data.

    Parameters:
    -----------
    n : int
        Number of intervals (updates every 5 seconds)

    Returns:
    --------
    tuple
        (table_data, total_pnl_text, total_pnl_class, unrealized_text,
         unrealized_class, positions_count, winning_count, losing_count)

    Features:
    ---------
    - Fetches live position data from order_manager
    - Calculates unrealized P&L from current prices
    - Color-codes P&L values (green=profit, red=loss)
    - Updates portfolio summary metrics
    - Handles empty positions gracefully
    """
    return update_positions_callback(n)


@app.callback(
    Output('symbol-chart', 'figure'),
    [
        Input('load-chart-btn', 'n_clicks'),
        Input('timeframe-tabs', 'active_tab')
    ],
    [State('symbol-input', 'value')]
)
def update_chart(n_clicks, active_tab, symbol):
    """
    Update chart when symbol or timeframe changes.

    Parameters:
    -----------
    n_clicks : int
        Number of times load button clicked
    active_tab : str
        Active timeframe tab ('15m', '1h', '4h')
    symbol : str
        Symbol to chart

    Returns:
    --------
    go.Figure
        Updated Plotly figure
    """
    if not symbol:
        symbol = 'AAPL'  # Default symbol

    # Map tab ID to timeframe
    timeframe_map = {
        '15m': '15 mins',
        '1h': '1 hour',
        '4h': '4 hours'
    }

    timeframe = timeframe_map.get(active_tab, '1 hour')

    logger.info(f"Updating chart: {symbol} {timeframe} (n_clicks={n_clicks})")

    try:
        fig = create_multitimeframe_chart(symbol.upper(), timeframe, bars=100)
        return fig
    except Exception as e:
        logger.error(f"Error creating chart for {symbol} {timeframe}: {e}")
        # Return empty chart with error
        from src.dashboard.components.charts import _create_empty_chart
        return _create_empty_chart(symbol, timeframe, f"Error: {str(e)}")


if __name__ == '__main__':
    logger.info("Starting Screener Dashboard...")
    logger.info("Navigate to: http://localhost:8050")

    # Run server
    app.run_server(
        debug=config.get('dashboard.debug', True),
        host='0.0.0.0',
        port=8050
    )
