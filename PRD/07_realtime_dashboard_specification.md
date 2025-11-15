# Real-Time Dashboard Specification
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Dashboard Overview

The dashboard is the primary interface for monitoring market conditions, screening results, and executing trades. It must present all critical information at a glance while providing drill-down capabilities for detailed analysis.

**Design Principles:**
- **Information Hierarchy:** Most critical data in top-left quadrant
- **Color Coding:** Consistent use of green (bullish), red (bearish), yellow (caution)
- **Real-Time Updates:** Auto-refresh without page reload
- **Actionability:** One-click access to charts and execution

---

## 2. Dashboard Layout

### 2.1 Grid Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER BAR: Time | Connection | Account | Regime Score         │
├──────────────────────┬──────────────────────────────────────────┤
│                      │                                          │
│  MARKET REGIME       │  TOP WATCHLIST (Ranked by SABR20)       │
│  (25% width)         │  (75% width)                             │
│                      │                                          │
│  - VIX              │  Table: Symbol | Score | State | R:R ...  │
│  - Trend            │                                          │
│  - Breadth          │                                          │
│  - Correlation      │                                          │
│                      │                                          │
├──────────────────────┼──────────────────────────────────────────┤
│                      │                                          │
│  ACTIVE POSITIONS    │  SELECTED SYMBOL CHARTS                  │
│  (25% width)         │  (75% width)                             │
│                      │                                          │
│  - Open trades       │  Multi-timeframe view:                   │
│  - P&L              │  [15m] [1h] [4h] tabs                     │
│  - Risk exposure     │  Chart with indicators overlaid           │
│                      │                                          │
└──────────────────────┴──────────────────────────────────────────┘
│  FOOTER: Recent Alerts | System Stats | Quick Actions           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Header Bar

```python
# Header components (always visible)
header_components = {
    'time': {
        'display': 'HH:MM:SS ET',
        'update_frequency': '1s',
        'color': 'white'
    },
    'ib_connection': {
        'display': '● Connected to TWS' or '○ Disconnected',
        'color': 'green' if connected else 'red',
        'click_action': 'show_connection_details'
    },
    'account_info': {
        'display': 'Equity: $XXX,XXX | Buying Power: $XXX,XXX',
        'update_frequency': '60s'
    },
    'regime_indicator': {
        'display': 'Regime: BULL_LOW_VOL (78/100)',
        'color': 'green' if score > 60 else 'yellow' if score > 40 else 'red',
        'tooltip': 'Click for detailed regime analysis',
        'click_action': 'open_regime_modal'
    }
}
```

**Implementation:**
```python
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

def create_header():
    """Create dashboard header bar."""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    html.Div(id='live-clock', className='text-white'),
                    width=2
                ),
                dbc.Col(
                    html.Div(id='connection-status'),
                    width=2
                ),
                dbc.Col(
                    html.Div(id='account-info'),
                    width=4
                ),
                dbc.Col(
                    html.Div(id='regime-indicator'),
                    width=4
                )
            ], align='center')
        ], fluid=True),
        color='dark',
        dark=True
    )
```

### 3.2 Market Regime Panel

**Information to Display:**

| Metric | Display Format | Color Logic |
|--------|----------------|-------------|
| VIX Level | "VIX: 15.2 ↓" | Green <20, Yellow 20-30, Red >30 |
| VIX Trend | Arrow + text | Green if falling, Red if rising |
| Trend Consensus | "Bullish (3/4)" | Green if bullish, Red if bearish |
| SPY Position | "+2.1% vs SMA20" | Green if positive, Red if negative |
| QQQ Position | "+3.5% vs SMA20" | Green if positive, Red if negative |
| A/D Ratio | "2.1 (Strong)" | Green >1.5, Yellow 0.8-1.5, Red <0.8 |
| Correlation | "0.65 (Moderate)" | Green 0.5-0.7, Yellow otherwise |
| Favorability | "78/100" | Large, bold, color-coded |

