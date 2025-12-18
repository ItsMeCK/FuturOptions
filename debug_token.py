import os
import pandas as pd
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ZERODHA_API_KEY")
access_token = os.getenv("ZERODHA_ACCESS_TOKEN")

print(f"Token: {access_token[:6]}...")

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Use valid Future or Option? 
# NIFTY25DECFUT might operate differently, let's look for known one.
print("Fetching instruments...")
instruments = kite.instruments("NFO")
token = None
for i in instruments:
    if i['name'] == 'NIFTY' and i['instrument_type'] == 'FUT':
        token = i['instrument_token']
        print(f"Found NIFTY FUT Token: {token}")
        break
        
if token:
    print("Testing Historical Data Fetch (Dec 5)...")
    try:
        data = kite.historical_data(
            token, 
            "2025-12-05 09:15:00", 
            "2025-12-05 09:20:00", 
            "minute"
        )
        print(f"Success! Rows: {len(data)}")
        print(data)
    except Exception as e:
        print(f"FAILED: {e}")
else:
    print("RELIANCE not found.")
