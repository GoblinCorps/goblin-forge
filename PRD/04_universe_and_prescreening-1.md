# Universe Definition and Pre-Screening Methodology
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Overview

This document specifies the methodology for constructing and maintaining the trading universe, applying coarse filters to identify potential reversal candidates, and feeding high-probability symbols into the fine screening pipeline.

**Objectives:**
- Define a tradeable universe of 500-2000 liquid stocks
- Filter universe daily based on fundamental liquidity criteria
- Apply coarse technical filters to identify reversal candidates
- Reduce computational load for fine multi-timeframe analysis

---

## 2. Universe Construction

### 2.1 Base Universe Selection

**Primary Sources:**
1. **S&P 500** - Large cap stability
2. **Russell 2000** - Small/mid cap volatility and momentum
3. **NASDAQ 100** - Tech-heavy high-beta names
4. **Custom additions** - High-volume stocks of interest

**Implementation:**
```python
import pandas as pd
from ib_insync import IB, Stock, Index

def fetch_sp500_components():
    """Fetch S&P 500 constituents."""
    # Method 1: From Wikipedia
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    sp500 = tables[0]
    return sp500['Symbol'].str.replace('.', '-').tolist()

def fetch_nasdaq100_components():
    """Fetch NASDAQ 100 constituents."""
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    tables = pd.read_html(url)
    nasdaq = tables[4]  # The constituents table
    return nasdaq['Ticker'].tolist()

def fetch_russell2000_high_volume():
    """
    Fetch top 500 Russell 2000 by volume.
    Note: This requires a data provider with Russell 2000 constituents.
    Alternatively, screen by market cap $300M-$10B + volume.
    """
    # Placeholder - implement with your data provider
    # Could use IB scanner or external API
    return []

def build_base_universe():
    """Construct the base universe."""
    universe = set()
    
    # Add S&P 500
    universe.update(fetch_sp500_components())
    
    # Add NASDAQ 100
    universe.update(fetch_nasdaq100_components())
    
    # Add Russell 2000 high volume
    # universe.update(fetch_russell2000_high_volume())
    
    # Remove known problematic symbols
    exclusions = {'BRK.B', 'BF.B'}  # Class B shares may have data issues
    universe = universe - exclusions
    
    return sorted(list(universe))
```

### 2.2 Universe Quality Filters

**Mandatory Filters (applied daily):**

```python
def apply_quality_filters(symbol_data: pd.DataFrame) -> pd.DataFrame:
    """
    Filter universe based on liquidity and tradability.
    
    Parameters:
    -----------
    symbol_data : pd.DataFrame
        Columns: symbol, price, avg_volume_20d, market_cap, bid_ask_spread
    
    Returns:
    --------
    pd.DataFrame : Filtered universe
    """
    filtered = symbol_data[
        # Price constraints (avoid penny stocks and too-expensive stocks)
        (symbol_data['price'] >= 1.0) & 
        (symbol_data['price'] <= 500.0) &
        
        # Volume constraints (ensure sufficient liquidity)
        (symbol_data['avg_volume_20d'] >= 500_000) &
        
        # Market cap constraints (optional, for stability)
        (symbol_data['market_cap'] >= 100_000_000) &  # $100M minimum
        
        # Spread constraints (ensure reasonable transaction costs)
        (symbol_data['bid_ask_spread_pct'] <= 0.5)  # Max 0.5% spread
    ].copy()
    
    return filtered
```

**Quality Metrics:**

| Metric | Minimum | Rationale |
|--------|---------|-----------|
| Price | $1.00 | Avoid penny stocks |
| Price | $500.00 | Avoid high-priced stocks (hard to size) |
| Avg Volume (20d) | 500K shares | Ensure fill-ability |
| Market Cap | $100M | Avoid micro-caps with manipulation risk |
| Bid-Ask Spread | <0.5% | Control transaction costs |

### 2.3 Dynamic Universe Updates

