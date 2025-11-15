# Mean-Reversion → Trend-Expansion Trading System
(*Risk management, execution, and workflow built around the Momentum Reversal Algorithm*)

---

## 1. System Overview

The system exploits a **transition from a compressed, oversold state (mean reversion)** into a **persistent upside move (trend expansion)**, detected by:

- Lower Bollinger band interaction and mid-band break.
- Stoch RSI oversold to up-cross.
- MACD histogram inflection from deep red to rising/green.
- RSI rising from depressed levels.

The **algorithm spec** is given in `01_algorithm_spec.md`; this document adds **risk, execution, and process**.

---

## 2. Timeframe Roles

- **T₁ (15m/30m)** – *Execution / trigger.*  
  Used for entries, tactical stop adjustments, and intraday exits.

- **T₂ (1h)** – *Trend confirmation.*  
  Determines whether to hold beyond the initial impulse and whether to trail stops.

- **T₃ (4h or Daily)** – *Regime context.*  
  Avoids trading against strong higher-timeframe downtrends and identifies favourable environments.

---

## 3. Trade Types

1. **Intraday Momentum Scalps**
   - Entry on T₁.
   - Target: 1.5–3R within the same session.
   - Exit based on T₁ signals (Stoch RSI overbought, MACD histogram rolling over).

2. **Short Swing (1–3 days)**
   - Entry on T₁ when T₂ is turning up.
   - Hold as long as T₂ MACD histogram rises and price remains above T₂ middle Bollinger band.
   - Exit on T₂ weakness.

3. **Position Trades (multi-day to multi-week)**
   - Entry when the same setup occurs on T₂ with T₃ confirmation.
   - T₁ used only for fine-tuning entry and risk.

---

## 4. Risk Management Framework

### 4.1 Account-Level Constraints

Define:

- **Max risk per trade**: \(r\_{trade} ∈ [0.25\%, 1.0\%]\) of account equity.  
- **Max concurrent risk**: \(r\_{total} ≤ 3\%\) (sum of open position risks).
- **Max positions**: determine by operational capacity (e.g. 3–8).

### 4.2 Position Sizing

For a long entry at price \(P\_{entry}\) with stop at \(P\_{SL}\):

- Per-share risk: \(R\_{share} = P\_{entry} - P\_{SL}\).
- Dollar risk per trade: \(R\_{dollar} = r\_{trade} · Equity\).
- Share size: \(Q = \left\lfloor \frac{R\_{dollar}}{R\_{share}} \right\rfloor\).

Optionally cap \(Q\) by maximum position notional (e.g., 10–20% of equity).

### 4.3 Volatility Normalisation

To avoid over-sizing high-volatility names, enforce:

- \(R\_{share} ≥ 0.8·ATR^{(T₁)}\).
- If calculated stop is tighter than that, widen stop to \(0.8\)–\(1.2·ATR\) and reduce size accordingly.

---

## 5. Entry Execution

1. Identify candidates via **screener** (see Algorithm and Decision-Tree docs).
2. Validate visually (optional but strongly recommended), ensuring:
   - Clean lower-band interaction.
   - No immediate overhead resistance cluster within 1–1.5R (recent swing highs, gaps).
3. Place orders:
   - **Primary**: market or limit near current price at next T₁ bar open after signal close.
   - **Stop**: hard stop at \(P\_{SL}\) immediately on entry; OCO with TP if your broker supports it.
   - **Alert**: set alerts near key levels (e.g., T₂ upper band, major resistance).

---

## 6. Trade Management

### 6.1 Intraday Management (T₁)

- Trail stop to just below *new* higher lows once price advances ≥ 1R.
- Consider partial profit at 1.5–2R:
  - Sell 1/3–1/2 of position.
  - Move stop on remainder to breakeven or small profit.

### 6.2 Trend Management (T₂)

If the move remains strong and you wish to swing:

1. **Hold** as long as:
   - T₂ price stays above middle Bollinger band.
   - T₂ MACD histogram is non‑decreasing (or remains > 0).
2. **Reduce / exit** when:
   - T₂ Stoch RSI crosses down from >80 **and** MACD histogram falls for ≥ 2 bars.
   - T₂ close closes below middle band after failing near upper band.

### 6.3 Higher-Timeframe Exit (T₃)

For position trades:

- Exit when T₃ MACD histogram turns down for ≥ 2 bars **and** RSI flattens or falls from overbought.
- Alternatively, use a weekly or 4h close below middle band as a structural exit.

---

## 7. Integration with a Daily Workflow

### 7.1 Pre-Market / Pre-Session

1. **Run coarse screener** on T₂ (1h) or T₃ (4h/daily) to find potential reversals.  
2. Label candidates:
   - A-tier: all filters passed, clean structure.
   - B-tier: slightly weaker, e.g., messy price action, illiquid.
3. Build a **watchlist** of A-tier names.

### 7.2 Intraday

1. On T₁ (15m/30m), watch for triggers on the pre-built watchlist.
2. When trigger fires, re-check:
   - Spread and depth acceptable.
   - No imminent major event (earnings, news spike) unless your strategy allows it.
3. Execute trade per rules.

### 7.3 End-of-Day

1. Log each trade:
   - Symbol, timeframes, entry/exit, risk, R-multiple, screenshots of setup.
2. Update statistics:
   - Win rate, average R, payoff ratio, expectancy.
3. Tag trades by pattern strength (e.g., “perfect confluence”, “weak regime”, etc.).

---

## 8. Parameter & Variant Ideas

1. **Aggressive variant**  
   - Enter when MACD histogram is still negative but clearly rising for ≥ 3 bars.  
   - Use tighter stops and smaller size.

2. **Conservative variant**  
   - Require first green histogram bar on both T₁ **and** T₂.  
   - Require RSI on T₂ ≥ 45.

3. **Re-entry logic**  
   - After taking profit, re-enter if:  
     - Price retests T₁ middle band without violating regime filters, and  
     - Stoch RSI cycles down to 40–50 then up again, while MACD histogram stays positive.

---

## 9. Performance Evaluation

For rigorous evaluation:

1. **Backtest per symbol and grouped by market cap / sector.**
2. Track performance by:
   - Volatility regime (e.g., VIX quartiles, index trend).
   - Time-of-day segments for intraday strategies.
3. Assess sensitivity to:
   - Stop distance, profit targets.
   - Stoch RSI thresholds (10 vs 20 vs 30).
   - MACD histogram requirements (first green vs simply rising).

Look for **robustness**: profitable regions that are wide in parameter space rather than narrow peaks.

---

## 10. Implementation Stack Suggestions

- Data: polygon.io, Alpaca, Interactive Brokers, or local HDF5/Parquet store.
- Analysis/backtest: pandas, NumPy, vectorbt / backtrader / zipline / your own engine.
- Screening: 
  - Offline batch (nightly) using Python on full universe.
  - Real-time or near real-time using a message queue and microservices, or platform-native screeners (e.g., TradingView conditions using equivalent logic).

---

## 11. System Boundaries and Risk

- This pattern **does not guarantee** reversals; it statistically tilts odds when validated on historical data.
- Expect clusters of false signals, particularly during strong bear trends or news-driven moves.
- The edge is realised through:
  - Strict adherence to entry & exit rules.
  - Controlled position sizing.
  - Consistent execution over a large sample of trades.

Combine this document with `01_algorithm_spec.md` and `03_decision_tree_and_screening.md` for a full end-to-end implementation.
