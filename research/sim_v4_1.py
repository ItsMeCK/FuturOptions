
import pandas as pd
import numpy as np
import sys
import os

# Add root to path
sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def run_v4_1_simulation():
    print("🧪 SIMULATION: v4.1 Dynamic Squeeze & Impulse Exits (Dec 24 & 26)...")
    
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
    
    stats = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'impulse_exits': 0}
    
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
            # Bandwidth (20, 2)
            u, l = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            m = s_5m['close'].rolling(20).mean()
            bw = (u - l) / m
            
            # Dynamic Squeeze: Rolling Min 375 (Approx 5 days, or as much history as we have)
            min_bw = bw.rolling(375, min_periods=20).min()
            
            # ATR for Trail
            atr = TechnicalIndicators.calculate_atr(s_5m['high'], s_5m['low'], s_5m['close'], 14)
            
            # VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_mask = s_5m.index >= day_start
            day_df = s_5m[day_mask].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0, index=s_5m.index)
            vwap_series.update(day_df['vwap'])
            
            # Vol SMA
            vol_sma = s_5m['volume'].rolling(20).mean()
            
            # Simulation Loop (Only Today's Data)
            # Find indices for today
            today_idxs = [i for i, t in enumerate(s_5m.index) if t >= day_start]
            
            in_trade = False
            entry_price = 0
            entry_idx = 0
            stop = 0
            
            for i in today_idxs:
                if i < 20: continue # Warmup
                
                # Close Trade Check
                if in_trade:
                    curr = s_5m.iloc[i]
                    # 1. Impulse Exit Check (3 Candle Rule)
                    bars_held = i - entry_idx
                    if bars_held == 3:
                        # Check if we made a new high vs Entry High
                        # Entry High is High of entry candle? No, price must act.
                        # Rule: Price must make New High within 3 candles.
                        # Check Max High since entry
                        max_h = s_5m['high'].iloc[entry_idx+1:i+1].max()
                        if max_h <= s_5m['high'].iloc[entry_idx]: 
                             # Failed Impulse -> EXIT
                             exit_price = curr['close']
                             pnl = (exit_price - entry_price)/entry_price * 100
                             stats['trades'] += 1
                             stats['impulse_exits'] += 1
                             if pnl > 0: stats['wins'] += 1; stats['pnl'] += pnl
                             else: stats['losses'] += 1; stats['pnl'] += pnl
                             in_trade = False
                             continue
                             
                    # 2. Trailing Stop Check (ATR)
                    # Stop = High - 2*ATR
                    # Dynamic: Trail up
                    new_stop = curr['high'] - (2 * atr.iloc[i])
                    if new_stop > stop: stop = new_stop
                    
                    if curr['low'] <= stop:
                         stats['trades'] += 1
                         stats['losses'] += 1
                         stats['pnl'] -= ((entry_price - stop)/entry_price * 100) # Loss at stop
                         in_trade = False
                    continue
                
                # Entry Logic (Waterfall)
                row = s_5m.iloc[i]
                
                # 1. Gatekeeper: Above VWAP
                if row['close'] < vwap_series.iloc[i]: continue
                
                # 2. Setup: Dynamic Squeeze
                curr_bw = bw.iloc[i]
                limit_bw = min_bw.iloc[i] * 1.10
                if curr_bw > limit_bw: continue
                
                # 3. Trigger: Vol & Body
                rvol = row['volume'] / vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0
                if rvol < 1.5 or rvol > 4.0: continue
                
                body = abs(row['close'] - row['open'])
                rng = row['high'] - row['low']
                dom = body / rng if rng > 0 else 0
                if dom < 0.6: continue
                
                # ENTRY VALID
                in_trade = True
                entry_price = row['close']
                entry_idx = i
                stop = row['high'] - (2 * atr.iloc[i])
                
                # ENTRY VALID
                in_trade = True
                entry_price = row['close']
                entry_idx = i
                stop = row['high'] - (2 * atr.iloc[i])
                
                # FORENSIC LOGGING:
                # Check if this "Squeeze" is actually high volatility
                squeeze_quality = "TIGHT" if curr_bw < 0.15 else "LOOSE"
                
                print(f"👉 ENTRY {stats['trades']+1}: {sym} @ {row.name.strftime('%H:%M')} | BW: {curr_bw:.3f} (Limit: {limit_bw:.3f}) | {squeeze_quality}")
                
                if curr_bw > 0.20:
                     print(f"   ⚠️ TRAP: Buying High Volatility! Relative Low, but Absolute High.")
                
    print("\n🏆 v4.1 RESULTS:")
    print(f"   Trades: {stats['trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Impulse Exits: {stats['impulse_exits']}")
    print(f"   Net P&L (pts): {stats['pnl']:.2f}%")

if __name__ == "__main__":
    run_v4_1_simulation()
