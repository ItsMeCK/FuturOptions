
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.utils.technical_indicators import TechnicalIndicators
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Environment Variables
load_dotenv()

def load_initial_token():
    """Load token from hot file."""
    if os.path.exists("zerodha_hot_token.txt"):
        with open("zerodha_hot_token.txt") as f:
            token = f.read().strip()
            if len(token) > 10:
                return token
    return os.getenv("ZERODHA_ACCESS_TOKEN")

def simulate_today():
    print("🚀 Starting Simulation for Dec 29...")
    
    # 1. Load Token
    token = load_initial_token()
    if not token:
        print("❌ No Token Found!")
        return
        
    # 2. Initialize Fetcher
    fetcher = ZerodhaDataFetcher(access_token=token)
    
    # 3. Load Universe
    universe = []
    if os.path.exists("fno_universe.txt"):
        with open("fno_universe.txt") as f:
            universe = [line.strip() for line in f if line.strip()]
    else:
        print("⚠️ fno_universe.txt not found. Using fallback.")
        universe = ["DALBHARAT", "CANBK", "BDL", "BEL", "RELIANCE", "INFY", "TATASTEEL", "SBIN"]
        
    print(f"🌌 Universe Size: {len(universe)}")
    
    signals = []
    
    # Loop
    count = 0
    for symbol in universe:
        count += 1
        # if count > 50: break # Safety limit for speed if needed
        
        try:
            # Get Token
            inst_token = fetcher.get_instrument_token(symbol)
            if not inst_token:
                # print(f"Skipping {symbol} (No Token)")
                continue
                
            # Fetch Data (5 Days)
            hist_df = fetcher.fetch_latest_data(inst_token, days=5, interval="5minute")
            
            if hist_df is None or hist_df.empty:
                continue
                
            if 'date' in hist_df.columns:
                hist_df['date'] = pd.to_datetime(hist_df['date'])
                hist_df.set_index('date', inplace=True)
                
            # Features
            hist_df['log_ret'] = np.log(hist_df['close'] / hist_df['close'].shift(1))
            
            # Indicators
            sma_50 = hist_df['close'].rolling(50).mean()
            # adx = TechnicalIndicators.calculate_adx(hist_df['high'], hist_df['low'], hist_df['close'], window=14)
            # Optimization: Calculate only if needed? No, need rolling series.
            
            # Calculate full series to be safe
            adx_series = TechnicalIndicators.calculate_adx(hist_df['high'], hist_df['low'], hist_df['close'], window=14)
            bw_series = TechnicalIndicators.calculate_bollinger_bandwidth(hist_df['close'], period=20, std_dev=2)
            upper_series, _ = TechnicalIndicators.calculate_bollinger_bands(hist_df['close'], period=20, std_dev=2)
            vwap_series = TechnicalIndicators.calculate_vwap(hist_df)
            
            vol_sma_series = hist_df['volume'].rolling(20).mean()
            rvol_series = hist_df['volume'] / vol_sma_series
            
            # Simulation for Today
            # today_df = hist_df[hist_df.index.date == datetime(2025, 12, 29).date()]
            # Or just use the last N candles if today
            today_str = "2025-12-29"
            today_mask = hist_df.index.strftime('%Y-%m-%d') == today_str
            indices = hist_df.index[today_mask]
            
            if len(indices) == 0:
                 # print(f"No Data Dec 29 for {symbol}")
                 continue
                 
            # print(f"Analyzing {symbol} ({len(indices)} candles)...")
            
            for ts in indices:
                # Get scalar values at this timestamp
                price = hist_df.loc[ts]['close']
                open_p = hist_df.loc[ts]['open']
                low_p = hist_df.loc[ts]['low']
                
                curr_sma = sma_50.loc[ts]
                curr_adx = adx_series.loc[ts]
                curr_bw = bw_series.loc[ts]
                curr_rvol = rvol_series.loc[ts]
                curr_vwap = vwap_series.loc[ts]
                
                # Logic (Exact Copy)
                trend_dist = (price - curr_sma)/curr_sma if pd.notna(curr_sma) else 0
                
                # Filter 1: Structure
                if trend_dist < 0: continue
                # Filter 2: VWAP
                if curr_vwap > 0 and price < curr_vwap: continue
                # Filter 3: Red Candle
                if open_p > 0 and price <= open_p: continue
                
                # SNIPER
                is_st = False
                is_sniper_squeeze = curr_bw < 0.15
                is_sniper_vol = curr_rvol > 1.5
                
                if is_sniper_squeeze and is_sniper_vol:
                    is_st = True
                    strategy = "SNIPER"
                    
                # GAMMA
                gamma_limit = 0.20 if price > 2000 else 0.15
                is_gamma_squeeze = curr_bw < gamma_limit
                is_gamma_vol = curr_rvol > 1.5
                
                if is_gamma_squeeze and is_gamma_vol and not is_st:
                    is_st = True
                    strategy = "GAMMA"
                    
                if is_st:
                    # Log Signal
                    # Check if duplicated (already signaled recently?)
                    # For simulation, we log ALL triggers to see freq
                    
                    signals.append({
                        "Time": ts.strftime("%H:%M:%S"),
                        "Symbol": symbol,
                        "Strategy": strategy,
                        "Price": price,
                        "BW": round(curr_bw, 3),
                        "RVOL": round(curr_rvol, 1),
                        "VWAP_Dist": round((price-curr_vwap)/curr_vwap*100, 2)
                    })
                    print(f"🚨 {symbol} {strategy} @ {ts.time()} | BW:{curr_bw:.2f} RV:{curr_rvol:.1f}")

        except Exception as e:
            # print(f"Err {symbol}: {e}")
            pass
            
    # Save
    if signals:
        df = pd.DataFrame(signals)
        print(df)
        df.to_csv("sim_dec29.csv", index=False)
        print(f"✅ Saved {len(df)} signals to sim_dec29.csv")
    else:
        print("No Signals Found.")

if __name__ == "__main__":
    simulate_today()
