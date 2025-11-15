# Claude Code Implementation Prompt
## Multi-Timeframe Momentum Reversal Trading System

---

## 🎯 Project Overview

You are tasked with implementing a professional-grade algorithmic trading system based on a comprehensive set of Product Requirements Documents (PRDs). This system screens 500-2000 stocks, identifies mean-reversion-to-trend-expansion opportunities using multi-timeframe analysis, and executes trades via Interactive Brokers.

---

## 📚 Reference Documentation

You have access to the following PRD documents in the project:

1. **README.md** - Master index and quick start guide
2. **00_system_requirements_and_architecture.md** - Tech stack and infrastructure
3. **01_algorithm_spec.md** - Core trading algorithm (user-provided)
4. **02_mean_reversion_trend_system.md** - Risk management (user-provided)
5. **03_decision_tree_and_screening.md** - Decision logic (user-provided)
6. **04_universe_and_prescreening.md** - Universe construction and coarse filtering
7. **05_watchlist_generation_and_scoring.md** - SABR20 scoring system with accumulation analysis
8. **06_regime_and_market_checks.md** - Market environment analysis
9. **07_realtime_dashboard_specification.md** - Dashboard UI specification
10. **08_data_pipeline_and_infrastructure.md** - Data management
11. **09_execution_and_monitoring.md** - Trade execution and tracking

**IMPORTANT:** Read these documents thoroughly before beginning implementation. They contain complete specifications including code examples, database schemas, and architecture diagrams.

---

## 🏗️ Implementation Instructions

### Phase 1: Project Setup and Infrastructure

**Objective:** Set up the development environment, project structure, and core dependencies.

**Tasks:**

1. **Initialize Git Repository**
   ```bash
   git init
   git remote add origin <GITHUB_REPO_URL>
   ```

2. **Create Project Structure** (as specified in README.md):
   ```
   trading-system/
   ├── README.md
   ├── requirements.txt
   ├── .env.example
   ├── .gitignore
   ├── docs/              # Copy all PRD documents here
   ├── src/
   │   ├── __init__.py
   │   ├── config.py
   │   ├── data/
   │   │   ├── __init__.py
   │   │   ├── ib_manager.py
   │   │   ├── historical_manager.py
   │   │   └── realtime_aggregator.py
   │   ├── indicators/
   │   │   ├── __init__.py
   │   │   ├── calculator.py
   │   │   ├── accumulation.py
   │   │   └── cache.py
   │   ├── screening/
   │   │   ├── __init__.py
   │   │   ├── universe.py
   │   │   ├── coarse_filter.py
   │   │   ├── sabr_scorer.py
   │   │   └── watchlist.py
   │   ├── regime/
   │   │   ├── __init__.py
   │   │   ├── analyzer.py
   │   │   └── monitor.py
   │   ├── execution/
   │   │   ├── __init__.py
   │   │   ├── validator.py
   │   │   ├── executor.py
   │   │   └── position_tracker.py
   │   ├── dashboard/
   │   │   ├── __init__.py
   │   │   ├── app.py
   │   │   ├── components/
   │   │   └── callbacks/
   │   ├── pipeline/
   │   │   ├── __init__.py
   │   │   └── pipeline_manager.py
   │   └── main.py
   ├── config/
   │   ├── trading_params.yaml
   │   └── system_config.yaml
   ├── data/
   │   ├── historical/
   │   └── cache/
   ├── logs/
   ├── tests/
   │   ├── __init__.py
   │   ├── test_indicators.py
   │   ├── test_screening.py
   │   └── test_execution.py
   └── scripts/
       ├── setup_database.py
       ├── download_historical.py
       └── backtest.py
   ```

