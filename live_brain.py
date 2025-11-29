import time
import pandas as pd
import joblib
import os
from datetime import datetime
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.feature_engineer import FeatureEngineer
from dotenv import load_dotenv

load_dotenv()

def live_scanner():
    print("🧠 AI Option Brain: LIVE SCANNER (Sniper Mode)")
    print("="*60)
    
    # 1. Load Leaderboard & Select Top Stocks
    lb_path = "ai_option_brain/results/nifty50_leaderboard.csv"
    if not os.path.exists(lb_path):
        print("⚠️ Leaderboard not found. Run backtest first.")
        return

    lb_df = pd.read_csv(lb_path)
    top_stocks = lb_df.head(20)['Symbol'].tolist()
    print(f"🎯 Monitoring Top {len(top_stocks)} Stocks: {top_stocks}")
    
    # 2. Load Models
    models = {}
    print("   Loading Models...")
    for symbol in top_stocks:
        model_path = f"ai_option_brain/models/{symbol}_rf_vol.pkl"
        if os.path.exists(model_path):
            models[symbol] = joblib.load(model_path)
        else:
            print(f"   ⚠️ Model missing for {symbol}")
            
    # 3. Connect to Zerodha
    fetcher = ZerodhaDataFetcher()
    # fetcher.connect() # Not needed
    
    print("="*60)
    print("📡 Scanner Active. Waiting for next minute candle...")
    
    while True:
        now = datetime.now()
        # Wait for the minute to close (e.g., at 00 seconds)
        # For simulation/demo, we just run immediately then sleep 60s
        
        print(f"\n⏰ Scan Time: {now.strftime('%H:%M:%S')}")
        
        for symbol in top_stocks:
            if symbol not in models: continue
            
            try:
                # A. Fetch Data (Last 5 days to ensure enough for indicators)
                # We need 1-min data
                token = fetcher.get_instrument_token(symbol)
                if not token: continue
                
                to_date = datetime.now()
                from_date = to_date - pd.Timedelta(days=5)
                
                df = fetcher.fetch_historical_data(token, from_date, to_date, interval="minute")
                
                if df.empty: continue
                
                # B. Feature Engineering
                # We need to process this mini-batch
                # Create 60m resample
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df_60m = df.resample('60min').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
                }).dropna().reset_index()
                df.reset_index(inplace=True)
                
                # VIX (Mock or Fetch) - For now None
                df_features = FeatureEngineer.prepare_training_data(df, df_60m, None)
                
                if df_features.empty: continue
                
                # Get latest candle
                latest_row = df_features.iloc[-1]
                
                # C. Predict
                # Prepare input vector (drop non-features)
                drop_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'target_rv', 'log_ret']
                features = [c for c in df_features.columns if c not in drop_cols]
                
                # Ensure columns match model training
                # This is tricky if feature order changed. 
                # Ideally we should save feature list with model.
                # For now assuming consistent order.
                
                X_input = latest_row[features].values.reshape(1, -1)
                pred_rv = models[symbol].predict(X_input)[0]
                
                # D. Logic (Sniper)
                market_iv = latest_row['hv_20'] # Proxy
                trend_dist = latest_row['trend_dist']
                
                # Signal Rules
                # 1. Pred RV > Market IV * 1.1
                # 2. Trend Active (|Trend Dist| > 1%)
                
                is_fat_pitch = pred_rv > (market_iv * 1.1)
                is_trend_active = abs(trend_dist) > 0.01
                
                if is_fat_pitch and is_trend_active:
                    print(f"🚀 ALERT: {symbol} | Price: {latest_row['close']:.1f} | Pred Vol: {pred_rv:.2f} > Market {market_iv:.2f}")
                    print(f"   ACTION: BUY STRADDLE (ATM)")
                # else:
                #     print(f"   {symbol}: Neutral (Pred {pred_rv:.2f} vs Mkt {market_iv:.2f})")
                    
            except Exception as e:
                # print(f"Error scanning {symbol}: {e}")
                pass
        
        print("   Scan complete. Sleeping 60s...")
        time.sleep(60)

if __name__ == "__main__":
    live_scanner()