**Implementation:**
```python
def create_regime_panel():
    """Create market regime panel."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Market Regime")),
        dbc.CardBody([
            # VIX Section
            html.Div([
                html.H6("Volatility"),
                html.Div(id='vix-display', className='metric-large'),
                html.Div(id='vix-trend', className='metric-small')
            ], className='mb-3'),
            
            html.Hr(),
            
            # Trend Section
            html.Div([
                html.H6("Trend"),
                html.Div(id='trend-consensus', className='metric-medium'),
                html.Div([
                    html.Span("SPY: ", className='label'),
                    html.Span(id='spy-position', className='value')
                ]),
                html.Div([
                    html.Span("QQQ: ", className='label'),
                    html.Span(id='qqq-position', className='value')
                ])
            ], className='mb-3'),
            
            html.Hr(),
            
            # Breadth Section
            html.Div([
                html.H6("Breadth"),
                html.Div(id='ad-ratio', className='metric-medium'),
                html.Div(id='breadth-strength', className='metric-small')
            ], className='mb-3'),
            
            html.Hr(),
            
            # Overall Score
            html.Div([
                html.H5("Favorability"),
                html.Div(id='favorability-score', className='score-display'),
                dbc.Progress(id='favorability-bar', value=0, max=100, className='mt-2')
            ])
        ])
    ])
```

### 3.3 Top Watchlist Table

**Columns to Display:**

