# Watchlist Generation and SABR20 Scoring System
**Multi-Timeframe Momentum Reversal Trading System**

---

## 1. Overview

This document specifies the fine-grained multi-timeframe analysis that converts coarse screening candidates into a ranked, actionable watchlist using the SABR20 (Setup Analysis & Bollinger Reversal 20-period) scoring system.

**Input:** Top 50-200 symbols from coarse screening (Document 04)  
**Output:** Ranked watchlist with 5-30 A+ setups ready for execution  
**Update Frequency:** Every 15 minutes during market hours

---

## 2. SABR20 Scoring Methodology

### 2.1 Score Components

The SABR20 score is a composite measure (0-100) evaluating setup quality across multiple dimensions:

```
SABR20 = w₁·(Setup Strength) + 
         w₂·(Bottom Phase) + 
         w₃·(Trend Momentum) + 
         w₄·(Risk/Reward) +
         w₅·(Volume Profile)

Where weights sum to 1.0
```

**Component Breakdown:**

| Component | Weight | Description | Range |
|-----------|--------|-------------|-------|
| Setup Strength | 0.30 | Multi-TF indicator confluence | 0-30 |
| Bottom Phase | 0.22 | Depth and cleanness of reversal | 0-22 |
| Accumulation Intensity | 0.18 | Stoch/RSI signal frequency ratio | 0-18 |
| Trend Momentum | 0.18 | Strength of emerging trend | 0-18 |
| Risk/Reward | 0.10 | Distance to resistance vs stop | 0-10 |
| Volume Profile | 0.02 | Volume characteristics | 0-2 |

### 2.2 Detailed Component Calculations

#### Component 1: Setup Strength (0-35 points)

**Evaluates:** Multi-timeframe indicator alignment

```python
def calculate_setup_strength(data_15m, data_1h, data_4h) -> float:
    """
    Calculate setup strength based on multi-TF indicator confluence.
    
    Returns: 0-35 points
    """
    score = 0.0
    
    # ===== T1 (15m) Indicators (15 points max) =====
    t1_current = data_15m.iloc[-1]
    t1_prev = data_15m.iloc[-2]
    
    # Stoch RSI: Oversold cross up (0-5 points)
    if t1_prev['stoch_k'] <= 20 and t1_prev['stoch_d'] <= 20:
        if t1_current['stoch_k'] > t1_current['stoch_d']:
            stoch_rise = t1_current['stoch_k'] - t1_prev['stoch_k']
            score += min(5, stoch_rise / 4)  # Max 5 points for 20+ rise
    
    # MACD: First green or rising (0-5 points)
    if t1_prev['macd_hist'] < 0 and t1_current['macd_hist'] >= 0:
        score += 5  # Perfect: just turned positive
    elif t1_current['macd_hist'] > t1_prev['macd_hist']:
        score += 3  # Good: rising but still negative
    
    # BB: Mid-band break (0-5 points)
    recent_low_touch = (data_15m.iloc[-5:]['close'] <= data_15m.iloc[-5:]['bb_lower'] * 1.02).any()
    mid_break = t1_current['close'] >= t1_current['bb_mid']
    
    if recent_low_touch and mid_break:
        score += 5
    elif mid_break:
        score += 3
    
    # ===== T2 (1h) Confirmation (12 points max) =====
    t2_current = data_1h.iloc[-1]
    t2_prev = data_1h.iloc[-2]
    
    # MACD: Rising histogram (0-6 points)
    if t2_current['macd_hist'] > t2_prev['macd_hist']:
        if t2_current['macd_hist'] > 0:
            score += 6  # Best: positive and rising
        else:
            score += 4  # Good: negative but rising
    
    # Stoch RSI: Not overbought (0-3 points)
    if t2_current['stoch_k'] < 70 and t2_current['stoch_d'] < 70:
        score += 3
    
    # Price: Above mid-band (0-3 points)
    if t2_current['close'] >= t2_current['bb_mid']:
        score += 3
    
    # ===== T3 (4h) Regime (8 points max) =====
    t3_current = data_4h.iloc[-1]
    t3_prev = data_4h.iloc[-2]
    
    # MACD: Non-hostile (0-4 points)
    if t3_current['macd_hist'] >= t3_prev['macd_hist']:
        score += 4
    elif t3_current['macd_hist'] > -2.0:  # Not deeply bearish
        score += 2
    
    # RSI: Acceptable (0-4 points)
    if t3_current['rsi'] >= 35:
        if t3_current['rsi'] >= 45:
            score += 4
        else:
            score += 2
    
    return round(score, 2)
```

