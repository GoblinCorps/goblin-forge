# Regime and Market Environment Analysis
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Overview

This document specifies the methodology for assessing market regime, environmental conditions, and risk-on/risk-off states that influence trading decisions and position sizing.

**Purpose:**
- Prevent trading against hostile market environments
- Adjust position sizing based on market volatility
- Identify favorable vs. unfavorable conditions for mean-reversion strategies
- Provide context for watchlist interpretation

---

## 2. Market Regime Framework

### 2.1 Regime Dimensions

We analyze four independent dimensions:

```
Market Regime = f(Trend, Volatility, Correlation, Breadth)
```

| Dimension | Measures | Impact |
|-----------|----------|--------|
| **Trend** | Directional bias of major indices | Affects success rate of reversals |
| **Volatility** | VIX level and trend | Affects stop sizing and trade frequency |
| **Correlation** | Inter-stock correlation | Affects diversification benefit |
| **Breadth** | Advance/decline, new highs/lows | Confirms or diverges from index |

### 2.2 Regime States

**Primary Classification:**

```python
from enum import Enum

class MarketRegime(Enum):
    BULL_LOW_VOL = "bull_low_vol"          # Best for trend following
    BULL_HIGH_VOL = "bull_high_vol"        # Good for reversals (bounces)
    BEAR_LOW_VOL = "bear_low_vol"          # Choppy, difficult
    BEAR_HIGH_VOL = "bear_high_vol"        # Worst (crashes)
    NEUTRAL_LOW_VOL = "neutral_low_vol"    # Range-bound
    NEUTRAL_HIGH_VOL = "neutral_high_vol"  # Whipsaw risk
```

---

## 3. Trend Analysis

### 3.1 Index Trend Classification

Monitor key indices on 4h and daily timeframes:

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class IndexTrend:
    """Trend state for a single index."""
    symbol: str
    timeframe: str
    
    # Price vs MAs
    price_vs_sma20: float  # % above/below
    price_vs_sma50: float
    price_vs_sma200: float
    
    # MA alignment
    ma_aligned: bool  # 20 > 50 > 200 (bull) or reverse (bear)
    
    # Momentum
    rsi: float
    macd_hist: float
    macd_slope: float  # Rising/falling
    
    # Classification
    trend_state: str  # "strong_bull", "bull", "neutral", "bear", "strong_bear"

def classify_index_trend(data: pd.DataFrame) -> IndexTrend:
    """
    Classify trend for an index.
    
    Parameters:
    -----------
    data : pd.DataFrame
        OHLCV data with indicators
    
    Returns:
    --------
    IndexTrend
    """
    current = data.iloc[-1]
    prev = data.iloc[-2]
    
    # Calculate SMAs
    sma20 = data['close'].rolling(20).mean().iloc[-1]
    sma50 = data['close'].rolling(50).mean().iloc[-1]
    sma200 = data['close'].rolling(200).mean().iloc[-1]
    
    price = current['close']
    
    # Calculate relationships
    price_vs_sma20 = (price - sma20) / sma20 * 100
    price_vs_sma50 = (price - sma50) / sma50 * 100
    price_vs_sma200 = (price - sma200) / sma200 * 100
    
    # MA alignment
    bull_aligned = sma20 > sma50 > sma200
    bear_aligned = sma20 < sma50 < sma200
    
    # MACD slope
    macd_slope = current['macd_hist'] - prev['macd_hist']
    
    # Determine trend state
    if bull_aligned and price_vs_sma20 > 2 and current['rsi'] > 55:
        trend_state = "strong_bull"
    elif price_vs_sma50 > 0 and current['rsi'] > 50:
        trend_state = "bull"
    elif -2 <= price_vs_sma50 <= 2:
        trend_state = "neutral"
    elif price_vs_sma50 < 0 and current['rsi'] < 50:
        trend_state = "bear"
    else:
        trend_state = "strong_bear"
    
    return IndexTrend(
        symbol=data.attrs.get('symbol', 'UNKNOWN'),
        timeframe=data.attrs.get('timeframe', 'UNKNOWN'),
        price_vs_sma20=round(price_vs_sma20, 2),
        price_vs_sma50=round(price_vs_sma50, 2),
        price_vs_sma200=round(price_vs_sma200, 2),
        ma_aligned=bull_aligned,
        rsi=round(current['rsi'], 2),
        macd_hist=round(current['macd_hist'], 4),
        macd_slope=round(macd_slope, 4),
        trend_state=trend_state
    )
