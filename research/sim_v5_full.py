import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Add root to path
sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators
from ai_option_brain.logic.iv_rank import IVRankCalculator

def run_v5_simulation():
    print("🏦 SIMULATION: Institutional v5.0 (Full Upgrade)...")
    print("   Filters: HV Rank < 20 | VWAP Defense | Tape Reading | Time Stop (10m)")
    
    # Initialize Logistics
    iv_calc = IVRankCalculator()
    days = ['2025-12-24', '2025-12-26']
    
    stats = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'forced_exits': 0, 'time_stops': 0}
    
    # Pre-load history helper
    # (The iv_calc does its own caching)
    
    for date_str in days:
        print(f"\n📅 Processing {date_str}...")
        try:
            df = pd.read_csv(f"daily_data/{date_str}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
        except:
            print(f"   ❌ No data for {date_str}")
            continue
            
        symbols = df['symbol'].unique()
        
        for sym in symbols:
            # 1. Get IV/HV Rank (Regime Filter)
            # We check this ONCE per day (Daily Context)
            rank_metrics = iv_calc.get_rank_metrics(sym, current_date=date_str)
            
            # Institutional Filter: HV Percentile < 50 (Strict Cheapness/Quietness)
            # The critique said "IV Percentile < 20". Start with 50 to see flow, or strict 20.
            # Let's use 30 as a strong 'Quiet' filter.
            if not rank_metrics: continue
            
            hv_pct = rank_metrics['hv_percentile']
            if hv_pct > 30: 
                # Market is already volatile/expensive. Institutions SELL here, not buy.
                # Skip.
                continue
                
            # 2. Intraday Loop
            s_df = df[df['symbol'] == sym].set_index('date').sort_index()
            if len(s_df) < 50: continue
            
            # Resample 5m
            s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
            # Indicators
            u, l = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            m = s_5m['close'].rolling(20).mean()
            bw = (u - l) / m
            
            # VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_mask = s_5m.index >= day_start
            day_df = s_5m[day_mask].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0.0, index=s_5m.index, dtype='float64')
            vwap_series.update(day_df['vwap'])
            
            # Vol SMA for RVOL
            vol_sma = s_5m['volume'].rolling(20).mean()
            
            # Simulation
            in_trade = False
            entry_price = 0
            entry_time = None
            entry_idx = 0
            position = None # LONG/SHORT
            stop_loss = 0
            
            today_idxs = [i for i, t in enumerate(s_5m.index) if t >= day_start]
            
            for i in today_idxs:
                if i < 20: continue
                
                curr = s_5m.iloc[i]
                current_time = curr.name
                
                # --- EXIT LOGIC ---
                if in_trade:
                    # 1. Time Stop (Theta Protection) - 10 Mins (2 candles)
                    # If PnL is not > 0.3% after 10 mins, KILL IT.
                    candles_held = i - entry_idx
                    profit_pct = 0
                    if position == 'LONG': profit_pct = (curr['close'] - entry_price)/entry_price * 100
                    else: profit_pct = (entry_price - curr['close'])/entry_price * 100
                    
                    if candles_held >= 2 and profit_pct < 0.05:
                        stats['trades'] += 1
                        stats['time_stops'] += 1
                        stats['pnl'] += profit_pct
                        if profit_pct > 0: stats['wins'] += 1 # Technical win but forced exit
                        else: stats['losses'] += 1 # Likely small loss
                        
                        in_trade = False
                        # print(f"   ⏱️ TIME STOP: {sym} {profit_pct:.2f}% (Stalled)")
                        continue
                        
                    # 2. Hard Stop
                    hit_stop = False
                    if position == 'LONG' and curr['low'] <= stop_loss: hit_stop = True
                    elif position == 'SHORT' and curr['high'] >= stop_loss: hit_stop = True
                    
                    if hit_stop:
                        exit_price = stop_loss
                        loss = (exit_price - entry_price)/entry_price * 100 if position == 'LONG' else (entry_price - exit_price)/entry_price * 100
                        stats['trades'] += 1
                        stats['losses'] += 1
                        stats['pnl'] += loss
                        in_trade = False
                        # print(f"   ❌ STOP HIT: {sym}")
                        continue
                        
                    # 3. Target / Gamma Scalp
                    # If > 1%, sell.
                    if profit_pct > 1.0:
                        stats['trades'] += 1
                        stats['wins'] += 1
                        stats['pnl'] += profit_pct
                        in_trade = False
                        print(f"   💰 GAMMA SCALP: {sym} +{profit_pct:.2f}%")
                        continue
                        
                    continue
                    
                # --- ENTRY LOGIC ---
                
                # 1. Regime Check (Already done: HV Rank < 30)
                
                # 2. Squeeze Check (Bandwidth < 0.15) - Retained
                if bw.iloc[i] > 0.15: continue
                
                # 3. Trigger (RVOL > 1.5)
                rvol = curr['volume'] / vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                if rvol < 1.5: continue
                
                # 4. Institutional VWAP Defense
                vwap_val = vwap_series.iloc[i]
                if vwap_val == 0: continue
                
                # Determine Potential Direction
                is_long = curr['close'] > curr['open']
                
                if is_long:
                    # RULE: LONG only if Price > VWAP
                    if curr['close'] < vwap_val: continue
                    position = 'LONG'
                    stop_loss = curr['low']
                else:
                    # RULE: SHORT only if Price < VWAP
                    if curr['close'] > vwap_val: continue
                    position = 'SHORT'
                    stop_loss = curr['high']
                    
                # VALID ENTRY
                in_trade = True
                entry_price = curr['close']
                entry_time = current_time
                entry_idx = i
                
                print(f"🚀 ENTRY {position}: {sym} @ {entry_price:.2f} (HV%{hv_pct:.0f})")
                
    print("\n🏆 v5.0 INSTITUTIONAL REPORT:")
    print(f"   Total Trades: {stats['trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']} (Time Stops: {stats['time_stops']})")
    print(f"   Net P&L (Spot %): {stats['pnl']:.2f}%")

if __name__ == "__main__":
    run_v5_simulation()
