
import pandas as pd
import logging
import os
from datetime import datetime, timedelta
from ai_option_brain.data_loader import ZerodhaDataFetcher
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

def load_initial_token():
    if os.path.exists("zerodha_hot_token.txt"):
        with open("zerodha_hot_token.txt") as f:
            return f.read().strip()
    return os.getenv("ZERODHA_ACCESS_TOKEN")

def simulate_continuous():
    try:
        signals_df = pd.read_csv("sim_dec29.csv")
    except:
        print("❌ sim_dec29.csv not found")
        return
        
    # Sort by Time
    signals_df.sort_values(by="Time", inplace=True)
    
    # Setup Fetcher
    token = load_initial_token()
    fetcher = ZerodhaDataFetcher(access_token=token)
    
    option_cache = {}
    
    # Portfolio State
    # { "TATASTEEL": { "status": "OPEN", "entry_price": 50, "hwm": 0.0, ... } }
    positions = {} 
    closed_trades = []
    
    print(f"🚀 Simulating CONTINUOUS Replay with {len(signals_df)} Signals...")
    
    # We iterate signal by signal. But wait, we need to advance time minute by minute?
    # No, signals drive the entries. But exits happen in between signals?
    
    # Better approach: For each symbol, process its signals sequentially.
    
    symbols = signals_df['Symbol'].unique()
    
    for symbol in symbols:
        sym_signals = signals_df[signals_df['Symbol'] == symbol].copy()
        
        # Get Option Data for Symbol (Only fetch once)
        # Assuming LONG CE for simulation
        # Need to know WHICH option?
        # Let's take the first signal to define the option for the day, or re-fetch per signal?
        
        # Fetching proper option symbols per signal
        
        position = None # Current active position for this symbol
        
        for idx, row in sym_signals.iterrows():
            signal_time_str = row['Time']
            run_date = "2025-12-29"
            signal_dt = pd.to_datetime(f"{run_date} {signal_time_str}")
            
            # 1. Update Existing Position first (Did it close before this new signal?)
            if position:
                # Check if position closed between its entry and this new signal time
                # Replay market data from PosEntry to SignalTime
                
                # Fetch Option Data if not loaded
                opt_sym = position['option_symbol']
                if opt_sym not in option_cache:
                    # Fetch
                    opt_token = fetcher.get_instrument_token(opt_sym, exchange="NFO")
                    if opt_token:
                        df = fetcher.fetch_latest_data(opt_token, days=1, interval="minute")
                        if not df.empty and 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            if df.index.tz:
                                df.index = df.index.tz_convert(None) # Make naive for easy compare
                            df.set_index('date', inplace=True)
                            option_cache[opt_sym] = df
                        else:
                             option_cache[opt_sym] = None
                
                opt_df = option_cache.get(opt_sym)
                
                if opt_df is not None:
                     # Replay from Last Update to NOW
                     last_chk = position['last_check']
                     # Ensure naive
                     last_chk = last_chk.replace(tzinfo=None)
                     curr_chk = signal_dt.replace(tzinfo=None)
                     
                     slice_df = opt_df[(opt_df.index > last_chk) & (opt_df.index <= curr_chk)]
                     
                     # Process Exit Logic on Slice
                     for _, candle in slice_df.iterrows():
                         high = candle['high']
                         low = candle['low']
                         close = candle['close']
                         
                         entry_p = position['entry_price']
                         
                         # Check Activation
                         curr_gain = (high - entry_p)/entry_p
                         if not position['trailing_active'] and curr_gain >= 0.30:
                             position['trailing_active'] = True
                             
                         # Update Stop
                         if position['trailing_active']:
                             # Dynamic Stop: High * 0.90
                             dyn_stop = high * 0.90
                             if dyn_stop > position['stop_price']:
                                 position['stop_price'] = dyn_stop
                                 
                         # Check Hit
                         if low <= position['stop_price']:
                             # EXIT
                             exit_p = position['stop_price']
                             closed_trades.append({
                                 "Symbol": symbol,
                                 "Entry": position['entry_time'].strftime("%H:%M"),
                                 "Exit": candle.name.strftime("%H:%M"),
                                 "PnL": (exit_p - entry_p)/entry_p * 100,
                                 "Reason": "Trail" if position['trailing_active'] else "Stop"
                             })
                             position = None
                             break
                             
                     if position:
                         position['last_check'] = signal_dt
                         
            # 2. Check for Entry (if no position)
            if position is None:
                # ENTRY SIGNAL
                strategy = row['Strategy']
                price = row['Price']
                
                # Fetch Option
                opt_sym, _ = fetcher.get_option_symbol(symbol, price, "CE", strategy)
                if not opt_sym: continue
                
                # Get Quote at this time
                if opt_sym not in option_cache:
                    # Fetch ... (Duplicate logic, wrap in function ideally but inline ok for script)
                    opt_token = fetcher.get_instrument_token(opt_sym, exchange="NFO")
                    if opt_token:
                        df = fetcher.fetch_latest_data(opt_token, days=1, interval="minute")
                        if not df.empty and 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df.set_index('date', inplace=True)
                            
                            if isinstance(df.index, pd.DatetimeIndex) and df.index.tz:
                                 df.index = df.index.tz_convert(None) # Remove tz
                            
                            option_cache[opt_sym] = df
                        else:
                            option_cache[opt_sym] = None
                
                opt_df = option_cache.get(opt_sym)
                if opt_df is None: continue
                
                # Get Entry Candle
                naive_dt = signal_dt.replace(tzinfo=None)
                try:
                    entry_candle = opt_df.loc[naive_dt] # Exact match?
                except:
                    # Find nearest after
                    future = opt_df[opt_df.index >= naive_dt]
                    if future.empty: continue
                    entry_candle = future.iloc[0]
                    
                entry_price = entry_candle['open'] # or close
                stop_price = entry_price * 0.80 # -20%
                
                position = {
                    "symbol": symbol,
                    "option_symbol": opt_sym,
                    "entry_price": entry_price,
                    "entry_time": naive_dt,
                    "stop_price": stop_price,
                    "trailing_active": False,
                    "last_check": naive_dt
                }
                # print(f"🟢 OPEN: {symbol} at {naive_dt.time()} @ {entry_price}")

        # End of Day Check (Close remaining positions)
        if position:
             closed_trades.append({
                 "Symbol": symbol,
                 "Entry": position['entry_time'].strftime("%H:%M"),
                 "Exit": "15:30",
                 "PnL": 0.0, # Approximate, assumed flat or take last close
                 "Reason": "EOD"
             })
             
    # Report
    print("\n--- CONTINUOUS SIMULATION REPORT ---")
    res_df = pd.DataFrame(closed_trades)
    print(res_df)
    
    if not res_df.empty:
        print(f"\nTotal Real Trades: {len(res_df)} (vs {len(signals_df)} Signals)")
        print(f"💰 Avg PnL: {res_df['PnL'].mean():.2f}%")
        print(f"✅ Wins: {len(res_df[res_df['PnL']>0])}")
        print(f"❌ Losses: {len(res_df[res_df['PnL']<=0])}")
        res_df.to_csv("sim_continuous.csv", index=False)

if __name__ == "__main__":
    simulate_continuous()
