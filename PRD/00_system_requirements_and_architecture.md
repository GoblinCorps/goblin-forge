# System Requirements and Architecture
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Executive Summary

This document defines the technical requirements, system architecture, and infrastructure specifications for a professional-grade algorithmic trading system that identifies and executes mean-reversion-to-trend-expansion opportunities across multiple timeframes.

**System Objectives:**
- Automate screening of 500-2000 symbols in near-real-time
- Identify high-probability reversal setups using multi-indicator confluence
- Provide real-time monitoring dashboard with actionable intelligence
- Execute trades via Interactive Brokers with sub-second latency
- Maintain complete audit trail and performance analytics

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dashboard  │  │  Chart View  │  │   Controls   │          │
│  │   (Dash/     │  │  (Plotly/    │  │  (Actions/   │          │
│  │   Streamlit) │  │   mplfinance)│  │   Config)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Screener   │  │   Signal     │  │  Portfolio   │          │
│  │   Engine     │  │   Generator  │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Regime     │  │   Risk       │  │  Execution   │          │
│  │   Analyzer   │  │   Controller │  │   Engine     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────────┐
│                   DATA PROCESSING LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Indicator  │  │  Multi-TF    │  │   Score      │          │
│  │   Calculator │  │  Aggregator  │  │   Calculator │          │
│  │   (TA-Lib)   │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Market     │  │   Historical │  │   Signal     │          │
│  │   Data Feed  │  │   Database   │  │   Database   │          │
│  │   (IB/TWS)   │  │  (Parquet/   │  │  (SQLite/    │          │
│  │              │  │   PostgreSQL)│  │   PostgreSQL)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────────┐
│                   BROKER INTEGRATION LAYER                       │
│                  ┌──────────────────┐                            │
│                  │  ib_insync       │                            │
│                  │  TWS API 10.19+  │                            │
│                  └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Technology Stack

### 3.1 Programming Language & Core Libraries

**Python 3.10+** (required for modern async features)

**Data Processing:**
- `pandas >= 2.0.0` - Core data manipulation
- `numpy >= 1.24.0` - Numerical computing
- `polars >= 0.19.0` - High-performance alternative to pandas for large-scale screening
- `pyarrow >= 13.0.0` - Parquet file I/O

**Technical Analysis:**
- `ta-lib >= 0.4.28` - Core technical indicators (requires compiled C library)
- `pandas-ta >= 0.3.14` - Additional indicators and convenience functions

**Market Data & Execution:**
- `ib_insync >= 0.9.86` - Interactive Brokers integration
- `ibapi >= 10.19` - Native IB API (dependency of ib_insync)

**Real-Time Dashboard:**
- `dash >= 2.14.0` - Web-based dashboard framework
- `plotly >= 5.17.0` - Interactive charting
- `dash-bootstrap-components >= 1.5.0` - UI components

**Database:**
- `sqlalchemy >= 2.0.0` - Database ORM
- `psycopg2-binary >= 2.9.9` - PostgreSQL driver (production)
- `sqlite3` - Built-in Python (development/testing)

**Utilities:**
- `asyncio` - Built-in async framework
- `loguru >= 0.7.0` - Advanced logging
- `python-dotenv >= 1.0.0` - Environment configuration
- `schedule >= 1.2.0` - Task scheduling

### 3.2 Data Storage Architecture

**Historical Price Data:**
- Format: Parquet (columnar, compressed)
- Location: `data/historical/{symbol}/{timeframe}/`
- Structure: Date-partitioned for efficient queries
- Retention: 2 years minimum for backtesting

**Real-Time Data Cache:**
- In-memory: Redis or Python dict with TTL
- Purpose: Sub-second indicator calculations
- Size: Last 200 bars per symbol per timeframe

**Signal Database:**
- Engine: PostgreSQL (production) / SQLite (development)
- Tables:
  - `signals` - All generated signals with scores
  - `trades` - Executed trades with P&L
  - `performance` - Daily/weekly/monthly metrics
  - `regime_state` - Market regime classifications

**Configuration:**
- Format: YAML + environment variables
- Location: `config/`
- Version control: Git (excluding sensitive credentials)

---

## 4. System Requirements

### 4.1 Hardware Requirements

**Development Environment:**
- CPU: 4+ cores (Intel i5/AMD Ryzen 5 equivalent)
- RAM: 16 GB minimum
- Storage: 100 GB SSD
- Network: Stable broadband (10+ Mbps)

**Production Environment:**
- CPU: 8+ cores (Intel i7/AMD Ryzen 7 or cloud equivalent)
- RAM: 32 GB minimum (for full universe screening)
- Storage: 500 GB NVMe SSD (low-latency I/O)
- Network: Low-latency connection (<50ms to IB servers)

**Recommended Cloud Setup:**
- AWS: c7g.2xlarge or c6i.2xlarge
- GCP: c3-standard-8
- Azure: F8s_v2
- Region: Co-located with IB data centers (e.g., us-east-1 for North America)

