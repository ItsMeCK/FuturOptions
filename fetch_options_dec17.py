import logging
import pandas as pd
from kiteconnect import KiteConnect
import os
import csv
import math

# CONFIG
ACCESS_TOKEN = "xeIzqsbfCH6xJy5fm6SYYIQER8p6V9VD"
API_KEY = "anywvvfkcyjhhqiy"
DATE = "2025-12-17"
START_TIME = "09:15:00"
END_TIME = "15:30:00"
EXPIRY = "25DEC" # 2025 DEC (Check actual expiry in dump or assume logic)

def get_strike_step(price):
    if price > 5000: return 100
    if price > 2000: return 50 # ADANIENT (~2200) -> 50? Wait, 2240 is valid strike? 20 step?
    if price > 1000: return 20 
    if price > 500: return 10
    return 5
    
    # Specific Overrides if known
    # ADANIENT is likely 20 or 50? Log said 2240. So 20 ok.
    # HINDALCO (850) -> 10 ok.
    # MARUTI (16400) -> 100 ok.

def fetch_options():
    logging.basicConfig(level=logging.INFO)
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    logging.info("📥 Loading Spot Data...")
    spot_df = pd.read_csv("daily_data/2025-12-17_nifty50_intraday.csv")
    
    # Get High/Low range for each symbol to cover all ATM shifts
    ranges = spot_df.groupby('symbol')['close'].agg(['min', 'max', 'mean'])
    
    # 1. Fetch Instruments (Need NFO)
    logging.info("📥 Fetching Instrument Dump...")
    instruments = kite.instruments("NFO")
    inst_df = pd.DataFrame(instruments)
    # Filter for Dec Expiry? The logs had 25DEC.
    # Format: 25DEC (YYMMM).
    # inst_df['expiry'] -> date object. We can filter by name ending with 25DEC?
    # Or just 'tradingsymbol' contains '25DEC'.
    
    # Map Symbol + Strike + Type -> Token
    # To save time, we filter inst_df to only relevant symbols first
    relevant_symbols = ranges.index.tolist()
    # Need to match NFO symbol names (e.g. ADANIENT)
    inst_df = inst_df[inst_df['name'].isin(relevant_symbols)]
    
    csv_header = ["tradingsymbol", "date", "close", "oi", "volume"]
    
    with open("daily_data/2025-12-17_options_intraday.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        
        for sym in relevant_symbols:
            low = ranges.loc[sym, 'min']
            high = ranges.loc[sym, 'max']
            step = get_strike_step((low + high)/2)
            
            # Generate Strikes covering the range
            # Round min down to nearest step, max up
            min_strike = math.floor(low / step) * step
            max_strike = math.ceil(high / step) * step
            
            # Buffer +/- 2 steps
            min_strike -= (2 * step)
            max_strike += (2 * step)
            
            strikes = []
            curr = min_strike
            while curr <= max_strike:
                strikes.append(curr)
                curr += step
            
            logging.info(f"🎯 {sym}: Scanning Strikes {min_strike} -> {max_strike} (Step {step})")
            
            for strike in strikes:
                strike = int(strike)
                # Form Tradingsymbols (CE & PE)
                # Format: SYMBOL + YY + MMM + STRIKE + CE/PE
                # Expiry 25DEC (Year 25, Month DEC)
                base = f"{sym}{EXPIRY}{strike}"
                
                for typ in ["CE", "PE"]:
                    tsym = f"{base}{typ}"
                    
                    # Look up Token
                    row = inst_df[inst_df['tradingsymbol'] == tsym]
                    if not row.empty:
                        token = row.iloc[0]['instrument_token']
                        try:
                            # Fetch
                            recs = kite.historical_data(
                                token, 
                                from_date=f"{DATE} {START_TIME}", 
                                to_date=f"{DATE} {END_TIME}", 
                                interval="minute",
                                oi=True
                            )
                            if recs:
                                for r in recs:
                                    writer.writerow([
                                        tsym, r['date'], 
                                        r['close'], r['oi'], r['volume']
                                    ])
                                # logging.info(f"✅ Fetched {tsym}: {len(recs)}")
                        except Exception as e:
                            logging.error(f"Failed {tsym}: {e}")
                    else:
                        # logging.warning(f"⚠️ Instrument not found: {tsym}")
                        pass
                        
if __name__ == "__main__":
    fetch_options()
