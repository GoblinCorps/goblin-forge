# Data Pipeline and Infrastructure
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Overview

This document specifies the data flow architecture, historical data management, real-time ingestion, indicator calculations, and caching strategies that power the trading system.

**Data Flow:**
```
IB Market Data → Real-Time Processor → Indicator Engine → 
  → Screening Pipeline → Watchlist Generator → Dashboard
                    ↓
                Historical Database
```

---

## 2. Data Sources and Connectivity

### 2.1 Interactive Brokers Integration

```python
from ib_insync import *
import asyncio
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class IBConnectionConfig:
    """IB connection configuration."""
    host: str = '127.0.0.1'
    port: int = 7497  # TWS paper: 7497, live: 7496, Gateway: 4001/4002
    client_id: int = 1
    timeout: int = 20
    readonly: bool = False

class IBDataManager:
    """Manage IB connection and data requests."""
    
    def __init__(self, config: IBConnectionConfig):
        self.config = config
        self.ib = IB()
        self.connected = False
        
    def connect(self):
        """Establish connection to IB."""
        try:
            self.ib.connect(
                self.config.host,
                self.config.port,
                clientId=self.config.client_id,
                timeout=self.config.timeout,
                readonly=self.config.readonly
            )
            self.connected = True
            logger.info(f"Connected to IB at {self.config.host}:{self.config.port}")
            
            # Set up error handler
            self.ib.errorEvent += self.on_error
            
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            self.connected = False
            raise
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IB")
    
    def on_error(self, reqId, errorCode, errorString, contract):
        """Handle IB errors."""
        logger.error(f"IB Error {errorCode}: {errorString}")
    
    def fetch_historical_bars(
        self,
        symbol: str,
        bar_size: str,
        duration: str,
        what_to_show: str = 'TRADES'
    ) -> pd.DataFrame:
        """
        Fetch historical bars from IB.
        
        Parameters:
        -----------
        symbol : str
            Stock symbol
        bar_size : str
            '1 min', '5 mins', '15 mins', '1 hour', '1 day'
        duration : str
            '1 D', '1 W', '1 M', '1 Y'
        what_to_show : str
            'TRADES', 'MIDPOINT', 'BID', 'ASK'
        
        Returns:
        --------
        pd.DataFrame : OHLCV data
        """
        if not self.connected:
            raise ConnectionError("Not connected to IB")
        
        contract = Stock(symbol, 'SMART', 'USD')
        
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=True,  # Regular trading hours only
            formatDate=1,
            keepUpToDate=False
        )
        
        if not bars:
            logger.warning(f"No data received for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = util.df(bars)
        
        # Clean up columns
        df = df.rename(columns={'date': 'timestamp'})
        df = df.set_index('timestamp')
        
        return df
    
    def subscribe_realtime_bars(
        self,
        symbol: str,
        bar_size: int = 5,
        what_to_show: str = 'TRADES'
    ):
        """
        Subscribe to real-time 5-second bars.
        
        Parameters:
        -----------
        symbol : str
            Stock symbol
        bar_size : int
            Must be 5 (IB limitation)
        what_to_show : str
            'TRADES', 'MIDPOINT', 'BID', 'ASK'
        
        Returns:
        --------
        RealTimeBarsList : Streaming bars object
        """
        contract = Stock(symbol, 'SMART', 'USD')
        
        bars = self.ib.reqRealTimeBars(
            contract,
            barSize=bar_size,
            whatToShow=what_to_show,
            useRTH=True
        )
        
        # Set up update handler
        bars.updateEvent += lambda bars: self.on_realtime_bar(symbol, bars)
        
        return bars
    
    def on_realtime_bar(self, symbol: str, bars):
        """Handle incoming real-time bar."""
        latest_bar = bars[-1]
        logger.debug(f"{symbol}: {latest_bar}")
        
        # Push to real-time processor
        # Implementation in Real-Time Processor section

# Global instance
ib_manager = IBDataManager(IBConnectionConfig())
```

---

## 3. Historical Data Management

### 3.1 Storage Schema

