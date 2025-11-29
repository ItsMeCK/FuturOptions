import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZERODHA_API_KEY")
api_secret = os.getenv("ZERODHA_API_SECRET")
request_token = "ovp2wVdjbl3bkswWXT0gd6esPOKH4L3U"

if not api_key or not api_secret:
    print("❌ Keys missing in .env")
else:
    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        print(f"ZERODHA_ACCESS_TOKEN={data['access_token']}")
    except Exception as e:
        print(f"❌ Error generating session: {e}")