```

### 3.2 Multi-Index Consensus

```python
def calculate_market_trend_consensus() -> Dict:
    """
    Calculate consensus trend across major indices.
    
    Monitors: SPY, QQQ, IWM, DIA
    
    Returns:
    --------
    dict : Consensus trend and individual index states
    """
    indices = ['SPY', 'QQQ', 'IWM', 'DIA']
    
    trends = {}
    for symbol in indices:
        data_4h = fetch_index_data(symbol, '4 hours', '30 D')
        data_4h.attrs['symbol'] = symbol
        data_4h.attrs['timeframe'] = '4h'
        
        trend = classify_index_trend(data_4h)
        trends[symbol] = trend
    
    # Calculate consensus
    states = [t.trend_state for t in trends.values()]
    
    bull_count = sum(1 for s in states if 'bull' in s)
    bear_count = sum(1 for s in states if 'bear' in s)
    
    if bull_count >= 3:
        consensus = "bullish"
    elif bear_count >= 3:
        consensus = "bearish"
    else:
        consensus = "mixed"
    
    return {
        'consensus': consensus,
        'indices': trends,
        'bull_count': bull_count,
        'bear_count': bear_count
    }
```

---

## 4. Volatility Analysis

### 4.1 VIX Monitoring

```python
@dataclass
class VolatilityRegime:
    """Volatility regime classification."""
    vix_level: float
    vix_trend: str  # "rising", "falling", "stable"
    regime: str     # "low", "normal", "elevated", "high", "extreme"
    
    # Historical context
    vix_percentile_30d: float
    vix_percentile_90d: float

def classify_volatility_regime() -> VolatilityRegime:
    """
    Classify current volatility environment.
    
    VIX Regime Thresholds:
    - Low: <15
    - Normal: 15-20
    - Elevated: 20-30
    - High: 30-40
    - Extreme: >40
    """
    # Fetch VIX data
    vix_data = fetch_index_data('VIX', '1 hour', '90 D')
    
    current_vix = vix_data.iloc[-1]['close']
    prev_vix = vix_data.iloc[-5:]['close'].mean()  # 5-period avg
    
    # Determine trend
    if current_vix > prev_vix * 1.05:
        trend = "rising"
    elif current_vix < prev_vix * 0.95:
        trend = "falling"
    else:
        trend = "stable"
    
    # Classify regime
    if current_vix < 15:
        regime = "low"
    elif current_vix < 20:
        regime = "normal"
    elif current_vix < 30:
        regime = "elevated"
    elif current_vix < 40:
        regime = "high"
    else:
        regime = "extreme"
    
    # Calculate percentiles
    vix_30d = vix_data.iloc[-180:]['close']  # Last 30 days (6 bars/day)
    vix_90d = vix_data['close']
    
    percentile_30d = (vix_30d < current_vix).sum() / len(vix_30d) * 100
    percentile_90d = (vix_90d < current_vix).sum() / len(vix_90d) * 100
    
    return VolatilityRegime(
        vix_level=round(current_vix, 2),
        vix_trend=trend,
        regime=regime,
        vix_percentile_30d=round(percentile_30d, 1),
        vix_percentile_90d=round(percentile_90d, 1)
    )
```

### 4.2 Individual Stock Volatility

```python
def calculate_stock_volatility_metrics(data: pd.DataFrame) -> Dict:
    """
    Calculate volatility metrics for individual stock.
    
    Returns:
    --------
    dict : Volatility metrics
    """
    import talib as ta
    
    # ATR
    current_atr = data.iloc[-1]['atr']
    avg_atr = data['atr'].rolling(20).mean().iloc[-1]
    atr_ratio = current_atr / avg_atr
    
    # Historical volatility
    returns = data['close'].pct_change()
    hvol_10d = returns.rolling(10).std() * (252 ** 0.5) * 100  # Annualized
    hvol_20d = returns.rolling(20).std() * (252 ** 0.5) * 100
    
    # Bollinger Width
    bb_width = (data.iloc[-1]['bb_upper'] - data.iloc[-1]['bb_lower']) / data.iloc[-1]['bb_mid']
    avg_bb_width = ((data['bb_upper'] - data['bb_lower']) / data['bb_mid']).rolling(20).mean().iloc[-1]
    
    return {
        'atr': round(current_atr, 2),
        'atr_ratio': round(atr_ratio, 2),
        'hvol_10d': round(hvol_10d.iloc[-1], 1),
        'hvol_20d': round(hvol_20d.iloc[-1], 1),
        'bb_width': round(bb_width, 4),
        'bb_width_ratio': round(bb_width / avg_bb_width, 2) if avg_bb_width > 0 else 1.0
    }