3. **Create requirements.txt** (from Document 00):
   ```
   ib-insync>=0.9.86
   pandas>=2.0.0
   numpy>=1.24.0
   polars>=0.19.0
   pyarrow>=13.0.0
   ta-lib>=0.4.28
   pandas-ta>=0.3.14
   dash>=2.14.0
   plotly>=5.17.0
   dash-bootstrap-components>=1.5.0
   sqlalchemy>=2.0.0
   psycopg2-binary>=2.9.9
   loguru>=0.7.0
   python-dotenv>=1.0.0
   schedule>=1.2.0
   pytest>=7.4.0
   pyyaml>=6.0
   ```

4. **Create .env.example**:
   ```bash
   # Interactive Brokers
   IB_HOST=127.0.0.1
   IB_PORT=7497
   IB_CLIENT_ID=1
   
   # Database
   DB_TYPE=sqlite
   DB_PATH=data/trading.db
   # DB_TYPE=postgresql
   # DB_HOST=localhost
   # DB_PORT=5432
   # DB_NAME=trading_system
   # DB_USER=trader
   # DB_PASSWORD=
   
   # Paths
   DATA_DIR=./data
   CONFIG_DIR=./config
   LOG_DIR=./logs
   
   # System
   MAX_WORKERS=8
   ENABLE_PAPER_TRADING=True
   ```

5. **Create .gitignore**:
   ```
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .Python
   env/
   venv/
   
   # Environment
   .env
   
   # Data
   data/historical/
   data/cache/
   *.parquet
   *.db
   
   # Logs
   logs/
   *.log
   
   # IDE
   .vscode/
   .idea/
   *.swp
   
   # OS
   .DS_Store
   Thumbs.db
   ```

6. **Initial commit**:
   ```bash
   git add .
   git commit -m "Initial project structure"
   git push -u origin main
   ```

**Deliverables for Phase 1:**
- [ ] Project structure created
- [ ] Dependencies documented in requirements.txt
- [ ] Environment configuration templated
- [ ] Git repository initialized and pushed to GitHub
- [ ] README.md with setup instructions

---

### Phase 2: Data Infrastructure Layer

**Objective:** Implement data fetching, storage, and indicator calculation components.

**Reference Documents:**
- Document 08: Data Pipeline and Infrastructure
- Document 00: System Requirements

**Tasks:**

1. **Implement `src/data/ib_manager.py`** (from Document 08):
   - `IBConnectionConfig` dataclass
   - `IBDataManager` class with connection management
   - `fetch_historical_bars()` method
   - `subscribe_realtime_bars()` method
   - Error handling and reconnection logic

2. **Implement `src/data/historical_manager.py`** (from Document 08):
   - `HistoricalDataManager` class
   - `save_bars()` - Write to Parquet
   - `load_bars()` - Read from Parquet
   - `update_historical_data()` - Merge new with existing
   - Directory structure management

3. **Implement `src/data/realtime_aggregator.py`** (from Document 08):
   - `RealtimeBarAggregator` class
   - `add_bar()` - Process 5-second bars
   - `_aggregate_to_timeframe()` - Convert to 1min, 15min, etc.
   - `get_bars()` - Retrieve aggregated data

4. **Implement `src/indicators/calculator.py`** (from Document 08):
   - `IndicatorEngine` class
   - `calculate_all_indicators()` - BB, StochRSI, MACD, RSI, ATR
   - Use TA-Lib for calculations
   - Return DataFrame with all indicators

5. **Implement `src/indicators/accumulation.py`** (from Document 05):
   - `detect_stoch_buy_signal()` - Stoch RSI oversold crosses
   - `detect_rsi_buy_signal()` - RSI oversold recoveries
   - `calculate_accumulation_ratio()` - Signal frequency ratio
   - `classify_accumulation_phase()` - Phase determination
   - `calculate_accumulation_score()` - 0-18 point scoring

6. **Implement `src/indicators/cache.py`** (from Document 08):
   - `IndicatorCache` class
   - In-memory caching with TTL
   - Cache invalidation methods

7. **Create `scripts/download_historical.py`**:
   - Bulk download script for universe
   - Rate limiting (0.5s between requests)
   - Progress tracking with tqdm
   - Error handling and retry logic

