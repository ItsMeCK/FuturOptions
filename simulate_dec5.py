import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os

# Import LiveBrain
# Assumes we are in the root directory
sys.path.append(os.getcwd())
from live_brain import LiveBrain

# Mock Fetcher
class MockDataFetcher:
    def __init__(self, spot_file, options_file):
        print(f"📖 Loading Spot Data: {spot_file}")
        self.spot_df = pd.read_csv(spot_file)
        self.spot_df['date'] = pd.to_datetime(self.spot_df['date'])
        
        print(f"📖 Loading Options Data: {options_file}")
        self.opt_df = pd.read_csv(options_file)
        self.opt_df['date'] = pd.to_datetime(self.opt_df['date'])
        
        self.data_index = {} # (symbol, timestamp) -> row index
        # self._build_index() # This method is not defined in the provided code, so commenting it out to avoid error.
        self.kite = True # Dummy for OptionsBrain check
        
        # Build Index for fast lookup
        # Map: Symbol -> DataFrame (Sorted by Date)
        self.spot_map = {}
        for sym, group in self.spot_df.groupby('symbol'):
            self.spot_map[sym] = group.sort_values('date').set_index('date')
            
        self.opt_map = {}
        for sym, group in self.opt_df.groupby('tradingsymbol'):
            self.opt_map[sym] = group.sort_values('date').set_index('date')
            
        self.current_time = None
        
        # Instrument Token Map (Mock)
        self.token_map = {sym: i for i, sym in enumerate(self.spot_map.keys(), 1000)}

    def set_time(self, time):
        self.current_time = time

    def get_instrument_token(self, symbol, exchange="NSE"):
        return self.token_map.get(symbol, 0)
        
    def get_lot_size(self, symbol):
        # Lot Sizes (Dec 2025 Standards - Approximate)
        LOT_MAP = {
            "NIFTY": 50, "BANKNIFTY": 15, "FINNIFTY": 40,
            "RELIANCE": 250, "HDFCBANK": 550, "ICICIBANK": 700, "INFY": 400,
            "ITC": 1600, "TCS": 175, "LT": 300, "AXISBANK": 625, "KOTAKBANK": 400,
            "SBIN": 1500, "BHARTIARTL": 950, "BAJFINANCE": 125, "ASIANPAINT": 200,
            "MARUTI": 100, "TITAN": 175, "HCLTECH": 700, "SUNPHARMA": 700,
            "TATASTEEL": 5500, "ADANIENT": 300, "HINDUNILVR": 300, "TATAMOTORS": 1425,
            "NTPC": 3000, "POWERGRID": 3600, "ULTRACEMCO": 100, "ONGC": 3850,
            "M&M": 350, "WIPRO": 1500, "COALINDIA": 4200, "JSWSTEEL": 675,
            "ADANIPORTS": 400, "GRASIM": 475, "CIPLA": 650, "TECHM": 600,
            "HINDALCO": 1400, "DRREDDY": 125, "EICHERMOT": 175, "INDUSINDBK": 500,
            "DIVISLAB": 200, "BPCL": 1800, "APOLLOHOSP": 125, "BAJAJFINSV": 500
        }
        return LOT_MAP.get(symbol, 1) # Default 1 if unknown, but cover major stocks
        
    def get_option_symbol(self, symbol, spot_price, option_type="CE"):
        # We need to replicate logic or use OptionsBrain logic.
        # Ideally, we call OptionsBrain logic, but here we mock the result 
        # if we can't easily import OptionsBrain's internal logic cleanly.
        # But LiveBrain uses its OWN fetcher for this usually? 
        # No, LiveBrain uses self.fetcher.get_option_symbol. 
        # Wait, LiveBrain calls self.fetcher.get_option_symbol lines 538.
        # So we must implement it.
        
        # Simplified logic for simulation (matches fetch_script)
        # Assuming OptionsBrain internal logic is consistent.
        
        # Step Map
        STEP_MAP = {
            "NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50,
            "RELIANCE": 20, "INFY": 20, "TCS": 50, "SBIN": 10,
            "HDFCBANK": 10, "ICICIBANK": 10, "LT": 50, "AXISBANK": 10,
            "HINDUNILVR": 20, "MARUTI": 100, "ADANIENT": 50, "KOTAKBANK": 20,
            "BHARTIARTL": 10, "BAJFINANCE": 50, "TITAN": 20, "TATASTEEL": 2.5,
            "HINDALCO": 10, "BEL": 5, "ASIANPAINT": 20, "ULTRACEMCO": 100
        }
        step = STEP_MAP.get(symbol, 10)
        if symbol == "NIFTY": step = 50
        
        strike = round(spot_price / step) * step
        
        # Format
        if strike % 1 == 0:
            str_strike = str(int(strike))
        else:
            str_strike = str(strike)
            
        base = f"{symbol}25DEC" # Hardcoded expiry for this dataset
        return f"{base}{str_strike}{option_type}", strike

    def fetch_live_quote(self, symbols):
        quotes = {}
        if not self.current_time:
            return {}
            
        for sym in symbols:
            # Handle NFO prefix
            search_sym = sym.replace("NFO:", "").replace("NSE:", "")
            
            # Check Spot or Opt
            df = None
            if search_sym in self.spot_map:
                df = self.spot_map[search_sym]
            elif search_sym in self.opt_map:
                df = self.opt_map[search_sym]
            
            if df is not None:
                # Find data at or just before current_time
                # using asof to get nearest past value
                try:
                    idx = df.index.get_indexer([self.current_time], method='pad')[0]
                    if idx == -1: continue # No data yet
                    
                    row = df.iloc[idx]
                    # Ensure validity (e.g. not from yesterday)
                    if row.name.date() != self.current_time.date():
                        continue
                        
                    quotes[sym] = {
                        'last_price': row['close'],
                        'volume': row['volume'],
                        'oi': row.get('oi', 0), # OI might be 0 for spot
                        'ohlc': {
                            'open': row['open'],
                            'high': row['high'],
                            'low': row['low'],
                            'close': row['close']
                        }
                    }
                except Exception:
                    pass
                    
        return quotes

    def fetch_latest_data(self, instrument_token, days=5, interval="minute"):
        # Reverse lookup token -> symbol
        found_sym = None
        for s, t in self.token_map.items():
            if t == instrument_token:
                found_sym = s
                break
        
        if not found_sym: return pd.DataFrame()
        
        if found_sym in self.spot_map:
            df = self.spot_map[found_sym]
            # Filter up to current_time (inclusive)
            # Limit to last N days? For sim, we usually just need "recent" history for indicators.
            # But the simulation is only 1 day. 
            # So we might need to rely on the fact that the CSV likely starts from 9:15.
            # Indicators need history. 
            # If our CSV is ONLY today, indicators will start from 0 at 9:15.
            # This is a limitation unless we downloaded previous days.
            # Assuming we accept this warmup period.
            
            mask = df.index <= self.current_time
            hist = df.loc[mask].tail(375) # Last 375 candles (1 day approx)
            
            # Zerodha format expected: date in index? No, date column usually.
            # Reformat to match Expected format for TechnicalIndicators
            # Expected cols: date (or index), open, high, low, close, volume
            
            res = hist.reset_index()
            # Standardize names
            res = res.rename(columns={'index': 'date'}) # if index was named
            return res
            
        return pd.DataFrame()

