import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Load Env
load_dotenv()

def test_options_data():
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    
    if not api_key or not access_token:
        print("❌ Missing API Key/Token")
        return

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    
    # Test Symbol: NIFTY 25 DEC 24500 CE (Example - need a valid symbol)
    # Let's search for a valid symbol first
    print("🔍 Searching for NIFTY Option...")
    instruments = kite.instruments("NFO")
    
    nifty_opts = [i for i in instruments if i['name'] == 'NIFTY' and i['instrument_type'] == 'CE']
    if not nifty_opts:
        print("❌ No NIFTY Options found.")
        return
        
    # Pick one
    opt = nifty_opts[0]
    symbol = opt['tradingsymbol']
    token = opt['instrument_token']
    print(f"✅ Found: {symbol} (Token: {token})")
    
    # Fetch Quote
    print(f"🔍 Fetching Quote for {symbol}...")
    quote = kite.quote([f"NFO:{symbol}"])
    
    if not quote:
        print("❌ Quote failed.")
        return
        
    data = quote[f"NFO:{symbol}"]
    print("\n--- Quote Data ---")
    print(f"OI: {data.get('oi', 'N/A')}")
    print(f"OI Day High: {data.get('oi_day_high', 'N/A')}")
    print(f"OI Day Low: {data.get('oi_day_low', 'N/A')}")
    print(f"Volume: {data.get('volume', 'N/A')}")
    print(f"Last Price: {data.get('last_price', 'N/A')}")

if __name__ == "__main__":
    test_options_data()
