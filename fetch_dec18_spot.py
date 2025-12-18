import logging
import pandas as pd
import datetime
from kiteconnect import KiteConnect
import os
import csv

# CONFIG
ACCESS_TOKEN = "xeIzqsbfCH6xJy5fm6SYYIQER8p6V9VD"
API_KEY = "anywvvfkcyjhhqiy"
DATE = "2025-12-18"
START_TIME = "09:15:00"
END_TIME = "15:30:00"

SPOT_SYMBOLS = [
    "ADANIENT", "HINDALCO", "INDUSINDBK", "BHARTIARTL", "BAJAJFINSV", 
    "INFY", "MARUTI", "HINDUNILVR", "BEL", "TATASTEEL", 
    "NIFTY 50", "NIFTY BANK"
]

def fetch_data():
    logging.basicConfig(level=logging.INFO)
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    logging.info("📥 Fetching Instrument Dump...")
    instruments = kite.instruments()
    inst_df = pd.DataFrame(instruments)
    
    spot_map = {} 
    
    for sym in SPOT_SYMBOLS:
        filt = inst_df[
            (inst_df['tradingsymbol'] == sym) & 
            (inst_df['exchange'] == 'NSE')
        ]
        if filt.empty and sym.startswith("NIFTY"):
             filt = inst_df[
                 (inst_df['tradingsymbol'] == sym) & 
                 (inst_df['segment'] == 'INDICES')
             ]
        
        if not filt.empty:
            spot_map[sym] = filt.iloc[0]['instrument_token']
        else:
            logging.warning(f"❌ Token not found for {sym}")

    logging.info("📥 Fetching Spot Data...")
    
    csv_header = ["symbol", "date", "open", "high", "low", "close", "volume", "oi"]
    
    with open(f"daily_data/{DATE}_nifty50_intraday.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        
        for sym, token in spot_map.items():
            try:
                records = kite.historical_data(
                    token, 
                    from_date=f"{DATE} {START_TIME}", 
                    to_date=f"{DATE} {END_TIME}", 
                    interval="minute"
                )
                logging.info(f"✅ {sym}: Fetched {len(records)} candles.")
                for r in records:
                    writer.writerow([
                        sym, r['date'], r['open'], r['high'], r['low'], r['close'], r['volume'], 0
                    ])
            except Exception as e:
                logging.error(f"❌ Failed to fetch {sym}: {e}")

if __name__ == "__main__":
    if not os.path.exists("daily_data"):
        os.makedirs("daily_data")
    fetch_data()