```

---

## 5. Correlation Analysis

### 5.1 Index Correlation

```python
def calculate_index_correlation() -> float:
    """
    Calculate correlation between major indices.
    High correlation (>0.8) = sector rotation limited
    Low correlation (<0.5) = divergent leadership
    """
    indices = ['SPY', 'QQQ', 'IWM']
    
    # Fetch 20 days of returns
    returns = {}
    for symbol in indices:
        data = fetch_index_data(symbol, '1 day', '30 D')
        returns[symbol] = data['close'].pct_change()
    
    # Create correlation matrix
    df_returns = pd.DataFrame(returns)
    corr_matrix = df_returns.corr()
    
    # Average correlation (excluding diagonal)
    avg_correlation = (corr_matrix.sum().sum() - len(indices)) / (len(indices) * (len(indices) - 1))
    
    return round(avg_correlation, 3)
```

---

## 6. Breadth Analysis

### 6.1 Advance/Decline Metrics

```python
@dataclass
class MarketBreadth:
    """Market breadth indicators."""
    
    # Advance/Decline
    advances: int
    declines: int
    unchanged: int
    ad_ratio: float  # advances / declines
    
    # New Highs/Lows
    new_highs: int
    new_lows: int
    nh_nl_ratio: float
    
    # Interpretation
    breadth_strength: str  # "strong", "moderate", "weak", "negative"

def calculate_market_breadth() -> MarketBreadth:
    """
    Calculate market breadth from S&P 500 constituents.
    
    Note: Requires real-time or EOD data for all constituents.
    Simplified version using IB scanner or external data feed.
    """
    # Simplified: use SPY components or IB scanner results
    # In production, scan all S&P 500 stocks
    
    # Placeholder implementation
    # Replace with actual market scan
    
    advances = 300
    declines = 150
    unchanged = 50
    
    new_highs = 45
    new_lows = 12
    
    ad_ratio = advances / declines if declines > 0 else 10
    nh_nl_ratio = new_highs / new_lows if new_lows > 0 else 10
    
    # Determine breadth strength
    if ad_ratio > 2.0 and nh_nl_ratio > 2.0:
        strength = "strong"
    elif ad_ratio > 1.2 and nh_nl_ratio > 1.0:
        strength = "moderate"
    elif ad_ratio > 0.8:
        strength = "weak"
    else:
        strength = "negative"
    
    return MarketBreadth(
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        ad_ratio=round(ad_ratio, 2),
        new_highs=new_highs,
        new_lows=new_lows,
        nh_nl_ratio=round(nh_nl_ratio, 2),
        breadth_strength=strength
    )
```

---

## 7. Composite Regime Classification

### 7.1 Regime Scoring System

```python
@dataclass
class MarketEnvironment:
    """Complete market environment assessment."""
    
    # Components
    trend_consensus: str
    volatility_regime: VolatilityRegime
    correlation: float
    breadth: MarketBreadth
    
    # Composite
    regime: MarketRegime
    favorability_score: float  # 0-100
    
    # Risk adjustments
    position_size_multiplier: float  # 0.5-1.5
    max_positions_allowed: int

