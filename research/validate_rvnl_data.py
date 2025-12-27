
import pandas as pd

def find_low():
    f_path = "daily_data/2025-12-26_options_full.csv"
    target = "RVNL25DEC380CE"
    
    print(f"🕵️‍♂️ Hunting for 0.20 Low in {target}...")
    
    chunk_size = 100000
    found = False
    
    for chunk in pd.read_csv(f_path, chunksize=chunk_size):
        match = chunk[chunk['tradingsymbol'] == target]
        if match.empty: continue
        
        # Check for Low <= 0.50
        lows = match[match['low'] <= 0.50]
        if not lows.empty:
            print("\n🚨 FOUND LOW PRICE TICKS:")
            print(lows[['date', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
            found = True
            
    if not found:
        print("❌ No price <= 0.50 found in the entire file.")
        
    # Also stats
    print("\n📊 General Stats for Option:")
    # We can't re-read whole file easily for stats without re-iterating everything or storing.
    # Just the hunt is enough.

if __name__ == "__main__":
    find_low()
