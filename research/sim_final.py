
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def run_final_sim():
    print("🧪 FINAL SIMULATION: Standard (1.5x) vs Ignition (3.0x) on Focus List...")
    
    # Focus List (High Octane Names)
    FOCUS_LIST = [
        'RVNL', 'ADANIENT', 'ADANIPORTS', 'BEL', 'HAL', 
        'TATASTEEL', 'VEDL', 'DLF', 'TRENT', 'ZOMATO',
        'BHEL', 'RECLTD', 'PFC', 'CANBK', 'SBIN'
    ]
    
    days = ['2025-12-24', '2025-12-26']
    
    # Results containers
    r15 = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0}
    r30 = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0}
    
    for date_str in days:
        try:
            df = pd.read_csv(f"daily_data/{date_str}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
        except: continue
        
        for sym in FOCUS_LIST:
            s_df = df[df['symbol'] == sym].set_index('date').sort_index()
            if len(s_df) < 50: continue
            
            # Resample 5m
            s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
            # Indicators
            u, l = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            m = s_5m['close'].rolling(20).mean()
            bw = (u - l) / m
            sma50 = s_5m['close'].rolling(50).mean()
            ema9 = TechnicalIndicators.calculate_ema(s_5m['close'], 9)
            vol_sma = s_5m['volume'].rolling(20).mean()
            
            # VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_df = s_5m[s_5m.index >= day_start].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0, index=s_5m.index)
            vwap_series.update(day_df['vwap'])
            
            # Loop
            # Track Two Strategies Concurrently
            in_15 = False; entry_15 = 0; sl_15 = 0; be_15 = False
            in_30 = False; entry_30 = 0; sl_30 = 0; be_30 = False
            
            idx_list = [i for i, t in enumerate(s_5m.index) if t >= day_start]
            
            for i in idx_list:
                if i < 20: continue
                curr = s_5m.iloc[i]
                
                # --- STRATEGY 1: RVOL > 1.5 ---
                if in_15:
                    # Exit Logic (Breathing Room)
                    if curr['low'] <= sl_15: # Stop
                        pnl = (sl_15 - entry_15)/entry_15 * 100
                        r15['trades'] += 1; r15['pnl'] += pnl
                        if pnl > 0: r15['wins'] += 1
                        else: r15['losses'] += 1
                        in_15 = False
                    elif curr['close'] < ema9.iloc[i]: # Trail
                        pnl = (curr['close'] - entry_15)/entry_15 * 100
                        r15['trades'] += 1; r15['pnl'] += pnl
                        if pnl > 0: r15['wins'] += 1
                        else: r15['losses'] += 1
                        in_15 = False
                    else:
                        # BE Trail
                        if not be_15 and (curr['close'] - entry_15)/entry_15 > 0.01:
                            sl_15 = entry_15 * 1.001
                            be_15 = True
                else:
                    # Entry
                    valid_squeeze = bw.iloc[i] < 0.15
                    valid_struct = curr['close'] > sma50.iloc[i]
                    valid_vwap = curr['close'] > vwap_series.iloc[i]
                    is_green = curr['close'] > curr['open']
                    
                    rvol = curr['volume']/vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                    valid_vol = 1.5 < rvol < 4.0
                    
                    if valid_squeeze and valid_struct and valid_vwap and is_green and valid_vol:
                        in_15 = True; entry_15 = curr['close']; sl_15 = curr['low']; be_15 = False
                        
                # --- STRATEGY 2: RVOL > 3.0 ---
                if in_30:
                    # Same Exit Logic
                    if curr['low'] <= sl_30:
                        pnl = (sl_30 - entry_30)/entry_30 * 100
                        r30['trades'] += 1; r30['pnl'] += pnl
                        if pnl > 0: r30['wins'] += 1
                        else: r30['losses'] += 1
                        in_30 = False
                    elif curr['close'] < ema9.iloc[i]:
                        pnl = (curr['close'] - entry_30)/entry_30 * 100
                        r30['trades'] += 1; r30['pnl'] += pnl
                        if pnl > 0: r30['wins'] += 1
                        else: r30['losses'] += 1
                        in_30 = False
                    else:
                        if not be_30 and (curr['close'] - entry_30)/entry_30 > 0.01:
                            sl_30 = entry_30 * 1.001
                            be_30 = True
                else:
                    # Entry (Modified Vol)
                    valid_squeeze = bw.iloc[i] < 0.15
                    valid_struct = curr['close'] > sma50.iloc[i]
                    valid_vwap = curr['close'] > vwap_series.iloc[i]
                    is_green = curr['close'] > curr['open']
                    
                    rvol = curr['volume']/vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                    valid_vol = rvol > 3.0 # IGNITION
                    
                    if valid_squeeze and valid_struct and valid_vwap and is_green and valid_vol:
                        in_30 = True; entry_30 = curr['close']; sl_30 = curr['low']; be_30 = False

    print("\n📊 RESULTS (Top 15 Focus List):")
    print(f"1️⃣  RVOL > 1.5 (Standard): {r15['trades']} Trades | Wins: {r15['wins']} | P&L: {r15['pnl']:.2f}%")
    print(f"2️⃣  RVOL > 3.0 (Ignition): {r30['trades']} Trades | Wins: {r30['wins']} | P&L: {r30['pnl']:.2f}%")

if __name__ == "__main__":
    run_final_sim()
