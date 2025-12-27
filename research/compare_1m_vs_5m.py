
import pandas as pd
import numpy as np

def compare_timeframes():
    print("⏱ Comparing 1-Minute vs 5-Minute Entry Timing...")
    
    # Load Stitched Data (Dec 24 + Dec 26)
    try:
        df_24 = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        df_26 = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        df = pd.concat([df_24, df_26]).sort_values(['symbol', 'date'])
        df['date'] = pd.to_datetime(df['date'])
    except:
        return

    targets = ['RVNL', 'ADANIPORTS']
    
    for sym in targets:
        print(f"\n🔍 Analyzing {sym} (Dec 26 Morning)...")
        s_df = df[df['symbol'] == sym].set_index('date').sort_index()
        
        # 1. 5-Minute Simulation
        s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        start_26 = pd.Timestamp("2025-12-26 09:15").tz_localize(s_5m.index.tz)
        
        # Calculate 5m Metrics
        s_5m['vol_sma'] = s_5m['volume'].rolling(20).mean()
        day_5m = s_5m[s_5m.index >= start_26].copy()
        day_5m['vwap'] = (day_5m['close'] * day_5m['volume']).cumsum() / day_5m['volume'].cumsum()
        
        # Find 5m Trigger
        trigger_5m = "NONE"
        for i in range(len(day_5m)):
            row = day_5m.iloc[i]
            t = row.name
            if t.hour > 11: break
            
            # Logic
            rvol = row['volume'] / s_5m.loc[t]['vol_sma'] if s_5m.loc[t]['vol_sma'] > 0 else 0
            vwap = row['vwap']
            range_pct = (row['high'] - row['low'])/row['open'] * 100
            
            # Simple Ignition
            if row['close'] > vwap:
                if rvol > 3.0 or range_pct > 2.0:
                    trigger_5m = f"{t.strftime('%H:%M')} (Price: {row['close']:.2f}, RVOL: {rvol:.1f})"
                    break
        
        # 2. 1-Minute Simulation
        s_1m = s_df.resample('1min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        # Calculate 1m Metrics (SMA 20 on 1m = 20 mins context)
        # Note: 1m RVOL usually needs longer baseline, e.g. SMA 60 (1 hour). Let's use SMA 20 for direct comparison of "bars".
        s_1m['vol_sma'] = s_1m['volume'].rolling(20).mean()
        day_1m = s_1m[s_1m.index >= start_26].copy()
        day_1m['vwap'] = (day_1m['close'] * day_1m['volume']).cumsum() / day_1m['volume'].cumsum()
        
        trigger_1m = "NONE"
        for i in range(len(day_1m)):
            row = day_1m.iloc[i]
            t = row.name
            if t.hour > 11: break
            
            # Logic
            # Note: 1m Volume is smaller, so "Spike" might need lower threshold? 
            # Or same Relative threshold? Usually RVol is RVol.
            vol_sma = s_1m.loc[t]['vol_sma']
            rvol = row['volume'] / vol_sma if vol_sma > 0 else 0
            vwap = row['vwap']
            
            # 1m Range is smaller usually. Let's look for Vol Ignition mainly.
            
            if row['close'] > vwap:
                if rvol > 3.0: # Same Ignition Rule
                    trigger_1m = f"{t.strftime('%H:%M')} (Price: {row['close']:.2f}, RVOL: {rvol:.1f})"
                    break
                    
        print(f"   👉 5-Min Entry: {trigger_5m}")
        print(f"   👉 1-Min Entry: {trigger_1m}")
        
        if sym == 'RVNL':
            print("   💡 Insight: Did 1m get us in cheaper?")
        else:
            print("   💡 Insight: Did 1m trigger a False Positive earlier?")

if __name__ == "__main__":
    compare_timeframes()
