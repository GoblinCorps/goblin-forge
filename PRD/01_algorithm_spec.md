# Multi-Timeframe Momentum Reversal Algorithm
(*Backtest-ready specification based on Bollinger Bands, Stoch RSI, MACD, and RSI*)

---

## 1. Instruments and Timeframes

- **Universe**: liquid stocks (e.g., average daily volume ≥ 500k; price between 1 and 100 USD; adjust as needed).
- **Trigger timeframe (T₁)**: 15m or 30m (intraday entries).
- **Confirmation timeframe (T₂)**: 1h.
- **Regime timeframe (T₃)**: 4h (or daily for swing bias).

You can run the same logic with any trio of nested timeframes; the ratios ~2–4× between frames are what matter.

---

## 2. Indicator Definitions

All parameters are configurable; values below are reasonable defaults and backtest starting points.

Let each candle at time *t* have close price \(C_t\).

1. **Bollinger Bands (BB)**  
   - Period: \(n_{BB} = 20\)  
   - Std dev: \(k_{BB} = 2\)  
   - Middle band: \(MB_t = SMA_{20}(C)_t\)  
   - Upper band: \(UB_t = MB_t + k_{BB}·\sigma_{20}(C)_t\)  
   - Lower band: \(LB_t = MB_t - k_{BB}·\sigma_{20}(C)_t\)

2. **Stochastic RSI (StochRSI)**  
   - Base RSI: period \(n_{RSI} = 14\)  
   - Stoch lookback: \(n_{Stoch} = 14\)  
   - Signal smoothing: \(k\_len = 3\), \(d\_len = 3\)  
   - %K and %D lines: \(K_t, D_t ∈ [0, 100]\)

3. **MACD (Moving Average Convergence Divergence)**  
   - Fast EMA: \(n\_f = 12\)  
   - Slow EMA: \(n\_s = 26\)  
   - Signal EMA: \(n\_{sig} = 9\)  
   - MACD line: \(M_t = EMA\_{12}(C)_t - EMA\_{26}(C)_t\)  
   - Signal line: \(S_t = EMA\_{9}(M)_t\)  
   - Histogram: \(H_t = M_t - S_t\)

4. **RSI (or Ultimate RSI indicator)**  
   - Standard RSI: period 14.  
   - We will use RSI value \(R_t ∈ [0, 100]\) and its slope \(ΔR_t = R_t - R_{t-1}\).

5. **Heikin-Ashi candles (optional but assumed from your charts)**  
   - Used mainly to visually smooth price; algorithmically we still rely on close prices and indicator values.

---

## 3. Qualitative Setup Description

The target setup is a **momentum reversal from a volatility-compressed downswing into an upside expansion**, characterised by:

1. Price riding the **lower Bollinger band**, then **rejecting** it and crossing the **middle band upward**.
2. **Stoch RSI** crossing up from oversold (≤ 20).
3. **MACD histogram** bottoming (red bars shrinking) and then turning green.
4. **RSI** bottoming and starting to rise but still **below classical overbought** levels (typically 30–60 depending on timeframe).
5. On higher timeframes, bearish momentum is **slowing or neutral**, not accelerating.

---

## 4. Regime Filter (T₃ – 4h or Daily)

We want to avoid trading against strong higher‑timeframe downtrends.

Define regime conditions on T₃:

- **Regime bullish or neutral** if all of the following hold:
  1. \(H^{(T₃)}_t ≥ H^{(T₃)}_{t-1}\) (MACD histogram non‑decreasing; bearish momentum not increasing).
  2. \(R^{(T₃)}_t ≥ 35\) (not deeply oversold) **or** \(ΔR^{(T₃)}_t ≥ 0\) (RSI rising).
  3. Close price not making fresh multi-week lows in the last \(N\_{low}\) candles (e.g., last 20 candles).

If any of the above are violated, label the regime **hostile** and either:
- Skip trades in this ticker, or
- Reduce position size and require stronger trigger conditions.

---

## 5. Confirmation Filter (T₂ – 1h)

On T₂ ensure that:

1. **MACD histogram rising**:  
   \(H^{(T₂)}_t > H^{(T₂)}_{t-1}\)
2. **Stoch RSI not overbought** at entry:  
   \(K^{(T₂)}_t < 80\) and \(D^{(T₂)}_t < 80\)
