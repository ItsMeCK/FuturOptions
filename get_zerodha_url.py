import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZERODHA_API_KEY")
api_secret = os.getenv("ZERODHA_API_SECRET")

if not api_key:
    print("❌ ZERODHA_API_KEY not found in .env")
else:
    kite = KiteConnect(api_key=api_key)
    print("\n🔐 Zerodha Login Required")
    print("To fetch historical data, we need an Access Token.")
    print("Please click the link below, login to Zerodha, and copy the 'request_token' from the URL.")
    print("-" * 60)
    print(kite.login_url())
    print("-" * 60)