8. **Create `scripts/setup_database.py`**:
   - Database schema creation (from Document 05, 06, 09)
   - Tables: trades, watchlist_realtime, regime_snapshots, etc.
   - Indexes for performance

**Testing Requirements:**
- Unit tests for indicator calculations (compare to known values)
- Test IB connection (mock or paper account)
- Test Parquet read/write
- Test accumulation ratio calculation

**Deliverables for Phase 2:**
- [ ] IB integration functional
- [ ] Historical data management working
- [ ] Real-time bar aggregation implemented
- [ ] All indicators calculating correctly
- [ ] Accumulation ratio analysis functional
- [ ] Database schema deployed
- [ ] Tests passing
- [ ] Git commit: "Phase 2: Data infrastructure complete"

---

### Phase 3: Screening and Scoring System

**Objective:** Implement universe screening, SABR20 scoring, and watchlist generation.

**Reference Documents:**
- Document 04: Universe and Prescreening
- Document 05: Watchlist Generation and Scoring

**Tasks:**

1. **Implement `src/screening/universe.py`** (from Document 04):
   - `fetch_sp500_components()`
   - `fetch_nasdaq100_components()`
   - `build_base_universe()` - Combine indices
   - `apply_quality_filters()` - Price, volume, spread filters
   - `update_universe_job()` - Scheduled daily update

2. **Implement `src/screening/coarse_filter.py`** (from Document 04):
   - `calculate_coarse_indicators()` - 1-hour indicators
   - `coarse_filter()` - Fast screening logic
   - `screen_single_symbol()` - Process one symbol
   - `screen_universe_parallel()` - Parallel processing
   - `calculate_preliminary_score()` - 0-100 ranking

3. **Implement `src/screening/sabr_scorer.py`** (from Document 05):
   - `SABR20Score` dataclass
   - `calculate_setup_strength()` - Component 1 (0-30 pts)
   - `calculate_bottom_phase()` - Component 2 (0-22 pts)
   - `calculate_accumulation_intensity()` - Component 3 (0-18 pts) **NEW**
   - `calculate_trend_momentum()` - Component 4 (0-18 pts)
   - `calculate_risk_reward()` - Component 5 (0-10 pts)
   - `calculate_volume_profile()` - Component 6 (0-2 pts)
   - `calculate_sabr20_score()` - Main scoring function
   - `classify_bottom_state()` - State determination

4. **Implement `src/screening/watchlist.py`** (from Document 05):
   - `run_multiframe_analysis()` - Full multi-TF analysis
   - `classify_setup()` - A+/A/B/C grading
   - `generate_actionable_watchlist()` - Filter to tradeable setups
   - `save_watchlist_snapshot()` - Database storage

**Testing Requirements:**
- Test universe construction (verify symbol counts)
- Test coarse filter performance (<30s for 1000 symbols)
- Test SABR20 calculations (verify scoring ranges)
- Test accumulation ratio on known patterns
- Integration test: full screening pipeline

**Deliverables for Phase 3:**
- [ ] Universe construction functional
- [ ] Coarse screening processing 1000+ symbols in <30s
- [ ] SABR20 scoring with accumulation analysis working
- [ ] Watchlist generation producing ranked results
- [ ] All components tested
- [ ] Git commit: "Phase 3: Screening and scoring complete"

---

### Phase 4: Market Regime Analysis

**Objective:** Implement market environment assessment and position sizing adjustments.

**Reference Documents:**
- Document 06: Regime and Market Checks

**Tasks:**

1. **Implement `src/regime/analyzer.py`** (from Document 06):
   - `IndexTrend` dataclass
   - `VolatilityRegime` dataclass
   - `MarketBreadth` dataclass
   - `MarketEnvironment` dataclass
   - `classify_index_trend()` - Trend for SPY/QQQ/IWM/DIA
   - `calculate_market_trend_consensus()` - Multi-index consensus
   - `classify_volatility_regime()` - VIX analysis
   - `calculate_index_correlation()` - Cross-index correlation
   - `calculate_market_breadth()` - A/D, new highs/lows
   - `assess_market_environment()` - Complete regime assessment

