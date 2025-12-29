
import pandas as pd
import os

def check_potential():
    print("🔬 Checking Max Potential for TATASTEEL & MAZDOCK...")
    
    symbols = ["TATASTEEL", "MAZDOCK"]
    
    for symbol in symbols:
        cache_file = f"sim_cache/{symbol}_dec29.csv"
        if not os.path.exists(cache_file):
            print(f"❌ Cache not found for {symbol}")
            continue
            
        df = pd.read_csv(cache_file)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Start at 09:30
        start_time = pd.to_datetime("2025-12-29 09:30:00")
        if df.index.tz: start_time = start_time.tz_localize(df.index.tz)
        
        valid_df = df[df.index >= start_time]
        
        if valid_df.empty: 
            print(f"No data after 09:30 for {symbol}")
            continue
            
        entry_price = valid_df.iloc[0]['open']
        max_high = valid_df['high'].max()
        eod_price = valid_df.iloc[-1]['close']
        
        max_stock_gain = (max_high - entry_price) / entry_price * 100
        eod_stock_gain = (eod_price - entry_price) / entry_price * 100
        
        # Option Leverage Proxy (15x for ATM, 20x for OTM Sniper)
        # Let's be generous: 20x
        est_opt_max = max_stock_gain * 20
        
        print(f"\n📊 {symbol}")
        print(f"   Entry: {entry_price}")
        print(f"   Max High: {max_high} (at {valid_df['high'].idxmax().time()})")
        print(f"   Max Stock Gain: {max_stock_gain:.2f}%")
        print(f"   Est. Max Option Gain (20x): {est_opt_max:.2f}%")
        print(f"   EOD Gain: {eod_stock_gain:.2f}%")
        
        if est_opt_max < 150:
            print("   ⚠️ 200% was IMPOSSIBLE today. Mathematical limit reached.")
        else:
            print("   ⚠️ 200% was POSSIBLE. Our strategy exited too early.")

if __name__ == "__main__":
    check_potential()
