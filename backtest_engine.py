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
        # Use the NEW Production Models (Brain Transplant)
        model_path = f"{model_dir}/{symbol}_vol_model.pkl"
        
        if not os.path.exists(model_path):
            print(f"⚠️ Model missing for {symbol}. Skipping.")
            continue
            
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        model = joblib.load(model_path)
        
        # 2. Re-create the STRICT Test Split (Date Based)
        # Must match training split exactly
        split_date = pd.Timestamp("2025-06-01")
        
        # Calculate ADX on full DF first (to avoid warmup issues)
        import ta
        # Assuming 'high_x', 'low_x', 'close' are the 1-min OHLC
        # If they are not present, we might need to check column names.
        # Based on previous `head` command: open_x, high_x, low_x, close
        try:
            df['adx'] = ta.trend.adx(df['high_x'], df['low_x'], df['close'], window=14)
        except Exception as e:
            print(f"⚠️ ADX Calc Failed: {e}")
            df['adx'] = 0

        test_df = df[df['date'] >= split_date].copy()
        
        if test_df.empty:
            print(f"⚠️ No test data found for {symbol} after {split_date}")
            continue
            
        print(f"📉 Backtesting {symbol} on {len(test_df)} unseen candles...")
        print(f"   Period: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # 3. Prepare Features
        # We need 'trend_dist' for the filter, so let's keep it in test_df but exclude from model input if it wasn't a feature
        # Actually, trend_dist WAS a feature in training.
        
        drop_cols = ['date', 'open_x', 'high_x', 'low_x', 'close', 'volume_x', 'target_rv', 'log_ret', 
                     'open_y', 'high_y', 'low_y', 'volume_y', 'tp', 'vwap_dev', 'adx'] # Exclude non-features
        
        # Ensure we only use features that the model expects
        # Model expects: ['hv_10', 'hv_20', 'log_ret', 'trend_dist', 'rsi', 'india_vix']
        # We need to be careful not to pass extra columns to predict
        model_features = ['hv_10', 'hv_20', 'log_ret', 'trend_dist', 'rsi', 'india_vix']
        
        # Check if all model features are present
        missing_feats = [f for f in model_features if f not in test_df.columns]
        if missing_feats:
            print(f"⚠️ Missing features for model: {missing_feats}. Skipping.")
            continue

        X_test = test_df[model_features]
        
        # 4. Generate Predictions (The "Brain's View")
        test_df['predicted_rv'] = model.predict(X_test)
        
        # 5. Simulate Strategy: "Vol Arbitrage"
        # Proxy: Market Price = Current 20-Day Historical Volatility (hv_20)
        
        test_df['market_iv_proxy'] = test_df['hv_20'] # Using HV20 as proxy for IV
        test_df['actual_rv'] = test_df['target_rv']
        
        # Signal: 1 = Buy Vol, -1 = Sell Vol
        # Refined Logic (INSTITUTIONAL GRADE):
        # 1. Regime: 11 < VIX < 20
        # 2. Trend: ADX > 25
        # 3. Conviction: Edge > 15%
        
        # --- INSTITUTIONAL CONFLUENCE SCORE (Vectorized) ---
        
        # 1. Calculate Missing Technicals
        # Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(close=test_df['close'], window=20, window_dev=2)
        test_df['upper_band'] = bb_indicator.bollinger_hband()
        test_df['lower_band'] = bb_indicator.bollinger_lband()
        test_df['ma_20'] = bb_indicator.bollinger_mavg()
        test_df['bandwidth'] = (test_df['upper_band'] - test_df['lower_band']) / test_df['ma_20']
        
        # VWAP (Approximate using typical price if volume available)
        # ta.volume.VolumeWeightedAveragePrice requires high, low, close, volume
        vwap_indicator = ta.volume.VolumeWeightedAveragePrice(
            high=test_df['high_x'], low=test_df['low_x'], close=test_df['close'], volume=test_df['volume_x'], window=14
        )
        test_df['vwap'] = vwap_indicator.volume_weighted_average_price()
        
        # RVOL (Volume / SMA20 Volume)
        test_df['vol_sma'] = test_df['volume_x'].rolling(20).mean()
        test_df['rvol'] = test_df['volume_x'] / test_df['vol_sma']
        
        # 2. Calculate Score Components
        test_df['score'] = 0
        
        # A. Trend (30 pts)
        test_df['score'] += np.where(test_df['adx'] > 25, 15, 0)
        test_df['score'] += np.where(test_df['trend_dist'] > 0, 15, 0) # Price > SMA50
        
        # B. Momentum (30 pts)
        test_df['score'] += np.where((test_df['rsi'] > 50) & (test_df['rsi'] < 70), 10, 0)
        test_df['score'] += np.where(test_df['bandwidth'] < 0.15, 10, 0) # Squeeze
        test_df['score'] += np.where((test_df['upper_band'] > 0) & (test_df['close'] > (test_df['upper_band'] * 0.99)), 10, 0) # Breakout
        
        # C. Volume (20 pts)
        test_df['score'] += np.where(test_df['rvol'] > 1.5, 10, 0)
        test_df['score'] += np.where(test_df['close'] > test_df['vwap'], 10, 0)
        
        # D. Volatility Edge (20 pts)
        test_df['edge_pct'] = np.where(test_df['market_iv_proxy'] > 0, 
                                     ((test_df['predicted_rv'] - test_df['market_iv_proxy']) / test_df['market_iv_proxy']) * 100, 
                                     0)
        test_df['score'] += np.where(test_df['edge_pct'] > 15, 20, 0)
        
        # --- STABILITY LAYER (Smoothing) ---
        test_df['smoothed_score'] = test_df['score'].rolling(window=5).mean().fillna(0)
        
        # --- BI-DIRECTIONAL SIGNALS ---
        # Long Signal: Score > 75 AND Price > Upper Band (Breakout)
        test_df['long_signal'] = np.where((test_df['smoothed_score'] >= 75) & (test_df['close'] > test_df['upper_band']), 1, 0)
        
        # Short Signal: Score > 75 AND Price < Lower Band (Breakdown)
        test_df['short_signal'] = np.where((test_df['smoothed_score'] >= 75) & (test_df['close'] < test_df['lower_band']), -1, 0)
        
        # Combine Signals (Priority to Long if both? Unlikely with BB logic)
        test_df['signal'] = test_df['long_signal'] + test_df['short_signal']
        
        # Calculate P&L (Delta Proxy = 0.5)
        # We assume we hold for 10 minutes (Sniper Scalp) or until signal flips?
        # For simple backtest, let's assume we capture the next 10 mins of move.
        # Shift close by -10 to get "Future Price"
        test_df['future_close'] = test_df['close'].shift(-10)
        test_df['price_change'] = test_df['future_close'] - test_df['close']
        
        # P&L = Signal * Price_Change * 0.5 (Delta)
        # If Long (1) and Price Up (+10) -> 1 * 10 * 0.5 = +5
        # If Short (-1) and Price Down (-10) -> -1 * -10 * 0.5 = +5
        test_df['pnl_points'] = test_df['signal'] * test_df['price_change'] * 0.5
        
        # Filter out NaNs (last 10 rows)
        test_df = test_df.dropna(subset=['pnl_points'])
        
        # Metrics
        total_pnl = test_df['pnl_points'].sum()
        win_rate = len(test_df[test_df['pnl_points'] > 0]) / len(test_df[test_df['signal'] != 0]) * 100 if len(test_df[test_df['signal'] != 0]) > 0 else 0
        trade_count = len(test_df[test_df['signal'] != 0])
        
        print(f"   💰 Total P&L (Points): {total_pnl:.2f}")
        print(f"   🎯 Trade Count: {trade_count}")
        print(f"   🏆 Win Rate: {win_rate:.1f}%")
        
        # Save Results
        test_df.to_csv(f"{results_dir}/{symbol}_backtest.csv", index=False)

    print("="*60)
    print("🏁 Backtest Complete.")

if __name__ == "__main__":
    run_backtest()