#### Component 2: Bottom Phase Quality (0-25 points)

**Evaluates:** How clean and definitive the bottom formation is

```python
def calculate_bottom_phase(data_15m, data_1h) -> float:
    """
    Calculate bottom phase quality.
    
    Returns: 0-25 points
    """
    score = 0.0
    
    t1 = data_15m.iloc[-1]
    t1_recent = data_15m.iloc[-10:]
    
    # ===== Depth of Oversold (0-10 points) =====
    min_stoch = t1_recent['stoch_k'].min()
    min_rsi = t1_recent['rsi'].min()
    
    if min_stoch <= 10:
        score += 6
    elif min_stoch <= 15:
        score += 4
    elif min_stoch <= 20:
        score += 2
    
    if min_rsi <= 25:
        score += 4
    elif min_rsi <= 30:
        score += 2
    
    # ===== Bars Since Pivot (0-8 points) =====
    # Prefer: reversal happened 1-5 bars ago (not too early, not too late)
    bars_since_low = (t1_recent['close'].idxmin() - t1_recent.index[-1])
    
    if 1 <= abs(bars_since_low) <= 5:
        score += 8
    elif 6 <= abs(bars_since_low) <= 10:
        score += 4
    
    # ===== State Classification (0-7 points) =====
    # Determine if we're PreBottom, BottomActive, or PostBottom
    state = classify_bottom_state(data_15m)
    
    state_scores = {
        'PreBottom': 3,      # Setup forming but not triggered
        'BottomActive': 7,   # Perfect: in the reversal zone
        'BottomSoon': 5,     # Close to triggering
        'PostBottom': 0      # Already moved too much
    }
    
    score += state_scores.get(state, 0)
    
    return round(score, 2)

def classify_bottom_state(data: pd.DataFrame) -> str:
    """
    Classify current position in bottom formation.
    
    States:
    - PreBottom: Oversold, no cross yet
    - BottomSoon: Indicators curling, about to cross
    - BottomActive: Just crossed, early move (BEST)
    - PostBottom: Well into move, late entry
    """
    current = data.iloc[-1]
    prev = data.iloc[-2]
    
    # Check Stoch RSI state
    is_oversold = current['stoch_k'] <= 25 or current['stoch_d'] <= 25
    just_crossed = (prev['stoch_k'] <= prev['stoch_d']) and (current['stoch_k'] > current['stoch_d'])
    is_rising = current['stoch_k'] > prev['stoch_k']
    
    # Check price action
    bb_range = current['bb_upper'] - current['bb_lower']
    bb_position = (current['close'] - current['bb_lower']) / bb_range
    
    if is_oversold and not just_crossed:
        if is_rising:
            return 'BottomSoon'
        return 'PreBottom'
    
    if just_crossed or (0.2 <= bb_position <= 0.5):
        return 'BottomActive'
    
    if bb_position > 0.6:
        return 'PostBottom'
    
    return 'BottomSoon'
```

#### Component 3: Accumulation Intensity (0-18 points)

**Evaluates:** Stoch/RSI signal frequency ratio indicating accumulation pressure

This component detects **institutional accumulation** by measuring the ratio of micro-structure signals (Stoch RSI oversold crosses) to macro-structure signals (RSI oversold recoveries) over a sliding window.

**Theory:**
When smart money accumulates a position, it creates repeated micro-reversals (visible in Stoch RSI) before the broader momentum indicators (RSI) confirm. A high ratio indicates systematic buying pressure that hasn't yet registered in the price trend.

