
import pandas as pd
import sys
import os

def analyze_rvnl():
    print("🕵️‍♂️ Forensic Analysis: RVNL Breakout (Dec 26)")
    
    # Files
    opt_file = "daily_data/2025-12-26_options_full.csv"
    spot_file = "daily_data/2025-12-26_spot_full.csv"
    
    # 1. Load Option Data for RVNL25DEC380CE
    print("   Loading Option Data...")
    target_opt = "RVNL25DEC380CE"
    
    opt_chunk = pd.read_csv(opt_file, chunksize=100000)
    opt_df = pd.DataFrame()
    for chunk in opt_chunk:
        match = chunk[chunk['tradingsymbol'] == target_opt]
        if not match.empty:
            opt_df = pd.concat([opt_df, match])
            
    if opt_df.empty:
        print("❌ Option Data not found!")
        return
        
    opt_df['date'] = pd.to_datetime(opt_df['date'])
    opt_df = opt_df.sort_values('date').set_index('date')
    
    # 2. Load Spot Data for RVNL
    print("   Loading Spot Data...")
    spot_df = pd.read_csv(spot_file)
    spot_df['date'] = pd.to_datetime(spot_df['date'])
    spot_df = spot_df[spot_df['symbol'] == 'RVNL'].sort_values('date').set_index('date')
    
    # 3. Merge and Analyze
    # Resample to 5 mins for clarity
    df = pd.concat([
        spot_df['close'].rename('Spot_Price'),
        spot_df['volume'].rename('Spot_Vol'),
        opt_df['close'].rename('Opt_Price'),
        opt_df['volume'].rename('Opt_Vol')
    ], axis=1).dropna()
    
    print("\n⏱ TIMELINE OF THE MOVE:")
    print("-" * 80)
    print(f"{'Time':<10} | {'Spot':<8} {'S_Vol':<10} | {'Opt':<8} {'O_Vol':<10} | {'Structure'}")
    print("-" * 80)
    
    # Rolling averages for spikes
    df['Opt_Vol_SMA'] = df['Opt_Vol'].rolling(5).mean()
    
    start_monitoring = False
    
    for time, row in df.iterrows():
        t_str = time.strftime('%H:%M')
        
        # Check for Volume Spikes
        spike_txt = ""
        if row['Opt_Vol'] > row['Opt_Vol_SMA'] * 3 and row['Opt_Vol'] > 10000:
            spike_txt = "🔥 HUGE OPT VOL"
            
        # Check for Price Breakout
        # ... logic ...
        
        # Print only relevant window (Morning to Breakout)
        if time.hour == 9 or (time.hour == 10 and time.minute < 30):
            print(f"{t_str:<10} | {row['Spot_Price']:<8.2f} {int(row['Spot_Vol']):<10} | {row['Opt_Price']:<8.2f} {int(row['Opt_Vol']):<10} | {spike_txt}")
            
    # Export for graphing if needed in future
    df.to_csv("research/rvnl_forensic_data.csv")

if __name__ == "__main__":
    analyze_rvnl()
