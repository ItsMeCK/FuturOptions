
import pandas as pd
import sys
import os
import numpy as np

# Add root
sys.path.append(os.getcwd())
from live_brain import LiveBrain

def check_rvnl():
    print("🕵️‍♂️ Diagnosing RVNL Failure on Dec 26 (WITH HISTORY)...")
    brain = LiveBrain()
    
    # 1. Load BOTH Days (Dec 24 & Dec 26)
    try:
        df_24 = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        df_26 = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        
        df_24['date'] = pd.to_datetime(df_24['date'])
        df_26['date'] = pd.to_datetime(df_26['date'])
        
        print("✅ Loaded Dec 24 & Dec 26 Data.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
        
    # 2. Stitch & Filter RVNL
    rvnl_24 = df_24[df_24['symbol'] == 'RVNL']
    rvnl_26 = df_26[df_26['symbol'] == 'RVNL']
    
    rvnl = pd.concat([rvnl_24, rvnl_26]).sort_values('date').set_index('date')
    
    if rvnl.empty:
        print("❌ RVNL data missing!")
        return
        
    # 3. Resample 5m (Continuous)
    rvnl_5m = rvnl.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    
    # 4. Calculate Indicators (With History!)
    # Hourly Trend
    rvnl_1h = rvnl_5m.resample('60min').agg({'close':'last'}).dropna()
    rvnl_1h['sma20'] = rvnl_1h['close'].rolling(20).mean()
    
    # Volume SMA for RVOL
    # Note: Rolling 20 on 5min = 100 mins. Institutional RVOL often needs more context (e.g. 5 days).
    # But even 20 periods from Dec 24 should give us a baseline!
    rvnl_5m['vol_sma'] = rvnl_5m['volume'].rolling(20).mean()
    
    # VWAP (Intraday Reset)
    # Need to calc VWAP only for Dec 26
    start_26 = pd.Timestamp("2025-12-26 09:15").tz_localize(rvnl_5m.index.tz)
    rvnl_26_5m = rvnl_5m[rvnl_5m.index >= start_26].copy()
    
    # Intraday VWAP for Dec 26
    rvnl_26_5m['vwap'] = (rvnl_26_5m['close'] * rvnl_26_5m['volume']).cumsum() / rvnl_26_5m['volume'].cumsum()
    
    # Iterate Dec 26 Morning
    print("\n⏱ TIMELINE (09:20 - 10:00) on Dec 26:")
    print("-" * 80)
    
    for i in range(len(rvnl_5m)):
        curr_time = rvnl_5m.index[i]
        if curr_time < start_26: continue # Skip Dec 24
        if curr_time.hour > 10: break
        
        row = rvnl_5m.iloc[i]
        price = row['close']
        vol = row['volume']
        vwap_val = rvnl_26_5m.loc[curr_time]['vwap']
        vol_sma = row['vol_sma']
        
        # RVOL
        rvol = vol / vol_sma if vol_sma > 0 else 0
        
        # Range % (Intraday)
        day_hist = rvnl_26_5m.loc[:curr_time]
        d_high = day_hist['high'].max()
        d_low = day_hist['low'].min()
        d_open = day_hist['open'].iloc[0]
        range_pct = ((d_high - d_low) / d_open) * 100
        
        # Simulation Logic
        status = "❌ BLOCKED"
        reasons = []
        
        if price < vwap_val:
            reasons.append("Below VWAP")
        else:
            # Ignition Check
            if rvol > 3.0:
                status = "✅ TRIGGERED"
                reasons.append(f"IGNITION VOL ({rvol:.1f}x)")
            elif range_pct > 2.0:
                status = "✅ TRIGGERED"
                reasons.append(f"IGNITION RANGE ({range_pct:.1f}%)")
            else:
                 reasons.append("Waiting for Ignition...")
        
        print(f"{curr_time.strftime('%H:%M')} | Price: {price:.2f} | VWAP: {vwap_val:.2f} | RVOL: {rvol:.1f}x | Range: {range_pct:.1f}% | {status} {reasons}")

if __name__ == "__main__":
    check_rvnl()