```python
def calculate_accumulation_intensity(data_15m, data_1h) -> float:
    """
    Calculate accumulation intensity based on signal frequency ratio.
    
    Returns: 0-18 points
    """
    score = 0.0
    window = 50  # bars
    
    # ===== Detect Signals =====
    
    # Stoch RSI buy signals (15m)
    t1 = data_15m.iloc[-window:]
    stoch_signals = 0
    
    for i in range(1, len(t1)):
        prev = t1.iloc[i-1]
        curr = t1.iloc[i]
        
        # Both were oversold
        if prev['stoch_k'] <= 20 and prev['stoch_d'] <= 20:
            # K crossed above D
            if curr['stoch_k'] > curr['stoch_d'] and prev['stoch_k'] <= prev['stoch_d']:
                # K is rising
                if curr['stoch_k'] > prev['stoch_k']:
                    stoch_signals += 1
    
    # RSI buy signals (15m)
    rsi_signals = 0
    
    for i in range(1, len(t1)):
        prev = t1.iloc[i-1]
        curr = t1.iloc[i]
        
        # Was oversold, now rising above 30
        if prev['rsi'] <= 30 and curr['rsi'] > 30 and curr['rsi'] > prev['rsi']:
            rsi_signals += 1
    
    # ===== Calculate Ratio =====
    epsilon = 0.5  # Prevent division by zero
    ratio = stoch_signals / (rsi_signals + epsilon)
    
    # Calculate frequency percentages
    stoch_freq = stoch_signals / window * 100
    rsi_freq = rsi_signals / window * 100
    
    # ===== Score Based on Ratio and Phase =====
    current_rsi = data_15m.iloc[-1]['rsi']
    
    # Early Accumulation Phase (Ratio > 5, RSI < 45)
    if ratio > 5 and current_rsi < 45:
        score += 18  # Maximum - best entry point
    
    # Mid Accumulation Phase (Ratio 3-5, RSI < 50)
    elif 3 <= ratio <= 5 and current_rsi < 50:
        score += 14
    
    # Late Accumulation Phase (Ratio 1.5-3, RSI 40-55)
    elif 1.5 <= ratio < 3 and 40 <= current_rsi <= 55:
        score += 10
    
    # Breakout Phase (Ratio ~1, RSI > 50)
    elif 0.8 <= ratio <= 1.5 and current_rsi > 50:
        score += 6  # Good but late
    
    # Distribution Phase (Ratio < 0.8)
    else:
        score += 0
    
    # ===== Bonus for Recent Activity =====
    # Count signals in last 10 bars
    recent_stoch = sum(1 for i in range(len(t1)-10, len(t1)) 
                       if detect_stoch_signal_at(t1, i))
    
    if recent_stoch >= 3:
        score += 2  # Very active accumulation
    elif recent_stoch >= 2:
        score += 1
    
    return round(min(score, 18), 2)

def detect_stoch_signal_at(df: pd.DataFrame, i: int) -> bool:
    """Helper to detect stoch signal at specific bar."""
    if i < 1:
        return False
    
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    
    return (prev['stoch_k'] <= 20 and prev['stoch_d'] <= 20 and
            curr['stoch_k'] > curr['stoch_d'] and 
            prev['stoch_k'] <= prev['stoch_d'] and
            curr['stoch_k'] > prev['stoch_k'])
```

**Accumulation Phases:**

| Phase | Ratio Range | RSI Context | Score | Interpretation |
|-------|-------------|-------------|-------|----------------|
| Early Accumulation | > 5 | < 45 | 18 | Best entry - institutional buying |
| Mid Accumulation | 3-5 | < 50 | 14 | High probability reversal imminent |
| Late Accumulation | 1.5-3 | 40-55 | 10 | Setup maturing |
| Breakout | 0.8-1.5 | > 50 | 6 | Momentum confirmed (late) |
| Distribution | < 0.8 | > 60 | 0 | Avoid - likely topping |

**Key Insight:**
A ratio of 5-10+ means Stoch RSI is firing 5-10x more frequently than RSI, indicating **hidden accumulation** before the broader trend shift. This is the mathematical signature of the pattern you've been identifying visually across all your chart examples.

#### Component 4: Trend Momentum (0-18 points)

