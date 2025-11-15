# Multi-Timeframe Decision Tree and Screening Blueprint

This document turns the algorithm and system into:

1. A **yes/no decision tree** a human can follow in real time.
2. A **screening blueprint** that can be implemented in code or charting-platform screeners.
3. A simple **scoring model** to rank candidates.

---

## 1. High-Level Decision Tree (Human Workflow)

Assume you are evaluating a single ticker at a given moment.

### STEP 1 – Regime Check (T₃: 4h or Daily)

**Q1. Is the higher-timeframe momentum hostile?**

- Check MACD histogram (T₃):
  - If it is strongly negative and **still decreasing**, answer = YES → *Reject trade*.
- Check RSI (T₃):
  - If \(R^{(T₃)} < 30\) **and still falling**, answer = YES → *Reject trade*.

If both are NO, mark **Regime = OK** and proceed.

---

### STEP 2 – Intermediate Trend (T₂: 1h)

**Q2. Is T₂ showing early signs of upside rotation?**

Require ALL:

1. \(H^{(T₂)}_t > H^{(T₂)}_{t-1}\) (MACD histogram rising).  
2. Price closed at or above middle Bollinger band (or within ~1% below).  
3. Stoch RSI not overbought (both K and D < 80).

If all three are satisfied → **Trend Confirmation = YES**.  
Otherwise → either *skip* or *flag as early watch* but **do not enter yet**.

---

### STEP 3 – Trigger Check (T₁: 15m/30m)

**Q3. Did price recently interact with lower Bollinger and now break above mid-band?**

- Within last 3–5 bars, was close ≤ lower band?  
- Current close ≥ middle band?  

If YES → proceed.

**Q4. Is Stoch RSI giving a fresh oversold up-cross?**

- Previous bar: K and D ≤ 20.  
- Current bar: K > D and K ≥ 25.  

If YES → proceed.

**Q5. Is MACD histogram bottoming and turning up?**

- Two bars ago < previous bar < 0.  
- Current bar ≥ previous bar (preferably > 0).  

If YES → proceed.

**Q6. Is RSI rising but not overbought?**

- Current RSI ≥ prior RSI.  
- 30 ≤ RSI ≤ 60.  

If YES → **Trigger = TRUE**.

If any of Q3–Q6 are NO, either skip or classify as *pre-trigger watch*.

---

### STEP 4 – Trade Classification

Based on how many layers align:

- **A+ Setup**: Regime OK, Trend Confirmation YES, Trigger TRUE, and price structure clean (no nearby resistance within 1.5R).  
- **B Setup**: Regime OK, Trigger TRUE, but Trend Confirmation marginal (e.g., MACD rising but price still slightly below T₂ mid-band).  
- **C Setup**: Some but not all conditions; use only for experimental or paper-trade logs.

Only A+ setups should be traded with full intended risk.

---

## 2. Programmatic Screening Blueprint

### 2.1 Universe Filter

Apply once per day (e.g., on daily data):

- Avg volume ≥ threshold (e.g., 500k shares).  
- Price between bounds (e.g., 1–100 USD).  
- Optional: exclude ADRs, ETFs, or penny stocks per your rules.

### 2.2 Regime Filter (T₃)

Compute MACD and RSI on 4h or daily bars.

Keep tickers where:

- MACD histogram today ≥ yesterday; and  
- RSI ≥ 30 **or** RSI rising; and  
- Not making fresh 20-bar low.

This reduces the universe to names where a bullish reversal is at least plausible.

### 2.3 Intermediate Filter (T₂ – 1h)

For each remaining ticker:

- Condition 1: \(H^{(T₂)}_t > H^{(T₂)}_{t-1}\).  
- Condition 2: \(C^{(T₂)}_t ≥ 0.99·MB^{(T₂)}_t\).  
- Condition 3: \(K^{(T₂)}_t < 80\) and \(D^{(T₂)}_t < 80\).

Keep only those where all 3 are true.

### 2.4 Trigger Filter (T₁ – 15m/30m)

For each of the remaining tickers:

1. **Lower-band interaction**  
   - ANY of last 5 bars have `close <= lower_band * 1.02`.

