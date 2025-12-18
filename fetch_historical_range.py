import os
import pandas as pd
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Setup
load_dotenv()
API_KEY = os.getenv("ZERODHA_API_KEY")
ACCESS_TOKEN = os.getenv("ZERODHA_ACCESS_TOKEN")
OUTPUT_DIR = "daily_data"
EXPIRY = "25DEC" # Dynamic? Current expiry for Dec contract is 25DEC.

STEP_MAP = {
    "NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50,
    "RELIANCE": 20, "INFY": 20, "TCS": 50, "SBIN": 10,
    "HDFCBANK": 10, "ICICIBANK": 10, "LT": 50, "AXISBANK": 10,
    "HINDUNILVR": 20, "MARUTI": 100, "ADANIENT": 50, "KOTAKBANK": 20,
    "BHARTIARTL": 10, "BAJFINANCE": 50, "TITAN": 20, "TATASTEEL": 2.5,
    "HINDALCO": 10, "BEL": 5, "ASIANPAINT": 20, "ULTRACEMCO": 100
}

def get_strike_step(symbol):
    return STEP_MAP.get(symbol, 10)

def format_strike(strike):
    if strike % 1 == 0:
        return str(int(strike))
    return str(strike)

def get_trading_days(start_date, end_date):
    """Return list of trading days (exclude Sat/Sun)"""
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5: # 0-4 is Mon-Fri
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days

def fetch_spot_data(kite, date_str, symbols):
    output_path = f"{OUTPUT_DIR}/{date_str}_nifty50_intraday.csv"
    if os.path.exists(output_path):
        print(f"   ✅ Spot data exists for {date_str}. Skipping.")
        return output_path

    print(f"   ⏳ Fetching Spot Data for {date_str}...")
    
    # Needs instrument lookup for NSE symbols
    # Reuse instruments if passed, or fetch
    # Ideally passing 'map' is better. 
    # Let's assume global or class based logic later, for now simple loop.
    
    # We need NSE token map
    # Load once in main to save time
    
    all_data = []
    from_date = f"{date_str} 09:15:00"
    to_date = f"{date_str} 15:30:00"
    
    for symbol in symbols:
        try:
            # We need token. Searching in global INSTRUMENTS_NSE
            token = INSTRUMENTS_NSE.get(symbol)
            if not token:
                print(f"      ⚠️ No Token for {symbol}")
                continue
                
            data = kite.historical_data(token, from_date, to_date, "minute")
            if data:
                df = pd.DataFrame(data)
                df['symbol'] = symbol
                all_data.append(df)
            time.sleep(0.1) # Fast fetch
        except Exception as e:
            print(f"      ❌ Error {symbol}: {e}")
            
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_csv(output_path, index=False)
        print(f"   💾 Saved Spot Data: {output_path}")
        return output_path
    else:
        print(f"   ❌ No Spot Data Fetched for {date_str}")
        return None

def fetch_options_data(kite, date_str, spot_file):
    output_path = f"{OUTPUT_DIR}/{date_str}_options_intraday.csv"
    if os.path.exists(output_path):
        print(f"   ✅ Options data exists for {date_str}. Skipping.")
        return

    print(f"   ⏳ Fetching Options Data for {date_str}...")
    
    try:
        spot_df = pd.read_csv(spot_file)
    except:
        print("      ❌ Could not read spot file.")
        return

    summaries = spot_df.groupby('symbol').agg({'close': ['min', 'max']})
    tasks = []
    
    for symbol, row in summaries.iterrows():
        min_price = row[('close', 'min')]
        max_price = row[('close', 'max')]
        step = get_strike_step(symbol)
        
        lower_bound = (int(min_price / step) - 2) * step
        upper_bound = (int(max_price / step) + 2) * step
        
        current_strike = lower_bound
        while current_strike <= upper_bound:
            str_strike = format_strike(current_strike)
            base = f"{symbol}{EXPIRY}"
            tasks.append(f"{base}{str_strike}CE")
            tasks.append(f"{base}{str_strike}PE")
            current_strike += step
            
    # Filter valid
    valid_tasks = [t for t in tasks if t in INSTRUMENTS_NFO]
    print(f"      📋 Fetching {len(valid_tasks)} option symbols...")
    
    all_options_data = []
    from_date = f"{date_str} 09:15:00"
    to_date = f"{date_str} 15:30:00"
    
    counter = 0
    for sym in valid_tasks:
        token = INSTRUMENTS_NFO[sym]
        try:
            data = kite.historical_data(token, from_date, to_date, "minute")
            if data:
                df = pd.DataFrame(data)
                df['tradingsymbol'] = sym
                df['symbol'] = sym 
                all_options_data.append(df)
            
            counter += 1
            if counter % 100 == 0:
                print(f"      ...{counter}/{len(valid_tasks)}")
                
            time.sleep(0.3) # 3 req/sec limit
        except Exception as e:
            print(f"      ❌ Err {sym}: {e}")
            
    if all_options_data:
        final_df = pd.concat(all_options_data, ignore_index=True)
        final_df.to_csv(output_path, index=False)
        print(f"   💾 Saved Options Data: {output_path}")
    else:
        print(f"   ❌ No Options Data Fetched.")

# Globals to be handled in main
INSTRUMENTS_NSE = {}
INSTRUMENTS_NFO = {}

def main():
    global INSTRUMENTS_NSE, INSTRUMENTS_NFO
    
    print("🚀 Background Data Fetcher Started...")
    
    if not API_KEY or not ACCESS_TOKEN:
        print("❌ Missing Credentials")
        return

    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    # Load Instruments ONCE
    print("⏳ Loading Instruments...")
    instruments = kite.instruments() # All
    
    for i in instruments:
        if i['exchange'] == 'NSE':
            INSTRUMENTS_NSE[i['tradingsymbol']] = i['instrument_token']
        elif i['exchange'] == 'NFO':
            INSTRUMENTS_NFO[i['tradingsymbol']] = i['instrument_token']
            
    print(f"✅ Instruments Loaded (NSE: {len(INSTRUMENTS_NSE)}, NFO: {len(INSTRUMENTS_NFO)})")
    
    # Load Symbols List (Top 50)
    try:
        leaderboard = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
        symbols = leaderboard['Symbol'].tolist()
    except:
        print("⚠️ Could not load leaderboard. Using default list.")
        symbols = list(STEP_MAP.keys())
        
    # Date Range
    start = datetime(2025, 12, 5)
    end = datetime(2025, 12, 17)
    trading_days = get_trading_days(start, end)
    
    print(f"📅 Trading Days to Process: {trading_days}")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    for date_str in trading_days:
        print(f"\nProcessing {date_str}...")
        
        # 1. Fetch Spot
        spot_file = fetch_spot_data(kite, date_str, symbols)
        
        # 2. Fetch Options (Only if spot successful)
        if spot_file:
            fetch_options_data(kite, date_str, spot_file)
            
    print("\n🎉 All Done!")

if __name__ == "__main__":
    main()