**Evaluates:** Strength and acceleration of emerging trend

```python
def calculate_trend_momentum(data_15m, data_1h) -> float:
    """
    Calculate trend momentum quality.
    
    Returns: 0-20 points
    """
    score = 0.0
    
    t1 = data_15m.iloc[-1]
    t1_prev = data_15m.iloc[-2]
    t1_prev2 = data_15m.iloc[-3]
    
    # ===== MACD Acceleration (0-8 points) =====
    hist_slope_1 = t1['macd_hist'] - t1_prev['macd_hist']
    hist_slope_2 = t1_prev['macd_hist'] - t1_prev2['macd_hist']
    
    if hist_slope_1 > 0 and hist_slope_2 > 0:
        score += 8  # Accelerating
    elif hist_slope_1 > 0:
        score += 5  # Rising
    
    # ===== RSI Slope (0-6 points) =====
    rsi_rise = t1['rsi'] - t1_prev['rsi']
    
    if rsi_rise >= 5:
        score += 6
    elif rsi_rise >= 3:
        score += 4
    elif rsi_rise >= 1:
        score += 2
    
    # ===== Price vs MA Trend (0-6 points) =====
    # Compare price to 20-period SMA slope
    sma_20 = data_15m['close'].rolling(20).mean()
    sma_slope = sma_20.iloc[-1] - sma_20.iloc[-5]
    
    if sma_slope > 0 and t1['close'] > sma_20.iloc[-1]:
        score += 6
    elif t1['close'] > sma_20.iloc[-1]:
        score += 3
    
    return round(score, 2)
```

#### Component 5: Risk/Reward Ratio (0-10 points)

**Evaluates:** Favorable entry point relative to stop and target

```python
def calculate_risk_reward(data_15m, data_1h) -> float:
    """
    Calculate risk/reward profile.
    
    Returns: 0-10 points
    """
    score = 0.0
    
    t1 = data_15m.iloc[-1]
    t2 = data_1h.iloc[-1]
    
    current_price = t1['close']
    
    # ===== Determine Stop Level =====
    # Stop = lower of: 1) Recent swing low, 2) Lower BB
    recent_swing_low = data_15m.iloc[-10:]['low'].min()
    stop_level = min(recent_swing_low, t1['bb_lower'])
    
    risk = current_price - stop_level
    risk_pct = risk / current_price * 100
    
    # ===== Determine Target Level =====
    # Target = higher of: 1) Upper BB on T1, 2) Mid BB on T2
    target_level = max(t1['bb_upper'], t2['bb_mid'] * 1.02)
    
    reward = target_level - current_price
    reward_pct = reward / current_price * 100
    
    # ===== Calculate R:R Ratio =====
    if risk > 0:
        rr_ratio = reward / risk
    else:
        rr_ratio = 0
    
    # ===== Score based on R:R (0-7 points) =====
    if rr_ratio >= 3.0:
        score += 7
    elif rr_ratio >= 2.5:
        score += 6
    elif rr_ratio >= 2.0:
        score += 5
    elif rr_ratio >= 1.5:
        score += 3
    
    # ===== Bonus for tight risk (0-3 points) =====
    if risk_pct <= 1.5:
        score += 3
    elif risk_pct <= 2.5:
        score += 2
    elif risk_pct <= 3.5:
        score += 1
    
    return round(score, 2)
```

#### Component 6: Volume Profile (0-2 points)

**Evaluates:** Volume characteristics supporting the move

```python
def calculate_volume_profile(data_15m) -> float:
    """
    Calculate volume profile quality.
    
    Returns: 0-2 points
    """
    score = 0.0
    
    current = data_15m.iloc[-1]
    avg_volume = data_15m['volume'].rolling(20).mean().iloc[-1]
    
    volume_ratio = current['volume'] / avg_volume
    
    # ===== Current Bar Volume (0-1.5 points) =====
    if volume_ratio >= 1.5:
        score += 1.5  # Strong volume
    elif volume_ratio >= 1.0:
        score += 1.0  # Normal volume
    elif volume_ratio >= 0.7:
        score += 0.5  # Acceptable
    
    # ===== Volume Trend (0-0.5 points) =====
    # Check if volume is increasing over last 3 bars
    recent_volumes = data_15m.iloc[-3:]['volume']
    if recent_volumes.is_monotonic_increasing:
        score += 0.5
    
    return round(score, 2)
```