2. **Implement `src/regime/monitor.py`** (from Document 06):
   - `RegimeMonitor` class
   - `update()` - Refresh regime assessment
   - `get_current()` - Return cached regime
   - `save_to_db()` - Persist to database
   - `check_regime_change()` - Alert on significant changes

3. **Create regime-based filters**:
   - `filter_watchlist_by_regime()` - Apply regime filters
   - `calculate_position_size_with_regime()` - Adjust sizes

**Testing Requirements:**
- Test VIX classification across regimes
- Test trend consensus calculation
- Test regime state transitions
- Verify position size adjustments

**Deliverables for Phase 4:**
- [ ] Regime analysis functional
- [ ] VIX monitoring working
- [ ] Trend consensus calculating
- [ ] Position sizing adjusting based on regime
- [ ] Tests passing
- [ ] Git commit: "Phase 4: Regime analysis complete"

---

### Phase 5: Dashboard and Visualization

**Objective:** Build real-time web dashboard for monitoring and analysis.

**Reference Documents:**
- Document 07: Real-Time Dashboard Specification

**Tasks:**

1. **Implement `src/dashboard/app.py`** (from Document 07):
   - Initialize Dash app with Bootstrap theme
   - Create main layout with grid structure
   - Set up interval components for updates
   - Configure callbacks

2. **Implement `src/dashboard/components/header.py`**:
   - `create_header()` - Clock, connection, regime indicator

3. **Implement `src/dashboard/components/regime_panel.py`**:
   - `create_regime_panel()` - VIX, trend, breadth display
   - Real-time metric updates

4. **Implement `src/dashboard/components/watchlist_table.py`**:
   - `create_watchlist_table()` - Interactive DataTable
   - Columns: Symbol, SABR20, Grade, State, **Acc Phase**, **Acc Ratio**, etc.
   - Conditional formatting for scores and phases
   - Click handlers for symbol selection

5. **Implement `src/dashboard/components/charts.py`**:
   - `create_multi_tf_chart()` - Multi-panel chart
   - Candlesticks + Bollinger Bands
   - Stoch RSI panel
   - MACD panel
   - Volume panel
   - `create_chart_tabs()` - 15m/1h/4h tabs
   - **Optional:** `create_accumulation_panel()` - Ratio visualization

6. **Implement `src/dashboard/components/positions.py`**:
   - `create_positions_panel()` - Active positions display
   - `create_position_card()` - Individual position details
   - P&L tracking

7. **Implement `src/dashboard/components/alerts.py`**:
   - `create_alerts_panel()` - Recent alerts
   - `create_alert_item()` - Individual alert formatting

8. **Implement `src/dashboard/callbacks/updates.py`**:
   - `update_watchlist()` - Refresh every 15s
   - `update_charts()` - On symbol selection or 1min timer
   - `update_regime_indicator()` - Every 30min
   - `update_positions()` - Every 5s

**Testing Requirements:**
- Test dashboard renders without errors
- Test all callbacks execute
- Test data updates in real-time
- Verify chart interactions
- Performance test (page load <2s)

**Deliverables for Phase 5:**
- [ ] Dashboard accessible at localhost:8050
- [ ] All panels rendering correctly
- [ ] Real-time updates working
- [ ] Charts interactive and responsive
- [ ] Accumulation phase displayed in watchlist
- [ ] Git commit: "Phase 5: Dashboard complete"

---

### Phase 6: Trade Execution and Risk Management

**Objective:** Implement order execution, position tracking, and risk controls.

**Reference Documents:**
- Document 09: Execution and Monitoring
- Document 02: Mean Reversion Trend System

**Tasks:**

1. **Implement `src/execution/validator.py`** (from Document 09):
   - `TradeValidation` dataclass
   - `RiskValidator` class
   - `validate_trade()` - Pre-trade checks
   - Enforce: max risk per trade, total risk, position limits, R:R minimums