1. **Rank** (#1, #2, ...)
2. **Symbol** (clickable)
3. **SABR20 Score** (color-coded)
4. **Setup Grade** (A+, A, B)
5. **State** (BottomActive, BottomSoon, etc.)
6. **Acc Phase** (EarlyAccumulation, MidAccumulation, etc.)
7. **Acc Ratio** (Stoch/RSI signal frequency)
8. **Price** (current)
9. **R:R Ratio**
10. **Bars Since Pivot**
11. **DD %** (drawdown from recent high)
12. **Quartile** (Q1-Q4)
13. **Actions** (View Chart, Quick Trade)

**Table Features:**
- Sortable columns
- Color-coded scores (green >75, yellow 65-75, orange <65)
- Hover to show mini-chart preview
- Click symbol to load charts
- Right-click for context menu

**Implementation:**
```python
import dash_table

def create_watchlist_table():
    """Create interactive watchlist table."""
    return dash_table.DataTable(
        id='watchlist-table',
        columns=[
            {'name': '#', 'id': 'rank'},
            {'name': 'Symbol', 'id': 'symbol', 'presentation': 'markdown'},
            {'name': 'SABR20', 'id': 'SABR20_score'},
            {'name': 'Grade', 'id': 'setup_grade'},
            {'name': 'State', 'id': 'state'},
            {'name': 'Acc Phase', 'id': 'acc_phase'},
            {'name': 'Acc Ratio', 'id': 'acc_ratio', 'type': 'numeric', 'format': {'specifier': '.1f'}},
            {'name': 'Price', 'id': 'price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
            {'name': 'R:R', 'id': 'rr_ratio', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Bars', 'id': 'bars_since_pivot'},
            {'name': 'DD%', 'id': 'dd_pct', 'type': 'numeric', 'format': {'specifier': '.1f'}},
            {'name': 'Q', 'id': 'quartile'},
        ],
        data=[],  # Populated dynamically
        
        # Styling
        style_table={'overflowY': 'auto', 'maxHeight': '400px'},
        style_cell={'textAlign': 'left', 'padding': '8px'},
        style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
        
        # Conditional formatting
        style_data_conditional=[
            # Score color coding
            {
                'if': {
                    'filter_query': '{SABR20_score} >= 75',
                    'column_id': 'SABR20_score'
                },
                'backgroundColor': '#28a745',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{SABR20_score} >= 65 && {SABR20_score} < 75',
                    'column_id': 'SABR20_score'
                },
                'backgroundColor': '#ffc107',
                'color': 'black'
            },
            # Grade highlighting
            {
                'if': {
                    'filter_query': '{setup_grade} = "A+"',
                    'column_id': 'setup_grade'
                },
                'backgroundColor': '#28a745',
                'color': 'white',
                'fontWeight': 'bold'
            },
            # Accumulation phase highlighting
            {
                'if': {
                    'filter_query': '{acc_phase} = "EarlyAccumulation"',
                    'column_id': 'acc_phase'
                },
                'backgroundColor': '#00ff00',
                'color': 'black',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{acc_phase} = "MidAccumulation"',
                    'column_id': 'acc_phase'
                },
                'backgroundColor': '#90ee90',
                'color': 'black'
            },
            # High accumulation ratio
            {
                'if': {
                    'filter_query': '{acc_ratio} >= 5',
                    'column_id': 'acc_ratio'
                },
                'backgroundColor': '#28a745',
                'color': 'white',
                'fontWeight': 'bold'
            },
            # Negative DD in red
            {
                'if': {
                    'filter_query': '{dd_pct} < 0',
                    'column_id': 'dd_pct'
                },
                'color': '#dc3545'
            }
        ],
        
        # Interactivity
        row_selectable='single',
        selected_rows=[],
        page_action='none',  # Show all rows
        sort_action='native',
        sort_by=[{'column_id': 'SABR20_score', 'direction': 'desc'}]
    )
```

### 3.4 Multi-Timeframe Charts

**Chart Configuration:**

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_multi_tf_chart(symbol: str, timeframe: str):
    """
    Create multi-panel chart with price + indicators.
    
    Layout:
    - Panel 1 (60% height): Price + Bollinger Bands
    - Panel 2 (15%): Stoch RSI
    - Panel 3 (15%): MACD
    - Panel 4 (10%): Volume
    """
    # Fetch data
    data = fetch_symbol_data(symbol, timeframe)
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.6, 0.15, 0.15, 0.1],
        subplot_titles=('Price & Bollinger Bands', 'Stoch RSI', 'MACD', 'Volume')
    )
    
    # Panel 1: Candlesticks + Bollinger Bands
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(x=data.index, y=data['bb_upper'], name='BB Upper', 
                   line=dict(color='gray', width=1, dash='dash')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data['bb_mid'], name='BB Mid',
                   line=dict(color='blue', width=1)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data['bb_lower'], name='BB Lower',
                   line=dict(color='gray', width=1, dash='dash')),
        row=1, col=1
    )
    
    # Panel 2: Stoch RSI
    fig.add_trace(
        go.Scatter(x=data.index, y=data['stoch_k'], name='Stoch K',
                   line=dict(color='blue', width=2)),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data['stoch_d'], name='Stoch D',
                   line=dict(color='red', width=2)),
        row=2, col=1
    )
    # Oversold/Overbought lines
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="green", row=2, col=1)
    
    # Panel 3: MACD
    colors = ['green' if val >= 0 else 'red' for val in data['macd_hist']]
    fig.add_trace(
        go.Bar(x=data.index, y=data['macd_hist'], name='MACD Hist',
               marker_color=colors),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data['macd'], name='MACD',
                   line=dict(color='blue', width=1)),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data['macd_signal'], name='Signal',
                   line=dict(color='red', width=1)),
        row=3, col=1
    )
    
    # Panel 4: Volume
    fig.add_trace(
        go.Bar(x=data.index, y=data['volume'], name='Volume',
               marker_color='lightblue'),
        row=4, col=1
    )
    
    # Layout
    fig.update_layout(
        title=f'{symbol} - {timeframe}',
        xaxis_rangeslider_visible=False,
        height=800,
        template='plotly_dark',
        showlegend=False
    )
    
    # Update y-axes labels
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Stoch RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)
    
    return fig