**Update Frequency:** Daily at 6:00 AM ET (before market open)

**Update Process:**
```python
import schedule
from datetime import datetime, time

def update_universe_job():
    """Daily job to refresh universe."""
    logger.info("Starting universe update")
    
    # 1. Fetch latest index constituents
    base = build_base_universe()
    
    # 2. Get current market data for filtering
    market_data = fetch_market_data_batch(base)
    
    # 3. Apply quality filters
    qualified = apply_quality_filters(market_data)
    
    # 4. Save to database
    save_universe_snapshot(qualified)
    
    # 5. Log changes
    log_universe_changes(qualified)
    
    logger.info(f"Universe updated: {len(qualified)} symbols qualified")

# Schedule daily at 6 AM ET
schedule.every().day.at("06:00").do(update_universe_job)
```

---

## 3. Coarse Pre-Screening Filters

### 3.1 Screening Philosophy

**Two-Stage Approach:**

1. **Coarse Filter (Single Timeframe)** ← THIS SECTION
   - Fast, computationally cheap
   - Run on entire universe (500-2000 symbols)
   - Goal: Reduce to 50-200 candidates
   - Based on 1-hour timeframe

2. **Fine Filter (Multi-Timeframe)** → See Document 05
   - Detailed, computationally intensive
   - Run only on coarse filter survivors
   - Goal: Identify 5-20 A+ setups
   - Based on 15m/30m (T1), 1h (T2), 4h (T3)

### 3.2 Coarse Filter Specification

**Timeframe:** 1 hour (balance between noise and timeliness)

**Indicator Requirements:**
```python
def calculate_coarse_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate minimal indicator set for coarse screening.
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLCV data with columns: open, high, low, close, volume
    
    Returns:
    --------
    pd.DataFrame : Original data + indicators
    """
    import talib as ta
    
    # Bollinger Bands
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = ta.BBANDS(
        df['close'], 
        timeperiod=20, 
        nbdevup=2, 
        nbdevdn=2
    )
    
    # Stochastic RSI
    rsi = ta.RSI(df['close'], timeperiod=14)
    df['stoch_k'], df['stoch_d'] = ta.STOCH(
        rsi, rsi, rsi,  # Use RSI as high, low, close for Stoch
        fastk_period=14,
        slowk_period=3,
        slowd_period=3
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
    
    return df
```

**Coarse Filter Conditions:**

```python
def coarse_filter(df: pd.DataFrame) -> bool:
    """
    Apply coarse filter to identify potential reversal candidates.
    
    Returns True if symbol passes coarse filter.
    """
    if len(df) < 30:
        return False
    
    current = df.iloc[-1]
    prev_1 = df.iloc[-2]
    prev_2 = df.iloc[-3]
    recent_5 = df.iloc[-5:]
    
    # ============================================
    # CONDITION 1: Price in lower half of BB range
    # ============================================
    bb_range = current['bb_upper'] - current['bb_lower']
    price_position = (current['close'] - current['bb_lower']) / bb_range
    
    # Currently in lower 60% of range OR recent touch of lower band
    lower_band_condition = (
        price_position <= 0.6 or
        (recent_5['close'] <= recent_5['bb_lower'] * 1.02).any()
    )
    
    # ============================================
    # CONDITION 2: Stoch RSI oversold to recovery
    # ============================================
    # At least one recent bar was oversold
    recent_oversold = (
        (recent_5['stoch_k'] <= 25).any() or 
        (recent_5['stoch_d'] <= 25).any()
    )
    
    # Current bar showing upward momentum but not overbought
    stoch_recovery = (
        current['stoch_k'] > prev_1['stoch_k'] and
        current['stoch_k'] < 65  # Not already extended
    )
    
    stoch_condition = recent_oversold and stoch_recovery
    
    # ============================================
    # CONDITION 3: MACD histogram bottoming/rising
    # ============================================
    # Histogram was negative and is now rising
    macd_bottoming = (
        prev_2['macd_hist'] <= prev_1['macd_hist'] and
        current['macd_hist'] >= prev_1['macd_hist']
    )
    
    # Not too far into positive territory (we want early entries)
    macd_not_extended = current['macd_hist'] < 1.0  # Adjust based on symbol
    
    macd_condition = macd_bottoming and macd_not_extended
    
    # ============================================
    # CONDITION 4: RSI in recovery zone
    # ============================================
    # RSI between 25-65 (oversold to neutral)
    # RSI rising
    rsi_condition = (
        25 <= current['rsi'] <= 65 and
        current['rsi'] >= prev_1['rsi']
    )
    
    # ============================================
    # CONDITION 5: Volume confirmation (optional)
    # ============================================
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_condition = current['volume'] >= avg_volume * 0.8
    
    # ============================================
    # FINAL VERDICT
    # ============================================
    # Must pass at least 3 of 4 primary conditions
    primary_conditions = [
        lower_band_condition,
        stoch_condition,
        macd_condition,
        rsi_condition
    ]
    
    passes_filter = sum(primary_conditions) >= 3 and volume_condition
    
    return passes_filter
```

