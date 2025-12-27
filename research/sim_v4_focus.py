
import pandas as pd
import numpy as np
import sys
import os
import json

# Add root to path
sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def run_v4_focus_simulation():
    print("🧪 SIMULATION: Hybrid v4.3 (Focus List ONLY)...")
    
    # Load Focus List
    focus_list = []
    if os.path.exists("focus_list.json"):
        with open("focus_list.json") as f:
            data = json.load(f)
            raw = data.get('focus_list', [])
            focus_list = [x['symbol'] for x in raw]
            print(f"🎯 Loaded Focus List ({len(focus_list)}): {focus_list}")
    else:
        print("❌ No Focus List found!")
        return

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
        
        # FILTER: Only Iterate Focus List Symbols
        symbols = [s for s in df['symbol'].unique() if s in focus_list]
        
        for sym in symbols:
            s_df = df[df['symbol'] == sym].set_index('date').sort_index()
            # Stitch for 26th
            if date_str == '2025-12-26' and sym in history_cache:
                s_df = pd.concat([history_cache[sym].set_index('date'), s_df]).sort_index()
                
            if len(s_df) < 100: continue
            
            # Resample 5m
            s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
            # Indicators
            # 1. Bandwidth (Strict 0.15)
            u, l = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            m = s_5m['close'].rolling(20).mean()
            bw = (u - l) / m
            
            # 2. SMA 50 (Structure)
            sma50 = s_5m['close'].rolling(50).mean()
            
            # 3. EMA 9 (Trailing)
            ema9 = TechnicalIndicators.calculate_ema(s_5m['close'], 9)
            
            # 4. VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_mask = s_5m.index >= day_start
            day_df = s_5m[day_mask].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0.0, index=s_5m.index, dtype='float64')
            vwap_series.update(day_df['vwap'])
            
            # Vol SMA
            vol_sma = s_5m['volume'].rolling(20).mean()
            
            # Simulation Loop
            today_idxs = [i for i, t in enumerate(s_5m.index) if t >= day_start]
            
            in_trade = False
            entry_price = 0
            stop_loss = 0
            is_breakeven = False
            
            for i in today_idxs:
                if i < 20: continue 
                
                curr = s_5m.iloc[i]
                current_time = curr.name
                
                # EXITS (Breathing Room)
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
                        # EXIT SIGNAL
                        exit_price = curr['close']
                        pnl = (exit_price - entry_price)/entry_price * 100
                        stats['trades'] += 1
                        if pnl > 0: stats['wins'] += 1
                        elif pnl == 0: stats['breakeven_hits'] += 1
                        else: stats['losses'] += 1
                        stats['pnl'] += pnl
                        in_trade = False
                        print(f"💰 TRAIL EXIT: {sym} @ {exit_price:.2f} P&L: {pnl:.2f}%")
                        continue
                        
                    continue
                
                # ENTRY LOGIC (Hybrid v4.3)
                
                # 1. Gatekeeper: Structure (SMA 50) & VWAP
                sma50_val = sma50.iloc[i]
                structure_ok = curr['close'] > sma50_val if pd.notna(sma50_val) else False
                
                if not structure_ok: continue
                if curr['close'] < vwap_series.iloc[i]: continue
                
                # 2. Setup: Strict Squeeze (Absolute 0.15)
                if bw.iloc[i] > 0.15: continue
                
                # 3. Trigger: RVOL & Green Candle
                rvol = curr['volume'] / vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                if rvol < 1.5 or rvol > 4.0: continue
                
                # Green Candle
                if curr['close'] <= curr['open']: continue
                
                # VALID ENTRY
                in_trade = True
                entry_price = curr['close']
                stop_loss = curr['low'] # Signal Low
                is_breakeven = False
                
                print(f"🚀 ENTRY: {sym} @ {entry_price:.2f} ({current_time.strftime('%H:%M')}) | BW: {bw.iloc[i]:.3f}")
 
    print("\n🏆 HYBRID v4.3 (FOCUS ONLY) RESULTS:")
    print(f"   Trades: {stats['trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Net Spot P&L Sum: {stats['pnl']:.2f}%")

if __name__ == "__main__":
    run_v4_focus_simulation()
