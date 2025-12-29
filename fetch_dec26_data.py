import os
import pandas as pd
import logging
from datetime import datetime, time
import pytz
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_data_for_date(target_date="2025-12-26"):
    load_dotenv()
    
    # Initialize Fetcher
    try:
        api_key = os.getenv("ZERODHA_API_KEY")
        # Load token from .env initially
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        
        # Override with hot file if exists (User just provided new token)
        if os.path.exists("zerodha_hot_token.txt"):
            try:
                with open("zerodha_hot_token.txt", "r") as f:
                    file_token = f.read().strip()
                if file_token:
                    access_token = file_token
                    logging.info("🔑 Used Access Token from zerodha_hot_token.txt")
            except Exception as e:
                logging.warning(f"Failed to read hot token file: {e}")

        if not api_key or not access_token:
            # Try loading from file similarly to live_brain
            try:
                with open("zerodha_hot_token.txt", "r") as f:
                    access_token = f.read().strip()
                logging.info("loaded access token from hot file")
            except:
                logging.error("❌ Credentials missing. Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN or zerodha_hot_token.txt")
                return

        fetcher = ZerodhaDataFetcher(api_key=api_key, access_token=access_token)
        logging.info("✅ Zerodha Fetcher Initialized.")
    except Exception as e:
        logging.error(f"❌ Failed to init fetcher: {e}")
        return

    # Load Universe
    try:
        with open("fno_universe.txt", "r") as f:
            universe = [line.strip() for line in f if line.strip()]
        logging.info(f"🌌 Loaded {len(universe)} stocks from fno_universe.txt")
    except FileNotFoundError:
        logging.error("❌ fno_universe.txt not found!")
        return

    # Date handling
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    from_date = datetime.combine(date_obj, time(9, 15))
    to_date = datetime.combine(date_obj, time(15, 30))
    
    # 1. Fetch Spot Data
    logging.info(f"⏳ Fetching Spot Data for {len(universe)} stocks ({target_date})...")
    spot_dfs = []
    
    # Fetch in batches to check progress
    batch_size = 50
    for i in range(0, len(universe), batch_size):
        batch = universe[i:i+batch_size]
        logging.info(f"   Batch {i}-{i+len(batch)}...")
        
        for symbol in batch:
            try:
                token = fetcher.get_instrument_token(symbol, exchange="NSE")
                if not token:
                    logging.warning(f"   ⚠️ Token not found for {symbol}")
                    continue
                    
                df = fetcher.fetch_historical_data(token, from_date, to_date, interval="minute")
                if not df.empty:
                    df['symbol'] = symbol
                    spot_dfs.append(df)
            except Exception as e:
                logging.error(f"   ❌ Error fetching {symbol}: {e}")

    if spot_dfs:
        full_spot = pd.concat(spot_dfs)
        spot_save_path = f"daily_data/{target_date}_spot_full.csv"
        os.makedirs("daily_data", exist_ok=True)
        full_spot.to_csv(spot_save_path)
        logging.info(f"✅ Saved Spot Data: {spot_save_path} ({len(full_spot)} rows)")
    else:
        logging.error("❌ No Spot Data Fetched!")
        return

    # 2. Fetch Option Data (ATM CE/PE)
    # We need to find the ATM strike for each stock based on the day's average/close price roughly
    # Optimally, we fetch ALL options? That's too much data.
    # User said "Get options data for 209 stocks".
    # Strategy: For each stock, calculate roughly the ATM strike from spot data, 
    # and fetch 1 OTM, 1 ATM, 1 ITM? Or just ATM?
    # LiveBrain checks ATM. Let's fetch ATM CE and PE.
    
    logging.info(f"⏳ Fetching Option Data (ATM) for {len(spot_dfs)} valid stocks...")
    opt_dfs = []
    
    expiry = "25DEC" # Check if this is valid for Dec 26? NO! 
    # If date is Dec 26, Dec 25 expiry is DONE.
    # Expiry for Dec 26 would be... Jan? or Next Weekly?
    # Stock Options are Monthly. Dec 26 is AFTER Dec 25.
    # So Expiry is JAN! "26JAN"? No, Last Thursday of Jan 2026.
    # Let's check the instrument dump or assume "26JAN".
    # Wait, simple heuristic: fetcher.get_option_symbol uses logic.
    # But hardcoded expiry in get_option_symbol might be an issue user mentioned?
    # Let's check `live_brain.py` expiry logic later. For now, we need to KNOW the expiry to fetch.
    # If today is Dec 26, the current expiry is JAN.
    
    # HACK: Retrieve one option chain to verify expiry format?
    # Or just try "26JAN".
    # Actually, we should check `ai_option_brain/data_loader.py` logic.
    # Let's assume "26JAN" for now (Standard 3-char month + 2-digit year).
    
    current_expiry = "26JAN" 
    
    for df in spot_dfs:
        symbol = df['symbol'].iloc[0]
        rec_price = df['close'].iloc[-1] # Use last close to find strike
        
        # Find strikes
        # We need step size.
        # This is hard without the master list. 
        # LETS DO: Fetch all strikes for the symbol and filter? No, heavy.
        
        # Heuristic: 
        # Attempt to use the fetcher's helper if it exists, or just scan the master list (requires dump).
        # RobustLiveBrain/Mock uses string matching.
        # Real fetcher uses `get_option_symbol`?
        
        # Let's rely on `fetcher.get_option_symbol` if it supports dynamic expiry?
        # If not, we iterate generic strikes around price.
        
        # ACTUALLY: The user's prompt implies "Get options data... check why we are missing".
        # If the bot is looking for "25DEC" on Dec 26, THAT is the bug.
        # So I should fetch what the BOT would look for, OR what is correct.
        # To backtest properly, I need CORRECT data (Jan Expiry).
        
        # Let's search for "26JAN" first.
        try:
           # Get all instruments for this symbol
           # This is expensive 209 times.
           # Better: Dump all NFO instruments once.
           pass 
        except: pass

    # Re-Dump Instruments to memory for fast lookup
    logging.info("   📥 Downloading full instrument list for filtered lookup...")
    instruments = fetcher.kite.instruments("NFO")
    inst_df = pd.DataFrame(instruments)
    inst_df = inst_df[inst_df['name'].isin(universe)]
    
    # Filter for Expiry (>= Today)
    # Ensure proper datetime comparison
    inst_df['expiry'] = pd.to_datetime(inst_df['expiry'])
    # Convert target date to datetime for comparison
    target_dt = pd.to_datetime(target_date)
    future_opts = inst_df[inst_df['expiry'] >= target_dt]
    if future_opts.empty:
        logging.error("❌ No future options found! Check Expiry.")
    else:
        # Find nearest expiry
        nearest_expiry = future_opts['expiry'].min().date()
        logging.info(f"   📅 Detected Expiry: {nearest_expiry}")
        target_opts = future_opts[future_opts['expiry'].dt.date == nearest_expiry]
        
        # Now for each stock, pick strikes around price
        for symbol in universe:
            sym_spot = full_spot[full_spot['symbol'] == symbol]
            if sym_spot.empty: continue
            
            avg_price = sym_spot['close'].mean()
            
            # Filter options for this symbol
            sym_opts = target_opts[target_opts['name'] == symbol]
            
            # Calculate distance to strike
            sym_opts['dist'] = abs(sym_opts['strike'] - avg_price)
            sym_opts = sym_opts.sort_values('dist')
            
            # Select top 4-6 contracts (ATM, ITM, OTM for CE/PE)
            # Just take top 10 closest strikes to be safe
            focus_tokens = sym_opts.head(10)['instrument_token'].tolist()
            
            for t in focus_tokens:
                try:
                    odf = fetcher.fetch_historical_data(t, from_date, to_date, interval="minute")
                    if not odf.empty:
                        # Extract tradingsymbol from df or map back?
                        # kite raw history doesn't feature tradingsymbol provided by fetcher usually?
                        # Check fetcher implementation. Assuming it returns df.
                        # We need to add cols.
                        row = sym_opts[sym_opts['instrument_token'] == t].iloc[0]
                        odf['tradingsymbol'] = row['tradingsymbol']
                        odf['strike'] = row['strike']
                        odf['type'] = row['instrument_type']
                        odf['symbol'] = symbol
                        opt_dfs.append(odf)
                except: pass
                
    if opt_dfs:
        full_opt = pd.concat(opt_dfs)
        opt_save_path = f"daily_data/{target_date}_options_full.csv"
        full_opt.to_csv(opt_save_path)
        logging.info(f"✅ Saved Option Data: {opt_save_path} ({len(full_opt)} rows)")
    else:
        logging.warning("⚠️ No Option Data Fetched.")

if __name__ == "__main__":
    fetch_data_for_date("2025-12-26")
