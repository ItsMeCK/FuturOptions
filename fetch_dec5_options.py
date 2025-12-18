import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from kiteconnect import KiteConnect
import time

# Load Env
load_dotenv()
API_KEY = os.getenv("ZERODHA_API_KEY")
ACCESS_TOKEN = os.getenv("ZERODHA_ACCESS_TOKEN")

SPOT_FILE = "daily_data/2025-12-05_nifty50_intraday.csv"
OUTPUT_FILE = "daily_data/2025-12-05_options_intraday.csv"
DATE_TARGET = "2025-12-05"
EXPIRY = "25DEC" # Hardcoded for Dec 5th simulation context

# Step Sizes Map (Copied from OptionsBrain)
STEP_MAP = {
    "NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50,
    "RELIANCE": 20, "INFY": 20, "TCS": 50, "SBIN": 10,
    "HDFCBANK": 10, "ICICIBANK": 10, "LT": 50, "AXISBANK": 10,
    "HINDUNILVR": 20, "MARUTI": 100, "ADANIENT": 50, "KOTAKBANK": 20,
    "BHARTIARTL": 10, "BAJFINANCE": 50, "TITAN": 20, "TATASTEEL": 2.5,
    "HINDALCO": 10, "BEL": 5, "ASIANPAINT": 20, "ULTRACEMCO": 100
}

def get_strike_step(symbol):
    return STEP_MAP.get(symbol, 10) # Default 10

def format_strike(strike):
    if strike % 1 == 0:
        return str(int(strike))
    return str(strike)

def main():
    print(f"🚀 Starting Option Data Collection for {DATE_TARGET}...")
    
    # 1. Initialize Kite
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    # 2. Load Instruments (Heavy Operation)
    print("⏳ Fetching NFO Instruments Dump...")
    instruments = kite.instruments("NFO")
    # Optimize Lookup
    token_map = {i['tradingsymbol']: i['instrument_token'] for i in instruments}
    print(f"✅ Loaded {len(token_map)} NFO instruments.")
    
    # 3. Load Spot Data Analysis
    print(f"📖 Reading Spot Data from {SPOT_FILE}...")
    spot_df = pd.read_csv(SPOT_FILE)
    
    # Group by symbol to find range
    summaries = spot_df.groupby('symbol').agg({'close': ['min', 'max']})
    
    tasks = []
    
    for symbol, row in summaries.iterrows():
        min_price = row[('close', 'min')]
        max_price = row[('close', 'max')]
        step = get_strike_step(symbol)
        
        # Add Buffer (e.g., 2 strikes above/below)
        lower_bound = (int(min_price / step) - 2) * step
        upper_bound = (int(max_price / step) + 2) * step
        
        print(f"🔍 {symbol}: Price {min_price:.1f}-{max_price:.1f} -> Strikes {lower_bound} to {upper_bound} (Step {step})")
        
        current_strike = lower_bound
        while current_strike <= upper_bound:
            str_strike = format_strike(current_strike)
            base = f"{symbol}{EXPIRY}"
            
            ce_sym = f"{base}{str_strike}CE"
            pe_sym = f"{base}{str_strike}PE"
            
            tasks.append(ce_sym)
            tasks.append(pe_sym)
            
            current_strike += step
            
    print(f"📋 Identified {len(tasks)} potential option symbols to fetch.")
    
    # 4. Fetch Data
    all_options_data = []
    
    # Filter only tasks that exist in map
    valid_tasks = [t for t in tasks if t in token_map]
    print(f"✅ Found {len(valid_tasks)} valid symbols in instrument list.")
    
    counter = 0
    for sym in valid_tasks:
        token = token_map[sym]
        try:
            # Rate limiting check
            # Zerodha allows 3 req/sec approx. Let's be safe.
            time.sleep(0.3) 
            
            from_date = f"{DATE_TARGET} 09:15:00"
            to_date = f"{DATE_TARGET} 15:30:00"
            
            data = kite.historical_data(token, from_date, to_date, "minute")
            
            if data:
                df = pd.DataFrame(data)
                df['tradingsymbol'] = sym
                df['symbol'] = sym  # For easier lookup
                all_options_data.append(df)
            
            counter += 1
            if counter % 50 == 0:
                print(f"   Fetched {counter}/{len(valid_tasks)}...")
                
        except Exception as e:
            print(f"❌ Error fetching {sym}: {e}")
            
    # 5. Save
    if all_options_data:
        final_df = pd.concat(all_options_data, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n🎉 Option Data Collection Complete!")
        print(f"💾 Saved {len(final_df)} rows to {OUTPUT_FILE}")
    else:
        print("❌ No option data fetched.")

if __name__ == "__main__":
    main()
