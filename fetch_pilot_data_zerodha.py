import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher

load_dotenv()

def fetch_pilot_data_zerodha():
    fetcher = ZerodhaDataFetcher()
    if not fetcher.kite:
        print("❌ Zerodha Login Failed. Check .env")
        return

    stocks = ["RELIANCE", "ADANIENT", "HDFCBANK", "SBIN", "TATAMOTORS", "INDIA VIX"]
    data_dir = "ai_option_brain/data/raw"
    os.makedirs(data_dir, exist_ok=True)
    
    print("🚀 Starting Pilot Data Fetch (Source: Zerodha)...")
    print("="*60)
    
    # Define Date Range (3 Years)
    to_date = datetime.now()
    from_date = to_date - timedelta(days=365*3)
    
    for symbol in stocks:
        print(f"🔍 Processing {symbol}...")
        
        # 1. Get Instrument Token
        # Note: INDIA VIX symbol might be different in Zerodha instrument dump. Usually 'INDIA VIX' or index token.
        # For indices, we might need to check Nifty 50 too.
        # Let's try standard NSE symbols.
        exchange = "NSE"
        token = fetcher.get_instrument_token(symbol, exchange)
        
        if not token and symbol == "INDIA VIX":
             # Try alternative for VIX
             token = fetcher.get_instrument_token("INDIA VIX", "NSE") # Sometimes it's an index
             if not token:
                 print("   ⚠️ Could not find token for INDIA VIX. Skipping.")
                 continue

        if not token:
            print(f"   ❌ Token not found for {symbol}")
            continue
            
        print(f"   ✅ Token: {token}")
        
        # 2. Fetch 60-min Data (For Trend)
        print(f"   📥 Fetching 60-min data...")
        df_60 = fetcher.fetch_historical_data(token, from_date, to_date, "60minute")
        if not df_60.empty:
            df_60.to_csv(f"{data_dir}/{symbol}_60min.csv", index=False)
            print(f"      Saved {len(df_60)} rows.")
            
        # 3. Fetch 1-min Data (For Volatility Training - Last 1 Year only to save time/bandwidth for pilot)
        # Fetching 3 years of 1-min is heavy. Let's do 1 year for the Pilot.
        print(f"   📥 Fetching 1-min data (Last 1 Year)...")
        from_date_1m = to_date - timedelta(days=365)
        df_1 = fetcher.fetch_historical_data(token, from_date_1m, to_date, "minute")
        if not df_1.empty:
            df_1.to_csv(f"{data_dir}/{symbol}_1min.csv", index=False)
            print(f"      Saved {len(df_1)} rows.")

    print("="*60)
    print("🏁 Data Fetch Complete.")

if __name__ == "__main__":
    fetch_pilot_data_zerodha()