def assess_market_environment() -> MarketEnvironment:
    """
    Complete market environment assessment.
    
    Returns:
    --------
    MarketEnvironment : Full regime analysis
    """
    # Gather components
    trend = calculate_market_trend_consensus()
    volatility = classify_volatility_regime()
    correlation = calculate_index_correlation()
    breadth = calculate_market_breadth()
    
    # Calculate favorability score (0-100)
    score = 0
    
    # Trend component (0-30)
    if trend['consensus'] == 'bullish':
        score += 30
    elif trend['consensus'] == 'mixed':
        score += 15
    
    # Volatility component (0-25)
    vix_score_map = {
        'low': 25,
        'normal': 20,
        'elevated': 10,
        'high': 5,
        'extreme': 0
    }
    score += vix_score_map.get(volatility.regime, 10)
    
    # Breadth component (0-25)
    breadth_score_map = {
        'strong': 25,
        'moderate': 15,
        'weak': 8,
        'negative': 0
    }
    score += breadth_score_map.get(breadth.breadth_strength, 10)
    
    # Correlation component (0-20)
    # Moderate correlation is best (0.5-0.7)
    if 0.5 <= correlation <= 0.7:
        score += 20
    elif 0.3 <= correlation <= 0.8:
        score += 12
    else:
        score += 5
    
    # Classify regime
    if trend['consensus'] == 'bullish' and volatility.regime in ['low', 'normal']:
        regime = MarketRegime.BULL_LOW_VOL
    elif trend['consensus'] == 'bullish':
        regime = MarketRegime.BULL_HIGH_VOL
    elif trend['consensus'] == 'bearish' and volatility.regime in ['low', 'normal']:
        regime = MarketRegime.BEAR_LOW_VOL
    elif trend['consensus'] == 'bearish':
        regime = MarketRegime.BEAR_HIGH_VOL
    elif volatility.regime in ['low', 'normal']:
        regime = MarketRegime.NEUTRAL_LOW_VOL
    else:
        regime = MarketRegime.NEUTRAL_HIGH_VOL
    
    # Determine position sizing multiplier
    if score >= 70:
        multiplier = 1.5  # Increase size in favorable conditions
    elif score >= 50:
        multiplier = 1.0  # Normal size
    elif score >= 30:
        multiplier = 0.75  # Reduce size
    else:
        multiplier = 0.5  # Minimum size
    
    # Determine max positions
    if score >= 70:
        max_positions = 8
    elif score >= 50:
        max_positions = 5
    elif score >= 30:
        max_positions = 3
    else:
        max_positions = 1  # Very selective
    
    return MarketEnvironment(
        trend_consensus=trend['consensus'],
        volatility_regime=volatility,
        correlation=correlation,
        breadth=breadth,
        regime=regime,
        favorability_score=round(score, 1),
        position_size_multiplier=multiplier,
        max_positions_allowed=max_positions
    )
```

---

## 8. Real-Time Regime Monitoring

### 8.1 Continuous Assessment

```python
import schedule
from datetime import datetime

class RegimeMonitor:
    """Monitor and cache market regime."""
    
    def __init__(self):
        self.current_environment = None
        self.last_update = None
    
    def update(self):
        """Update regime assessment."""
        logger.info("Updating market regime assessment")
        
        self.current_environment = assess_market_environment()
        self.last_update = datetime.now()
        
        # Save to database
        self.save_to_db()
        
        # Check for regime changes
        self.check_regime_change()
    
    def get_current(self) -> MarketEnvironment:
        """Get current regime (cached)."""
        if self.current_environment is None:
            self.update()
        return self.current_environment
    
    def save_to_db(self):
        """Save regime to database."""
        # Implementation: save to regime_snapshots table
        pass
    
    def check_regime_change(self):
        """Alert if regime changed significantly."""
        # Load previous regime
        # Compare to current
        # Send alert if changed
        pass

# Global instance
regime_monitor = RegimeMonitor()

# Schedule updates every 30 minutes during market hours
schedule.every(30).minutes.do(regime_monitor.update)
```

### 8.2 Pre-Market Regime Report

```python
def generate_premarket_regime_report() -> str:
    """
    Generate comprehensive regime report before market open.
    
    Returns:
    --------
    str : Formatted report
    """
    env = regime_monitor.get_current()
    
    report = f"""
    ========================================
    MARKET REGIME REPORT
    {datetime.now().strftime('%Y-%m-%d %H:%M')}
    ========================================
    
    OVERALL REGIME: {env.regime.value.upper()}
    Favorability Score: {env.favorability_score}/100
    
    TREND ANALYSIS:
    ---------------
    Consensus: {env.trend_consensus.upper()}
    
    VOLATILITY:
    -----------
    VIX Level: {env.volatility_regime.vix_level}
    VIX Regime: {env.volatility_regime.regime.upper()}
    VIX Trend: {env.volatility_regime.vix_trend}
    VIX 30D Percentile: {env.volatility_regime.vix_percentile_30d}%
    
    BREADTH:
    --------
    A/D Ratio: {env.breadth.ad_ratio}
    NH/NL Ratio: {env.breadth.nh_nl_ratio}
    Strength: {env.breadth.breadth_strength.upper()}
    
    CORRELATION:
    ------------
    Index Correlation: {env.correlation}
    
    TRADING IMPLICATIONS:
    --------------------
    Position Size Multiplier: {env.position_size_multiplier}x
    Max Positions Allowed: {env.max_positions_allowed}
    
    RECOMMENDATIONS:
    ----------------
    {get_regime_recommendations(env)}
    ========================================
    """
    
    return report

