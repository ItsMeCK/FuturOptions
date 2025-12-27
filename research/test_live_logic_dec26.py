
import pandas as pd
import numpy as np
import sys
import os

# Add root to path to import live_brain
sys.path.append(os.getcwd())
from live_brain import LiveBrain
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def test_activations():
    print("🚀 Simulating LiveBrain v2.0 on Dec 26 Data...")
    
    # Initialize Brain (Logic Only)
    brain = LiveBrain()
    
    # Load Data
    try:
        df = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['symbol', 'date'])
    except Exception as e:
        print(f"Error: {e}")
        return

    symbols = df['symbol'].unique()
    signals = []
    
    print(f"📊 Scanning {len(symbols)} Stocks...")
    
    for sym in symbols:
        s_df = df[df['symbol'] == sym]
        if len(s_df) < 50: continue
        
        # We simulate the status at 14:00 PM (Peak Stagnation/Trend Time)
        # We need enough history for 50SMA etc.
        
        # Snapshot Loop: Check every 15 mins from 09:30 to 15:00
        # Actually, let's just check the "Trend" moments.
        # Resample to 5 min to match Live Brain
        s_df = s_df.set_index('date')
        s_5m = s_df.resample('5min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        
        if len(s_5m) < 30: continue
        
        # Calculate Indicators (Replicating Scan Logic)
        # ADX
        adx = TechnicalIndicators.calculate_adx(s_5m['high'], s_5m['low'], s_5m['close'], 14)
        
        # BB
        up, lo = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
        mid = s_5m['close'].rolling(20).mean()
        
        # VWAP
        vwap = TechnicalIndicators.calculate_vwap(s_5m)
        
        # Iterate through the day to see if ANY signal fired
        for i in range(30, len(s_5m)):
            # Slice History
            hist = s_5m.iloc[:i+1]
            curr = hist.iloc[-1]
            
            # Metrics
            price = curr['close']
            adx_val = adx.iloc[i] if i < len(adx) else 0
            
            sma50 = hist['close'].rolling(50).mean().iloc[-1]
            trend_dist = (price - sma50)/sma50 if pd.notna(sma50) else 0
            
            rsi = TechnicalIndicators.calculate_rsi(hist['close'], 14).iloc[-1]
            
            # Bands
            u = up.iloc[i]
            l = lo.iloc[i]
            m = mid.iloc[i]
            bw = (u - l)/m if m > 0 else 0
            
            # Volume 
            vol_sma = hist['volume'].rolling(20).mean().iloc[-1]
            rvol = curr['volume']/vol_sma if vol_sma > 0 else 0
            
            # --- SMART METRICS (The New Stuff) ---
            # ER (Last 30m = 6 bars)
            if len(hist) < 7: continue
            
            # Calculate ER explicitly here as per Brain logic
            closes = hist['close'].tail(7)
            net = abs(closes.iloc[-1] - closes.iloc[0])
            path = np.sum(np.abs(np.diff(closes)))
            er = net/path if path > 0 else 1.0
            
            # Vol Breath
            vol_ratio = 1.0
            if len(hist) >= 12:
                curr_v = hist['volume'].tail(6).mean()
                prev_v = hist['volume'].iloc[-12:-6].mean()
                vol_ratio = curr_v/prev_v if prev_v > 0 else 0
                
            # Range Pct (AI Predictor #1)
            d_high = hist['high'].max()
            d_low = hist['low'].min()
            d_open = hist['open'].iloc[0]
            range_pct = ((d_high - d_low) / d_open) * 100 if d_open > 0 else 0

            # HTF Logic (Hourly) - Simplified
            htf_trend = "NEUTRAL"
            if len(hist) > 0:
                # We need context beyond just `hist`. We need broader data.
                # `s_5m` has full day. `hist` is slice.
                # We can resample `hist` to 1H.
                # Ideally we want the value AT THIS MOMENT `i`.
                current_time_val = hist.index[-1]
                
                # Resample FULL history available up to `i`
                full_hist_upto_now = s_5m.iloc[:i+1]
                htf_df_now = full_hist_upto_now.resample('60min').agg({'close':'last'}).dropna()
                
                if len(htf_df_now) > 20: 
                    sma20_h = htf_df_now['close'].rolling(20).mean().iloc[-1]
                    price_h = htf_df_now['close'].iloc[-1]
                    htf_trend = "BULLISH" if price_h > sma20_h else "BEARISH"

            # CALL BRAIN
            # Mock objects
            focus_data = {}
            if price > u: focus_data['breakout_level'] = price # Mock breakout
            
            res = brain.calculate_confluence_score(
                sym, price, adx_val, trend_dist, rsi, bw, u, rvol, 
                0, 0, 15, focus_data, # pred_rv=0, iv=15
                history=None,
                rvol_5m_avg=rvol,
                is_momentum_active=False,
                er_value=er,
                vol_ratio=vol_ratio,
                vwap_value=vwap.iloc[i],
                range_pct=range_pct,
                htf_trend=htf_trend
            )
            
            if res['score'] >= 60:
                # DEDUPLICATE: Only add if we haven't seen this symbol recently
                should_add = True
                for s in signals:
                    if s['symbol'] == sym: 
                        should_add = False # Just one signal per stock for summary
                
                if should_add:
                    signals.append({
                        'time': hist.index[-1].strftime('%H:%M'),
                        'symbol': sym,
                        'score': res['score'],
                        'reasons': res['reasons'],
                        'er': er,
                        'rvol': rvol
                    })

    # REPORT
    print("\n✅ ACTIVATED TRADES (LiveBrain v2.0 Logic):")
    print("-" * 60)
    df_sig = pd.DataFrame(signals)
    if not df_sig.empty:
        df_sig = df_sig.sort_values('score', ascending=False)
        print(df_sig[['time', 'symbol', 'score', 'er', 'reasons']].to_string(index=False))
        print("-" * 60)
        print(f"Total Approved Trades: {len(df_sig)}")
    else:
        print("No trades found. Logic might be too strict or data missing.")

if __name__ == "__main__":
    test_activations()
