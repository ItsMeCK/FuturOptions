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
        logging.info(f"📖 Loading Spot Data: {spot_file}")
        self.spot_df = pd.read_csv(spot_file)
        self.spot_df['date'] = pd.to_datetime(self.spot_df['date'])
        
        logging.info(f"📖 Loading Options Data: {options_file}")
        self.opt_df = pd.read_csv(options_file)
        self.opt_df['date'] = pd.to_datetime(self.opt_df['date'])
        
        self.kite = True # Dummy for OptionsBrain
        self.current_time = None
        
        # Build Index for fast lookup
        self.spot_map = {}
        for symbol, group in self.spot_df.groupby('symbol'):
            group = group.sort_values('date').set_index('date')
            self.spot_map[symbol] = group

        self.opt_map = {}
        for symbol, group in self.opt_df.groupby('tradingsymbol'):
            group = group.sort_values('date').set_index('date')
            self.opt_map[symbol] = group

    def set_time(self, time):
        self.current_time = time

    def get_instrument_token(self, symbol, exchange="NSE"):
        # Dummy token, not used for historical lookup here 
        # (LiveBrain calls it, but we bypass it in fetch_latest_data)
        return 12345 

    def get_option_symbol(self, symbol, spot_price, option_type, expiry="25DEC"):
        # Use OptionsBrain logic (Need an instance or static method)
        # Reusing the simple logic from fetch script for consistency
        ob = OptionsBrain(self) 
        ce, pe, strk = ob.construct_option_symbols(symbol, spot_price)
        if option_type == "CE": return ce.replace("NFO:", ""), strk
        return pe.replace("NFO:", ""), strk

    def get_lot_size(self, symbol):
        LOT_MAP = {
            "NIFTY": 50, "BANKNIFTY": 15, "FINNIFTY": 40,
            "RELIANCE": 250, "HDFCBANK": 550, "ICICIBANK": 700, "INFY": 400,
            "SBIN": 1500, "LT": 300, "AXISBANK": 625, "MARUTI": 100,
            "TATASTEEL": 5500, "ADANIENT": 300
        }
        return LOT_MAP.get(symbol, 1)

    def fetch_live_quote(self, symbols):
        # Return data closest to self.current_time (<=)
        quotes = {}
        
        for sym in symbols:
            # Check Spot Map
            if sym in self.spot_map:
                df = self.spot_map[sym]
                try:
                    # AsOf Lookup
                    idx = df.index.get_indexer([self.current_time], method='pad')[0]
                    if idx != -1:
                        row = df.iloc[idx]
                        # Check freshness (within 5 mins)
                        delay = (self.current_time - row.name).total_seconds() / 60
                        if delay < 60: # Allow delay?
                            quotes[sym] = {
                                'last_price': row['close'],
                                'ohlc': {'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']},
                                'oi': 0, # Spot OI not tracked
                                'volume': row['volume']
                            }
                except:
                    pass
            
            # Check Option Map (sym might be option)
            # Remove NFO: prefix if present
            clean_sym = sym.replace("NFO:", "")
            if clean_sym in self.opt_map:
                df = self.opt_map[clean_sym]
                try:
                    idx = df.index.get_indexer([self.current_time], method='pad')[0]
                    if idx != -1:
                        row = df.iloc[idx]
                        quotes[sym] = {
                            'last_price': row['close'] if 'close' in row else 0, # Handling varying columns
                            'oi': row['oi'] if 'oi' in row else 0,
                            'volume': row['volume'] if 'volume' in row else 0
                        }
                except:
                    pass
        
        return quotes

    def fetch_latest_data(self, instrument_token, days=5, interval="minute"):
        # For simulation, we need to return historical data ENDING at current_time
        # Since we only have 'today', we simulate history by returning data from today up to now.
        # In a real multi-day sim, we'd stitch days. 
        # Here, we just return the intraday slice.
        
        # We don't have token->symbol map easily here without passing it.
        # LiveBrain passes token. Problem mapping back to symbol?
        # LiveBrain.scan_market calls: token = get_instr_token(symbol); fetch(token)
        # We can cheat: LiveBrain should pass symbol if possible, or we assume token->symbol mapping is handled or unused.
        # Wait, LiveBrain expects a DataFrame.
        # Let's try to infer symbol or return dummy?
        # Actually, LiveBrain uses this for Technical Indicators.
        # If we can't map token back, we fail.
        # But LiveBrain loops `for symbol in focus_list`.
        # We can MonkeyPatch LiveBrain to call `fetch_latest_data_by_symbol`?
        # Or we map token=hash(symbol).
        pass 
        return pd.DataFrame() # Fallback empty

    # Helper to fix the above:
    # We will Inject a "get_history(symbol)" method into LiveBrain or Mock Fetcher that accepts symbol?
    # LiveBrain calls `fetch_latest_data(token)`.
    # I will modify Mock to accept token as string (Symbol) if possible?
    # LiveBrain: `token = self.fetcher.get_instrument_token(symbol)` -> returns 12345.
    # We need that 12345 to map back to symbol.
    
    def register_symbol(self, symbol, token):
        if not hasattr(self, 'token_map'): self.token_map = {}
        self.token_map[token] = symbol
        
    def fetch_latest_data_mock(self, token, days, interval):
        # Custom method to replace fetch_latest_data
        if not hasattr(self, 'token_map'): return pd.DataFrame()
        symbol = self.token_map.get(token)
        if not symbol or symbol not in self.spot_map: return pd.DataFrame()
        
        df = self.spot_map[symbol]
        # Slice: up to current_time
        mask = df.index <= self.current_time
        sliced = df.loc[mask]
        
        # Return last N days?
        # Simulation usually just looks back.
        return sliced.tail(500) # Last 500 candles ~ 1-2 days

