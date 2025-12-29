import os
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher

# Setup
load_dotenv()
OUTPUT_DIR = "daily_data/history_3yr"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_history():
    print("⏳ Starting 3-Year Historical Data Downloader...")
    
    # Initialize Fetcher
    try:
        fetcher = ZerodhaDataFetcher()
    except Exception as e:
        print(f"❌ Failed to init fetcher: {e}")
        return

    # Load Universe
    universe = []
    if os.path.exists("fno_universe.txt"):
        with open("fno_universe.txt") as f:
            universe = [line.strip() for line in f if line.strip()]
    else:
        print("⚠️ fno_universe.txt not found. Using small default list.")
        universe = ["RELIANCE", "INFY", "TCS", "SBIN", "HDFCBANK"]
        
    print(f"📋 Found {len(universe)} symbols to process.")
    
    # Date Range (3 Years)
    # Zerodha Historical Data is strict about range.
    # We want 'day' interval.
    # From: 2023-01-01 To: Now
    from_date = datetime(2023, 1, 1)
    to_date = datetime.now()
    
    success_count = 0
    
    for i, symbol in enumerate(universe):
        print(f"[{i+1}/{len(universe)}] Fetching {symbol}...", end=" ")
        
        output_file = f"{OUTPUT_DIR}/{symbol}.csv"
        
        # Skip if exists and recent (optional optimization, but let's overwrite to be safe)
        # if os.path.exists(output_file): ...
        
        try:
            token = fetcher.get_instrument_token(symbol)
            if not token:
                print("❌ Token Not Found")
                continue
                
            # Fetch Data
            # Note: fetcher.fetch_latest_data usually does 'days=X'. 
            # We call kite directly for custom range or use fetcher if it exposes custom range.
            # Using kite directly for precision.
            
            data = fetcher.kite.historical_data(token, from_date, to_date, "day")
            
            if data:
                df = pd.DataFrame(data)
                df['symbol'] = symbol
                df.to_csv(output_file, index=False)
                print(f"✅ Saved {len(df)} rows.")
                success_count += 1
            else:
                print("⚠️ No Data Returned")
                
            time.sleep(0.1) # Rate limit protection
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
    print("="*50)
    print(f"🏁 Download Complete. Successfully fetched {success_count}/{len(universe)} stocks.")

if __name__ == "__main__":
    fetch_history()
