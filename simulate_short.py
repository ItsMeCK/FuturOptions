
import pandas as pd
import numpy as np
import logging
import os
import time

# Setup
logging.basicConfig(level=logging.INFO)

def simulate_short():
    print("🐻 Starting Short (PE) Strategy Simulation...")
    
    CACHE_DIR = "sim_cache"
    if not os.path.exists(CACHE_DIR):
        print("❌ Cache dir missing")
        return

    closed_trades = []
    
    # Iterate through cached files to find bearish setups
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith("_dec29.csv")]
    
    for filename in files:
        symbol = filename.replace("_dec29.csv", "")
        # Load Data
        df = pd.read_csv(f"{CACHE_DIR}/{filename}")
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
        # Indicators
        df['sma50'] = df['close'].rolling(50).mean()
        df['std'] = df['close'].rolling(20).std()
        df['upper'] = df['close'].rolling(20).mean() + (2 * df['std'])
        df['lower'] = df['close'].rolling(20).mean() - (2 * df['std'])
        df['bandwidth'] = (df['upper'] - df['lower']) / df['close'].rolling(20).mean()
        
        # VWAP approximation (Cumsum)
        df['vwap'] = (df['volume'] * (df['high']+df['low']+df['close'])/3).cumsum() / df['volume'].cumsum()

        # ATR
        df['tr'] = abs(df['high'] - df['low']) # Simplified TR
        df['atr'] = df['tr'].rolling(14).mean()

        # RVOL (20 period)
        df['vol_ma'] = df['volume'].rolling(20).mean()
        df['rvol'] = df['volume'] / df['vol_ma']
        
        position = None
        
        # Start at 09:30
        sim_df = df[df.index.time >= pd.to_datetime("09:30").time()]
        
        for i, candle in sim_df.iterrows():
            # 1. Manage Active Short
            if position:
                # Check Profit (Covering lower)
                pct_gain = (position['entry'] - candle['low']) / position['entry'] # Short PnL logic
                
                # Exit Logic (Mirrored)
                # Activation 30% Option ~ 2% Stock? Let's use Stock logic for proxy
                # Target: Entry - 3 ATR
                
                if candle['low'] <= position['target']:
                     closed_trades.append({
                         "Symbol": symbol, "Type": "PE", "Outcome": "WIN", 
                         "Entry": position['entry'], "Exit": position['target'], 
                         "Time": i.time()
                     })
                     position = None
                     continue
                     
                # Stop Loss (Price goes UP)
                if candle['high'] >= position['stop']:
                     closed_trades.append({
                         "Symbol": symbol, "Type": "PE", "Outcome": "LOSS", 
                         "Entry": position['entry'], "Exit": position['stop'], 
                         "Time": i.time()
                     })
                     position = None
                     continue
            
            # 2. Enter Short (Institutional Sniper PE)
            if position is None:
                # FILTERS (Safety)
                if candle['bandwidth'] < 0.03: continue # Dead Zone
                # if candle['rvol'] < 1.5: continue # User didn't specify RVOL for this specific test, but Sniper implies it. 
                # Let's try WITHOUT RVOL first to see if we find candidates, then filter.
                
                # Logic: Price < SMA 50 AND Bandwidth < 0.15
                if (candle['close'] < candle['sma50'] and 
                    candle['bandwidth'] < 0.15):
                    
                    # Entry
                    entry_p = candle['close']
                    atr = candle['atr'] if not pd.isna(candle['atr']) else entry_p*0.01
                    
                    position = {
                        "entry": entry_p,
                        "target": entry_p - (3*atr),
                        "stop": entry_p + (2*atr)
                    }
                    # print(f"🔴 SHORT {symbol} at {entry_p}")

    # Report
    res_df = pd.DataFrame(closed_trades)
    print("\n--- SHORT SIMULATION REPORT ---")
    if not res_df.empty:
        print(f"Total Short Trades: {len(res_df)}")
        wins = res_df[res_df['Outcome'] == "WIN"]
        print(f"✅ Wins: {len(wins)} ({len(wins)/len(res_df)*100:.1f}%)")
    else:
        print("No Short Trades triggered with strict logic.")

if __name__ == "__main__":
    simulate_short()
