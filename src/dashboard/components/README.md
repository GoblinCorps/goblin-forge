# Dashboard Components

Reusable Dash components for the Screener dashboard interface.

## Charts Component

Multi-timeframe candlestick charts with technical indicators.

### Features

- **4-Panel Layout**:
  1. Price panel: Candlestick chart with Bollinger Bands and EMAs (8, 21, 50)
  2. Stochastic RSI panel: Oscillator with 80/20 overbought/oversold levels
  3. MACD panel: MACD line, signal line, and color-coded histogram
  4. Volume panel: Color-coded volume bars (green=up, red=down)

- **Multi-Timeframe Support**: 15-minute, 1-hour, and 4-hour charts
- **Interactive**: Zoom, pan, hover details via Plotly
- **Dark Theme**: Optimized for dark mode dashboard
- **Error Handling**: Graceful fallback for missing data

### Usage

```python
from src.dashboard.components.charts import create_multitimeframe_chart

# Create chart for AAPL, 1-hour timeframe, 100 bars
fig = create_multitimeframe_chart('AAPL', '1 hour', 100)

# Display in Dash
dcc.Graph(figure=fig)
```

### API

#### `create_multitimeframe_chart(symbol, timeframe, bars)`

Create multi-panel chart for a symbol.

**Parameters:**
- `symbol` (str): Stock symbol (e.g., 'AAPL')
- `timeframe` (str): Timeframe ('15 mins', '1 hour', '4 hours')
- `bars` (int, default=100): Number of bars to display

**Returns:**
- `go.Figure`: Plotly figure with 4 panels

**Example:**
```python
fig = create_multitimeframe_chart('GOOGL', '15 mins', 200)
```

#### `validate_symbol_data(symbol, timeframe)`

Check if data exists for symbol and timeframe.

**Parameters:**
- `symbol` (str): Stock symbol
- `timeframe` (str): Timeframe identifier

**Returns:**
- `bool`: True if data exists

**Example:**
```python
if validate_symbol_data('AAPL', '1 hour'):
    fig = create_multitimeframe_chart('AAPL', '1 hour', 100)
```

#### `get_available_timeframes()`

Get list of supported timeframes.

**Returns:**
- `list`: ['15 mins', '1 hour', '4 hours']

### Integration with Dashboard

The chart component is integrated into the main dashboard at `/home/aaron/github/astoreyai/screener/src/dashboard/app.py`:

1. **Symbol Input**: Text field to enter symbol
2. **Timeframe Tabs**: Switch between 15m/1h/4h
3. **Load Button**: Trigger chart refresh
4. **Auto-Update**: Charts update when tab or symbol changes

### Data Requirements

Charts require:
- Historical data loaded via `historical_manager`
- Minimum 85 bars for indicator calculation
- Valid OHLCV data (open/high/low/close/volume)

### Testing

Comprehensive test suite with 100% coverage:

```bash
pytest tests/test_dashboard_charts.py -v --cov=src.dashboard.components.charts
```

**Test Coverage:**
- 24 tests
- 100% code coverage
- Tests for all panels, error cases, and edge conditions

### Technical Details

**Dependencies:**
- Plotly (charting)
- pandas (data manipulation)
- TA-Lib (via indicator_engine)
- historical_manager (data loading)
- indicator_engine (technical indicators)

**Color Scheme (Dark Theme):**
- Background: `rgb(17,17,17)`
- Candlesticks: Green (#00cc00) up, Red (#ff3333) down
- BB bands: Gray (#888888) with 10% fill
- EMAs: Blue (#3366ff), Orange (#ff9900), Purple (#cc00cc)
- Stoch RSI: Purple (#9966ff) %K, Orange (#ff9900) %D
- MACD: Blue (#3366ff) line, Orange (#ff9900) signal

**Performance:**
- Charts render in <500ms for 100 bars
- Supports up to 500 bars efficiently
- Cached indicator calculations

### Known Limitations

1. Requires minimum 85 bars for full indicator calculation
2. No real-time streaming (planned for future)
3. Fixed panel heights (50%, 15%, 15%, 20%)

### Future Enhancements

- [ ] Real-time bar updates
- [ ] Adjustable panel heights
- [ ] Additional indicators (volume profile, order flow)
- [ ] Entry/exit markers
- [ ] Drawing tools (trendlines, fibs)
- [ ] Multi-symbol comparison
- [ ] Save/load chart layouts

## Author

Screener Trading System
Date: 2025-11-15
