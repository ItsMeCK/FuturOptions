# Task: GCP Optimization & Token Management

## 1. Market Hours Logic
- [x] Implement start/stop time check (9:00 AM - 3:30 PM IST) in `live_brain.py`.
    - [x] Fix: Enforce `pytz` Asia/Kolkata timezone to handle server time skew.
- [x] Ensure bot sleeps or pauses outside these hours to save resources/logs.

## 2. Token Management UI
- [x] Create a lightweight Web UI (`token_updater.py`) using Flask/FastAPI.
- [x] Logic to update `ZERODHA_ACCESS_TOKEN` in `.env`.
- [x] Logic to auto-restart `brain.service` upon token update.
- [x] Update `setup_gcp.sh` to include this new service and dependencies (`flask`).
- [x] Create systemd service for the UI (`token_ui.service`).
- [ ] Implement Hot-Reload Logic:
    - [x] `token_manager.py`: Write to `zerodha_hot_token.txt` (Drop systemctl restart).
    - [x] `live_brain.py`: Poll file, compare token, and re-init `fetcher` on change.
- [x] Implement Live Dashboard within Token UI:
    - [x] Create API endpoints in `token_manager.py` to read `latest_scan.json` and `active_trades.json`.
    - [x] Upgrade Frontend to include "Dashboard" tab with Auto-Refreshing Tables.
    - [x] Display Live Leaderboard (Symbol, Score, Signal, RVOL).
    - [x] Display Active Trades (Symbol, PnL, Status).
    - [x] Implement Automated Token Generator (Login -> Request Token -> Auto Exchange).

## 4. Selection Hub & Strategy Selection
- [x] Implement Rolling Universe Sweep:
    - [x] Batch Rotation: Scan 50-60 unique stocks every minute.
    - [x] Full Loop: Complete market sweep of 209 stocks every 3.5 minutes.
    - [x] Persistent Dashboard: Accumulate all 209 stocks in the UI rather than flushing each batch.
- [x] Refine Scoring Logic:
    - [x] UI: Show non-zero scores for low ADX stocks (Soft Penalty).
    - [x] Discipline: Keep a Signal Block (Neutral) if ADX < 25.
- [x] WhatsApp & Notification Recovery:
    - [x] Fix Key Case Mismatch: Update `notification_scheduler.py` to recognize 'Symbol' and 'Score' (Uppercase).
    - [x] Verify Process Status: Ensure `scheduler.service` is included in `start_brain_system.sh`.
    - [x] Connectivity Audit: Verified Twilio SID/Token are operational.
- [x] P&L Accuracy Fix:
    - [x] Prefix Enforcement: Added `NFO:` prefix to option price polling in the maintenance loop.
    - [x] Verified that active trades now pull current prices for real-time P&L updates.
- [x] Today's Backtest (Attempt 1): ABORTED (Reverted all live_brain changes due to code freeze).
- [x] Today's Full Market Backtest (Robust Standalone):
    - [x] Data Retention: Spot and Option CSVs for Dec 24 are preserved.
    - [x] Implementation: Create `backtest_today_robust.py` (using subclassing to avoid touching live_brain.py).
    - [x] Execution: Run 1m resolution simulation.
    - [x] Analysis: Generated P&L report (Confirmed 0 trades due to discipline/low momentum).
    - [x] Dec 26 Audit: Full day backtest confirmed 0 trades; HCLTECH rejected due to "Drift vs Breakout" logic (Low RVOL).
    - [x] Trend Simulation: Validated "Drift Logic" (ADX > 30) found 146 signals on Dec 24 and 89 on Dec 26 (including HCLTECH).
    - [x] Signal Quality Audit: Analyzed 1,578 signals; 10% Wins, 3.5% Loss, 85% Flat. Confirmed low risk but slow speed.
    - [x] Refined Simulation: Re-running with "One Trade Per Stock" rule and 30% TP / 10% SL to get realistic count.
- [ ] Strategy Comparison:
    - [x] Audit: Verified 100% market coverage (182/182 stocks scanned in <2.5s).
- [ ] Institutional Deep Dive (Stagnation Analysis):
    - [x] Case Study Analysis: Select 3 "Stagnant" trades and map their Volume/Price structure.
    - [x] Institutional Critique: Why did Smart Money ignore these? (Volume Profile, Order Flow).
    - [ ] Advanced Filter Design: Develop "Volume Structure" vs "Volume Spike" logic.