2. **Mid-band break now**  
   - Current bar `close >= mid_band`.

3. **Stoch oversold cross**  
   - `k_prev <= 20 and d_prev <= 20`  
   - `k_now > d_now and k_now >= 25`.

4. **MACD histogram bottoming**  
   - `hist_2 < hist_1 < 0 and hist_now >= hist_1`.

5. **RSI rising in the middle zone**  
   - `rsi_now >= rsi_prev and 30 <= rsi_now <= 60`.

Tickers that satisfy all conditions are **ready-to-trade candidates**.

---

## 3. Example Scoring Function

Instead of a hard pass/fail, define a score:

```text
Score = w1 * f_regime + w2 * f_trend + w3 * f_trigger + w4 * f_structure
```

Where:

- **f_regime** (0–1)  
  - 1.0 if all regime conditions strong.  
  - 0.5 if mixed (e.g., MACD flat, RSI rising from <30).  
  - 0 otherwise.

- **f_trend** (0–1)  
  - 1.0 if all T₂ filters pass.  
  - 0.5 if only some pass.

- **f_trigger** (0–1)  
  - 1.0 if all T₁ filters pass.  
  - 0.5 if near-miss but promising.

- **f_structure** (0–1)  
  - Down-rank names with nearby resistance or messy price action.

You can then **rank by Score** and start with top N symbols.

---

## 4. Implementation Hints

### 4.1 Python / pandas Pipeline Sketch

At a high level (per symbol):

```python
def screen_symbol(data_15m, data_1h, data_4h):
    regime_ok = regime_filter(data_4h)
    if not regime_ok:
        return 0.0  # score

    trend_ok = trend_filter(data_1h)
    trigger_ok = trigger_filter(data_15m)

    score = (
        1.0 * float(regime_ok) +
        1.5 * float(trend_ok) +
        2.0 * float(trigger_ok)
    )
    return score
```

You would vectorize over symbols using your preferred backtest framework.

### 4.2 TradingView-Style Screener Conditions (Conceptual)

On the **1h timeframe**:

- `stoch_rsi_k(14,14,3,3) < 80`  
- `macd_hist(12,26,9) > macd_hist(12,26,9)[1]`  
- `close >= bb_mid(close, 20, 2)`

On the **15m timeframe**:

- `lowest(close, 5) <= bb_low(close, 20, 2) * 1.02`  
- `close >= bb_mid(close, 20, 2)`  
- `stoch_rsi_k[1] <= 20 and stoch_rsi_d[1] <= 20`  
- `stoch_rsi_k > stoch_rsi_d and stoch_rsi_k >= 25`  
- `macd_hist[2] < macd_hist[1] and macd_hist[1] < 0 and macd_hist >= macd_hist[1]`  
- `rsi(14) >= rsi(14)[1] and rsi(14) >= 30 and rsi(14) <= 60`

Plus higher-timeframe (4h/daily) regime rules.

You can translate this logic into a Pine Script to drive custom alerts.

---

## 5. Quick Reference Checklist

For fast discretionary screening, here is a compressed checklist:

1. **4h / Daily**
   - [ ] MACD histogram not making new lows.  
   - [ ] RSI rising from ≥ 25–30.  
   - [ ] Not at multiweek low.

2. **1h**
   - [ ] MACD histogram rising (ideally positive).  
   - [ ] Price at or above middle Bollinger band.  
   - [ ] Stoch RSI not overbought (<80).

3. **15m / 30m**
   - [ ] Recent touch / ride on lower Bollinger band.  
   - [ ] Current close breaks above mid-band.  
   - [ ] Stoch RSI: oversold last bar, now crossing up.  
   - [ ] MACD histogram: deep red → flatten → rising (prefer first green).  
   - [ ] RSI rising from 30–60 zone.

If all items are checked, you have the system’s **ideal setup**.

---

This decision-tree file, together with `01_algorithm_spec.md` and `02_mean_reversion_trend_system.md`, gives you everything needed to:

- Scan universes of stocks for the pattern.
- Make consistent discretionary decisions.
- Implement fully automated screeners and backtests.
