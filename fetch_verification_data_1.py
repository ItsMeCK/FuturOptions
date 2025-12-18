import logging
import pandas as pd
import datetime
from kiteconnect import KiteConnect
import os
import csv

# CONFIG
ACCESS_TOKEN = "xeIzqsbfCH6xJy5fm6SYYIQER8p6V9VD"
API_KEY = "anywvvfkcyjhhqiy"
DATE = "2025-12-17"
START_TIME = "09:15:00"
END_TIME = "15:30:00"

# Symbols to Fetch (Spot)
SPOT_SYMBOLS = [
    "ADANIENT", "HINDALCO", "INDUSINDBK", "BHARTIARTL", "BAJAJFINSV", 
    "INFY", "MARUTI", "HINDUNILVR", "BEL", "TATASTEEL", 
    "NIFTY 50", "NIFTY BANK"
]

# Traded Options (Manual List from Audit + JSON)
# Looking at trade_report_dec17.md or extracted list
# I will fetch the instrument dump to find tokens first? No, easier to just search if I had tokens.
# But I don't have tokens for options easily without mapping.
# Actually, I can search by symbol string using Kite.quote or just instrument lookup.
# Since I need *Historical* data, I need the *Instrument Token*.
# Solution: Fetch full Instrument Dump, map Symbols to Tokens, then fetch history.

def fetch_data():
    logging.basicConfig(level=logging.INFO)
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    # 1. Get Instruments to map Symbols -> Tokens
    logging.info("📥 Fetching Instrument Dump...")
    instruments = kite.instruments()
    inst_df = pd.DataFrame(instruments)
    
    # Map Spot Symbols
    spot_map = {} # Symbol -> Token
    logging.info(f"Columns: {inst_df.columns}")
    
    for sym in SPOT_SYMBOLS:
        # Check NSE Equity
        filt = inst_df[
            (inst_df['tradingsymbol'] == sym) & 
            (inst_df['exchange'] == 'NSE')
        ]
        
        # Check Indices (NSE-INDICES? or just NSE)
        if filt.empty and sym.startswith("NIFTY"):
             filt = inst_df[
                 (inst_df['tradingsymbol'] == sym) & 
                 (inst_df['segment'] == 'INDICES')
             ]
        
        if not filt.empty:
            spot_map[sym] = filt.iloc[0]['instrument_token']
        else:
            logging.warning(f"❌ Token not found for {sym}")

    # Map Option Symbols (We need to parse 25DEC etc)
    # Let's just list the known ones from our earlier report/logs if possible.
    # From trade_history.csv: NFO:ADANIENT25DEC2240PE etc. (Prefix NFO: might need cleaning)
    # I'll read trade_history to get exact option symbols.
    
    # 2. Fetch Historical Data (Spot)
    logging.info("📥 Fetching Spot Data...")
    
    csv_header = ["symbol", "date", "open", "high", "low", "close", "volume", "oi"]
    
    with open("daily_data/2025-12-17_nifty50_intraday.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        
        for sym, token in spot_map.items():
            try:
                # Fetch Intraday
                records = kite.historical_data(
                    token, 
                    from_date=f"{DATE} {START_TIME}", 
                    to_date=f"{DATE} {END_TIME}", 
                    interval="minute"
                )
                
                logging.info(f"✅ {sym}: Fetched {len(records)} candles.")
                
                for r in records:
                    # Write to CSV
                    writer.writerow([
                        sym, 
                        r['date'], 
                        r['open'], r['high'], r['low'], r['close'], r['volume'], 
                        0 # Spot OI is 0
                    ])
            except Exception as e:
                logging.error(f"❌ Failed to fetch {sym}: {e}")

if __name__ == "__main__":
    if not os.path.exists("daily_data"):
        os.makedirs("daily_data")
    fetch_data()
