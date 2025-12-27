
import pandas as pd
import numpy as np
import sys
import os
from datetime import timedelta

# Add root to path
sys.path.append(os.getcwd())
from live_brain import LiveBrain
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def simulate_days():
    # Cache Dec 24 for History
    history_cache = {}
    try:
        print("📥 Pre-loading Dec 24 Data for History Stitched Simulation...")
        hist_df_raw = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        hist_df_raw['date'] = pd.to_datetime(hist_df_raw['date'])
        all_syms = hist_df_raw['symbol'].unique()
        for s in all_syms:
             history_cache[s] = hist_df_raw[hist_df_raw['symbol'] == s].sort_values('date')
    except Exception as e:
        print(f"⚠️ Could not load history cache: {e}")

    days = ['2025-12-24', '2025-12-26']
    
    print("🚀 Generating Validation Report (Grandmaster Filter Active)...")
    brain = LiveBrain()
    all_trades = []
    
    for date_str in days:
        print(f"\n📅 Processing {date_str}...")
        try:
            df = pd.read_csv(f"daily_data/{date_str}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['symbol', 'date'])
        except:
            continue

        symbols = df['symbol'].unique()
        
        for sym in symbols:
            s_df = df[df['symbol'] == sym].set_index('date').sort_index()
            if len(s_df) < 10: continue
            
            # --- STITCH HISTORY ---
            full_series = s_df
            if date_str == '2025-12-26' and sym in history_cache:
                hist_series = history_cache[sym].set_index('date')
                full_series = pd.concat([hist_series, s_df]).sort_index()
            
            # Resample 5min
            s_5m = full_series.resample('5min').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
            
            # Day Start
            current_day_start = pd.Timestamp(f"{date_str} 09:15").tz_localize(s_df.index.tz)
            
            if len(s_5m) < 30: continue
            
            # Indicators
            adx = TechnicalIndicators.calculate_adx(s_5m['high'], s_5m['low'], s_5m['close'], 14)
            up, lo = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
            mid = s_5m['close'].rolling(20).mean()
            
            # VWAP (Intraday Reset)
            day_5m = s_5m[s_5m.index >= current_day_start].copy()
            if day_5m.empty: continue
            day_5m['vwap'] = (day_5m['close'] * day_5m['volume']).cumsum() / day_5m['volume'].cumsum()
            vwap_full = pd.Series(0, index=s_5m.index)
            vwap_full.update(day_5m['vwap'])
            
            # RVOL Series
            vol_sma_series = s_5m['volume'].rolling(20).mean()
            
            # State
            in_trade = False
            entry_price = 0
            entry_time = None
            stop_loss = 0
            target = 0
            trade_type = ""
            
            day_indices = [i for i, idx in enumerate(s_5m.index) if idx >= current_day_start]
            
            for i in day_indices:
                current_time = s_5m.index[i]
                
                # Exits
                if in_trade and current_time.hour >= 15 and current_time.minute >= 15:
                    exit_price = s_5m.iloc[i]['close']
                    pnl = (exit_price - entry_price)/entry_price * 100
                    all_trades.append({'Date':date_str, 'Symbol':sym, 'Status':'CLOSED_TIME', 'Spot P&L %':round(pnl,2), 'Entry Time':entry_time.strftime('%H:%M')})
                    in_trade = False
                    continue

                if in_trade:
                    curr_bar = s_5m.iloc[i]
                    if trade_type == "LONG":
                        if curr_bar['low'] <= stop_loss:
                            all_trades.append({'Date':date_str, 'Symbol':sym, 'Status':'STOP_LOSS', 'Spot P&L %':round((stop_loss-entry_price)/entry_price*100,2), 'Entry Time':entry_time.strftime('%H:%M')})
                            in_trade = False
                        elif curr_bar['high'] >= target:
                            all_trades.append({'Date':date_str, 'Symbol':sym, 'Status':'TARGET_HIT', 'Spot P&L %':round((target-entry_price)/entry_price*100,2), 'Entry Time':entry_time.strftime('%H:%M')})
                            in_trade = False
                    continue
                
                # --- ENTRY LOGIC ---
                hist = s_5m.iloc[:i+1]
                curr = hist.iloc[-1]
                price = curr['close']
                
                # Core Indicators
                adx_val = adx.iloc[i] if i < len(adx) else 0
                sma50 = hist['close'].rolling(50).mean().iloc[-1]
                trend_dist = (price - sma50)/sma50 if pd.notna(sma50) else 0
                rsi = TechnicalIndicators.calculate_rsi(hist['close'], 14).iloc[-1]
                u = up.iloc[i]; l = lo.iloc[i]; m = mid.iloc[i]
                bw = (u - l)/m if m > 0 else 0
                
                vol_sma = vol_sma_series.iloc[i]
                rvol = curr['volume']/vol_sma if (pd.notna(vol_sma) and vol_sma > 0) else 0
                
                if len(hist) < 7: continue
                closes = hist['close'].tail(7)
                net = abs(closes.iloc[-1] - closes.iloc[0])
                path = np.sum(np.abs(np.diff(closes)))
                er = net/path if path > 0 else 1.0
                
                vol_ratio = 1.0
                if len(hist) >= 12:
                    c_v = hist['volume'].tail(6).mean()
                    p_v = hist['volume'].iloc[-12:-6].mean()
                    vol_ratio = c_v/p_v if p_v > 0 else 0
                
                # Range Pct
                range_pct = 0.0
                try:
                    upto_now_day = day_5m.loc[:current_time]
                    if not upto_now_day.empty:
                        d_high = upto_now_day['high'].max(); d_low = upto_now_day['low'].min(); d_open = upto_now_day['open'].iloc[0]
                        range_pct = ((d_high - d_low) / d_open) * 100 if d_open > 0 else 0
                except: pass

                # --- GRANDMASTER FILTER (HTF TREND) ---
                htf_trend = "NEUTRAL"
                # Need at least 20 hours ~ 240 5min bars
                if len(hist) > 240:
                    # Resample `hist` to 1H
                    h_df = hist.resample('60min').agg({'close':'last'}).dropna()
                    if len(h_df) > 20:
                        sma20h = h_df['close'].rolling(20).mean().iloc[-1]
                        last_h_close = h_df['close'].iloc[-1]
                        htf_trend = "BULLISH" if last_h_close > sma20h else "BEARISH"

                focus_data = {}
                if price > u: focus_data['breakout_level'] = price
                
                # Market Relative Strength (RS) - Simplified Proxy for Validation
                relative_strength = 0.5 # Default to 'Positive' RS for backtest to test Squeeze primarily
                if len(hist) > 12:
                     p_now = hist['close'].iloc[-1]
                     p_old = hist['close'].iloc[-12]
                     rs_val = (p_now - p_old)/p_old * 100
                     relative_strength = rs_val

                res = brain.calculate_confluence_score(
                    sym, price, adx_val, trend_dist, rsi, bw, u, rvol, 
                    0, 0, 15, focus_data, 
                    history=None, rvol_5m_avg=rvol, is_momentum_active=False,
                    er_value=er, vol_ratio=vol_ratio, vwap_value=vwap_full.iloc[i],
                    range_pct=range_pct, htf_trend=htf_trend,
                    relative_strength=relative_strength
                )
                
                if res['score'] >= 65:
                    in_trade = True
                    entry_time = current_time
                    entry_price = price
                    trade_type = "LONG"
                    # Tighter SL for validation
                    stop_loss = entry_price * 0.995 
                    target = entry_price * 1.015
                    
    df_res = pd.DataFrame(all_trades)
    print(f"\n✅ Total Trades Generated: {len(df_res)}")
    df_res.to_csv("research/recent_trades_report.csv", index=False)
    
    if not df_res.empty:
        print("\n🔎 Trade Preview:")
        print(df_res[['Date', 'Symbol', 'Status', 'Spot P&L %']].head(5).to_string(index=False))

if __name__ == "__main__":
    simulate_days()
