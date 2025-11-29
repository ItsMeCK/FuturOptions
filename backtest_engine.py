import pandas as pd
import numpy as np
import joblib
import os
import matplotlib.pyplot as plt

import glob

def run_backtest():
    data_dir = "ai_option_brain/data/processed"
    model_dir = "ai_option_brain/models"
    results_dir = "ai_option_brain/results"
    os.makedirs(results_dir, exist_ok=True)
    
    print("🧪 Starting Mass Backtest (Nifty 50)...")
    print("="*60)
    
    # Scan for all processed training data
    files = glob.glob(f"{data_dir}/*_training_data.csv")
    print(f"   Found {len(files)} datasets.")
    
    for file_path in files:
        # Extract Symbol
        filename = os.path.basename(file_path)
        symbol = filename.replace("_training_data.csv", "")
        
        # 1. Load Data & Model
        model_path = f"{model_dir}/{symbol}_rf_vol.pkl"
        
        if not os.path.exists(model_path):
            print(f"⚠️ Model missing for {symbol}. Skipping.")
            continue
            
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        model = joblib.load(model_path)
        
        # 2. Re-create the STRICT Test Split (Date Based)
        # Must match training split exactly
        split_date = pd.Timestamp("2025-06-01")
        test_df = df[df['date'] >= split_date].copy()
        
        if test_df.empty:
            print(f"⚠️ No test data found for {symbol} after {split_date}")
            continue
            
        print(f"📉 Backtesting {symbol} on {len(test_df)} unseen candles...")
        print(f"   Period: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # 3. Prepare Features
        # We need 'trend_dist' for the filter, so let's keep it in test_df but exclude from model input if it wasn't a feature
        # Actually, trend_dist WAS a feature in training.
        
        drop_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'target_rv', 'log_ret']
        # features = [c for c in test_df.columns if c not in drop_cols] 
        # The above line might include 'trend_dist' if it's in the csv.
        # Let's verify if trend_dist is in the csv.
        
        features = [c for c in test_df.columns if c not in drop_cols]
        X_test = test_df[features]
        
        # 4. Generate Predictions (The "Brain's View")
        test_df['predicted_rv'] = model.predict(X_test)
        
        # 5. Simulate Strategy: "Vol Arbitrage"
        # Proxy: Market Price = Current 20-Day Historical Volatility (hv_20)
        # Logic:
        #   - If Predicted RV < Market HV (Brain says "Calm") -> SELL VOL (Short Straddle)
        #   - If Predicted RV > Market HV (Brain says "Chaos") -> BUY VOL (Long Straddle)
        
        # P&L Calculation (Theoretical Vol Points):
        #   - Short Vol P&L = Market_HV - Actual_Future_RV
        #   - Long Vol P&L  = Actual_Future_RV - Market_HV
        
        test_df['market_iv_proxy'] = test_df['hv_20'] # Using HV20 as proxy for IV
        test_df['actual_rv'] = test_df['target_rv']
        
        # Signal: 1 = Buy Vol, -1 = Sell Vol
        # Refined Logic:
        # Buy Vol (1) ONLY if:
        #   1. Brain predicts Chaos (Pred RV > Market IV * 1.1) -> 10% Edge required (Margin of Safety)
        #   2. Trend is Active (Price is > 1% away from 200 SMA)
        
        test_df['trend_active'] = np.where(abs(test_df['trend_dist']) > 0.01, 1, 0)
        
        # Original Signal with Margin of Safety
        # If Pred RV > 1.1 * Market IV -> Buy (1)
        # If Pred RV < 0.9 * Market IV -> Sell (-1)
        # Else -> Neutral (0)
        
        raw_signal = np.where(test_df['predicted_rv'] > (test_df['market_iv_proxy'] * 1.1), 1, 
                             np.where(test_df['predicted_rv'] < (test_df['market_iv_proxy'] * 0.9), -1, 0))
        
        # Filtered Signal (For Long Only)
        test_df['signal'] = np.where(
            (raw_signal == 1) & (test_df['trend_active'] == 1), 1, 
            np.where(raw_signal == -1, -1, 0)
        )
        
        # Calculate P&L
        # If Signal 1 (Long): Profit = Actual - Market
        # If Signal -1 (Short): Profit = Market - Actual
        test_df['pnl_points'] = test_df['signal'] * (test_df['actual_rv'] - test_df['market_iv_proxy'])
        
        # Cumulative P&L
        test_df['cum_pnl'] = test_df['pnl_points'].cumsum()
        
        # Metrics
        total_pnl = test_df['pnl_points'].sum()
        win_rate = len(test_df[test_df['pnl_points'] > 0]) / len(test_df) * 100
        
        # --- Long Straddle Specific Analysis (Budget < 30k) ---
        long_trades = test_df[test_df['signal'] == 1]
        long_pnl = long_trades['pnl_points'].sum()
        long_win_rate = len(long_trades[long_trades['pnl_points'] > 0]) / len(long_trades) * 100 if len(long_trades) > 0 else 0
        long_count = len(long_trades)
        
        print(f"   💰 Total Vol Points Gained: {total_pnl:.2f}")
        print(f"   🏆 Win Rate (Overall): {win_rate:.1f}%")
        print(f"   --- Long Straddle (Budget Strategy) ---")
        print(f"   🔹 Long Trades Triggered: {long_count}")
        print(f"   🔹 Long P&L Points: {long_pnl:.2f}")
        print(f"   🔹 Long Win Rate: {long_win_rate:.1f}%")
        
        # Save Results
        test_df.to_csv(f"{results_dir}/{symbol}_backtest.csv", index=False)

    print("="*60)
    print("🏁 Backtest Complete.")

if __name__ == "__main__":
    run_backtest()