3. Price is **above or near the middle Bollinger band**:  
   \(C^{(T₂)}_t ≥ MB^{(T₂)}_t\ · (1 - ε\_{MB})\) with \(ε\_{MB} ≈ 0.01\).

This filter confirms that the reversal seen on T₁ is propagating to the higher timeframe.

---

## 6. Trigger Conditions (T₁ – 15m or 30m)

The **entry signal** occurs on the trigger timeframe when **all** of the following are true at bar *t*:

### 6.1 Volatility & Location

1. **Prior compression / lower-band interaction**:  
   - At least one of the last \(m\) candles (e.g., \(m = 5\)) has  
     \(C^{(T₁)}_{t-k} ≤ LB^{(T₁)}_{t-k} · (1 + ε\_{LB})\) with \(ε\_{LB} ≈ 0.01–0.02\).  
   - Current close is **at or above** middle band:  
     \(C^{(T₁)}_t ≥ MB^{(T₁)}_t\).

2. **Band expansion starting** (optional but powerful):  
   - Bandwidth \(BW_t = UB_t - LB_t\) satisfies \(BW_t > BW_{t-1}\) and \(BW_{t-1} ≤ BW\_{avg}\)  
     where \(BW\_{avg}\) is the rolling mean of \(BW\) (period 20).

### 6.2 Stoch RSI Momentum

3. **Oversold cross up**:  
   - \(K^{(T₁)}_{t-1} ≤ 20\) and \(D^{(T₁)}_{t-1} ≤ 20\)  
   - \(K^{(T₁)}_t > D^{(T₁)}_t\) and \(K^{(T₁)}_t ≥ 25\).

This encodes “deep oversold, then aggressive curl upward.”

### 6.3 MACD Momentum

4. **Histogram bottom and inflection**:  
   - \(H^{(T₁)}_{t-2} < H^{(T₁)}_{t-1} < 0\) (red bars getting less negative), and  
   - \(H^{(T₁)}_t ≥ H^{(T₁)}_{t-1}\).  
   - Optional stronger trigger: \(H^{(T₁)}_t > 0\) (first green bar).

5. **MACD line vs signal** (optional):  
   - \(M^{(T₁)}_t ≥ S^{(T₁)}_t\) **or** distance narrowing:  
     \(|M^{(T₁)}_t - S^{(T₁)}_t| < |M^{(T₁)}_{t-1} - S^{(T₁)}_{t-1}|\).

### 6.4 RSI State

6. **RSI rising, not yet overbought**:  
   - \(R^{(T₁)}_t ≥ R^{(T₁)}_{t-1}\) and \(R^{(T₁)}_t ∈ [30, 60]\).

---

## 7. Entry Rule

**Long Entry at time \(t\_0\) on timeframe T₁:**  
Enter at next bar’s open (or limit near \(C^{(T₁)}_{t_0}\)) if:

- Regime filter (T₃) is bullish/neutral, and  
- Confirmation filter (T₂) holds at \(t_0\), and  
- Trigger conditions (Section 6) all hold at \(t_0\).

Position size \(Q\) should be set via risk management (see System doc).

---

## 8. Exit Rules

Define three layers: **profit target**, **hard stop**, and **time/structure stop**.

### 8.1 Initial Stop-Loss

The stop is placed at the more conservative of:

1. A multiple of ATR on T₁ below entry, e.g.:  
   \(SL = EntryPrice - k\_{ATR}·ATR^{(T₁)}_{t_0}\) with \(k\_{ATR} ∈ [1.2, 2.0]\).

2. A volatility/structure level, e.g.:
   - Below recent swing low on T₁.
   - Or below lower Bollinger band: \(SL ≤ LB^{(T₁)}_{t_0}\).

### 8.2 Profit Targets

Example tiered structure:

- **TP1 (scalp/partial)**: +2–3× initial risk (R).  
- **TP2 (trend)**: when RSI on T₁ crosses above 70 or price touches **upper Bollinger band** on T₂.  
- **Optional runner**: keep a small fraction until MACD histogram on T₂ starts declining for 2–3 bars.

### 8.3 Time & Momentum Stop

Close remaining position if any of the following occur:

1. On T₁, Stoch RSI crosses down from >80 to <80 **and** MACD histogram declines for ≥ 2 bars.
2. On T₂, close falls back below middle Bollinger band after failing to reach upper band.
3. Time-based stop: after **N** bars (e.g., 12–16 on T₁) if price has not reached at least 1R.

