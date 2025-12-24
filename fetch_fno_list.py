
from ai_option_brain.data_loader import ZerodhaDataFetcher
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_universe():
    token = open("zerodha_hot_token.txt").read().strip()
    fetcher = ZerodhaDataFetcher(access_token=token)
    
    print("⏳ Fetching Instrument Dump (Raw)...")
    # Bypass helper to get EVERYTHING (including FUT)
    dump = fetcher.kite.instruments("NFO")
    df = pd.DataFrame(dump)
    
    print(f"Total Instruments: {len(df)}")
    
    # Filter for FUTURES to get the underlying symbols
    # segment for NSE Stocks is 'NSE'
    # segment for Derivatives is 'NFO-FUT'
    
    fno_fut = df[df['segment'] == 'NFO-FUT']
    current_expiry = fno_fut['expiry'].dropna().sort_values().unique()
    
    # Get active symbols (name)
    # The 'name' column usually contains the underlying symbol e.g., 'RELIANCE'
    fno_symbols = fno_fut['name'].unique()
    
    fno_symbols = sorted([s for s in fno_symbols if s.isalpha()]) # Filter out test symbols
    
    print(f"✅ Found {len(fno_symbols)} F&O Symbols.")
    print("Example:", fno_symbols[:10])
    
    # Save
    with open("fno_universe.txt", "w") as f:
        for s in fno_symbols:
            f.write(f"{s}\n")
            
    print("Saved to fno_universe.txt")

if __name__ == "__main__":
    fetch_universe()
