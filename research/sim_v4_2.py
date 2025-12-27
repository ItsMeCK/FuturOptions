
import pandas as pd
import numpy as np
import sys
import os

# Add root to path
sys.path.append(os.getcwd())
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def run_v4_2_simulation():
    print("🧪 SIMULATION: v4.2 Gamma Sniper (Dec 24 & 26)...")
    
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
            # 1. Bandwidth
            u, l = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            m = s_5m['close'].rolling(20).mean()
            bw = (u - l) / m
            
            # 2. Hourly Trend (Grandmaster)
            h_df = s_5m.resample('60min').agg({'close':'last'}).dropna()
            h_sma20 = h_df['close'].rolling(20).mean()
            
            # 3. EMA 9 (Trailing)
            ema9 = TechnicalIndicators.calculate_ema(s_5m['close'], 9)
            
            # 3.5 SMA 50 (Structure Filter)
            sma50 = s_5m['close'].rolling(50).mean()
            
            # 4. VWAP
            day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_5m.index.tz)
            day_mask = s_5m.index >= day_start
            day_df = s_5m[day_mask].copy()
            if day_df.empty: continue
            day_df['vwap'] = (day_df['close'] * day_df['volume']).cumsum() / day_df['volume'].cumsum()
            vwap_series = pd.Series(0, index=s_5m.index)
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
                
                # Update Hourly SMA
                # Find latest hourly close before current time
                # Simple approximation: reindex
                h_idx = h_df.index.get_indexer([current_time], method='pad')[0]
                if h_idx < 0: continue
                htf_trend_ok = h_df['close'].iloc[h_idx] > h_sma20.iloc[h_idx] if h_idx < len(h_sma20) else False
                
                # EXITS
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
                        # print(f"❌ STOP: {sym} @ {exit_price}")
                        continue
                        
                    # 2. Breakeven Migration
                    profit_pct = (curr['close'] - entry_price)/entry_price
                    if not is_breakeven and profit_pct > 0.01:
                        stop_loss = entry_price * 1.001 # Move to BE + slippage coverage
                        is_breakeven = True
                        # print(f"🛡️ BREAKEVEN ARMED: {sym}")
                        
                    # 3. EMA 9 Trail (If profitable)
                    # Use closing basis? Or Intraday? "Ride until momentum physically breaks" -> Close below EMA9
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
                
                # ENTRY LOGIC (Waterfall v4.2)
                
                # 1. Gatekeeper: Structure & VWAP
                # Replaced Broken Hourly SMA (Insufficient Data) with Structure SMA 50
                # Rule: Price must be above SMA 50 to buy Breakout
                sma50_val = sma50.iloc[i]
                structure_ok = curr['close'] > sma50_val if pd.notna(sma50_val) else False
                
                # Define Limit for Debug scope
                limit = 0.20 if curr['close'] > 2000 else 0.15
                
                # Calc RVOL early for Debug
                rvol = curr['volume'] / vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 0

                # DEBUG RVNL
                if sym == 'RVNL' and current_time.hour == 9 and current_time.minute == 20:
                    print(f"🕵️‍♂️ DEBUG RVNL 09:20:")
                    print(f"   - Close: {curr['close']}")
                    print(f"   - Open: {curr['open']} (Green? {curr['close'] > curr['open']})")
                    print(f"   - VWAP: {vwap_series.iloc[i]:.2f} (Above? {curr['close'] > vwap_series.iloc[i]})")
                    print(f"   - SMA 50: {sma50_val:.2f} (Above? {structure_ok})")
                    print(f"   - Bandwidth: {bw.iloc[i]:.3f} (Limit: {limit:.3f})")
                    print(f"   - RVOL: {rvol:.2f}")

                if not structure_ok: continue
                if curr['close'] < vwap_series.iloc[i]: continue
                
                # 2. Setup: Tiered Squeeze
                limit = 0.20 if curr['close'] > 2000 else 0.15
                if bw.iloc[i] > limit: continue
                
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
                
                print(f"🚀 ENTRY: {sym} @ {entry_price:.2f} ({current_time.strftime('%H:%M')}) | BW: {bw.iloc[i]:.3f} | Signal Low: {stop_loss:.2f}")

    print("\n🏆 v4.2 GAMMA SNIPER RESULTS:")
    print(f"   Trades: {stats['trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Breakeven Hits: {stats['breakeven_hits']}")
    # Adjust P&L to roughly account for Option Leverage (x20 approx or just spot pts)
    # Showing Spot P&L Sum
    print(f"   Net Spot P&L Sum: {stats['pnl']:.2f}%")

if __name__ == "__main__":
    run_v4_2_simulation()
