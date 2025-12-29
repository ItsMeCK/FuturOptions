
import pandas as pd
import logging
import os
import time
from datetime import datetime
from ai_option_brain.data_loader import ZerodhaDataFetcher
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

def load_initial_token():
    if os.path.exists("zerodha_hot_token.txt"):
        with open("zerodha_hot_token.txt") as f:
            return f.read().strip()
    return os.getenv("ZERODHA_ACCESS_TOKEN")

def simulate_optimized():
    # 1. Load Signals
    try:
        signals_df = pd.read_csv("sim_dec29.csv")
    except:
        print("❌ sim_dec29.csv not found")
        return
        
    signals_df['TimeStr'] = signals_df['Time']
    signals_df.sort_values(by="Time", inplace=True)
    
    # Setup
    token = load_initial_token()
    fetcher = ZerodhaDataFetcher(access_token=token)
    
    unique_symbols = signals_df['Symbol'].unique()
    print(f"🚀 Optimizing: {len(signals_df)} Signals -> {len(unique_symbols)} Unique Stocks")
    
    # 2. Batch Download Stock Data (With Caching)
    stock_data = {}
    CACHE_DIR = "sim_cache"
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    print("📥 Loading Stock Data (Checking Cache)...")
    
    for i, symbol in enumerate(unique_symbols):
        cache_file = f"{CACHE_DIR}/{symbol}_dec29.csv"
        
        # Try Cache First
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    stock_data[symbol] = df
                    # print(f"   ✅ {symbol}: Loaded from Cache")
                    continue
            except Exception as e:
                print(f"   ⚠️ Cache Corrupt {symbol}: {e}")
        
        # If not in cache, Download
        try:
            # Rate Limit Protection
            if i > 0 and i % 3 == 0: 
                time.sleep(1) 
                
            token_id = fetcher.get_instrument_token(symbol)
            if token_id:
                # Fetch last 2 days
                df = fetcher.fetch_latest_data(token_id, days=2, interval="minute")
                
                if not df.empty and 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Save to Cache (Reset index to keep date column in CSV)
                    df.to_csv(cache_file, index=False)
                    
                    # Force Date Index for usage
                    df.set_index('date', inplace=True)
                    
                    # Remove TZ if present
                    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz:
                        df.index = df.index.tz_convert(None) 
                        
                    stock_data[symbol] = df
                    print(f"   ⬇️ {symbol}: Downloaded & Cached")
                else:
                    print(f"   ⚠️ {symbol}: No Data")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
            
    print(f"💾 Data Loaded. Ready for Replay.")
    
    # 3. Simulate Continuous Replay
    # Params
    LEVERAGE = 15.0 # Approx 1% Stock move = 15% Option move (ATM Delta 0.5 * Gamma)
    # Target: 30% Option -> 30/15 = 2.0% Stock Move
    # Stop: -20% Option -> -20/15 = -1.33% Stock Move
    # Trail: 10% Option -> 0.66% Stock Move
    
    TARGET_GAIN = 0.30 
    STOP_LOSS = -0.20
    TRAIL_GAP = 0.10
    
    TARGET_STOCK_GAIN = TARGET_GAIN / LEVERAGE
    STOP_STOCK_LOSS = STOP_LOSS / LEVERAGE
    TRAIL_STOCK_GAP = TRAIL_GAP / LEVERAGE
    
    closed_trades = []
    positions = {} # { "SYMBOL": {entry, stop...} }
    
    # Replay by Signal Time? No, replay per stock sequence
    for symbol in unique_symbols:
        if symbol not in stock_data: continue
        
        df = stock_data[symbol]
        sym_signals = signals_df[signals_df['Symbol'] == symbol]
        
        position = None
        
        # Iterate Signals
        for _, row in sym_signals.iterrows():
            sig_time_str = row['TimeStr']
            # Find Signal Time in DF
            sig_dt = pd.to_datetime(f"2025-12-29 {sig_time_str}")
            
            # 1. Update Existing Position
            if position:
                # Replay Price from Last Update to Now
                last_chk = position['last_check']
                slice_df = df[(df.index > last_chk) & (df.index <= sig_dt)]
                
                for _, candle in slice_df.iterrows():
                    high = candle['high']
                    low = candle['low']
                    entry_p = position['entry_price']
                    
                    # Gain Check
                    curr_gain = (high - entry_p) / entry_p
                    
                    # Activation
                    if not position['trailing']:
                        if curr_gain >= TARGET_STOCK_GAIN:
                            position['trailing'] = True
                            
                    # Update Stop
                    if position['trailing']:
                        # Dynamic Stop = High - Gap
                        dyn_stop_p = high * (1 - TRAIL_STOCK_GAP)
                        if dyn_stop_p > position['stop_price']:
                            position['stop_price'] = dyn_stop_p
                            
                    # Exit Check
                    if low <= position['stop_price']:
                        exit_p = position['stop_price']
                        pnl_stock = (exit_p - entry_p)/entry_p
                        pnl_opt = pnl_stock * LEVERAGE
                        
                        closed_trades.append({
                            "Symbol": symbol,
                            "Outcome": "WIN (Trail)" if position['trailing'] else "LOSS (Stop)",
                            "PnL": pnl_opt * 100,
                            "Entry": position['entry_time'].strftime("%H:%M"),
                            "Exit": candle.name.strftime("%H:%M")
                        })
                        position = None
                        break
                        
                if position:
                    position['last_check'] = sig_dt
                    
            # 2. Enter if Flat
            if position is None:
                # Find Entry Candle
                future = df[df.index >= sig_dt]
                if future.empty:
                     # print(f"   ⚠️ {symbol}: No Future Data after {sig_dt.time()}")
                     continue
                     
                entry_candle = future.iloc[0]
                entry_p = entry_candle['open']
                
                stop_p = entry_p * (1 + STOP_STOCK_LOSS) # Loss is negative
                
                position = {
                    "entry_price": entry_p,
                    "stop_price": stop_p,
                    "entry_time": sig_dt,
                    "last_check": sig_dt,
                    "trailing": False
                }
                # print(f"   🟢 ENTRY: {symbol} at {sig_dt.time()}")
                
        # End of Day Check
        if position:
             closed_trades.append({"Symbol": symbol, "Outcome": "OPEN (EOD)", "PnL": 0, "Entry": "", "Exit": "15:30"})

    # Report
    res_df = pd.DataFrame(closed_trades)
    print("\n--- OPTIMIZED SIMULATION REPORT ---")
    if not res_df.empty:
        # Filter EOD
        finished = res_df[res_df['Outcome'] != "OPEN (EOD)"]
        print(f"Total Completed Trades: {len(finished)}")
        print(f"💰 Avg PnL: {finished['PnL'].mean():.2f}%")
        
        wins = finished[finished['PnL'] > 0]
        losses = finished[finished['PnL'] <= 0]
        
        print(f"✅ Wins: {len(wins)} ({len(wins)/len(finished)*100:.1f}%)")
        print(f"❌ Losses: {len(losses)}")
        print(f"🏆 Best: {finished['PnL'].max():.1f}%")
        
        finished.to_csv("sim_optimized_results.csv", index=False)
        print("Saved results to sim_optimized_results.csv")
    else:
        print("No trades completed.")

if __name__ == "__main__":
    simulate_optimized()