---

## 3. Complete SABR20 Calculator

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class SABR20Score:
    """Container for SABR20 score breakdown."""
    total: float
    setup_strength: float
    bottom_phase: float
    accumulation_intensity: float
    trend_momentum: float
    risk_reward: float
    volume_profile: float
    
    state: str  # PreBottom, BottomActive, etc.
    acc_phase: str  # Accumulation phase
    acc_ratio: float  # Signal frequency ratio
    rr_ratio: float
    
    def to_dict(self) -> Dict:
        return {
            'SABR20_score': self.total,
            'setup_strength': self.setup_strength,
            'bottom_phase': self.bottom_phase,
            'accumulation_intensity': self.accumulation_intensity,
            'trend_momentum': self.trend_momentum,
            'risk_reward': self.risk_reward,
            'volume_profile': self.volume_profile,
            'state': self.state,
            'acc_phase': self.acc_phase,
            'acc_ratio': self.acc_ratio,
            'rr_ratio': self.rr_ratio
        }

def calculate_sabr20_score(data_15m, data_1h, data_4h) -> SABR20Score:
    """
    Calculate complete SABR20 score with breakdown.
    
    Parameters:
    -----------
    data_15m, data_1h, data_4h : pd.DataFrame
        OHLCV data with calculated indicators for each timeframe
    
    Returns:
    --------
    SABR20Score : Complete score breakdown
    """
    # Calculate components
    setup = calculate_setup_strength(data_15m, data_1h, data_4h)
    bottom = calculate_bottom_phase(data_15m, data_1h)
    accumulation = calculate_accumulation_intensity(data_15m, data_1h)
    momentum = calculate_trend_momentum(data_15m, data_1h)
    rr = calculate_risk_reward(data_15m, data_1h)
    volume = calculate_volume_profile(data_15m)
    
    # Calculate total
    total = setup + bottom + accumulation + momentum + rr + volume
    
    # Extract metadata
    state = classify_bottom_state(data_15m)
    
    # Calculate accumulation phase
    stoch_signals = count_stoch_signals(data_15m, window=50)
    rsi_signals = count_rsi_signals(data_15m, window=50)
    acc_ratio = stoch_signals / (rsi_signals + 0.5)
    current_rsi = data_15m.iloc[-1]['rsi']
    acc_phase = classify_accumulation_phase(acc_ratio, current_rsi)
    
    # Calculate R:R ratio for reporting
    current_price = data_15m.iloc[-1]['close']
    stop_level = min(
        data_15m.iloc[-10:]['low'].min(),
        data_15m.iloc[-1]['bb_lower']
    )
    target_level = max(
        data_15m.iloc[-1]['bb_upper'],
        data_1h.iloc[-1]['bb_mid'] * 1.02
    )
    
    risk = current_price - stop_level
    reward = target_level - current_price
    rr_ratio = reward / risk if risk > 0 else 0
    
    return SABR20Score(
        total=round(total, 2),
        setup_strength=setup,
        bottom_phase=bottom,
        accumulation_intensity=accumulation,
        trend_momentum=momentum,
        risk_reward=rr,
        volume_profile=volume,
        state=state,
        acc_phase=acc_phase,
        acc_ratio=round(acc_ratio, 2),
        rr_ratio=round(rr_ratio, 2)
    )

def count_stoch_signals(df: pd.DataFrame, window: int = 50) -> int:
    """Count Stoch RSI buy signals in window."""
    count = 0
    recent = df.iloc[-window:]
    
    for i in range(1, len(recent)):
        if detect_stoch_signal_at(recent, i):
            count += 1
    
    return count

def count_rsi_signals(df: pd.DataFrame, window: int = 50) -> int:
    """Count RSI buy signals in window."""
    count = 0
    recent = df.iloc[-window:]
    
    for i in range(1, len(recent)):
        prev = recent.iloc[i-1]
        curr = recent.iloc[i]
        
        if prev['rsi'] <= 30 and curr['rsi'] > 30 and curr['rsi'] > prev['rsi']:
            count += 1
    
    return count

