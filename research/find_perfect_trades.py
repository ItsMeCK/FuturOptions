
import pandas as pd
import numpy as np
import os

def find_movers():
    print("🕵️‍♂️ Starting Ground Truth Scan (Target: 30% Movers)...")
    
    files = [
        "daily_data/2025-12-24_options_full.csv",
        "daily_data/2025-12-26_options_full.csv"
    ]
    
    all_movers = []
    
    for f_path in files:
        if not os.path.exists(f_path):
            print(f"❌ Missing: {f_path}")
            continue
            
        print(f"📂 Scanning {f_path} ...")
        date_str = f_path.split("/")[-1].split("_")[0]
        
        # Read in Chunks (Memory Safe)
        chunk_size = 100000
        # Check header
        # date,open,high,low,close,volume,tradingsymbol
        
        # We need to aggregate by symbol to find DAY's Low and High
        # More efficient: Read columns we need
        try:
            df_iter = pd.read_csv(f_path, usecols=['tradingsymbol', 'high', 'low', 'volume'], chunksize=chunk_size)
        except Exception as e:
            print(f"Read Error: {e}")
            continue
            
        # Aggregators
        sym_stats = {} # {sym: {'high': -1, 'low': 99999, 'vol': 0}}
        
        for chunk in df_iter:
            # Group chunk by symbol
            # We want LOWEST low and HIGHEST high of the day
            agg = chunk.groupby('tradingsymbol').agg({
                'high': 'max',
                'low': 'min', 
                'volume': 'sum'
            })
            
            for sym, row in agg.iterrows():
                if sym not in sym_stats:
                    sym_stats[sym] = {'high': row['high'], 'low': row['low'], 'vol': row['volume']}
                else:
                    sym_stats[sym]['high'] = max(sym_stats[sym]['high'], row['high'])
                    sym_stats[sym]['low'] = min(sym_stats[sym]['low'], row['low'])
                    sym_stats[sym]['vol'] += row['volume']
                    
        # Filter Logic
        print(f"   Analyzing {len(sym_stats)} Contracts...")
        
        day_movers = 0
        for sym, stats in sym_stats.items():
            h = stats['high']
            l = stats['low']
            vol = stats['vol']
            
            if l <= 0 or vol < 5000: continue # Skip illiquid / bad data
            
            gain = (h - l) / l
            
            if gain >= 0.30: # 30% Mover
                # Parse Symbol for root? "ABB25DEC5200CE" -> ABB
                # Usually Symbol + expiry + Strike + Type
                # Basic parsing for overlapping
                # Assuming standard format: SYMBOL + YY + MON + STRIKE + CE/PE
                # Let's extract root using simplistic alphanumeric split or heuristics
                # Better: Just store full symbol for now.
                
                all_movers.append({
                    'Date': date_str,
                    'OptionSymbol': sym,
                    'Low': l,
                    'High': h,
                    'MaxReturn%': round(gain * 100, 1),
                    'Volume': vol
                })
                day_movers += 1
                
        print(f"   Found {day_movers} 'Perfect Trades' (+30%) on {date_str}")

    # Export
    df_res = pd.DataFrame(all_movers)
    out_path = "research/ground_truth_movers.csv"
    df_res.to_csv(out_path, index=False)
    print(f"✅ Ground Truth Saved: {len(df_res)} Options ({out_path})")
    
    if not df_res.empty:
        print("\n🚀 Top 5 Movers (The Ones We Wanted):")
        print(df_res.sort_values('MaxReturn%', ascending=False).head(5).to_string(index=False))

if __name__ == "__main__":
    find_movers()