### 4.2 Software Requirements

**Operating System:**
- Linux: Ubuntu 22.04 LTS (recommended for production)
- macOS: 13+ (development)
- Windows: 11 with WSL2 (development only)

**Interactive Brokers:**
- TWS (Trader Workstation) 10.19+ OR IB Gateway 10.19+
- Account: Live trading or Paper trading
- Permissions: Market data subscriptions for target exchanges
- API: Enabled in account settings

**Python Environment:**
- Virtual environment: `venv` or `conda`
- Package manager: `pip` or `poetry`

---

## 5. Pre-Flight System Checks

### 5.1 Connectivity Checks

**IB Connection Test:**
```python
from ib_insync import IB

def test_ib_connection():
    """Verify IB connection and permissions."""
    ib = IB()
    try:
        # Connect to TWS/Gateway
        ib.connect('127.0.0.1', 7497, clientId=1)  # TWS paper
        
        # Test market data
        contract = Stock('AAPL', 'SMART', 'USD')
        ib.reqMktData(contract, '', False, False)
        ib.sleep(2)
        
        # Verify data received
        ticker = ib.ticker(contract)
        assert ticker.last is not None, "No market data received"
        
        print("✓ IB connection successful")
        return True
    except Exception as e:
        print(f"✗ IB connection failed: {e}")
        return False
    finally:
        ib.disconnect()
```

**Data Integrity Check:**
```python
def check_data_availability():
    """Verify historical data completeness."""
    required_symbols = ['AAPL', 'TSLA', 'SPY']
    required_timeframes = ['15 mins', '1 hour', '4 hours']
    
    for symbol in required_symbols:
        for tf in required_timeframes:
            # Check if data exists and is recent
            # Verify no gaps in data
            pass
    
    print("✓ Historical data validated")
```

### 5.2 Performance Benchmarks

**Indicator Calculation Speed:**
- Target: Process 1000 symbols × 3 timeframes in <30 seconds
- Test with full indicator suite (BB, StochRSI, MACD, RSI)

**Database Query Performance:**
- Target: Retrieve screening results in <1 second
- Index all timestamp and symbol columns

**Dashboard Refresh Rate:**
- Target: Update all panels in <500ms
- Use async data loading and caching

---

## 6. Configuration Management

### 6.1 Environment Variables

```bash
# .env file structure
# IB Connection
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=1

# Database
DB_TYPE=postgresql  # or sqlite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_system
DB_USER=trader
DB_PASSWORD=secure_password

# Paths
DATA_DIR=./data
CONFIG_DIR=./config
LOG_DIR=./logs

# System
MAX_WORKERS=8
ENABLE_PAPER_TRADING=True
```

### 6.2 Trading Parameters Configuration

```yaml
# config/trading_params.yaml
universe:
  min_price: 1.0
  max_price: 500.0
  min_avg_volume: 500000
  excluded_exchanges: ['PINK', 'OTC']
  
timeframes:
  trigger: '15 mins'      # T1
  confirmation: '1 hour'  # T2
  regime: '4 hours'       # T3

indicators:
  bollinger_bands:
    period: 20
    std_dev: 2.0
  
  stoch_rsi:
    rsi_period: 14
    stoch_period: 14
    k_smooth: 3
    d_smooth: 3
  
  macd:
    fast: 12
    slow: 26
    signal: 9
  
  rsi:
    period: 14

thresholds:
  stoch_rsi_oversold: 20
  stoch_rsi_overbought: 80
  rsi_min: 30
  rsi_max: 60
  
risk:
  max_risk_per_trade: 0.01  # 1% of equity
  max_concurrent_risk: 0.03  # 3% total
  max_positions: 5
  min_reward_risk: 1.5
```

---

## 7. Logging and Monitoring

### 7.1 Log Structure

```python
from loguru import logger

# Configure logging
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",
    level="INFO"
)

# Log levels:
# DEBUG: Indicator calculations, data fetches
# INFO: Signals, trades, system events
# WARNING: Near-threshold conditions, data gaps
# ERROR: Execution failures, API errors
# CRITICAL: System failures requiring intervention
```

### 7.2 Health Monitoring

**System Health Metrics:**
- IB connection status (heartbeat every 60s)
- Data feed latency
- Indicator calculation time
- Memory usage
- Database connection pool status

**Alert Conditions:**
- IB disconnection
- Data feed delay >30 seconds
- Memory usage >80%
- Database errors
- Missed signals (expected vs. actual)

---

## 8. Deployment Architecture

### 8.1 Development Workflow

```
1. Local Development
   ├── VSCode/PyCharm IDE
   ├── IB Gateway (paper trading)
   ├── SQLite database
   └── Sample universe (50-100 symbols)

2. Testing
   ├── Pytest unit tests
   ├── Backtesting on historical data
   ├── Paper trading validation
   └── Performance profiling

3. Staging
   ├── Cloud instance (smaller tier)
   ├── PostgreSQL database
   ├── Extended universe (500 symbols)
   └── 1-week paper trading validation

4. Production
   ├── Production cloud instance
   ├── Live IB account
   ├── Full universe (1000-2000 symbols)
   └── Full monitoring suite
```

