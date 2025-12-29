
import pandas as pd
import numpy as np
import logging
import os
import time
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

# Setup
logging.basicConfig(level=logging.INFO)

def simulate_filters_atr():
    print("🚀 Starting Filtered ATR Simulation...")
    
    # 1. Load Signals (Raw)
    try:
        signals_df = pd.read_csv("sim_dec29.csv")
    except:
        print("❌ sim_dec29.csv not found")
        return
        
    signals_df['TimeStr'] = signals_df['Time']
    signals_df.sort_values(by="Time", inplace=True)
    
    # 2. Apply Signal Filters (Reduce Noise)
    # Filter 1: Time (Exit Morning Chop)
    # Ignore signals before 09:30:00
    signals_df = signals_df[signals_df['Time'] >= "09:30:00"]
    
    # Filter 2: Bandwidth Floor (Avoid Dead Stocks)
    # Keep BW > 0.03
    signals_df = signals_df[signals_df['BW'] >= 0.03]
    
    # Filter 3: RVOL Floor (Avoid Weak Vol)
    # Keep RVOL > 2.0
    signals_df = signals_df[signals_df['RVOL'] >= 2.0]
    
    print(f"📉 Signal Reduction: 176 -> {len(signals_df)} Signals (ATR + Time Filters)")
    
    # 3. Simulate Trades with ATR Logic
    CACHE_DIR = "sim_cache"
    unique_symbols = signals_df['Symbol'].unique()
    
    # ATR Params
    # Target = Entry + (3 * ATR)
    # Stop = Entry - (2 * ATR)
    # Trailing? Let's stick to pure ATR Target for profit booking as requested.
    
    closed_trades = []
    
    for symbol in unique_symbols:
        cache_file = f"{CACHE_DIR}/{symbol}_dec29.csv"
        if not os.path.exists(cache_file):
            print(f"⚠️ Cache missing for {symbol}")
            continue
            
        try:
            df = pd.read_csv(cache_file)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
        except:
            continue
            
        # Calculate ATR on 1-min data? Or use fixed ATR from signal time?
        # Ideally calculate ATR(14) on 1-min data.
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift())
        df['tr2'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        sym_signals = signals_df[signals_df['Symbol'] == symbol]
        position = None
        
        for _, row in sym_signals.iterrows():
            sig_time_str = row['TimeStr']
            sig_dt = pd.to_datetime(f"2025-12-29 {sig_time_str}")
            
            # 1. Manage Active Position
            if position:
                # Replay
                last_chk = position['last_check']
                
                # TZ Fix
                if df.index.tz:
                     last_chk_aware = last_chk.tz_localize(df.index.tz)
                     sig_dt_aware = sig_dt.tz_localize(df.index.tz)
                else:
                     last_chk_aware = last_chk
                     sig_dt_aware = sig_dt
                     
                slice_df = df[(df.index > last_chk_aware) & (df.index <= sig_dt_aware)]
                
                for _, candle in slice_df.iterrows():
                    high = candle['high']
                    low = candle['low']
                    
                    # Check Target (ATR Profit Booking)
                    if high >= position['target']:
                        exit_p = position['target']
                        closed_trades.append({
                            "Symbol": symbol,
                            "Outcome": "WIN (ATR Target)",
                            "PnL": (exit_p - position['entry'])/position['entry']*100,
                            "Entry": position['entry_time'].strftime("%H:%M"),
                            "Exit": candle.name.strftime("%H:%M")
                        })
                        position = None
                        break
                        
                    # Check Stop
                    if low <= position['stop']:
                        exit_p = position['stop']
                        closed_trades.append({
                            "Symbol": symbol,
                            "Outcome": "LOSS (Stop)",
                            "PnL": (exit_p - position['entry'])/position['entry']*100,
                            "Entry": position['entry_time'].strftime("%H:%M"),
                            "Exit": candle.name.strftime("%H:%M")
                        })
                        position = None
                        break
                
                if position:
                    position['last_check'] = sig_dt
                    
            # 2. Enter if Flat
            if position is None:
                # Look for candle
                # TZ Fix
                if df.index.tz:
                     sig_dt_aware = sig_dt.tz_localize(df.index.tz)
                else:
                     sig_dt_aware = sig_dt
                     
                future = df[df.index >= sig_dt_aware]
                if future.empty: continue
                entry_candle = future.iloc[0]
                entry_p = entry_candle['open']
                
                # Get ATR
                # If ATR is nan (start of data), use % fallback
                curr_atr = df.loc[entry_candle.name]['atr']
                if pd.isna(curr_atr) or curr_atr == 0:
                    curr_atr = entry_p * 0.01 # 1% Fallback
                    
                target_p = entry_p + (3.0 * curr_atr)
                stop_p = entry_p - (2.0 * curr_atr)
                
                position = {
                    "symbol": symbol,
                    "entry": entry_p,
                    "target": target_p,
                    "stop": stop_p,
                    "entry_time": sig_dt,
                    "last_check": sig_dt
                }
                
                # Calculate Potential R:R
                # print(f"🟢 {symbol} Entry {entry_p} | Tgt {target_p} (+{(target_p-entry_p)/entry_p*100:.1f}%)")

        # EOD
        if position:
             closed_trades.append({
                 "Symbol": symbol, "Outcome": "OPEN (EOD)", "PnL": 0, "Entry": position['entry_time'].strftime("%H:%M"), "Exit": "15:30"
             })
             
    # Report
    res_df = pd.DataFrame(closed_trades)
    print("\n--- FILTERED ATR SIMULATION REPORT ---")
    print(res_df)
    
    if not res_df.empty:
        finished = res_df[res_df['Outcome'] != "OPEN (EOD)"]
        print(f"\nFinal Trade Count: {len(finished)}")
        wins = finished[finished['PnL'] > 0]
        print(f"✅ Wins: {len(wins)} ({len(wins)/len(finished)*100:.1f}%)")
        print(f"💰 Avg PnL (Stock): {finished['PnL'].mean():.2f}%")
        print(f"   (Approx Option PnL ~15x: {finished['PnL'].mean()*15:.1f}%)")
        finished.to_csv("sim_atr_results.csv", index=False)

if __name__ == "__main__":
    simulate_filters_atr()