```

**Timeframe Tabs:**
```python
def create_chart_tabs():
    """Create tabbed interface for timeframes."""
    return dbc.Tabs([
        dbc.Tab(
            dcc.Graph(id='chart-15m'),
            label='15 min',
            tab_id='15m'
        ),
        dbc.Tab(
            dcc.Graph(id='chart-1h'),
            label='1 hour',
            tab_id='1h'
        ),
        dbc.Tab(
            dcc.Graph(id='chart-4h'),
            label='4 hour',
            tab_id='4h'
        )
    ], id='chart-tabs', active_tab='15m')
```

### 3.5 Active Positions Panel

**Display Elements:**

```python
def create_positions_panel():
    """Create active positions monitoring panel."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Active Positions")),
        dbc.CardBody([
            # Summary
            html.Div([
                html.Div([
                    html.Span("Total P&L: ", className='label'),
                    html.Span(id='total-pnl', className='pnl-value')
                ]),
                html.Div([
                    html.Span("Open Positions: ", className='label'),
                    html.Span(id='open-count', className='value')
                ]),
                html.Div([
                    html.Span("Total Risk: ", className='label'),
                    html.Span(id='total-risk', className='value')
                ])
            ], className='mb-3'),
            
            html.Hr(),
            
            # Position list
            html.Div(id='positions-list')
        ])
    ])

def create_position_card(position_data):
    """Create individual position card."""
    return dbc.Card([
        dbc.CardBody([
            html.H6(position_data['symbol'], className='mb-2'),
            html.Div([
                html.Small(f"Entry: ${position_data['entry_price']:.2f}"),
                html.Br(),
                html.Small(f"Current: ${position_data['current_price']:.2f}"),
                html.Br(),
                html.Small(f"Stop: ${position_data['stop_price']:.2f}"),
                html.Br(),
                html.Small([
                    "P&L: ",
                    html.Span(
                        f"${position_data['pnl']:.2f} ({position_data['pnl_pct']:.1f}%)",
                        className='pnl-positive' if position_data['pnl'] > 0 else 'pnl-negative'
                    )
                ])
            ]),
            dbc.Button("Close", size='sm', color='danger', className='mt-2')
        ])
    ], className='mb-2', color='light')
```

---

## 4. Real-Time Data Updates

### 4.1 Update Strategy

```python
from dash import Input, Output, State
from dash.exceptions import PreventUpdate

# Update frequencies
UPDATE_INTERVALS = {
    'clock': 1000,            # 1 second
    'connection': 5000,       # 5 seconds
    'watchlist': 15000,       # 15 seconds
    'charts': 60000,          # 1 minute
    'positions': 5000,        # 5 seconds
    'regime': 1800000         # 30 minutes
}

# Interval components
intervals = html.Div([
    dcc.Interval(id='interval-clock', interval=UPDATE_INTERVALS['clock']),
    dcc.Interval(id='interval-watchlist', interval=UPDATE_INTERVALS['watchlist']),
    dcc.Interval(id='interval-charts', interval=UPDATE_INTERVALS['charts']),
    dcc.Interval(id='interval-positions', interval=UPDATE_INTERVALS['positions']),
    dcc.Interval(id='interval-regime', interval=UPDATE_INTERVALS['regime'])
])
```

### 4.2 Callback Implementations

```python
@app.callback(
    Output('watchlist-table', 'data'),
    Input('interval-watchlist', 'n_intervals')
)
def update_watchlist(n):
    """Update watchlist table every 15 seconds."""
    if n is None:
        raise PreventUpdate
    
    # Fetch latest watchlist
    watchlist = fetch_current_watchlist()
    
    # Format for display
    data = watchlist.to_dict('records')
    
    return data

@app.callback(
    [Output('chart-15m', 'figure'),
     Output('chart-1h', 'figure'),
     Output('chart-4h', 'figure')],
    [Input('watchlist-table', 'selected_rows'),
     Input('interval-charts', 'n_intervals')],
    State('watchlist-table', 'data')
)
def update_charts(selected_rows, n, table_data):
    """Update charts when symbol selected or on timer."""
    if not selected_rows or not table_data:
        raise PreventUpdate
    
    # Get selected symbol
    row_idx = selected_rows[0]
    symbol = table_data[row_idx]['symbol']
    
    # Create charts for all timeframes
    fig_15m = create_multi_tf_chart(symbol, '15 mins')
    fig_1h = create_multi_tf_chart(symbol, '1 hour')
    fig_4h = create_multi_tf_chart(symbol, '4 hours')
    
    return fig_15m, fig_1h, fig_4h

@app.callback(
    Output('regime-indicator', 'children'),
    Input('interval-regime', 'n_intervals')
)
def update_regime_indicator(n):
    """Update regime indicator."""
    env = regime_monitor.get_current()
    
    return html.Div([
        html.Span(f"Regime: {env.regime.value.upper()} ", className='regime-label'),
        html.Span(f"({env.favorability_score}/100)", className='regime-score')
    ], style={
        'color': 'green' if env.favorability_score > 60 else 'yellow' if env.favorability_score > 40 else 'red'
    })
```

---

## 5. Alert and Notification System

### 5.1 Alert Panel

```python
def create_alerts_panel():
    """Create alerts display panel."""
    return dbc.Card([
        dbc.CardHeader(html.H6("Recent Alerts")),
        dbc.CardBody([
            html.Div(id='alerts-list', style={'maxHeight': '150px', 'overflowY': 'auto'})
        ])
    ], className='mt-2')

def create_alert_item(alert):
    """Create individual alert item."""
    icon_map = {
        'HIGH': '🔴',
        'MEDIUM': '🟡',
        'LOW': '🟢',
        'INFO': 'ℹ️'
    }
    
    return html.Div([
        html.Span(icon_map.get(alert['priority'], 'ℹ️')),
        html.Span(f" {alert['timestamp'].strftime('%H:%M')} ", className='alert-time'),
        html.Span(alert['message'], className='alert-message')
    ], className='alert-item mb-1')
```

---

## 6. Quick Actions Bar

```python
def create_actions_bar():
    """Create quick actions toolbar."""
    return dbc.ButtonGroup([
        dbc.Button("Refresh All", id='btn-refresh', color='primary', size='sm'),
        dbc.Button("Pause Updates", id='btn-pause', color='secondary', size='sm'),
        dbc.Button("Export Watchlist", id='btn-export', color='info', size='sm'),
        dbc.Button("System Settings", id='btn-settings', color='dark', size='sm')
    ])
```

---

## 7. Complete Dashboard Assembly

```python
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

# Initialize app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# Layout
app.layout = dbc.Container([
    # Header
    create_header(),
    
    # Main content
    dbc.Row([
        # Left column: Regime + Positions
        dbc.Col([
            create_regime_panel(),
            html.Br(),
            create_positions_panel()
        ], width=3),
        
        # Right column: Watchlist + Charts
        dbc.Col([
            # Watchlist table
            html.H4("Top Setups"),
            create_watchlist_table(),
            html.Br(),
            
            # Charts
            html.H4("Chart Analysis"),
            create_chart_tabs()
        ], width=9)
    ], className='mt-3'),
    
    # Footer
    dbc.Row([
        dbc.Col(create_alerts_panel(), width=8),
        dbc.Col(create_actions_bar(), width=4, className='d-flex align-items-center justify-content-end')
    ], className='mt-3'),
    
    # Intervals for updates
    intervals
    
], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
```

---

## 8. Mobile/Responsive Considerations

- Use Bootstrap responsive classes
- Collapse panels on small screens
- Simplified mobile view with essential metrics only
- Touch-friendly button sizes

---

## 9. Next Document

**Document 08: Data Pipeline and Infrastructure** will detail:
- Historical data management
- Real-time data ingestion
- Indicator calculation pipeline
- Caching strategies
- Database operations
