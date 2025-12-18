import os
import logging
from ai_option_brain.data_loader import ZerodhaDataFetcher
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

def test_data_fetch():
    print("🚀 Starting Data Fetch Test...")
    
    fetcher = ZerodhaDataFetcher()
    
    if not fetcher.kite:
        print("❌ Zerodha API not initialized. Check .env")
        return

    # Test Symbols (Focus List Candidates)
    symbols = ["RELIANCE", "TCS", "SUNPHARMA", "INFY", "HDFCBANK"]
    
    print(f"🔍 Testing Symbols: {symbols}")
    
    # 1. Test Instrument Token Fetch
    print("\n--- 1. Testing Instrument Tokens ---")
    tokens = {}
    for sym in symbols:
        token = fetcher.get_instrument_token(sym)
        if token:
            print(f"✅ {sym}: {token}")
            tokens[sym] = token
        else:
            print(f"❌ {sym}: Token Not Found!")
            
    # 2. Test Live Quote Fetch
    print("\n--- 2. Testing Live Quotes ---")
    quotes = fetcher.fetch_live_quote(symbols)
    for sym in symbols:
        if sym in quotes:
            print(f"✅ {sym}: {quotes[sym]['last_price']}")
        else:
            print(f"❌ {sym}: Quote Missing!")

    # 3. Test Historical Data Fetch
    print("\n--- 3. Testing Historical Data (5 Days) ---")
    for sym, token in tokens.items():
        if token:
            df = fetcher.fetch_latest_data(token, days=5)
            if not df.empty:
                print(f"✅ {sym}: Fetched {len(df)} candles. Last Close: {df['close'].iloc[-1]}")
                # Check Volume
                if 'volume' in df.columns and df['volume'].sum() > 0:
                     print(f"   Volume Data Present. Avg Vol: {df['volume'].mean():.0f}")
                else:
                     print(f"   ⚠️ Volume Data Missing or Zero!")
            else:
                print(f"❌ {sym}: Historical Data Empty!")

    # 4. Test Option Symbol Construction
    print("\n--- 4. Testing Option Symbol Construction ---")
    for sym in symbols:
        if sym in quotes:
            spot = quotes[sym]['last_price']
            opt_sym, strike = fetcher.get_option_symbol(sym, spot, "CE")
            print(f"ℹ️ {sym} Spot: {spot} -> Option: {opt_sym} (Strike {strike})")
            
            # Try fetching option quote
            opt_quote = fetcher.fetch_live_quote([opt_sym])
            if opt_sym in opt_quote:
                print(f"   ✅ Option Quote: {opt_quote[opt_sym]['last_price']}")
            else:
                print(f"   ❌ Option Quote Missing for {opt_sym}")

if __name__ == "__main__":
    test_data_fetch()