def get_regime_recommendations(env: MarketEnvironment) -> str:
    """Generate trading recommendations based on regime."""
    
    if env.regime == MarketRegime.BULL_LOW_VOL:
        return """
        ✓ Favorable for trend following and breakouts
        ✓ Use full position sizes
        ✓ Trail stops aggressively
        ✗ Mean reversion may underperform
        """
    
    elif env.regime == MarketRegime.BULL_HIGH_VOL:
        return """
        ✓ Good for mean reversion (dip buying)
        ✓ Wider stops needed
        ✓ Take profits quickly
        ⚠ Whipsaw risk elevated
        """
    
    elif env.regime == MarketRegime.BEAR_LOW_VOL:
        return """
        ⚠ Choppy conditions
        ⚠ Reduce position sizes by 50%
        ⚠ Be very selective (A+ setups only)
        ✗ Avoid holding overnight
        """
    
    elif env.regime == MarketRegime.BEAR_HIGH_VOL:
        return """
        🚫 HOSTILE ENVIRONMENT
        🚫 Minimize trading
        🚫 Only trade with 25% normal size
        🚫 Use tightest stops
        """
    
    else:
        return """
        ⚠ Neutral/choppy conditions
        ⚠ Be selective
        ⚠ Reduce size modestly
        ✓ Focus on best setups
        """
```

---

## 9. Integration with Trading System

### 9.1 Watchlist Filtering

```python
def filter_watchlist_by_regime(watchlist: pd.DataFrame) -> pd.DataFrame:
    """
    Filter and adjust watchlist based on market regime.
    
    Parameters:
    -----------
    watchlist : pd.DataFrame
        Watchlist from scoring system
    
    Returns:
    --------
    pd.DataFrame : Filtered and adjusted watchlist
    """
    env = regime_monitor.get_current()
    
    # In hostile regimes, keep only A+ setups
    if env.favorability_score < 40:
        watchlist = watchlist[watchlist['setup_grade'] == 'A+']
    
    # Limit to max positions allowed
    watchlist = watchlist.head(env.max_positions_allowed)
    
    # Add regime context columns
    watchlist['regime'] = env.regime.value
    watchlist['regime_score'] = env.favorability_score
    watchlist['position_multiplier'] = env.position_size_multiplier
    
    return watchlist
```

### 9.2 Position Sizing Adjustment

```python
def calculate_position_size_with_regime(
    base_size: int,
    symbol: str,
    stop_distance: float
) -> int:
    """
    Adjust position size based on regime.
    
    Parameters:
    -----------
    base_size : int
        Base position size (shares)
    symbol : str
        Stock symbol
    stop_distance : float
        Distance to stop in dollars
    
    Returns:
    --------
    int : Adjusted position size
    """
    env = regime_monitor.get_current()
    
    # Apply regime multiplier
    adjusted_size = int(base_size * env.position_size_multiplier)
    
    # Additional volatility adjustment
    stock_vol = get_stock_volatility(symbol)
    
    if stock_vol['atr_ratio'] > 1.5:  # Stock is volatile
        adjusted_size = int(adjusted_size * 0.75)
    
    return max(adjusted_size, 100)  # Minimum 100 shares
```

---

## 10. Database Schema

```sql
CREATE TABLE regime_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    
    -- Composite
    regime VARCHAR(50) NOT NULL,
    favorability_score DECIMAL(5,2),
    position_size_multiplier DECIMAL(3,2),
    max_positions_allowed INTEGER,
    
    -- Trend
    trend_consensus VARCHAR(20),
    
    -- Volatility
    vix_level DECIMAL(5,2),
    vix_regime VARCHAR(20),
    vix_trend VARCHAR(20),
    
    -- Breadth
    ad_ratio DECIMAL(5,2),
    nh_nl_ratio DECIMAL(5,2),
    breadth_strength VARCHAR(20),
    
    -- Correlation
    index_correlation DECIMAL(4,3),
    
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_regime (regime)
);
```

---

## 11. Next Document

**Document 07: Real-Time Dashboard Specification** will detail:
- Dashboard layout and information architecture
- Real-time data visualization
- Interactive chart components
- Alert and notification panels
- User controls and actions
