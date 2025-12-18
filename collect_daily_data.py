import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher

# Setup
load_dotenv()
DATE_TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = "daily_data"
OUTPUT_FILE = f"{OUTPUT_DIR}/{DATE_TODAY}_nifty50_intraday.csv"

def collect_data():
    print(f"🚀 Starting Data Collection for {DATE_TODAY}...")
    
    # 1. Initialize Fetcher
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    if not access_token:
        print("❌ No Access Token found!")
        return
        
    fetcher = ZerodhaDataFetcher(api_key, access_token)
    
    # 2. Load Nifty 50 Symbols
    try:
        leaderboard = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
        symbols = leaderboard['Symbol'].tolist()
        print(f"📋 Loaded {len(symbols)} symbols from leaderboard.")
    except Exception as e:
        print(f"❌ Error loading leaderboard: {e}")
        return

    # 3. Create Output Directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 4. Fetch Data
    all_data = []
    
    for symbol in symbols:
        try:
            print(f"⏳ Fetching data for {symbol}...")
            token = fetcher.get_instrument_token(symbol, exchange="NSE")
            if not token:
                print(f"   ⚠️ Token not found for {symbol}")
                continue
                
            # Fetch for today (from 9:15 to now)
            from_date = f"{DATE_TODAY} 09:15:00"
            to_date = f"{DATE_TODAY} 15:30:00"
            
            df = fetcher.fetch_historical_data(token, from_date, to_date, interval="minute")
            
            if not df.empty:
                df['symbol'] = symbol
                all_data.append(df)
                print(f"   ✅ Fetched {len(df)} candles.")
            else:
                print(f"   ⚠️ No data returned for {symbol}")
                
        except Exception as e:
            print(f"   ❌ Error fetching {symbol}: {e}")
            
    # 5. Save to CSV
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n🎉 Data Collection Complete!")
        print(f"💾 Saved {len(final_df)} rows to {OUTPUT_FILE}")
        print(f"📊 Symbols Covered: {final_df['symbol'].nunique()}")
    else:
        print("\n❌ No data collected.")

if __name__ == "__main__":
    collect_data()