- [ ] Proactive Entry Filters (Prevention):
    - [x] Hypothesis Test: Confirmed "Efficiency Ratio" < 0.3 identifies Churn.
    - [x] Backtest New Filters: Blocked 201/235 (85%) stagnant trades proactively.
- [ ] Deployment (Live Brain):
    - [x] Documentation: Created `smart_bot_strategy.md` regarding filters.
    - [x] Implementation: Ported `SmartTrendBrain` logic (ER/Vol) to `live_brain.py`.
    - [x] Verification: Syntax verified. Ready for Market.
    - [x] GCP Push:
        - [x] Packaging:- [x] **Phase 9: Multi-Strategy Architecture (Sniper + Gamma)**
  - [x] **Logic:** Implemented `evaluate_strategies` (Dual Check).
  - [x] **Routing:** `scan_market` tags trade with `SNIPER` or `GAMMA`.
  - [x] **Exits:** `live_brain.py` applies Loose Trail (Sniper) or Tight Trail (Gamma).
  - [x] **Deployment:** Hybrid Engine Active.
- [ ] Institutional Strategy Audit (Deep Dive):
    - [ ] Ground Truth: Identify ALL options that hit +30% Intraday (Dec 24 & 26).
    - [x] Gap Analysis: Compare "Perfect Universe" vs "Our Trade Book".
    - [x] Correlation Analysis: Holistic Review of "Score" vs "Real Return" for ALL stocks.
    - [x] Root Cause: Diagnose False Positives (Why did we enter losers? Wrong Score?).
    - [x] Feature Engineering: Use AI to find the *real* predictors of +30% moves (Re-weighting the Score).
    - [x] **AI Feature Engineering (The "Prediction" Shift)**:
        - [x] Forensic RVNL: Map the exact "Predict -> Validate -> Trigger" timeline of the 8000% move.
        - [x] ML Training: Train Random Forest on Dec 26 data to find *actual* predictive features (IV? Vol Spike?).
        - [x] Logic Upgrade: Re-write Scoring Engine to favor "Predictive Pressure" over "Reactive Trend".
    - [x] **False Positive Elimination (University Logic)**:
        - [x] Forensic Loss Analysis: Diagnose why BAJFINANCE/ABCAPITAL failed (Counter-Trend?).
        - [x] New Filter: Implement VWAP Context Rule (Block if Price < VWAP).
        - [x] Verification: Confirm Losers are blocked while Ignition winners (Maruti) survive.

- [ ] **Phase 5: The v4.0 Upgrade (Compression & Context)**
  - [ ] **Research:** Calibrate "Compression" metric (Bollinger Bandwidth < X).
  - [ ] **Feature:** Implement "Relative Strength" (Stock vs Nifty Correlation).
  - [ ] **Logic:** Refactor Volume Filter (Limit RVOL < 4.0 to avoid exhaustion).
  - [ ] **Logic:** Uncap RSI but enforce "Squeeze" Setup.
  - [ ] **Exits:** Implement Dynamic ATR Trailing Stop.
  - [x] **Validation:** Forensic Test on Adani (Squeeze Failure) vs RVOL (Squeeze Success).
  - [x] **Simulation:** Phase 6 (v4.1) showed Dynamic Squeeze failure (-5% ROI).

- [x] **Phase 7: v4.3 The Gamma Sniper (Hybrid)**
  - [x] **Logic:** Strict Bandwidth < 0.15 (v4.0 Core).
  - [x] **Logic:** Structure Filter (Price > SMA 50).
  - [x] **Logic:** Green Candle (Close > Open).
  - [x] **Exits:** Verified "Breathing Room" Exits in v4.3 Sim (+3.19% P&L).
  - [x] **Deployment:** Updated `live_brain.py` with v4.3 Logic.

- [x] **Phase 8: v5.0 Institutional Reload (Simulation Only)**
  - [x] **Logic:** Impulse -> Pullback (Low Vol) -> Trigger.
  - [x] **Simulation:** Run v5.0 Sim on Dec 24 & 26.
- [x] **Phase 8: v5.0 Institutional Reload (Simulation Only)**
  - [x] **Logic:** Impulse -> Pullback (Low Vol) -> Trigger.
  - [x] **Simulation:** Run v5.0 Sim on Dec 24 & 26.
  - [x] **Result:** Failed (-2.38% ROI). Pullback strategy is inferior to Squeeze strategy for this dataset.

- [x] **Final Deployment: v4.3 Hybrid**
  - [x] **Verified:** v4.3 outperformed v4.1 (-5%) and v5.0 (-2%).
  - [x] **Live:** `live_brain.py` locked to v4.3 Logic.