2. **Implement `src/execution/executor.py`** (from Document 09):
   - `OrderExecutor` class
   - `place_bracket_order()` - Entry + stop + target
   - `place_market_order()` - Simple market orders
   - `cancel_order()` - Cancel pending
   - `modify_stop()` - Trail stops

3. **Implement `src/execution/position_tracker.py`** (from Document 09):
   - `Position` dataclass
   - `PositionTracker` class
   - `add_position()` - Record new position
   - `update_position()` - Update with current price
   - `remove_position()` - Close and archive
   - `get_total_unrealized_pnl()`
   - `get_total_risk_exposure()`

4. **Implement trade flow functions** (from Document 09):
   - `execute_trade_from_watchlist()` - Complete execution flow
   - `record_trade_entry()` - Database logging
   - `record_trade_exit()` - Update with exit info

5. **Implement exit management**:
   - `check_and_update_trailing_stops()` - Trail logic
   - `check_time_based_exits()` - Close before market close

6. **Implement performance tracking**:
   - `PerformanceAnalyzer` class
   - `calculate_daily_metrics()` - Win rate, avg R, etc.
   - `generate_equity_curve()` - Cumulative P&L
   - `calculate_sharpe_ratio()`

**Testing Requirements:**
- Test risk validation (reject invalid trades)
- Test order placement (paper account)
- Test position tracking updates
- Test trailing stop logic
- Verify performance calculations

**Deliverables for Phase 6:**
- [ ] Risk validation preventing bad trades
- [ ] Bracket orders executing correctly
- [ ] Positions tracked in real-time
- [ ] Trailing stops updating
- [ ] Performance metrics calculating
- [ ] Trade journal recording
- [ ] Git commit: "Phase 6: Execution engine complete"

---

### Phase 7: Pipeline Orchestration and Main System

**Objective:** Integrate all components into cohesive automated system.

**Reference Documents:**
- Document 08: Data Pipeline
- Document 09: Execution and Monitoring

**Tasks:**

1. **Implement `src/pipeline/pipeline_manager.py`** (from Document 08):
   - `DataPipelineManager` class
   - `start()` - Initialize all components
   - `stop()` - Graceful shutdown
   - `_schedule_jobs()` - Set up scheduled tasks
   - `_update_historical_job()` - Pre-market data update
   - `_update_subscriptions_job()` - Real-time subscriptions
   - `_save_realtime_data_job()` - Post-market save

2. **Implement `src/main.py`** (from Document 09):
   - `TradingSystem` class
   - `start()` - Complete system startup
   - `run_main_loop()` - Main execution loop
   - `stop()` - Graceful shutdown
   - Signal handlers (Ctrl+C)

3. **Implement scheduled jobs**:
   - Pre-market (6:00 AM): Update universe and historical data
   - Pre-market (7:00 AM): Run comprehensive screening
   - Intraday (every 30min): Update coarse screening
   - Intraday (every 15min): Update watchlist
   - Intraday (every 5sec): Update positions
   - Intraday (every 1min): Check trailing stops
   - Post-market (4:30 PM): Save data, generate reports

4. **Create `config/trading_params.yaml`** (from Document 00):
   - Universe parameters
   - Timeframe definitions
   - Indicator parameters
   - Risk limits
   - Threshold values

5. **Create `config/system_config.yaml`**:
   - IB connection settings
   - Database configuration
   - Logging configuration
   - Performance parameters

**Testing Requirements:**
- Integration test: full system startup
- Test scheduled jobs execute
- Test graceful shutdown
- Test error recovery
- Load test: sustained operation

**Deliverables for Phase 7:**
- [ ] Pipeline manager orchestrating all components
- [ ] Main system integrating all modules
- [ ] Scheduled jobs running automatically
- [ ] Configuration files complete
- [ ] Error handling robust
- [ ] Git commit: "Phase 7: System integration complete"