def classify_accumulation_phase(ratio: float, rsi: float) -> str:
    """Classify accumulation phase from ratio."""
    if ratio > 5 and rsi < 45:
        return 'EarlyAccumulation'
    elif 3 <= ratio <= 5 and rsi < 50:
        return 'MidAccumulation'
    elif 1.5 <= ratio < 3 and 40 <= rsi <= 55:
        return 'LateAccumulation'
    elif 0.8 <= ratio <= 1.5 and rsi > 50:
        return 'Breakout'
    else:
        return 'Distribution'
```

---

## 4. Multi-Timeframe Analysis Pipeline

### 4.1 Fine Screening Function

```python
from typing import List
import pandas as pd

def run_multiframe_analysis(symbols: List[str]) -> pd.DataFrame:
    """
    Run full multi-timeframe analysis on candidate symbols.
    
    Parameters:
    -----------
    symbols : List[str]
        Symbols that passed coarse filter
    
    Returns:
    --------
    pd.DataFrame : Complete analysis results with SABR20 scores
    """
    from ib_insync import IB, Stock, util
    import talib as ta
    
    results = []
    
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    
    for symbol in symbols:
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Fetch all timeframes
            data_15m = fetch_and_prepare(ib, contract, '15 mins', '3 D')
            data_1h = fetch_and_prepare(ib, contract, '1 hour', '10 D')
            data_4h = fetch_and_prepare(ib, contract, '4 hours', '30 D')
            
            # Skip if insufficient data
            if any(len(df) < 30 for df in [data_15m, data_1h, data_4h]):
                continue
            
            # Calculate SABR20 score
            sabr = calculate_sabr20_score(data_15m, data_1h, data_4h)
            
            # Get current market data
            current_15m = data_15m.iloc[-1]
            
            # Compile results
            result = {
                'symbol': symbol,
                'SABR20_score': sabr.total,
                'setup_strength': sabr.setup_strength,
                'bottom_phase': sabr.bottom_phase,
                'state': sabr.state,
                'quartile': classify_quartile(data_1h),
                'price': current_15m['close'],
                'rsi': current_15m['rsi'],
                'stoch_k': current_15m['stoch_k'],
                'macd_hist': current_15m['macd_hist'],
                'bars_since_pivot': calculate_bars_since_pivot(data_15m),
                'rr_ratio': sabr.rr_ratio,
                'volume_ratio': current_15m['volume'] / data_15m['volume'].rolling(20).mean().iloc[-1],
                'dd_pct': calculate_drawdown_pct(data_1h),
                'trend_exhaust': calculate_trend_exhaust(data_1h),
                'timestamp': pd.Timestamp.now()
            }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            continue
    
    ib.disconnect()
    
    # Convert to DataFrame
    df_results = pd.DataFrame(results)
    
    # Sort by SABR20 score
    df_results = df_results.sort_values('SABR20_score', ascending=False)
    
    return df_results

