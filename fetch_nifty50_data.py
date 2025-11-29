import os
import pandas as pd
from ai_option_brain.data_loader import ZerodhaDataFetcher
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv()

# Failed Stocks Retry List
NIFTY_50 = [
    'NTPC', 'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 
    'SBIN', 'SUNPHARMA', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 
    'TCS', 'TECHM', 'TITAN', 'ULTRACEMCO', 'WIPRO'
]

def fetch_all_nifty_data():
    fetcher = ZerodhaDataFetcher()
    # fetcher.connect() # Removed as connection happens in __init__
    
    # Date Range: 2 Years (Max allowed for 1min data usually, but we'll try)
    # Actually Zerodha allows 1min for ~6 months to 1 year depending on subscription?
    # Let's try to fetch as much as possible.
    # Based on previous runs, we got data from Dec 2024 to Nov 2025.
    # Let's ask for 2 years, it will return what's available.
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2) # 2 Years
    
    print(f"🚜 Starting Nifty 50 Data Harvest...")
    print(f"   Target: {len(NIFTY_50)} Stocks")
    print(f"   Range: {start_date.date()} to {end_date.date()}")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(NIFTY_50):
        print(f"[{i+1}/{len(NIFTY_50)}] Fetching {symbol}...")
        
        try:
            # 1. Get Instrument Token
            token = fetcher.get_instrument_token(symbol)
            if not token:
                print(f"   ⚠️ Token not found for {symbol}")
                fail_count += 1
                continue
                
            # 2. Fetch Data
            df = fetcher.fetch_historical_data(token, start_date, end_date, interval="minute")
            
            if df is not None and not df.empty:
                # 3. Save to CSV
                filename = f"data/{symbol}.NS_2y_1d.csv"
                df.to_csv(filename, index=False)
                print(f"   ✅ Saved {len(df)} rows to {filename}")
                success_count += 1
            else:
                print(f"   ⚠️ No data returned for {symbol}")
                fail_count += 1
                
        except Exception as e:
            print(f"   ❌ Error fetching {symbol}: {e}")
            fail_count += 1
            
        # Respect API Rate Limits (3 requests per second allowed, but let's be safe)
        time.sleep(0.5)
        
    print("="*60)
    print(f"🏁 Harvest Complete.")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")

if __name__ == "__main__":
    fetch_all_nifty_data()