**Directory Structure:**
```
data/
├── historical/
│   ├── stocks/
│   │   ├── AAPL/
│   │   │   ├── 1min.parquet
│   │   │   ├── 5min.parquet
│   │   │   ├── 15min.parquet
│   │   │   ├── 1hour.parquet
│   │   │   └── 1day.parquet
│   │   ├── TSLA/
│   │   └── ...
│   └── indices/
│       ├── SPY/
│       ├── QQQ/
│       └── VIX/
└── cache/
    └── indicators/
```

### 3.2 Historical Data Loader

```python
import pyarrow.parquet as pq
from pathlib import Path

class HistoricalDataManager:
    """Manage historical data storage and retrieval."""
    
    def __init__(self, data_dir: str = './data/historical'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_bars(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """
        Save historical bars to parquet.
        
        Parameters:
        -----------
        symbol : str
            Stock symbol
        timeframe : str
            '1min', '5min', '15min', '1hour', '1day'
        df : pd.DataFrame
            OHLCV data with timestamp index
        """
        symbol_dir = self.data_dir / 'stocks' / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = symbol_dir / f"{timeframe}.parquet"
        
        # Convert index to column for parquet
        df_copy = df.reset_index()
        
        # Write to parquet with compression
        df_copy.to_parquet(
            filepath,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        logger.info(f"Saved {len(df)} bars for {symbol} {timeframe} to {filepath}")
    
    def load_bars(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Load historical bars from parquet.
        
        Returns:
        --------
        pd.DataFrame : OHLCV data
        """
        filepath = self.data_dir / 'stocks' / symbol / f"{timeframe}.parquet"
        
        if not filepath.exists():
            logger.warning(f"No data file found: {filepath}")
            return pd.DataFrame()
        
        df = pd.read_parquet(filepath, engine='pyarrow')
        
        # Set timestamp as index
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        
        return df
    
    def update_historical_data(self, symbol: str, timeframe: str):
        """
        Update historical data with latest bars from IB.
        
        Merges new data with existing data, removing duplicates.
        """
        # Load existing data
        existing = self.load_bars(symbol, timeframe)
        
        # Fetch new data from IB
        new_data = ib_manager.fetch_historical_bars(
            symbol,
            timeframe.replace('min', ' mins'),
            '5 D'  # Fetch last 5 days
        )
        
        if new_data.empty:
            logger.warning(f"No new data for {symbol} {timeframe}")
            return
        
        # Merge
        if not existing.empty:
            combined = pd.concat([existing, new_data])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
        else:
            combined = new_data
        
        # Save
        self.save_bars(symbol, timeframe, combined)
        
        logger.info(f"Updated {symbol} {timeframe}: {len(combined)} total bars")

# Global instance
hist_manager = HistoricalDataManager()
```

### 3.3 Bulk Historical Data Download

```python
def download_historical_universe(
    symbols: List[str],
    timeframes: List[str] = ['15min', '1hour', '4hour', '1day']
):
    """
    Download historical data for entire universe.
    
    Run this during off-hours to populate/update database.
    """
    from tqdm import tqdm
    
    # Connect to IB
    ib_manager.connect()
    
    try:
        for symbol in tqdm(symbols, desc="Downloading symbols"):
            for timeframe in timeframes:
                try:
                    hist_manager.update_historical_data(symbol, timeframe)
                    
                    # Rate limiting (IB has pacing limits)
                    import time
                    time.sleep(0.5)  # 500ms between requests
                    
                except Exception as e:
                    logger.error(f"Error downloading {symbol} {timeframe}: {e}")
                    continue
    finally:
        ib_manager.disconnect()
    
    logger.info("Historical data download complete")
```

---

## 4. Real-Time Data Pipeline

