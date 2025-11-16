"""
Positions Panel Component for Dashboard

Displays open trading positions with real-time P&L updates.

Features:
---------
- Color-coded P&L (green=profit, red=loss)
- Entry, current, stop, target prices
- Unrealized P&L in $ and %
- Portfolio-level summary metrics
- Auto-refresh every 5 seconds (via dashboard interval)

Usage:
------
from src.dashboard.components.positions import create_positions_panel

# In dashboard layout
layout = html.Div([
    create_positions_panel(),
    # ... other components
])

# Add callback for updates
@app.callback(...)
def update_positions(n):
    # See update_positions_callback() docstring for full implementation
    pass
"""

from typing import List, Dict, Any
import dash_bootstrap_components as dbc
from dash import dash_table, html
import pandas as pd
from loguru import logger


def create_positions_table() -> dash_table.DataTable:
    """
    Create interactive positions table with color-coded P&L.

    Returns:
    --------
    dash_table.DataTable
        Table displaying open positions with real-time updates

    Features:
    ---------
    - Columns: Symbol, Side, Qty, Entry, Current, Stop, Target, P&L $, P&L %, Risk $
    - Green background for profitable positions
    - Red background for losing positions
    - Bold, colored P&L columns
    - Sortable and filterable
    - Numeric formatting for prices and P&L

    Notes:
    ------
    - Data populated by update_positions_callback()
    - Updates every 5 seconds via interval component
    - Empty table shown when no positions open
    """
    return dash_table.DataTable(
        id='positions-table',
        columns=[
            {'name': 'Symbol', 'id': 'symbol'},
            {'name': 'Side', 'id': 'side'},
            {'name': 'Qty', 'id': 'quantity', 'type': 'numeric'},
            {'name': 'Entry', 'id': 'entry_price', 'type': 'numeric',
             'format': {'specifier': '$.2f'}},
            {'name': 'Current', 'id': 'current_price', 'type': 'numeric',
             'format': {'specifier': '$.2f'}},
            {'name': 'Stop', 'id': 'stop_price', 'type': 'numeric',
             'format': {'specifier': '$.2f'}},
            {'name': 'Target', 'id': 'target_price', 'type': 'numeric',
             'format': {'specifier': '$.2f'}},
            {'name': 'P&L $', 'id': 'unrealized_pnl', 'type': 'numeric',
             'format': {'specifier': '$,.2f'}},
            {'name': 'P&L %', 'id': 'unrealized_pnl_pct', 'type': 'numeric',
             'format': {'specifier': '.2f'}},
            {'name': 'Risk $', 'id': 'current_risk', 'type': 'numeric',
             'format': {'specifier': '$,.2f'}},
        ],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'backgroundColor': '#1e1e1e',
            'color': '#ffffff',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': '#2d2d2d',
            'fontWeight': 'bold',
            'color': '#ffffff',
            'textAlign': 'left'
        },
        style_data_conditional=[
            # Profit rows - green background
            {
                'if': {
                    'filter_query': '{unrealized_pnl} > 0',
                },
                'backgroundColor': 'rgba(0, 128, 0, 0.2)',
            },
            # Loss rows - red background
            {
                'if': {
                    'filter_query': '{unrealized_pnl} < 0',
                },
                'backgroundColor': 'rgba(255, 0, 0, 0.2)',
            },
            # P&L $ column - green for profit
            {
                'if': {
                    'filter_query': '{unrealized_pnl} > 0',
                    'column_id': 'unrealized_pnl'
                },
                'color': '#00ff00',
                'fontWeight': 'bold'
            },
            # P&L $ column - red for loss
            {
                'if': {
                    'filter_query': '{unrealized_pnl} < 0',
                    'column_id': 'unrealized_pnl'
                },
                'color': '#ff0000',
                'fontWeight': 'bold'
            },
            # P&L % column - green for profit
            {
                'if': {
                    'filter_query': '{unrealized_pnl_pct} > 0',
                    'column_id': 'unrealized_pnl_pct'
                },
                'color': '#00ff00',
                'fontWeight': 'bold'
            },
            # P&L % column - red for loss
            {
                'if': {
                    'filter_query': '{unrealized_pnl_pct} < 0',
                    'column_id': 'unrealized_pnl_pct'
                },
                'color': '#ff0000',
                'fontWeight': 'bold'
            }
        ],
        page_size=10,
        sort_action='native',
        filter_action='native'
    )


def create_portfolio_summary_card() -> dbc.Card:
    """
    Create portfolio summary card with aggregated metrics.

    Returns:
    --------
    dbc.Card
        Card displaying portfolio-level P&L and position counts

    Displays:
    ---------
    - Total P&L (realized + unrealized)
    - Unrealized P&L (open positions)
    - Open Positions count
    - Winning Positions count
    - Losing Positions count

    Notes:
    ------
    - Values updated by update_positions_callback()
    - Color-coded P&L values (green/red)
    - Updates every 5 seconds
    """
    return dbc.Card([
        dbc.CardHeader(html.H5("Portfolio Summary", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("Total P&L", className="text-muted mb-2"),
                    html.H3(id="total-pnl", children="$0.00", className="mb-0")
                ], width=3),
                dbc.Col([
                    html.H6("Unrealized P&L", className="text-muted mb-2"),
                    html.H3(id="unrealized-pnl", children="$0.00", className="mb-0")
                ], width=3),
                dbc.Col([
                    html.H6("Open Positions", className="text-muted mb-2"),
                    html.H3(id="positions-count", children="0", className="mb-0")
                ], width=2),
                dbc.Col([
                    html.H6("Winning", className="text-muted mb-2"),
                    html.H3(id="winning-positions", children="0",
                           className="mb-0 text-success")
                ], width=2),
                dbc.Col([
                    html.H6("Losing", className="text-muted mb-2"),
                    html.H3(id="losing-positions", children="0",
                           className="mb-0 text-danger")
                ], width=2)
            ])
        ])
    ], className="mb-3")


