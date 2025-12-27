
# Release Notes v9.0: The Multi-Strategy Brain (Sniper + Gamma)

**Date:** Dec 27, 2025
**Status:** PROD DEPLOYED

## 🚀 The Paradigm Shift
We have moved from a single-strategy bot to a **Dual-Engine Architecture**. The bot no longer treats every stock the same. It now dynamically assigns the optimal strategy based on the specific "Physics" of the setup.

---

## 🏗️ The Engines

### 1. Strategy A: "THE SNIPER" (Priority)
*   **Philosophy:** "Big Fish Only."
*   **The Setup:** Price Compression so extreme (Bandwidth < 0.15) that the subsequent expansion is explosive.
*   **History:** Based on the legendary v4.0 logic that caught RVNL (+1200% ROI).
*   **Exit Management:** **Loose Leash.**
    *   **Trail:** Activates at +20% profit, trails by 15%.
    *   **Stop:** Wide (-20%). We accept volatility to capture the +100% moves.

### 2. Strategy B: "THE GAMMA" (Secondary)
*   **Philosophy:** "Steady Income."
*   **The Setup:** Standard Volatility Squeeze (Bandwidth < 0.20) on High-Priced Leaders (Bosch, MRF, etc.).
*   **History:** Based on v4.2 logic which proved "Safe & Steady" (+3.19% ROI).
*   **Exit Management:** **Tight Leash (Breathing Room).**
    *   **Trail:** Activates at +10% profit, trails by 5%.
    *   **Stop:** Tight (-10%). We cut losers immediately.

---

## 🛠️ Technical Upgrades
*   **Logic Refactor:** `calculate_confluence_score` replaced by `evaluate_strategies` to support multi-tagging.
*   **Routing:** `scan_market` now tags trades with `SNIPER` or `GAMMA`.
*   **Execution:** `trade_manager` applies different exit math based on the strategy tag.
*   **Structure Filter:** Added `Price > SMA 50` hard block to prevent counter-trend suicide.
*   **Green Candle Rule:** Added `Close > Open` block to prevent catching falling knives.

## ⚠️ Critical Checks
*   [x] **Syntax:** Verified `live_brain.py` compiles correctly.
*   [x] **ML Integrity:** Confirmed ~50 AI Models are present for Nifty stocks.
*   [x] **Fallback:** Confirmed Non-Nifty stocks fallback gracefully to Pure Physics.

**Ready for Monday Market Open.**