### 3.3 Batch Screening Implementation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import time

def fetch_hourly_data_ib(symbol: str, bars: int = 100) -> pd.DataFrame:
    """
    Fetch 1-hour bars from Interactive Brokers.
    
    Parameters:
    -----------
    symbol : str
        Stock symbol
    bars : int
        Number of bars to fetch
    
    Returns:
    --------
    pd.DataFrame : OHLCV data
    """
    from ib_insync import IB, Stock, util
    
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    
    try:
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Request historical data
        bars_data = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='5 D',
            barSizeSetting='1 hour',
            whatToShow='TRADES',
            useRTH=True,  # Regular trading hours only
            formatDate=1
        )
        
        # Convert to DataFrame
        df = util.df(bars_data)
        
        if len(df) == 0:
            logger.warning(f"No data received for {symbol}")
            return pd.DataFrame()
        
        df.rename(columns={
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }, inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
    finally:
        ib.disconnect()

def screen_single_symbol(symbol: str) -> Dict:
    """
    Screen a single symbol through coarse filter.
    
    Returns:
    --------
    dict : {symbol, passed, score, data}
    """
    try:
        # Fetch data
        df = fetch_hourly_data_ib(symbol)
        
        if df.empty:
            return {'symbol': symbol, 'passed': False, 'reason': 'no_data'}
        
        # Calculate indicators
        df = calculate_coarse_indicators(df)
        
        # Apply filter
        passed = coarse_filter(df)
        
        if not passed:
            return {'symbol': symbol, 'passed': False, 'reason': 'filter_fail'}
        
        # Calculate preliminary score
        score = calculate_preliminary_score(df)
        
        return {
            'symbol': symbol,
            'passed': True,
            'score': score,
            'price': df.iloc[-1]['close'],
            'rsi': df.iloc[-1]['rsi'],
            'stoch_k': df.iloc[-1]['stoch_k'],
            'macd_hist': df.iloc[-1]['macd_hist'],
            'timestamp': pd.Timestamp.now()
        }
        
    except Exception as e:
        logger.error(f"Error screening {symbol}: {e}")
        return {'symbol': symbol, 'passed': False, 'reason': str(e)}

def screen_universe_parallel(symbols: List[str], max_workers: int = 10) -> pd.DataFrame:
    """
    Screen entire universe in parallel.
    
    Parameters:
    -----------
    symbols : List[str]
        List of symbols to screen
    max_workers : int
        Number of parallel workers
    
    Returns:
    --------
    pd.DataFrame : Screening results
    """
    results = []
    
    logger.info(f"Starting coarse screening of {len(symbols)} symbols")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(screen_single_symbol, symbol): symbol 
            for symbol in symbols
        }
        
        # Process completed tasks
        for i, future in enumerate(as_completed(future_to_symbol), 1):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
                
                if i % 50 == 0:
                    logger.info(f"Progress: {i}/{len(symbols)} symbols screened")
                    
            except Exception as e:
                logger.error(f"Exception for {symbol}: {e}")
                results.append({'symbol': symbol, 'passed': False, 'reason': str(e)})
    
    elapsed = time.time() - start_time
    logger.info(f"Coarse screening completed in {elapsed:.1f}s")
    
    # Convert to DataFrame
    df_results = pd.DataFrame(results)
    
    # Filter to only passing candidates
    candidates = df_results[df_results['passed'] == True].copy()
    
    # Sort by score
    if len(candidates) > 0:
        candidates = candidates.sort_values('score', ascending=False)
    
    logger.info(f"Found {len(candidates)} candidates passing coarse filter")
    
    return candidates
