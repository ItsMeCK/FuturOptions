import logging
import pandas as pd
from kiteconnect import KiteConnect
import os
import csv
import math
import time

# CONFIG
ACCESS_TOKEN = "xeIzqsbfCH6xJy5fm6SYYIQER8p6V9VD"
API_KEY = "anywvvfkcyjhhqiy"
DATE = "2025-12-18"
START_TIME = "09:15:00"
END_TIME = "15:30:00"
EXPIRY = "25DEC" 

def get_strike_step(price):
    if price > 5000: return 100
    if price > 2000: return 50
    if price > 1000: return 20 
    if price > 500: return 10
    return 5

def fetch_options():
    logging.basicConfig(level=logging.INFO)
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    logging.info("📥 Loading Spot Data...")
    spot_df = pd.read_csv(f"daily_data/{DATE}_nifty50_intraday.csv")
    ranges = spot_df.groupby('symbol')['close'].agg(['min', 'max'])
    
    logging.info("📥 Fetching Instrument Dump...")
    instruments = kite.instruments("NFO")
    inst_df = pd.DataFrame(instruments)
    
    relevant_symbols = ranges.index.tolist()
    inst_df = inst_df[inst_df['name'].isin(relevant_symbols)]
    
    csv_header = ["tradingsymbol", "date", "close", "oi", "volume"]
    
    with open(f"daily_data/{DATE}_options_intraday.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        
        for sym in relevant_symbols:
            low = ranges.loc[sym, 'min']
            high = ranges.loc[sym, 'max']
            step = get_strike_step((low + high)/2)
            
            min_strike = math.floor(low / step) * step - (2 * step)
            max_strike = math.ceil(high / step) * step + (2 * step)
            
            strikes = range(int(min_strike), int(max_strike) + step, step)
            logging.info(f"🎯 {sym}: Scanning Strikes {min_strike} -> {max_strike}")
            
            for strike in strikes:
                base = f"{sym}{EXPIRY}{strike}"
                for typ in ["CE", "PE"]:
                    tsym = f"{base}{typ}"
                    row = inst_df[inst_df['tradingsymbol'] == tsym]
                    if not row.empty:
                        token = row.iloc[0]['instrument_token']
                        try:
                            recs = kite.historical_data(
                                token, 
                                from_date=f"{DATE} {START_TIME}", 
                                to_date=f"{DATE} {END_TIME}", 
                                interval="minute",
                                oi=True
                            )
                            if recs:
                                for r in recs:
                                    writer.writerow([tsym, r['date'], r['close'], r['oi'], r['volume']])
                            time.sleep(0.1) # Rate Limit Buffer
                        except Exception as e:
                            logging.error(f"Failed {tsym}: {e}")
                            
if __name__ == "__main__":
    fetch_options()