### 8.2 Backup and Recovery

**Data Backup:**
- Historical data: Weekly backup to S3/GCS
- Signal database: Daily backup
- Configuration: Version controlled in Git

**Disaster Recovery:**
- RTO (Recovery Time Objective): 15 minutes
- RPO (Recovery Point Objective): 1 hour
- Automated failover for critical components

---

## 9. Security Considerations

### 9.1 Credential Management

- Use environment variables or secure vault (AWS Secrets Manager)
- Never commit credentials to Git
- Rotate IB API passwords regularly
- Use read-only database users for dashboard

### 9.2 API Security

- Rate limiting on IB API calls
- Validate all external inputs
- Sanitize database queries (use ORM)
- HTTPS only for web dashboard

---

## 10. Performance Optimization

### 10.1 Computation Optimization

**Vectorization:**
- Use NumPy/Pandas vectorized operations
- Avoid Python loops for indicator calculations
- Pre-compile TA-Lib indicators

**Parallel Processing:**
```python
from concurrent.futures import ProcessPoolExecutor
from functools import partial

def screen_universe_parallel(symbols, max_workers=8):
    """Screen universe using multiprocessing."""
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        screen_func = partial(screen_single_symbol)
        results = list(executor.map(screen_func, symbols))
    return results
```

**Caching:**
- Cache indicator values for 1 bar period
- Cache screening results until next bar close
- Use Redis for distributed caching in multi-instance setup

### 10.2 Database Optimization

**Indexes:**
```sql
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_score ON signals(score DESC);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
```

**Query Optimization:**
- Use prepared statements
- Batch inserts for historical data
- Partition tables by date for large datasets

---

## 11. Testing Requirements

### 11.1 Unit Tests

- Indicator calculation accuracy (compare to known values)
- Signal generation logic
- Risk calculation functions
- Data validation functions

### 11.2 Integration Tests

- IB connection and data retrieval
- Database CRUD operations
- End-to-end screening pipeline
- Dashboard rendering

### 11.3 Performance Tests

- Screen 1000 symbols in <30 seconds
- Dashboard refresh <500ms
- Database query <100ms
- Memory usage stable over 24 hours

---

## 12. Maintenance and Operations

### 12.1 Daily Operations Checklist

**Pre-Market (30 minutes before open):**
- [ ] Verify IB connection
- [ ] Check data feed status
- [ ] Review overnight regime changes
- [ ] Validate database integrity
- [ ] Check disk space and memory

**Intraday:**
- [ ] Monitor screening pipeline
- [ ] Review generated signals
- [ ] Track open positions
- [ ] Monitor system health metrics

**Post-Market:**
- [ ] Generate daily performance report
- [ ] Backup signal database
- [ ] Review logs for errors
- [ ] Update watchlist for next session

### 12.2 Weekly Maintenance

- [ ] Review and optimize slow queries
- [ ] Analyze false signal patterns
- [ ] Update symbol universe
- [ ] Parameter sensitivity analysis
- [ ] Performance attribution review

---

## 13. Success Metrics

### 13.1 System Performance KPIs

**Reliability:**
- Uptime: >99.5% during market hours
- Data accuracy: 100% (validate against broker)
- Signal generation latency: <5 seconds from bar close

**Scalability:**
- Support 2000+ symbols without performance degradation
- Handle 10+ concurrent users on dashboard

**Operational:**
- Mean time to detect issues: <2 minutes
- Mean time to resolve issues: <15 minutes

### 13.2 Trading Performance KPIs

- Win rate (target: 45-60%)
- Profit factor (target: >1.5)
- Average R-multiple per trade (target: >1.5)
- Max drawdown (limit: <15%)
- Sharpe ratio (target: >1.0)

---

## 14. Documentation Requirements

**Code Documentation:**
- Docstrings for all functions (Google style)
- Type hints for function signatures
- README for each module

**Operational Documentation:**
- System architecture diagram (this document)
- Runbook for common issues
- Configuration guide
- Deployment guide

**Trading Documentation:**
- Algorithm specification (01_algorithm_spec.md)
- Decision tree guide (03_decision_tree_and_screening.md)
- Trade journal template

---

## 15. Next Steps

After completing system setup:

1. **Data Pipeline** → Document 08_data_pipeline_and_infrastructure.md
2. **Universe Screening** → Document 04_universe_and_prescreening.md
3. **Scoring System** → Document 05_watchlist_generation_and_scoring.md
4. **Regime Analysis** → Document 06_regime_and_market_checks.md
5. **Dashboard** → Document 07_realtime_dashboard_specification.md
6. **Execution** → Document 09_execution_and_monitoring.md

Each document will reference this architecture as the foundation.