---

## 9. Screening Logic (Quantitative Filters)

To screen thousands of tickers, you can first run **coarse filters**, then apply full trigger logic.

### 9.1 Coarse Screener (single timeframe, e.g. 1h)

For each symbol at current bar \(t\):

1. **Volatility & price constraints**  
   - Avg true range, liquidity, price bounds.

2. **Stoch RSI oversold curl candidate**  
   - \(K_t ≥ D_t\)  
   - \(\min(K_{t-3..t}, D_{t-3..t}) ≤ 20\)  
   - \(K_t ≤ 40\).

3. **MACD histogram bottoming**  
   - \(H_t > H_{t-1}\) and \(H_{t-1} < 0\).

4. **Price near lower/middle Bollinger**  
   - \(C_t ≤ MB_t\)  
   - \(C_{t-3..t} ≤ MB_{t-3..t} + 0.5·(UB_{t-3..t}-MB_{t-3..t})\)
     (i.e., mostly in lower half of band).

Tickers passing this go to **fine filter**.

### 9.2 Fine Filter (full multi-timeframe)

For each remaining ticker:

- Apply Regime filter on T₃.  
- Apply Confirmation filter on T₂.  
- Apply full Trigger conditions on T₁.

If all pass, label ticker as **Setup = TRUE**.

You can also assign a **score**:

\[
Score = w\_1·z(H^{(T₁)}) + w\_2·z(ΔR^{(T₁)}) + w\_3·z(BandExpansion^{(T₁)}) + w\_4·z(H^{(T₂)})
\]

where \(z(·)\) is a z-score or scaled feature, and \(w\_i\) are weights.

---

## 10. Pseudocode (Python-style, vectorized)

Below is high-level pseudocode for a single symbol:

```python
def compute_setup(df_T1, df_T2, df_T3):
    # df_* contain OHLCV + indicators per timeframe, aligned on their own index.
    # Assume latest index is 't' for each.

    # --- Regime filter on T3 ---
    ok_regime = (
        df_T3["macd_hist"].iloc[-1] >= df_T3["macd_hist"].iloc[-2] and
        (df_T3["rsi"].iloc[-1] >= 35 or
         df_T3["rsi"].iloc[-1] >= df_T3["rsi"].iloc[-2])
    )

    if not ok_regime:
        return False

    # --- Confirmation filter on T2 ---
    t2 = df_T2.iloc[-1]
    t2_prev = df_T2.iloc[-2]

    ok_conf = (
        t2["macd_hist"] > t2_prev["macd_hist"] and
        t2["stoch_k"] < 80 and t2["stoch_d"] < 80 and
        t2["close"] >= t2["bb_mid"] * 0.99
    )
    if not ok_conf:
        return False

    # --- Trigger on T1 ---
    t1 = df_T1.iloc[-1]
    t1_prev = df_T1.iloc[-2]
    t1_prev2 = df_T1.iloc[-3]

    recent = df_T1.iloc[-5:]

    lower_touch = (recent["close"] <= recent["bb_low"] * 1.02).any()
    mid_break = t1["close"] >= t1["bb_mid"]

    stoch_ok = (
        t1_prev["stoch_k"] <= 20 and t1_prev["stoch_d"] <= 20 and
        t1["stoch_k"] > t1["stoch_d"] and t1["stoch_k"] >= 25
    )

    macd_ok = (
        t1_prev2["macd_hist"] < t1_prev["macd_hist"] < 0 and
        t1["macd_hist"] >= t1_prev["macd_hist"]
    )

    rsi_ok = (
        t1["rsi"] >= t1_prev["rsi"] and
        30 <= t1["rsi"] <= 60
    )

    trigger = lower_touch and mid_break and stoch_ok and macd_ok and rsi_ok

    return trigger
```

You can adapt this into a vectorized backtest or screener across many tickers.

---

## 11. Notes for Backtesting

1. **No lookahead**: use only fully closed candles; entry at next-bar open.
2. **Survivorship bias**: use a survivorship-bias-free universe for serious research.
3. **Transaction costs & slippage**: include realistic spreads, fees, and slippage assumptions.
4. **Parameter sweeps**: grid-search over thresholds (e.g., Stoch oversold 10–30, RSI bands 25–45–65, etc.).
5. **Regime robustness**: test performance in different volatility regimes (e.g., low VIX vs high VIX environments).