```

### 3.4 Preliminary Scoring System

```python
def calculate_preliminary_score(df: pd.DataFrame) -> float:
    """
    Calculate a preliminary score for ranking candidates.
    Higher score = more promising setup.
    
    Score components:
    1. Stoch RSI position and momentum (0-30 points)
    2. MACD histogram shape (0-30 points)
    3. RSI recovery angle (0-20 points)
    4. Bollinger position (0-20 points)
    
    Total: 0-100 points
    """
    current = df.iloc[-1]
    prev_1 = df.iloc[-2]
    prev_2 = df.iloc[-3]
    
    score = 0.0
    
    # ===== STOCH RSI SCORING (0-30) =====
    # Prefer: was deep oversold, now rising sharply
    min_recent_stoch = df.iloc[-5:]['stoch_k'].min()
    stoch_rise = current['stoch_k'] - prev_1['stoch_k']
    
    if min_recent_stoch <= 10:
        score += 15
    elif min_recent_stoch <= 20:
        score += 10
    elif min_recent_stoch <= 30:
        score += 5
    
    if stoch_rise >= 10:
        score += 15
    elif stoch_rise >= 5:
        score += 10
    elif stoch_rise >= 2:
        score += 5
    
    # ===== MACD HISTOGRAM SCORING (0-30) =====
    # Prefer: clear bottoming pattern, recently turned positive
    hist_slope_1 = current['macd_hist'] - prev_1['macd_hist']
    hist_slope_2 = prev_1['macd_hist'] - prev_2['macd_hist']
    
    # Both slopes positive = accelerating momentum
    if hist_slope_1 > 0 and hist_slope_2 > 0:
        score += 20
    elif hist_slope_1 > 0:
        score += 10
    
    # Just crossed zero (first green bar)
    if prev_1['macd_hist'] <= 0 and current['macd_hist'] > 0:
        score += 10
    
    # ===== RSI SCORING (0-20) =====
    # Prefer: RSI rising from 30-50 range (sweet spot)
    rsi_rise = current['rsi'] - prev_1['rsi']
    
    if 30 <= current['rsi'] <= 50:
        score += 10
    elif 25 <= current['rsi'] <= 55:
        score += 5
    
    if rsi_rise >= 3:
        score += 10
    elif rsi_rise >= 1:
        score += 5
    
    # ===== BOLLINGER POSITION (0-20) =====
    # Prefer: just bounced from lower band, not yet at mid
    bb_range = current['bb_upper'] - current['bb_lower']
    bb_position = (current['close'] - current['bb_lower']) / bb_range
    
    if 0.2 <= bb_position <= 0.4:  # Just off bottom
        score += 20
    elif 0.4 <= bb_position <= 0.5:  # Approaching mid
        score += 15
    elif bb_position <= 0.2:  # Still at bottom
        score += 10
    
    return round(score, 2)
```

---

## 4. Pre-Screening Schedule

### 4.1 Continuous Intraday Screening

```python
import schedule
from datetime import time as dt_time