---

### Phase 8: Testing, Documentation, and Deployment

**Objective:** Comprehensive testing, documentation, and production deployment preparation.

**Tasks:**

1. **Unit Tests** (`tests/`):
   - `test_indicators.py` - All indicator calculations
   - `test_accumulation.py` - Accumulation ratio logic
   - `test_screening.py` - Coarse and fine screening
   - `test_sabr_scoring.py` - SABR20 score components
   - `test_regime.py` - Regime classification
   - `test_execution.py` - Order validation and placement
   - Target: >80% code coverage

2. **Integration Tests**:
   - End-to-end screening pipeline
   - Dashboard rendering and updates
   - Trade execution flow
   - Data pipeline operation

3. **Performance Tests**:
   - Screening speed (must process 1000 symbols in <30s)
   - Dashboard responsiveness (<500ms updates)
   - Database query performance (<100ms)
   - Memory stability over 24 hours

4. **Update Documentation**:
   - README.md with complete setup instructions
   - API documentation (docstrings)
   - Configuration guide
   - Troubleshooting guide
   - Example usage

5. **Paper Trading Validation** (1 week minimum):
   - Run system on paper account
   - Monitor for errors
   - Validate signals match visual analysis
   - Verify P&L calculations
   - Document any issues

6. **Production Deployment Checklist**:
   - [ ] All tests passing
   - [ ] Paper trading validated
   - [ ] Database backups configured
   - [ ] Monitoring alerts set up
   - [ ] Error logging comprehensive
   - [ ] Risk parameters conservative
   - [ ] Emergency shutdown procedure documented

**Deliverables for Phase 8:**
- [ ] Test suite with >80% coverage
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Paper trading successful (1 week)
- [ ] Production deployment ready
- [ ] Git tag: "v1.0.0-production-ready"

---

## 🔧 Development Best Practices

### Code Quality Standards

1. **Type Hints**: Use type hints for all function signatures
   ```python
   def calculate_sabr20_score(
       data_15m: pd.DataFrame,
       data_1h: pd.DataFrame,
       data_4h: pd.DataFrame
   ) -> SABR20Score:
   ```

2. **Docstrings**: Google-style docstrings for all functions
   ```python
   def calculate_accumulation_ratio(df: pd.DataFrame, window: int = 50) -> pd.Series:
       """
       Calculate Stoch/RSI signal ratio over sliding window.
       
       Parameters:
       -----------
       df : pd.DataFrame
           OHLCV data with indicators
       window : int
           Lookback period (default: 50)
       
       Returns:
       --------
       pd.Series : Accumulation ratio
       """
   ```

3. **Error Handling**: Comprehensive try-except blocks with logging
   ```python
   try:
       data = ib_manager.fetch_historical_bars(symbol, '15 mins', '5 D')
   except ConnectionError as e:
       logger.error(f"IB connection failed for {symbol}: {e}")
       return None
   except Exception as e:
       logger.error(f"Unexpected error fetching {symbol}: {e}")
       return None
   ```

4. **Logging**: Use loguru for structured logging
   ```python
   logger.info(f"Screening {len(symbols)} symbols")
   logger.warning(f"Low data quality for {symbol}")
   logger.error(f"Failed to calculate indicators: {e}")
   ```

5. **Configuration**: Use environment variables and YAML for configuration
   - Never hardcode credentials
   - Use .env for secrets
   - Use YAML for parameters

### Git Workflow

1. **Branches**:
   - `main` - Production-ready code
   - `develop` - Integration branch
   - `feature/xyz` - Feature branches
   - `hotfix/xyz` - Emergency fixes

2. **Commit Messages**:
   ```
   feat: Add accumulation ratio analysis to SABR20
   fix: Correct Stoch RSI signal detection logic
   docs: Update README with installation steps
   test: Add unit tests for indicator calculations
   refactor: Optimize coarse screening performance
   ```