def fetch_and_prepare(ib: IB, contract, bar_size: str, duration: str) -> pd.DataFrame:
    """Fetch historical data and calculate all indicators."""
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow='TRADES',
        useRTH=True
    )
    
    df = util.df(bars)
    
    # Calculate indicators
    df = calculate_all_indicators(df)
    
    return df

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate full indicator suite."""
    import talib as ta
    
    # Bollinger Bands
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = ta.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    
    # Stochastic RSI
    rsi = ta.RSI(df['close'], timeperiod=14)
    df['stoch_k'], df['stoch_d'] = ta.STOCH(
        rsi, rsi, rsi,
        fastk_period=14, slowk_period=3, slowd_period=3
    )
    
    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = ta.MACD(
        df['close'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    
    # RSI
    df['rsi'] = ta.RSI(df['close'], timeperiod=14)
    
    # ATR
    df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    
    return df
```

### 4.2 Supporting Calculations

```python
def classify_quartile(data_1h: pd.DataFrame) -> str:
    """Classify symbol into quartile based on momentum."""
    current = data_1h.iloc[-1]
    
    if current['rsi'] >= 60 and current['macd_hist'] > 0:
        return 'Q1'  # Strongest
    elif current['rsi'] >= 50 or current['macd_hist'] > 0:
        return 'Q2'
    elif current['rsi'] >= 40:
        return 'Q3'
    else:
        return 'Q4'

def calculate_bars_since_pivot(data: pd.DataFrame) -> int:
    """Calculate bars since price pivot low."""
    recent = data.iloc[-20:]
    pivot_idx = recent['low'].idxmin()
    return len(recent) - recent.index.get_loc(pivot_idx)

def calculate_drawdown_pct(data: pd.DataFrame) -> float:
    """Calculate current drawdown from recent high."""
    recent_high = data.iloc[-20:]['high'].max()
    current_price = data.iloc[-1]['close']
    dd = (current_price - recent_high) / recent_high * 100
    return round(dd, 2)

def calculate_trend_exhaust(data: pd.DataFrame) -> float:
    """
    Calculate trend exhaustion score (0-100).
    Higher = more exhausted (overbought)
    Lower = more room to run
    """
    current = data.iloc[-1]
    
    # RSI component
    rsi_exhaust = max(0, current['rsi'] - 50) / 50 * 50
    
    # Stoch component
    stoch_exhaust = current['stoch_k'] / 100 * 50
    
    return round(rsi_exhaust + stoch_exhaust, 1)
```

---

## 5. Watchlist Classification

### 5.1 Setup Grades

Based on SABR20 score and additional criteria:

```python
def classify_setup(row: pd.Series) -> str:
    """
    Classify setup into A+, A, B, C grades.
    
    Parameters:
    -----------
    row : pd.Series
        Row from results DataFrame with SABR20 score and metadata
    
    Returns:
    --------
    str : Grade (A+, A, B, or C)
    """
    score = row['SABR20_score']
    state = row['state']
    rr = row['rr_ratio']
    
    # A+ Setup: Highest quality
    if (score >= 75 and 
        state == 'BottomActive' and 
        rr >= 2.0):
        return 'A+'
    
    # A Setup: Very good
    if (score >= 65 and 
        state in ['BottomActive', 'BottomSoon'] and 
        rr >= 1.5):
        return 'A'
    
    # B Setup: Good but not perfect
    if score >= 55 and rr >= 1.2:
        return 'B'
    
    # C Setup: Marginal
    return 'C'

def apply_setup_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Apply setup classification to results."""
    df['setup_grade'] = df.apply(classify_setup, axis=1)
    return df
```

### 5.2 Filtering for Actionable Watchlist

```python
def generate_actionable_watchlist(results: pd.DataFrame) -> pd.DataFrame:
    """
    Filter results to actionable watchlist.
    
    Criteria:
    - Grade A+ or A
    - SABR20 score >= 65
    - State = BottomActive or BottomSoon
    - R:R >= 1.5
    """
    watchlist = results[
        (results['setup_grade'].isin(['A+', 'A'])) &
        (results['SABR20_score'] >= 65) &
        (results['state'].isin(['BottomActive', 'BottomSoon'])) &
        (results['rr_ratio'] >= 1.5)
    ].copy()
    
    # Sort by score
    watchlist = watchlist.sort_values('SABR20_score', ascending=False)
    
    # Limit to top 20
    watchlist = watchlist.head(20)
    
    return watchlist
```

---

## 6. Database Schema for Watchlist

```sql
CREATE TABLE watchlist_realtime (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    
    -- SABR20 Components
    sabr20_score DECIMAL(5,2) NOT NULL,
    setup_strength DECIMAL(5,2),
    bottom_phase DECIMAL(5,2),
    trend_momentum DECIMAL(5,2),
    risk_reward_score DECIMAL(5,2),
    volume_profile DECIMAL(5,2),
    
    -- Classification
    setup_grade VARCHAR(2),
    state VARCHAR(20),
    quartile VARCHAR(2),
    
    -- Market Data
    price DECIMAL(10,2),
    rsi DECIMAL(5,2),
    stoch_k DECIMAL(5,2),
    macd_hist DECIMAL(10,4),
    
    -- Metadata
    bars_since_pivot INTEGER,
    rr_ratio DECIMAL(5,2),
    volume_ratio DECIMAL(5,2),
    dd_pct DECIMAL(5,2),
    trend_exhaust DECIMAL(5,2),
    
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_score (sabr20_score DESC),
    INDEX idx_grade (setup_grade)
);

