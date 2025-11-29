import os
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher
from datetime import datetime, timedelta

load_dotenv()

def debug_tata():
    fetcher = ZerodhaDataFetcher()
    if not fetcher.kite:
        print("❌ Login Failed")
        return

    symbol = "TATAMOTORS"
    print(f"🔍 Debugging {symbol}...")
    
    # 1. Check Token
    token = fetcher.get_instrument_token(symbol, "NSE")
    print(f"   Token: {token}")
    
    if token:
        # 2. Try Fetching
        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)
        print(f"   Fetching 5 days of data...")
        df = fetcher.fetch_historical_data(token, from_date, to_date, "minute")
        print(f"   Rows fetched: {len(df)}")
        if not df.empty:
            print(df.head())
    else:
        print("   ❌ Token lookup failed. Searching dump for 'TATA'...")
        instruments = fetcher.kite.instruments("NSE")
        found = [i['tradingsymbol'] for i in instruments if 'TATA' in i['tradingsymbol']]
        with open("debug_output.txt", "w") as f:
            f.write(f"Found {len(found)} matches:\n")
            f.write(str(found))
        print("   Debug output written to debug_output.txt")






if __name__ == "__main__":
    debug_tata()
