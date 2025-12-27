
import pandas as pd
import numpy as np
import sys
import os

# Add root to path
sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

# State Constants
WAITING_FOR_IMPULSE = 0
WAITING_FOR_PULLBACK = 1
READY_TO_ENTER = 2

def run_v5_0_simulation():
    print("🧪 SIMULATION: v5.0 Institutional Reload (Pullback Sniping)...")
    
    # Load Data (Stitched)
    days = ['2025-12-24', '2025-12-26']
    history_cache = {}
    
    # Pre-load history for 26th
    try:
        h_df = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        h_df['date'] = pd.to_datetime(h_df['date'])
        for s in h_df['symbol'].unique():
            history_cache[s] = h_df[h_df['symbol'] == s].sort_values('date')
    except: pass
    
    stats = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'breakeven_hits': 0}
    
    for date_str in days:
        try:
            df = pd.read_csv(f"daily_data/{date_str}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
        except: continue
        
        symbols = df['symbol'].unique()
        
        for sym in symbols:
            s_df = df[df['symbol'] == sym].set_index('date').sort_index()
            # Stitch for 26th
            if date_str == '2025-12-26' and sym in history_cache:
                s_df = pd.concat([history_cache[sym].set_index('date'), s_df]).sort_index()
                
            if len(s_df) < 100: continue
            
            # Resample 5m
            s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
            # Indicators
            # 1. SMA 50 (Structure)
            sma50 = s_5m['close'].rolling(50).mean()
            
            # 2. VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_mask = s_5m.index >= day_start
            day_df = s_5m[day_mask].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0, index=s_5m.index)
            vwap_series.update(day_df['vwap'])
            
            # 2.5 EMA 20 (Target Zone - Optional, using VWAP primary as requested)
            
            # 3. EMA 9 (Exit Trail)
            ema9 = TechnicalIndicators.calculate_ema(s_5m['close'], 9)
            
            # Vol SMA
            vol_sma = s_5m['volume'].rolling(20).mean()
            
            # Simulation Loop
            today_idxs = [i for i, t in enumerate(s_5m.index) if t >= day_start]
            
            in_trade = False
            entry_price = 0
            stop_loss = 0
            is_breakeven = False
            
            state = WAITING_FOR_IMPULSE
            impulse_high = 0
            
            for i in today_idxs:
                if i < 20: continue 
                
                curr = s_5m.iloc[i]
                current_time = curr.name
                
                # EXITS (Breathing Room - Standardized)
                if in_trade:
                    # 1. Stop Loss Check
                    if curr['low'] <= stop_loss:
                        exit_price = stop_loss
                        pnl = (exit_price - entry_price)/entry_price * 100
                        stats['trades'] += 1
                        if pnl > 0: stats['wins'] += 1
                        elif pnl == 0: stats['breakeven_hits'] += 1
                        else: stats['losses'] += 1
                        stats['pnl'] += pnl
                        in_trade = False
                        # Reset State
                        state = WAITING_FOR_IMPULSE 
                        print(f"❌ STOP: {sym} @ {exit_price}")
                        continue
                        
                    # 2. Breakeven Migration
                    profit_pct = (curr['close'] - entry_price)/entry_price
                    if not is_breakeven and profit_pct > 0.01:
                        stop_loss = entry_price * 1.001 # Move to BE
                        is_breakeven = True
                        print(f"🛡️ BREAKEVEN ARMED: {sym}")
                        
                    # 3. EMA 9 Trail (If profitable)
                    if curr['close'] < ema9.iloc[i]:
                        exit_price = curr['close']
                        pnl = (exit_price - entry_price)/entry_price * 100
                        stats['trades'] += 1
                        if pnl > 0: stats['wins'] += 1
                        elif pnl == 0: stats['breakeven_hits'] += 1
                        else: stats['losses'] += 1
                        stats['pnl'] += pnl
                        in_trade = False
                        state = WAITING_FOR_IMPULSE
                        print(f"💰 TRAIL EXIT: {sym} @ {exit_price:.2f} P&L: {pnl:.2f}%")
                        continue
                    continue
                
                # ENTRY LOGIC (v5.0 Institutional Reload)
                
                vwap_val = vwap_series.iloc[i]
                sma50_val = sma50.iloc[i]
                rvol = curr['volume'] / vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                
                # Failsafe: Trend Broken? Reset.
                # If Price falls significantly below VWAP (0.5%), the setup is dead.
                if state != WAITING_FOR_IMPULSE:
                     if curr['close'] < (vwap_val * 0.995):
                         state = WAITING_FOR_IMPULSE
                         # print(f"⚠️ {sym}: Trend Broken. Resetting.")
                
                # STATE MACHINE
                
                if state == WAITING_FOR_IMPULSE:
                    # Phase 1: Detect Footprint (Ignition)
                    # RVOL > 3.0, Green, Above VWAP, Above SMA50
                    is_green = curr['close'] > curr['open']
                    above_vwap = curr['close'] > vwap_val
                    above_sma = curr['close'] > sma50_val
                    
                    if rvol > 3.0 and is_green and above_vwap and above_sma:
                        state = WAITING_FOR_PULLBACK
                        impulse_high = curr['high']
                        print(f"👀 WATCHLIST: {sym} Impulse detected @ {curr['close']:.2f} (RVOL {rvol:.1f})")
                        
                elif state == WAITING_FOR_PULLBACK:
                    # Phase 2: The Shakeout (Pullback to Value)
                    # Dist to VWAP < 0.2% AND Low Volume (RVOL < 0.8)
                    dist_to_vwap = abs(curr['close'] - vwap_val) / vwap_val
                    is_low_vol = rvol < 0.8
                    
                    # Logic: Must be close to VWAP. 
                    if dist_to_vwap < 0.002 and is_low_vol:
                        state = READY_TO_ENTER
                        print(f"🎯 TARGET ACQUIRED: {sym} Pullback to VWAP (Dist {dist_to_vwap*100:.2f}%, RVOL {rvol:.1f})")
                        
                elif state == READY_TO_ENTER:
                    # Phase 3: The Reload (Entry Trigger)
                    # Buy on first Green Candle
                    if curr['close'] > curr['open']:
                        # ENTRY!
                        in_trade = True
                        entry_price = curr['close']
                        stop_loss = curr['low'] # Stop below trigger candle
                        is_breakeven = False
                        print(f"🚀 RELOAD ENTRY: {sym} @ {entry_price:.2f} ({current_time.strftime('%H:%M')})")
                        state = WAITING_FOR_IMPULSE # Reset state after entry execution

    print("\n🏆 v5.0 INSTITUTIONAL RELOAD RESULTS:")
    print(f"   Trades: {stats['trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Breakeven: {stats['breakeven_hits']}")
    print(f"   Net Spot P&L: {stats['pnl']:.2f}%")

if __name__ == "__main__":
    run_v5_0_simulation()