def intraday_screening_job():
    """Run coarse screening every hour during market hours."""
    # Check if market is open
    if not is_market_open():
        logger.info("Market closed, skipping screening")
        return
    
    # Get current universe
    universe = load_current_universe()
    
    # Run coarse screening
    candidates = screen_universe_parallel(universe, max_workers=15)
    
    # Save results
    save_screening_results(candidates, timeframe='1h')
    
    # Trigger alerts for new candidates
    check_and_alert_new_candidates(candidates)
    
    logger.info(f"Hourly screening completed: {len(candidates)} candidates")

# Schedule hourly during market hours (9:30 AM - 4:00 PM ET)
for hour in range(9, 16):
    for minute in [0, 30]:  # Every 30 minutes for more frequent updates
        schedule_time = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(schedule_time).do(intraday_screening_job)
```

### 4.2 Pre-Market Screening

```python
def premarket_screening_job():
    """
    Run comprehensive screening before market open.
    Uses daily + 4h data for regime assessment.
    """
    logger.info("Starting pre-market screening")
    
    # Update universe
    update_universe_job()
    
    # Get fresh universe
    universe = load_current_universe()
    
    # Run screening on 4h timeframe (more stable for pre-market)
    candidates_4h = screen_universe_4h(universe)
    
    # Save as pre-market watchlist
    save_premarket_watchlist(candidates_4h)
    
    # Generate morning report
    generate_daily_report(candidates_4h)
    
    logger.info("Pre-market screening completed")

# Schedule at 7:00 AM ET (before market open)
schedule.every().day.at("07:00").do(premarket_screening_job)
```

---

## 5. Data Management for Screening

### 5.1 Data Caching Strategy

**Cache Structure:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class ScreeningDataCache:
    """Manage screening data with intelligent caching."""
    
    def __init__(self, cache_duration_minutes: int = 60):
        self.cache = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Get cached data or fetch fresh."""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            
            # Check if cache is still valid
            if datetime.now() - timestamp < self.cache_duration:
                return data
        
        # Fetch fresh data
        fresh_data = fetch_hourly_data_ib(symbol)
        self.cache[cache_key] = (fresh_data, datetime.now())
        
        return fresh_data
    
    def invalidate(self, symbol: str = None):
        """Invalidate cache for symbol or all."""
        if symbol:
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()

# Global instance
data_cache = ScreeningDataCache(cache_duration_minutes=60)
```

### 5.2 Database Schema for Screening Results

```sql
CREATE TABLE coarse_screening_results (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    passed BOOLEAN NOT NULL,
    score DECIMAL(5,2),
    price DECIMAL(10,2),
    rsi DECIMAL(5,2),
    stoch_k DECIMAL(5,2),
    macd_hist DECIMAL(10,4),
    reason VARCHAR(50),
    
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_symbol (symbol),
    INDEX idx_score (score DESC),
    INDEX idx_passed (passed)
);

CREATE TABLE universe_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    symbols TEXT NOT NULL,  -- JSON array of symbols
    count INTEGER NOT NULL,
    
    INDEX idx_date (snapshot_date DESC)
);
```

---

## 6. Performance Metrics and Monitoring

### 6.1 Screening Performance Metrics

Track these metrics for each screening run:

```python
class ScreeningMetrics:
    """Track and report screening performance."""
    
    def __init__(self):
        self.metrics = {
            'total_symbols': 0,
            'symbols_processed': 0,
            'symbols_passed': 0,
            'symbols_failed': 0,
            'avg_score': 0.0,
            'duration_seconds': 0.0,
            'errors': []
        }
    
    def record_run(self, results: pd.DataFrame, duration: float):
        """Record metrics from a screening run."""
        self.metrics['total_symbols'] = len(results)
        self.metrics['symbols_processed'] = len(results)
        self.metrics['symbols_passed'] = len(results[results['passed']])
        self.metrics['symbols_failed'] = len(results[~results['passed']])
        self.metrics['avg_score'] = results[results['passed']]['score'].mean()
        self.metrics['duration_seconds'] = duration
    
    def get_summary(self) -> str:
        """Generate summary report."""
        return f"""
        Screening Summary:
        ==================
        Total Symbols: {self.metrics['total_symbols']}
        Passed Filter: {self.metrics['symbols_passed']} ({self.metrics['symbols_passed']/self.metrics['total_symbols']*100:.1f}%)
        Failed Filter: {self.metrics['symbols_failed']}
        Average Score: {self.metrics['avg_score']:.2f}
        Duration: {self.metrics['duration_seconds']:.1f}s
        Rate: {self.metrics['total_symbols']/self.metrics['duration_seconds']:.1f} symbols/sec
        """
```

### 6.2 Alert Conditions

Generate alerts when:
- Screening duration exceeds 60 seconds
- Pass rate <1% or >20% (indicates filter misconfiguration)
- Data fetch failures >10%
- Any symbol with score >80 (very strong setup)

---

## 7. Integration with Fine Screening

**Output Format:**

The coarse screening produces a ranked list of candidates that feeds into the fine multi-timeframe analysis:

```python
def handoff_to_fine_screening(coarse_results: pd.DataFrame):
    """
    Pass high-quality candidates to fine screening pipeline.
    
    Selection criteria:
    - Score >= 60 (strong preliminary signal)
    - Top 100 by score (computational limit)
    """
    # Select top candidates
    top_candidates = coarse_results.nlargest(100, 'score')
    
    # Filter by minimum score threshold
    qualified = top_candidates[top_candidates['score'] >= 60]
    
    logger.info(f"Passing {len(qualified)} candidates to fine screening")
    
    # Trigger fine screening (see Document 05)
    from fine_screening import run_multiframe_analysis
    
    fine_results = run_multiframe_analysis(
        symbols=qualified['symbol'].tolist()
    )
    
    return fine_results
```

---

## 8. Continuous Improvement

### 8.1 Backtesting Coarse Filter

Periodically validate the coarse filter effectiveness:

```python
def backtest_coarse_filter(start_date: str, end_date: str):
    """
    Backtest coarse filter to validate it catches actual setups.
    
    Metrics:
    - Recall: % of actual A+ setups that passed coarse filter
    - Precision: % of coarse filter passes that became A+ setups
    - False negative rate
    """
    # Load historical A+ setups from signal database
    actual_setups = load_historical_setups(start_date, end_date, grade='A+')
    
    # Simulate coarse filter on historical data
    simulated_passes = simulate_coarse_filter(start_date, end_date)
    
    # Calculate metrics
    true_positives = set(actual_setups) & set(simulated_passes)
    false_negatives = set(actual_setups) - set(simulated_passes)
    
    recall = len(true_positives) / len(actual_setups)
    precision = len(true_positives) / len(simulated_passes)
    
    logger.info(f"""
    Coarse Filter Backtest Results:
    ================================
    Recall: {recall:.2%} (caught {len(true_positives)}/{len(actual_setups)} setups)
    Precision: {precision:.2%}
    Missed Setups: {len(false_negatives)}
    """)
    
    return {
        'recall': recall,
        'precision': precision,
        'missed_setups': list(false_negatives)
    }
```

### 8.2 Filter Optimization

If recall <80%, consider:
- Loosening Stoch RSI threshold (20 → 25)
- Accepting 2 of 4 conditions instead of 3 of 4
- Adding alternative patterns (e.g., tight BB squeeze)

If precision <20%, consider:
- Raising score threshold (60 → 70)
- Adding volume requirement
- Tightening MACD histogram criteria

---

## 9. Next Document

**Document 05: Watchlist Generation and Scoring** will detail:
- Multi-timeframe fine analysis (15m, 1h, 4h)
- SABR20 scoring methodology (as shown in screenshot)
- A+ / B / C setup classification
- Integration with dashboard for real-time monitoring