def create_positions_panel() -> dbc.Card:
    """
    Create complete positions panel with summary and table.

    Returns:
    --------
    dbc.Card
        Full positions panel containing summary card and positions table

    Structure:
    ----------
    - Card header: "Active Positions"
    - Card body:
        - Portfolio summary card (top)
        - Positions table (bottom)

    Integration:
    ------------
    Add to dashboard layout:
        app.layout = html.Div([
            create_positions_panel(),
            # ... other components
        ])

    Add callback for updates:
        @app.callback(
            [Output('positions-table', 'data'),
             Output('total-pnl', 'children'),
             Output('total-pnl', 'className'),
             Output('unrealized-pnl', 'children'),
             Output('unrealized-pnl', 'className'),
             Output('positions-count', 'children'),
             Output('winning-positions', 'children'),
             Output('losing-positions', 'children')],
            Input('interval-component', 'n_intervals')
        )
        def update_positions(n):
            # Implementation in update_positions_callback() docstring
            pass

    Notes:
    ------
    - Auto-refreshes via interval component (5 seconds)
    - Fetches data from order_manager singleton
    - Handles empty positions gracefully
    """
    return dbc.Card([
        dbc.CardHeader(html.H5("Active Positions", className="mb-0")),
        dbc.CardBody([
            create_portfolio_summary_card(),
            create_positions_table()
        ])
    ], className="mb-4")


def update_positions_callback(n_intervals: int) -> tuple:
    """
    Callback function to update positions panel with live data.

    This function should be used as the callback implementation for updating
    the positions panel. It fetches live position data from order_manager
    and formats it for display.

    Parameters:
    -----------
    n_intervals : int
        Number of intervals elapsed (from dcc.Interval component)

    Returns:
    --------
    tuple
        (table_data, total_pnl_text, total_pnl_class, unrealized_text,
         unrealized_class, positions_count, winning_count, losing_count)

    Implementation:
    ---------------
    @app.callback(
        [Output('positions-table', 'data'),
         Output('total-pnl', 'children'),
         Output('total-pnl', 'className'),
         Output('unrealized-pnl', 'children'),
         Output('unrealized-pnl', 'className'),
         Output('positions-count', 'children'),
         Output('winning-positions', 'children'),
         Output('losing-positions', 'children')],
        Input('interval-component', 'n_intervals')
    )
    def update_positions(n):
        return update_positions_callback(n)

    Data Flow:
    ----------
    1. Fetch positions DataFrame from order_manager.get_positions_dataframe()
    2. Fetch portfolio P&L from order_manager.get_portfolio_pnl()
    3. Format data for table display
    4. Format P&L values with color classes
    5. Return all outputs

    Error Handling:
    ---------------
    - Logs errors to loguru logger
    - Returns empty/zero values on error
    - Never crashes the dashboard

    Examples:
    ---------
    >>> # In dashboard app.py
    >>> from src.execution.order_manager import order_manager
    >>> from src.dashboard.components.positions import update_positions_callback
    >>>
    >>> @app.callback([...], Input('interval-component', 'n_intervals'))
    >>> def update_positions(n):
    ...     return update_positions_callback(n)
    """
    from src.execution.order_manager import order_manager

    try:
        # Get positions DataFrame
        df = order_manager.get_positions_dataframe()

        # Get portfolio P&L
        pnl = order_manager.get_portfolio_pnl()

        # Format data for table
        if df is not None and len(df) > 0:
            # Convert DataFrame to dict records for table
            table_data = df.to_dict('records')
        else:
            table_data = []

        # Format total P&L
        total_pnl = pnl['total_pnl']
        total_pnl_text = f"${total_pnl:+,.2f}"
        total_pnl_class = "mb-0 text-success" if total_pnl >= 0 else "mb-0 text-danger"

        # Format unrealized P&L
        unrealized = pnl['unrealized_pnl']
        unrealized_text = f"${unrealized:+,.2f}"
        unrealized_class = "mb-0 text-success" if unrealized >= 0 else "mb-0 text-danger"

        # Format counts
        positions_count = str(pnl['positions_count'])
        winning_count = str(pnl['winning_positions'])
        losing_count = str(pnl['losing_positions'])

        return (
            table_data,
            total_pnl_text,
            total_pnl_class,
            unrealized_text,
            unrealized_class,
            positions_count,
            winning_count,
            losing_count
        )

    except Exception as e:
        logger.error(f"Failed to update positions panel: {e}")
        # Return safe defaults on error
        return (
            [],
            "$0.00",
            "mb-0",
            "$0.00",
            "mb-0",
            "0",
            "0",
            "0"
        )