def run_simulation():
    print("🎬 Initializing Simulation Environment...")
    
    # 1. Initialize Mock Fetcher
    mock_fetcher = MockDataFetcher(
        "daily_data/2025-12-05_nifty50_intraday.csv",
        "daily_data/2025-12-05_options_intraday.csv"
    )
    
    # 2. Initialize Brain
    brain = LiveBrain()
    
    # 3. Inject Mock Components
    brain.fetcher = mock_fetcher
    brain.options_brain.fetcher = mock_fetcher # Critical: OptBrain uses its own reference
    
    # Disable LLM for Speed/Cost (Optional: Mock it to always approve)
    # brain.llm_judge = MockLLM() 
    
    # 4. Create Focus List for Sim
    sim_focus = {
        "date": "2025-12-05", 
        "focus_list": [
            {"symbol": "ADANIENT", "reason": "Sim"},
            {"symbol": "TATASTEEL", "reason": "Sim"},
            {"symbol": "HDFCBANK", "reason": "Sim"},
            {"symbol": "SBIN", "reason": "Sim"},
            {"symbol": "INFY", "reason": "Sim"},
            {"symbol": "RELIANCE", "reason": "Sim"},
            {"symbol": "ICICIBANK", "reason": "Sim"},
            {"symbol": "AXISBANK", "reason": "Sim"},
            {"symbol": "LT", "reason": "Sim"},
            {"symbol": "MARUTI", "reason": "Sim"}
        ],
        "reasoning": "Simulation Run"
    }
    import json
    with open("focus_list.json", "w") as f:
        json.dump(sim_focus, f)
        
    # 5. Time Loop
    print("⏳ Starting Time Loop (2025-12-05 09:15 -> 15:30 +05:30)")
    
    # Use timezone aware datetime to match CSV
    # Method 1: Use pd.Timestamp with timezone
    tz =  pd.Timestamp("2025-12-05 09:15:00+05:30").tz
    
    start_time = pd.Timestamp("2025-12-05 09:15:00").tz_localize(tz)
    end_time = pd.Timestamp("2025-12-05 15:30:00").tz_localize(tz)
    delta = timedelta(minutes=1)
    
    current = start_time
    
    while current <= end_time:
        # Update Mock Time
        mock_fetcher.set_time(current)
        brain.simulation_time = current.to_pydatetime() # Convert back to python datetime for compatibility logic if needed
        
        # Run Scan
        brain.scan_market()
        
        # Step
        current += delta
        
        # Determine speed (e.g. process 1 day in 1 min?)
        # No sleep needed for pure calc simulation
        
    print("🏁 Simulation Complete.")
    
    # Extract Results
    # brain.tm.active_trades ... save to report

if __name__ == "__main__":
    run_simulation()
