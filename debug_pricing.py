import os
import logging
from kiteconnect import KiteConnect
import json

# Setup Logging
logging.basicConfig(level=logging.INFO)

def debug_pricing():
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")

    if not api_key or not access_token:
        print("❌ Missing API Key or Access Token")
        return

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    # Symbols to check
    # Note: Zerodha symbols for NSE options usually don't need "NSE:" prefix in the symbol string itself 
    # if passed to quote, but keys might have it. 
    # Actually, quote takes "exchange:symbol".
    
    symbol_underlying = "NSE:INFY"
    symbol_option = "NFO:INFY25DEC1580PE" # Options are on NFO

    print(f"🔍 Fetching quotes for: {symbol_underlying}, {symbol_option}")

    try:
        quotes = kite.quote([symbol_underlying, symbol_option])
        print(json.dumps(quotes, indent=4, default=str))
        
        if symbol_option in quotes:
            opt_data = quotes[symbol_option]
            print(f"\n--- Analysis for {symbol_option} ---")
            print(f"LTP: {opt_data.get('last_price')}")
            print(f"Volume: {opt_data.get('volume')}")
            print(f"Last Trade Time: {opt_data.get('last_trade_time')}")
            print(f"Bid: {opt_data['depth']['buy'][0]['price'] if opt_data.get('depth') else 'N/A'}")
            print(f"Ask: {opt_data['depth']['sell'][0]['price'] if opt_data.get('depth') else 'N/A'}")
        else:
            print(f"❌ No data found for {symbol_option}")

    except Exception as e:
        print(f"❌ Error fetching quotes: {e}")

if __name__ == "__main__":
    debug_pricing()