3. **Pull Requests**:
   - Create PR for each phase
   - Include description of changes
   - Link to relevant PRD document
   - Require tests to pass

### Testing Strategy

1. **Unit Tests**: Test individual functions in isolation
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Verify speed and memory requirements
4. **End-to-End Tests**: Test complete workflows
5. **Paper Trading**: Real-world validation

---

## 📊 Success Metrics

### System Performance

- [ ] Screen 1000 symbols in <30 seconds
- [ ] Dashboard updates in <500ms
- [ ] Database queries <100ms average
- [ ] 99.5% uptime during market hours
- [ ] Zero data loss

### Trading Performance (Paper Trading)

- [ ] Win rate: 45-60% (target from PRDs)
- [ ] Average R-multiple: >1.5
- [ ] Profit factor: >1.5
- [ ] Max drawdown: <15%
- [ ] Signal accuracy: >70% (A+ setups)

### Code Quality

- [ ] Test coverage >80%
- [ ] Zero critical bugs in production
- [ ] All type hints present
- [ ] All functions documented
- [ ] Passes linting (flake8, mypy)

---

## 🚨 Critical Implementation Notes

### Must Read Before Coding

1. **Accumulation Ratio** (Document 05):
   - This is the NEW component added to SABR20
   - Component 3: 0-18 points
   - Calculates Stoch/RSI signal frequency ratio
   - Detects institutional accumulation before breakout
   - **This is critical** - carefully implement signal detection functions

2. **Risk Management** (Document 09):
   - Never exceed 1% risk per trade
   - Never exceed 3% total portfolio risk
   - Always validate trades before execution
   - Implement hard stops immediately on entry

3. **IB API** (Document 08):
   - Respect rate limits (0.5s between requests)
   - Handle disconnections gracefully
   - Never place live orders in testing
   - Use paper trading account initially

4. **Data Integrity** (Document 08):
   - Validate all data before processing
   - Handle missing bars
   - Check for duplicate timestamps
   - Backup database daily

5. **Performance** (Document 00):
   - Use parallel processing for screening
   - Cache indicator calculations
   - Optimize database queries
   - Profile bottlenecks

---

## 🎯 Quick Start Command Sequence

Once you're ready to begin implementation:

```bash
# 1. Clone and setup
git clone <GITHUB_REPO_URL>
cd trading-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your IB credentials

# 3. Setup database
python scripts/setup_database.py

# 4. Download historical data (optional - takes time)
python scripts/download_historical.py

# 5. Run tests
pytest tests/

# 6. Start dashboard
python src/dashboard/app.py

# 7. Start system (separate terminal)
python src/main.py
```

---

## 📞 Getting Help

If you encounter issues during implementation:

1. **Check PRD Documents**: All specifications are detailed in docs/
2. **Review Code Examples**: PRDs contain working code snippets
3. **Check Test Files**: Look at test cases for usage examples
4. **IB API Issues**: Check https://ib-insync.readthedocs.io/
5. **TA-Lib Issues**: Check https://ta-lib.org/

---

## ✅ Final Checklist Before Production

- [ ] All phases complete (1-8)
- [ ] All tests passing
- [ ] Paper trading validated (1+ week)
- [ ] Documentation complete
- [ ] Monitoring and alerts configured
- [ ] Backup systems in place
- [ ] Risk parameters reviewed
- [ ] Emergency procedures documented
- [ ] Code reviewed by second person
- [ ] Performance benchmarks met

---

## 🎓 Learning Resources

- **IB API**: https://interactivebrokers.github.io/tws-api/
- **ib_insync**: https://ib-insync.readthedocs.io/
- **TA-Lib**: https://mrjbq7.github.io/ta-lib/
- **Dash**: https://dash.plotly.com/
- **Pandas**: https://pandas.pydata.org/docs/

---

**Remember:** This is a complex system. Take it one phase at a time. Read the PRD documents thoroughly. Test extensively. Start with paper trading. Never risk real capital until the system is fully validated.

Good luck! 🚀
