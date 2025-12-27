
import pandas as pd
import numpy as np
import sys
import os

# Add root to path
sys.path.append(os.getcwd())
try:
    from live_brain import LiveBrain
    from ai_option_brain.utils.technical_indicators import TechnicalIndicators
except ImportError:
    # Handle running from research/ dir? No cwd is set to root.
    pass

def correlate_reality():
    print("🔬 Starting Holistic Review: LiveBrain Score vs Market Reality (Dec 26)")
    
    # 1. Load Ground Truth (Reality)
    try:
        gt_df = pd.read_csv("research/ground_truth_movers.csv")
        # Filter for Dec 26
        gt_df = gt_df[gt_df['Date'] == '2025-12-26']
        print(f"📚 Loaded {len(gt_df)} Reality Points (Dec 26 Options > 30%)")
    except Exception as e:
        print(f"❌ Error loading ground truth: {e}")
        return

    # Extract clean Symbol from GT
    import re
    def get_sym(s):
        m = re.match(r"([A-Z&]+)", s)
        return m.group(1) if m else s
        
    gt_df['StockSymbol'] = gt_df['OptionSymbol'].apply(get_sym)
    
    # Get Max Return per Stock (The Potential)
    stock_potential = gt_df.groupby('StockSymbol')['MaxReturn%'].max().to_dict()
    
    # 2. Load Spot Data (Universe)
    try:
        spot_df = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        spot_df['date'] = pd.to_datetime(spot_df['date'])
        spot_df = spot_df.sort_values(['symbol', 'date'])
        all_symbols = spot_df['symbol'].unique()
        print(f"🌍 Scanning Universe: {len(all_symbols)} Stocks")
    except Exception as e:
        print(f"❌ Error loading spot data: {e}")
        return
        
    # 3. Brain Simulation (Get Score for EVERY Stock)
    brain = LiveBrain()
    results = [] # {Symbol, MaxScore, AvgScore, MaxReturn, Status}
    
    count = 0
    for sym in all_symbols:
        count += 1
        if count % 20 == 0: print(f"   ...scanned {count}/{len(all_symbols)}")
        
        s_df = spot_df[spot_df['symbol'] == sym].set_index('date')
        if len(s_df) < 50: continue
        
        # Resample 5m
        s_5m = s_df.resample('5min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        if len(s_5m) < 30: continue
        
        # Calculate Indicators
        adx = TechnicalIndicators.calculate_adx(s_5m['high'], s_5m['low'], s_5m['close'], 14)
        up, lo = TechnicalIndicators.calculate_bollinger_bands(s_5m['close'], 20, 2)
        mid = s_5m['close'].rolling(20).mean()
        vwap = TechnicalIndicators.calculate_vwap(s_5m)
        
        max_score = 0
        rejection_reasons = []
        
        # Scan Day
        for i in range(30, len(s_5m)):
            hist = s_5m.iloc[:i+1]
            curr = hist.iloc[-1]
            price = curr['close']
            
            # Metric Prep
            # (Skipping lengthy re-calc for speed, using approximation for logic check)
            
            # Need ER and VolRatio specifically as they are the new filters
            if len(hist) < 7: continue
            closes = hist['close'].tail(7)
            path = np.sum(np.abs(np.diff(closes)))
            er = (abs(closes.iloc[-1] - closes.iloc[0]) / path) if path > 0 else 1.0
            
            vol_ratio = 1.0
            if len(hist) >= 12:
                v_curr = hist['volume'].tail(6).mean()
                v_prev = hist['volume'].iloc[-12:-6].mean()
                vol_ratio = v_curr/v_prev if v_prev > 0 else 0
                
            # Inputs
            adx_val = adx.iloc[i] if i < len(adx) else 0
            sma50 = hist['close'].rolling(50).mean().iloc[-1]
            trend_dist = (price - sma50)/sma50 if pd.notna(sma50) else 0
            rsi = TechnicalIndicators.calculate_rsi(hist['close'], 14).iloc[-1]
            u = up.iloc[i]
            l = lo.iloc[i]
            m = mid.iloc[i]
            bw = (u - l)/m if m > 0 else 0
            v_sma = hist['volume'].rolling(20).mean().iloc[-1]
            rvol = curr['volume']/v_sma if v_sma > 0 else 0
            
            focus = {}
            if price > u: focus['breakout_level'] = price
            
            # Brain Call
            res = brain.calculate_confluence_score(
                sym, price, adx_val, trend_dist, rsi, bw, u, rvol, 
                0, 0, 15, focus, 
                history=None, rvol_5m_avg=rvol, is_momentum_active=False,
                er_value=er, vol_ratio=vol_ratio, vwap_value=vwap.iloc[i]
            )
            
            s = res['score']
            if s > max_score:
                max_score = s
                # Keep track of reasons for high-ish scores
                if s > 0: rejection_reasons = res['reasons']
            # If 0, check reasons?
            if s == 0 and max_score == 0:
                 rejection_reasons = res['reasons'] # Keep last error
                 
        # End of Stock loop
        real_ret = stock_potential.get(sym, 0.0) # 0 if < 30%
        
        results.append({
            'Symbol': sym,
            'MaxScore': max_score,
            'MaxReturn': real_ret,
            'LastReason': str(rejection_reasons)
        })

    # Save Results
    res_df = pd.DataFrame(results)
    res_df.to_csv("research/score_vs_reality_dec26.csv", index=False)
    print(f"✅ Correlation Data Saved: {len(res_df)} Stocks")
    
    # 4. Report Findings
    print("\n📊 CORRELATION REPORT: SYSTEM vs REALITY")
    print("-" * 60)
    
    # A. Did High Scores = High Returns?
    high_scorers = res_df[res_df['MaxScore'] >= 65]
    avg_ret_high = high_scorers['MaxReturn'].mean()
    print(f"High Scorer Accuracy (Score >= 65):")
    print(f"   - Count:               {len(high_scorers)}")
    print(f"   - Avg Option Return:   {avg_ret_high:.1f}%")
    print(f"   - % with >30% Return:  {len(high_scorers[high_scorers['MaxReturn'] > 30]) / len(high_scorers) * 100:.1f}%")
    
    # B. The MISSED MONSTERS (High Return, Low Score)
    missed = res_df[(res_df['MaxReturn'] > 100) & (res_df['MaxScore'] < 60)]
    print(f"\n🦖 MAJOR MISSES (Return > 100% but Score < 60):")
    print(f"   - Count: {len(missed)}")
    print(missed.sort_values('MaxReturn', ascending=False).head(10)[['Symbol', 'MaxReturn', 'MaxScore', 'LastReason']].to_string(index=False))

if __name__ == "__main__":
    correlate_reality()
