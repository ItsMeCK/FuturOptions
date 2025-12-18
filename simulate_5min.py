import sys
import os
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from live_brain import LiveBrain
from ai_option_brain.options_brain import OptionsBrain

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockDataFetcher:
    def __init__(self, spot_file, options_file):
        self.spot_df = pd.read_csv(spot_file)
        self.spot_df['date'] = pd.to_datetime(self.spot_df['date'])
        self.spot_df.set_index('date', inplace=True)
        
        self.opt_df = pd.read_csv(options_file)
        self.opt_df['date'] = pd.to_datetime(self.opt_df['date'])
        self.opt_df.set_index('date', inplace=True) # Index crucial for fast resampling
        
        self.kite = True 
        self.current_time = None
        
        # Spot Map (Resampled Cache could go here, but doing on fly is safer for "latest")
        self.spot_map = {}
        for symbol, group in self.spot_df.groupby('symbol'):
            self.spot_map[symbol] = group

        self.opt_map = {}
        for symbol, group in self.opt_df.groupby('tradingsymbol'):
            self.opt_map[symbol] = group

    def set_time(self, time):
        self.current_time = time

    def get_instrument_token(self, symbol, exchange="NSE"):
        return hash(symbol) 

    def get_option_symbol(self, symbol, spot_price, option_type, expiry="25DEC"):
        ob = OptionsBrain(self) 
        ce, pe, strk = ob.construct_option_symbols(symbol, spot_price)
        if option_type == "CE": return ce.replace("NFO:", ""), strk
        return pe.replace("NFO:", ""), strk

    def get_lot_size(self, symbol):
        LOT_MAP = {
            "NIFTY": 50, "BANKNIFTY": 15, "FINNIFTY": 40,
            "RELIANCE": 250, "HDFCBANK": 550, "ICICIBANK": 700, "INFY": 400,
            "SBIN": 1500, "LT": 300, "AXISBANK": 625, "MARUTI": 100,
            "TATASTEEL": 5500, "ADANIENT": 300, "BEL": 1
        }
        return LOT_MAP.get(symbol, 1)

    def fetch_live_quote(self, symbols):
        # Return data closest to self.current_time
        # For Quote, we should probably still return the *Real Time* price (Minute level)
        # Even if Brain runs on 5-min candles, execution is at current market price.
        quotes = {}
        for sym in symbols:
            # Check Spot Map
            if sym in self.spot_map:
                df = self.spot_map[sym]
                try:
                    # AsOf Lookup on Minute Data
                    idx = df.index.get_indexer([self.current_time], method='pad')[0]
                    if idx != -1:
                        row = df.iloc[idx]
                        if (self.current_time - row.name).total_seconds() / 60 < 60:
                            quotes[sym] = {
                                'last_price': row['close'],
                                'ohlc': {'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']},
                                'oi': 0, 'volume': row['volume']
                            }
                except: pass
            
            clean_sym = sym.replace("NFO:", "")
            if clean_sym in self.opt_map:
                df = self.opt_map[clean_sym]
                try:
                    idx = df.index.get_indexer([self.current_time], method='pad')[0]
                    if idx != -1:
                        row = df.iloc[idx]
                        quotes[sym] = {
                            'last_price': row['close'],
                            'oi': row['oi'],
                            'volume': row['volume']
                        }
                except: pass
        return quotes

    def register_symbol(self, symbol, token):
        if not hasattr(self, 'token_map'): self.token_map = {}
        self.token_map[token] = symbol
        
    def fetch_latest_data_mock(self, token, days, interval):
        # KEY CHANGE: RESAMPLE TO 5 MIN
        if not hasattr(self, 'token_map'): return pd.DataFrame()
        symbol = self.token_map.get(token)
        if not symbol or symbol not in self.spot_map: return pd.DataFrame()
        
        df = self.spot_map[symbol]
        # Slice up to current time
        mask = df.index <= self.current_time
        history = df.loc[mask]
        
        if history.empty: return pd.DataFrame()
        
        # Resample to 5 Min
        # Rules: Close=Last, Open=First, High=Max, Low=Min, Volume=Sum
        resampled = history.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Return last 100 candles (500 mins) to ensure indicators have enough data
        return resampled.tail(100)

def run_simulation_day(date_str, spot_file, opt_file):
    print(f"\n⚡ Running 5-MIN Simulation for {date_str}...")
    
    # Clean Output Files for this run
    hist_file = f"sim_5min_history_{date_str}.csv"
    active_file = f"sim_5min_active_{date_str}.json"
    if os.path.exists(hist_file): os.remove(hist_file)
    if os.path.exists(active_file): os.remove(active_file)

    mock_fetcher = MockDataFetcher(spot_file, opt_file)
    brain = LiveBrain()
    brain.fetcher = mock_fetcher
    brain.options_brain.fetcher = mock_fetcher
    
    # Redirect Output
    brain.tm.history_file = hist_file
    brain.tm.state_file = active_file
    brain.tm.active_trades = {} 

    def get_token_mock(symbol, exchange=None):
        t = hash(symbol) 
        mock_fetcher.register_symbol(symbol, t)
        return t
        
    brain.fetcher.get_instrument_token = get_token_mock
    brain.fetcher.fetch_latest_data = mock_fetcher.fetch_latest_data_mock
    
    class MockNewsFetcher:
        def get_news_summary(self, symbol):
            return "Sim Mode"
    brain.news_fetcher = MockNewsFetcher()
    
    # Create valid focus list
    available_symbols = mock_fetcher.spot_df['symbol'].unique()
    focus_list_data = {
        "date": date_str,
        "focus_list": [{"symbol": s} for s in available_symbols if s not in ["NIFTY 50", "NIFTY BANK"]],
        "reasoning": "Simulation 5-Min"
    }
    with open("focus_list.json", "w") as f:
        json.dump(focus_list_data, f)
        
    # Time Loop - Step by 1 minute, but Brain sees 5-min candles
    # This simulates "checking every minute" but "decision based on 5-min structure"
    # Actually, Brain calculates on latest data. If we resample up to HH:MM:SS, 
    # the last candle might be incomplete (forming).
    # LiveBrain typically uses `iloc[:-1]` (Completed Candles) for stability.
    # If we feed it resampled data, it will strip the last one.
    # This means it trades based on the LAST COMPLETED 5-MIN CANDLE.
    # This effectively adds a delay but ensures stability.
    
    tz = pd.Timestamp(f"{date_str} 09:15:00+05:30").tz
    start_time = pd.Timestamp(f"{date_str} 09:15:00").tz_localize(tz)
    end_time = pd.Timestamp(f"{date_str} 15:30:00").tz_localize(tz)
    
    current = start_time
    delta = timedelta(minutes=1) # We still scan every minute!
    
    while current <= end_time:
        mock_fetcher.set_time(current)
        brain.simulation_time = current.to_pydatetime()
        try:
            brain.scan_market()
        except Exception as e:
            logging.error(f"Sim Step Error: {e}")
        current += delta

    print(f"✅ Simulation {date_str} Done.")
    return hist_file

def main():
    days = ["2025-12-17", "2025-12-18"]
    for date_str in days:
        spot_file = f"daily_data/{date_str}_nifty50_intraday.csv"
        opt_file = f"daily_data/{date_str}_options_intraday.csv"
        
        if os.path.exists(spot_file) and os.path.exists(opt_file):
            run_simulation_day(date_str, spot_file, opt_file)
        else:
            print(f"⚠️ Missing data for {date_str}")

if __name__ == "__main__":
    main()