### 4.1 Real-Time Bar Aggregator

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RealtimeBarAggregator:
    """
    Aggregate 5-second IB bars into higher timeframes.
    Maintains in-memory buffer of recent bars.
    """
    
    def __init__(self, buffer_size: int = 200):
        self.buffer_size = buffer_size
        self.buffers = defaultdict(lambda: defaultdict(list))  # {symbol: {timeframe: [bars]}}
        
    def add_bar(self, symbol: str, bar: dict):
        """
        Add new 5-second bar.
        
        bar format: {
            'timestamp': datetime,
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': int
        }
        """
        # Add to 1-minute buffer
        self._aggregate_to_timeframe(symbol, bar, '1min', 60)
        
        # Aggregate 1min to higher timeframes
        if len(self.buffers[symbol]['1min']) >= 15:
            self._create_15min_bar(symbol)
        
    def _aggregate_to_timeframe(
        self,
        symbol: str,
        bar: dict,
        timeframe: str,
        seconds: int
    ):
        """Aggregate 5-sec bars to target timeframe."""
        buffer = self.buffers[symbol][timeframe]
        
        if not buffer:
            # Start new bar
            buffer.append(bar.copy())
        else:
            current_bar = buffer[-1]
            
            # Check if we need new bar
            time_diff = (bar['timestamp'] - current_bar['timestamp']).total_seconds()
            
            if time_diff >= seconds:
                # Close current bar and start new one
                buffer.append(bar.copy())
                
                # Limit buffer size
                if len(buffer) > self.buffer_size:
                    buffer.pop(0)
            else:
                # Update current bar
                current_bar['high'] = max(current_bar['high'], bar['high'])
                current_bar['low'] = min(current_bar['low'], bar['low'])
                current_bar['close'] = bar['close']
                current_bar['volume'] += bar['volume']
    
    def _create_15min_bar(self, symbol: str):
        """Create 15-minute bar from 1-minute bars."""
        min_bars = self.buffers[symbol]['1min'][-15:]
        
        if len(min_bars) < 15:
            return
        
        bar_15min = {
            'timestamp': min_bars[0]['timestamp'],
            'open': min_bars[0]['open'],
            'high': max(b['high'] for b in min_bars),
            'low': min(b['low'] for b in min_bars),
            'close': min_bars[-1]['close'],
            'volume': sum(b['volume'] for b in min_bars)
        }
        
        buffer_15min = self.buffers[symbol]['15min']
        buffer_15min.append(bar_15min)
        
        if len(buffer_15min) > self.buffer_size:
            buffer_15min.pop(0)
    
    def get_bars(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        """Get recent bars for symbol and timeframe."""
        buffer = self.buffers[symbol][timeframe]
        
        # Get last N bars
        bars = buffer[-count:]
        
        if not bars:
            return pd.DataFrame()
        
        df = pd.DataFrame(bars)
        df = df.set_index('timestamp')
        
        return df

# Global instance
realtime_aggregator = RealtimeBarAggregator()
```

### 4.2 Real-Time Data Subscriber

```python
class RealtimeDataSubscriber:
    """Manage real-time subscriptions for watchlist symbols."""
    
    def __init__(self):
        self.subscriptions = {}  # {symbol: RealTimeBarsList}
        self.active_symbols = set()
    
    def subscribe_symbols(self, symbols: List[str]):
        """Subscribe to real-time data for symbols."""
        for symbol in symbols:
            if symbol not in self.active_symbols:
                self._subscribe_symbol(symbol)
    
    def _subscribe_symbol(self, symbol: str):
        """Subscribe to single symbol."""
        try:
            bars = ib_manager.subscribe_realtime_bars(symbol)
            
            # Set up handler
            bars.updateEvent += lambda bars, sym=symbol: self._on_bar_update(sym, bars)
            
            self.subscriptions[symbol] = bars
            self.active_symbols.add(symbol)
            
            logger.info(f"Subscribed to real-time data: {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {symbol}: {e}")
    
    def _on_bar_update(self, symbol: str, bars):
        """Handle real-time bar update."""
        latest = bars[-1]
        
        # Convert to dict
        bar_dict = {
            'timestamp': latest.time,
            'open': latest.open_,
            'high': latest.high,
            'low': latest.low,
            'close': latest.close,
            'volume': latest.volume
        }
        
        # Feed to aggregator
        realtime_aggregator.add_bar(symbol, bar_dict)
    
    def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from symbol."""
        if symbol in self.subscriptions:
            self.ib.cancelRealTimeBars(self.subscriptions[symbol])
            del self.subscriptions[symbol]
            self.active_symbols.remove(symbol)
            logger.info(f"Unsubscribed from {symbol}")
    
    def update_subscriptions(self, new_watchlist: List[str]):
        """Update subscriptions based on new watchlist."""
        new_set = set(new_watchlist)
        current_set = self.active_symbols
        
        # Unsubscribe from symbols no longer on watchlist
        to_remove = current_set - new_set
        for symbol in to_remove:
            self.unsubscribe_symbol(symbol)
        
        # Subscribe to new symbols
        to_add = new_set - current_set
        self.subscribe_symbols(list(to_add))

# Global instance
realtime_subscriber = RealtimeDataSubscriber()
```

---

## 5. Indicator Calculation Engine

### 5.1 Indicator Calculator

```python
import talib as ta
from typing import Optional

class IndicatorEngine:
    """Calculate technical indicators using TA-Lib."""
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate full indicator suite.
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        
        Returns:
        --------
        pd.DataFrame : Original data + indicators
        """
        if len(df) < 50:
            logger.warning("Insufficient data for indicators")
            return df
        
        df = df.copy()
        
        # Bollinger Bands
        df['bb_upper'], df['bb_mid'], df['bb_lower'] = ta.BBANDS(
            df['close'],
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2,
            matype=0
        )
        
        # Stochastic RSI
        rsi = ta.RSI(df['close'], timeperiod=14)
        df['stoch_k'], df['stoch_d'] = ta.STOCH(
            rsi, rsi, rsi,
            fastk_period=14,
            slowk_period=3,
            slowk_matype=0,
            slowd_period=3,
            slowd_matype=0
        )
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = ta.MACD(
            df['close'],
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        
        # RSI
        df['rsi'] = ta.RSI(df['close'], timeperiod=14)
        
        # ATR
        df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # SMAs for trend analysis
        df['sma_20'] = ta.SMA(df['close'], timeperiod=20)
        df['sma_50'] = ta.SMA(df['close'], timeperiod=50)
        df['sma_200'] = ta.SMA(df['close'], timeperiod=200)
        
        return df
    
    @staticmethod
    def calculate_indicators_cached(
        symbol: str,
        timeframe: str,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Calculate indicators with caching.
        
        Returns cached results if available and recent.
        """
        cache_key = f"{symbol}_{timeframe}"
        
        # Check cache
        if not force_refresh:
            cached = indicator_cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Load historical data
        df = hist_manager.load_bars(symbol, timeframe)
        
        if df.empty:
            logger.warning(f"No data for {symbol} {timeframe}")
            return df
        
        # Calculate indicators
        df = IndicatorEngine.calculate_all_indicators(df)
        
        # Cache result
        indicator_cache.set(cache_key, df)
        
        return df

# Simple in-memory cache
class IndicatorCache:
    """Simple cache for indicator calculations."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get cached data if available and fresh."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return data
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, data: pd.DataFrame):
        """Cache data with timestamp."""
        self.cache[key] = (data, datetime.now())
    
    def clear(self):
        """Clear all cached data."""
        self.cache.clear()

indicator_cache = IndicatorCache(ttl_seconds=3600)
```

---

## 6. Data Pipeline Orchestration

### 6.1 Pipeline Manager

```python
import schedule
import threading

class DataPipelineManager:
    """Orchestrate all data pipeline operations."""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start all pipeline jobs."""
        logger.info("Starting data pipeline")
        
        # Connect to IB
        ib_manager.connect()
        
        # Schedule jobs
        self._schedule_jobs()
        
        # Start scheduler thread
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.start()
        
        logger.info("Data pipeline started")
    
    def stop(self):
        """Stop pipeline."""
        logger.info("Stopping data pipeline")
        self.running = False
        
        if self.thread:
            self.thread.join()
        
        ib_manager.disconnect()
    
    def _schedule_jobs(self):
        """Schedule all recurring jobs."""
        # Pre-market: Update historical data
        schedule.every().day.at("06:00").do(self._update_historical_job)
        
        # Every hour during market: Update watchlist subscriptions
        for hour in range(9, 16):
            schedule.every().day.at(f"{hour:02d}:00").do(self._update_subscriptions_job)
        
        # Post-market: Save real-time data
        schedule.every().day.at("16:30").do(self._save_realtime_data_job)
    
    def _run_scheduler(self):
        """Run scheduler loop."""
        while self.running:
            schedule.run_pending()
            import time
            time.sleep(1)
    
    def _update_historical_job(self):
        """Update historical data for universe."""
        universe = load_current_universe()
        
        for symbol in universe:
            try:
                for tf in ['15min', '1hour', '4hour']:
                    hist_manager.update_historical_data(symbol, tf)
                    import time
                    time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")
    
    def _update_subscriptions_job(self):
        """Update real-time subscriptions based on current watchlist."""
        watchlist = fetch_current_watchlist()
        symbols = watchlist['symbol'].tolist()
        
        realtime_subscriber.update_subscriptions(symbols)
    
    def _save_realtime_data_job(self):
        """Save accumulated real-time data to historical database."""
        for symbol in realtime_subscriber.active_symbols:
            for tf in ['15min', '1hour']:
                try:
                    # Get real-time data
                    rt_data = realtime_aggregator.get_bars(symbol, tf)
                    
                    if not rt_data.empty:
                        # Load historical
                        hist = hist_manager.load_bars(symbol, tf)
                        
                        # Merge and save
                        combined = pd.concat([hist, rt_data])
                        combined = combined[~combined.index.duplicated(keep='last')]
                        
                        hist_manager.save_bars(symbol, tf, combined)
                        
                except Exception as e:
                    logger.error(f"Error saving RT data for {symbol}: {e}")

# Global instance
pipeline_manager = DataPipelineManager()
```

---

## 7. Database Operations

### 7.1 PostgreSQL Schema

```sql
-- Already defined in previous docs, adding missing tables

CREATE TABLE historical_data_metadata (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    bar_count INTEGER NOT NULL,
    last_updated TIMESTAMP NOT NULL,
    
    UNIQUE(symbol, timeframe)
);

CREATE INDEX idx_metadata_symbol ON historical_data_metadata(symbol);
CREATE INDEX idx_metadata_updated ON historical_data_metadata(last_updated DESC);
```

### 7.2 Database Manager

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

class DatabaseManager:
    """Manage database connections and operations."""
    
    def __init__(self):
        db_url = os.getenv('DATABASE_URL', 'sqlite:///data/trading.db')
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def save_screening_results(self, results: pd.DataFrame):
        """Save coarse screening results."""
        results.to_sql(
            'coarse_screening_results',
            self.engine,
            if_exists='append',
            index=False
        )
    
    def save_watchlist(self, watchlist: pd.DataFrame):
        """Save watchlist snapshot."""
        watchlist.to_sql(
            'watchlist_realtime',
            self.engine,
            if_exists='replace',  # Replace current watchlist
            index=False
        )
    
    def load_latest_watchlist(self) -> pd.DataFrame:
        """Load most recent watchlist."""
        query = "SELECT * FROM watchlist_realtime ORDER BY timestamp DESC"
        return pd.read_sql(query, self.engine)

db_manager = DatabaseManager()
```

---

## 8. Performance Optimization

### 8.1 Parallel Data Fetching

```python
from concurrent.futures import ThreadPoolExecutor

def fetch_multiple_symbols_parallel(
    symbols: List[str],
    timeframe: str,
    max_workers: int = 10
) -> Dict[str, pd.DataFrame]:
    """Fetch data for multiple symbols in parallel."""
    
    def fetch_single(symbol):
        try:
            data = ib_manager.fetch_historical_bars(symbol, timeframe, '30 D')
            return symbol, data
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return symbol, pd.DataFrame()
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_single, sym) for sym in symbols]
        
        for future in futures:
            symbol, data = future.result()
            results[symbol] = data
    
    return results
```

---

## 9. Next Document

**Document 09: Execution and Monitoring** will detail:
- Trade execution via IB API
- Order management (entry, stops, targets)
- Position tracking
- Performance metrics
- Trade journaling