def run_simulation_day(date_str, spot_file, opt_file):
    print(f"\n⚡ Running Simulation for {date_str}...")
    
    mock_fetcher = MockDataFetcher(spot_file, opt_file)
    brain = LiveBrain()
    
    # Inject Mock
    brain.fetcher = mock_fetcher
    brain.options_brain.fetcher = mock_fetcher
    
    # Monkey Patch fetch_latest_data to use our symbol-aware version
    # And register tokens
    def get_token_mock(symbol, exchange=None):
        t = hash(symbol) 
        mock_fetcher.register_symbol(symbol, t)
        return t
        
    brain.fetcher.get_instrument_token = get_token_mock
    brain.fetcher.fetch_latest_data = mock_fetcher.fetch_latest_data_mock
    
    # Mock News Fetcher (Disable DDG calls)
    class MockNewsFetcher:
        def get_news_summary(self, symbol):
            return "Simulation Mode: No News Fetched."
            
    brain.news_fetcher = MockNewsFetcher()
    
    # Create valid focus list for the day
    # Assume Top 10 from spot file
    available_symbols = mock_fetcher.spot_df['symbol'].unique()[:10]
    focus_list_data = {
        "date": date_str,
        "focus_list": [{"symbol": s} for s in available_symbols],
        "reasoning": "Simulation Top 10"
    }
    with open("focus_list.json", "w") as f:
        json.dump(focus_list_data, f)
        f.flush()
        os.fsync(f.fileno())
        
    # Verify Write
    with open("focus_list.json", "r") as f:
        check = json.load(f)
        if check.get('date') != date_str:
            logging.error(f"❌ Focus List Write Failed! Expected {date_str}, Got {check.get('date')}")
            # Retry once?
            with open("focus_list.json", "w") as f2:
                json.dump(focus_list_data, f2)
                f2.flush()
                os.fsync(f2.fileno())
        
    # Time Loop (IST)
    tz = pd.Timestamp(f"{date_str} 09:15:00+05:30").tz
    start_time = pd.Timestamp(f"{date_str} 09:15:00").tz_localize(tz)
    end_time = pd.Timestamp(f"{date_str} 15:30:00").tz_localize(tz)
    
    current = start_time
    delta = timedelta(minutes=1)
    
    while current <= end_time:
        mock_fetcher.set_time(current)
        brain.simulation_time = current.to_pydatetime()
        
        try:
            brain.scan_market()
        except Exception as e:
            logging.error(f"Sim Step Error: {e}")
            
        current += delta

    # End of Day Report
    trades = []
    if os.path.exists("trade_history.csv"):
        try:
            df = pd.read_csv("trade_history.csv")
            # Filter for trades opened on this date
            # Ensure filtering works on string or datetime
            df['EntryTime'] = df['EntryTime'].astype(str)
            day_trades = df[df['EntryTime'].str.startswith(date_str)]
            
            # Convert to list of dicts for logic compatibility
            for _, row in day_trades.iterrows():
                trades.append({
                    'pnl': float(row['PnL']),
                    'status': 'CLOSED'
                })
        except Exception as e:
            logging.error(f"Error reading trade logs: {e}")

    pnl = sum(t.get('pnl', 0) for t in trades)
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    win_rate = (len(win_trades) / len(trades) * 100) if trades else 0.0
    
    print(f"📊 {date_str} Report: {len(trades)} Trades, P&L: {pnl:.2f}, WR: {win_rate:.1f}%")
    
    return {
        "date": date_str,
        "trades": len(trades),
        "pnl": pnl,
        "win_rate": win_rate
    }

def main():
    data_dir = "daily_data"
    files = os.listdir(data_dir)
    
    # Find Spot Files
    spot_files = [f for f in files if "nifty50_intraday.csv" in f]
    spot_files.sort()
    
    results = []
    
    for f in spot_files:
        date_str = f.split("_")[0]
        opt_file = f"{data_dir}/{date_str}_options_intraday.csv"
        
        if os.path.exists(opt_file):
            stats = run_simulation_day(date_str, f"{data_dir}/{f}", opt_file)
            results.append(stats)
        else:
            print(f"⚠️ Missing Option Data for {date_str}. Skipping.")
            
    # Final Report
    if results:
        df = pd.DataFrame(results)
        print("\n================== BACKTEST SUMMARY ==================")
        print(df.to_string(index=False))
        df.to_csv("simulation_report.csv", index=False)
        print(f"💾 Report saved to simulation_report.csv")
    else:
        print("❌ No days simulated.")

if __name__ == "__main__":
    main()