CREATE TABLE watchlist_history (
    -- Same schema as watchlist_realtime
    -- Stores historical snapshots for analysis
) PARTITION BY RANGE (timestamp);
```

---

## 7. Real-Time Monitoring Integration

### 7.1 Continuous Watchlist Updates

```python
import schedule

def update_watchlist_continuous():
    """
    Continuously update watchlist during market hours.
    Run every 15 minutes.
    """
    if not is_market_open():
        return
    
    # Get candidates from coarse screening
    from prescreening import get_latest_candidates
    candidates = get_latest_candidates()
    
    # Run multi-timeframe analysis
    results = run_multiframe_analysis(candidates['symbol'].tolist())
    
    # Classify setups
    results = apply_setup_classification(results)
    
    # Generate actionable watchlist
    watchlist = generate_actionable_watchlist(results)
    
    # Save to database
    save_watchlist_snapshot(watchlist)
    
    # Trigger alerts for new A+ setups
    check_for_new_alerts(watchlist)
    
    logger.info(f"Watchlist updated: {len(watchlist)} symbols")

# Schedule every 15 minutes
schedule.every(15).minutes.do(update_watchlist_continuous)
```

---

## 8. Alert System

### 8.1 Alert Conditions

Generate immediate alerts when:

```python
def check_for_new_alerts(current_watchlist: pd.DataFrame):
    """Check for conditions requiring immediate alerts."""
    
    # Load previous watchlist
    previous = load_previous_watchlist()
    
    # Find new A+ setups
    new_symbols = set(current_watchlist[current_watchlist['setup_grade'] == 'A+']['symbol'])
    old_symbols = set(previous[previous['setup_grade'] == 'A+']['symbol']) if not previous.empty else set()
    
    newly_qualified = new_symbols - old_symbols
    
    for symbol in newly_qualified:
        row = current_watchlist[current_watchlist['symbol'] == symbol].iloc[0]
        
        send_alert(
            priority='HIGH',
            title=f'New A+ Setup: {symbol}',
            message=f"""
            Symbol: {symbol}
            SABR20 Score: {row['SABR20_score']}
            State: {row['state']}
            Price: ${row['price']:.2f}
            R:R Ratio: {row['rr_ratio']:.2f}
            """
        )
```

---

## 9. Performance Tracking

### 9.1 Watchlist Quality Metrics

Track these metrics daily:

```python
class WatchlistMetrics:
    """Track watchlist performance."""
    
    def calculate_daily_metrics(self, date: str):
        """Calculate metrics for watchlist performance."""
        
        # Load watchlist from date
        watchlist = load_watchlist_snapshot(date)
        
        # Load subsequent trade outcomes
        outcomes = load_trade_outcomes_after(date, days=5)
        
        # Calculate hit rate
        symbols_on_watchlist = set(watchlist['symbol'])
        symbols_that_worked = set(outcomes[outcomes['outcome'] == 'WIN']['symbol'])
        
        hit_rate = len(symbols_on_watchlist & symbols_that_worked) / len(symbols_on_watchlist)
        
        # Average score of winners vs losers
        winners = watchlist[watchlist['symbol'].isin(symbols_that_worked)]
        avg_score_winners = winners['SABR20_score'].mean()
        
        return {
            'date': date,
            'symbols_on_watchlist': len(symbols_on_watchlist),
            'hit_rate': hit_rate,
            'avg_score_winners': avg_score_winners
        }
```

---

## 10. Next Document

**Document 06: Regime and Market Checks** will detail:
- Multi-timeframe regime classification
- Market environment analysis (VIX, sector rotation)
- Risk-on/risk-off detection
- Integration with watchlist filtering
