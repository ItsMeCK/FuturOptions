
import pandas as pd
import numpy as np

def load_signals():
    # Load signals from V5 log (most accurate)
    signals = []
    try:
        with open("trend_sim_v5.txt", "r") as f:
            lines = f.readlines()
            
        current_date = "2025-12-24"
        for line in lines:
            if "Simulation Complete for 2025-12-24" in line:
                current_date = "2025-12-26"
            
            if "POTENTIAL SIGNAL" in line:
                # 2025-12-26 14:38:20,442 - INFO - 🚨 POTENTIAL SIGNAL: HFCL | Score: ...
                try:
                    parts = line.split("POTENTIAL SIGNAL:")[1]
                    sym = parts.split("|")[0].strip()
                    signals.append({'date': current_date, 'symbol': sym})
                except: pass
    except:
        print("Log file not found.")
        return []
    
    # Deduplicate
    unique_signals = []
    seen = set()
    for s in signals:
        key = f"{s['date']}_{s['symbol']}"
        if key not in seen:
            seen.add(key)
            unique_signals.append(s)
            
    return unique_signals

def analyze_stagnation():
    signals = load_signals()
    print(f"🔍 Analyzing Volume Structure for {len(signals)} Trades...")
    
    results = []
    
    # Load Data Once
    spot_data = {}
    for d in ["2025-12-24", "2025-12-26"]:
        try:
            df = pd.read_csv(f"daily_data/{d}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
            spot_data[d] = df
        except: pass
        
    for i, sig in enumerate(signals):
        date = sig['date']
        sym = sig['symbol']
        
        if date not in spot_data: continue
        df = spot_data[date]
        s_df = df[df['symbol'] == sym].copy()
        if s_df.empty: continue
        
        s_df = s_df.set_index('date').sort_index()
        
        # Resample 15m
        rs = s_df.resample('15min').agg({'volume':'sum', 'close':'last', 'open':'first'})
        rs = rs.dropna()
        
        if len(rs) < 10: continue # Not enough data
        
        # Metrics
        # 1. Volume Drop-off: First 2 hours vs Next 2 hours
        morning_vol = rs.iloc[0:8]['volume'].mean() # 09:15 - 11:15
        mid_vol = rs.iloc[8:16]['volume'].mean()    # 11:15 - 13:15
        
        drop_off = (mid_vol - morning_vol) / morning_vol if morning_vol > 0 else 0
        
        # 2. Price Churn: Range / Volume. 
        # If Volume High but Range Low = Churn.
        # Calculate for Afternoon
        pm_data = rs.iloc[8:20] # 11:15 onwards
        if pm_data.empty: continue
        
        pm_range = (pm_data['close'].max() - pm_data['close'].min()) / pm_data['close'].mean()
        pm_vol_total = pm_data['volume'].sum()
        
        # Normalized Churn Score? (Lower is worse stagnation)
        # We just want to see if Range was < 0.5%
        is_flat = pm_range < 0.005 # Less than 0.5% move in 3 hours
        
        results.append({
            'symbol': sym,
            'date': date,
            'morning_vol': morning_vol,
            'mid_vol': mid_vol,
            'drop_off': drop_off,
            'pm_range_pct': pm_range,
            'is_flat': is_flat
        })
        
        if i % 20 == 0: print(f"  Processed {i}/{len(signals)}...")

    # Aggregate
    res_df = pd.DataFrame(results)
    avg_drop = res_df['drop_off'].mean()
    pct_flat = len(res_df[res_df['is_flat']]) / len(res_df) * 100
    
    print("\n📊 INSTITUTIONAL AUDIT RESULTS (All Trades)")
    print(f"   Avg Volume Drop-off: {avg_drop*100:.1f}%")
    print(f"   % of Trades Flat (<0.5% range): {pct_flat:.1f}%")
    
    print("\n📉 Worst Liquidity Vacuums (Top 5):")
    vacuums = res_df.sort_values('drop_off').head(5)
    print(vacuums[['date', 'symbol', 'drop_off']])

if __name__ == "__main__":
    analyze_stagnation()
