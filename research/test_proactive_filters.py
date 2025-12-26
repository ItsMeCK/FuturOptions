
import pandas as pd
import numpy as np

def calculate_er(close_series, period=10):
    # Efficiency Ratio = Abs(Net Change) / Sum(Abs(Change))
    # Measures directional efficiency vs noise
    if len(close_series) < period+1: return 1.0
    
    net_change = abs(close_series.iloc[-1] - close_series.iloc[-period-1])
    total_path = np.sum(np.abs(np.diff(close_series.iloc[-period-1:])))
    
    if total_path == 0: return 1.0
    return net_change / total_path

def test_filters():
    # Load Signals from Batch Analysis results or Sim Log
    # Let's reuse the 'signals' extraction logic 
    signals = []
    try:
        with open("trend_sim_v5.txt", "r") as f:
            lines = f.readlines()
        current_date = "2025-12-24"
        for line in lines:
            if "Simulation Complete for 2025-12-24" in line:
                current_date = "2025-12-26"
            if "POTENTIAL SIGNAL" in line:
                # Extract time from previous lines? No, 'Sim Sweep' time is needed.
                # Assuming approximate Sim Time for now or just analyze Day data at signal point?
                # Actually, we need Minute Data to calculate Pre-Entry Metrics.
                # Let's use the 'extract_forensic_data' logic: Load Full Day Minute Data for the symbol.
                try:
                    parts = line.split("POTENTIAL SIGNAL:")[1]
                    sym = parts.split("|")[0].strip()
                    # We need TIME of signal. Log has 'Time: HH:MM:ss' in Sweep line.
                    # This is hard to sync without precise timestamp in signal log.
                    # Updated Sim V5 prints "Sim Sweep ... Time: ... " before signal.
                    # We can parse that statefully.
                    signals.append({'date': current_date, 'symbol': sym})
                except: pass
    except: return

    print(f"🧪 Testing Proactive Filters on {len(signals)} Signals...")
    
    # Load Data Cache
    spot_data = {}
    for d in ["2025-12-24", "2025-12-26"]:
        try:
            df = pd.read_csv(f"daily_data/{d}_spot_full.csv")
            df['date'] = pd.to_datetime(df['date'])
            spot_data[d] = df
        except: pass

    blocked_count = 0
    total_checked = 0
    
    results = []

    for i, sig in enumerate(signals):
        # We process unique symbols per day to avoid re-calc overhead?
        # Actually logic triggers multiple times. Let's check the FIRST signal for simplicity.
        pass

    # Simplified Loop: Iterate UNIQUE triggers
    unique_keys = set()
    cleaned_signals = []
    for s in signals:
        k = f"{s['date']}_{s['symbol']}"
        if k not in unique_keys:
            unique_keys.add(k)
            cleaned_signals.append(s)
            
    for sig in cleaned_signals:
        date = sig['date']
        sym = sig['symbol']
        
        if date not in spot_data: continue
        df = spot_data[date]
        s_df = df[df['symbol'] == sym].sort_values('date').set_index('date')
        
        if s_df.empty: continue
        
        # Test Point: Noon (12:00)? Or Morning (10:00)?
        # Most Trend Signals fired all day.
        # Let's test at 10:30 (Morning Trigger) and 13:00 (Afternoon Trigger) if data exists so far?
        # Better: Scan the 15m candles over the day and see if ANY met conditions?
        # Or calculate metrics for the whole day and see % of time pass?
        
        # Implementation: Calculate Metrics at 11:00 AM (Typical Entry)
        # 1. ER (Efficiency Ratio) over last 60 mins
        # 2. Volume Expansion (Last 30m vs Prev 30m)
        
        cutoff = pd.to_datetime(f"{date} 11:00:00").tz_localize("Asia/Kolkata")
        
        hist = s_df[s_df.index <= cutoff]
        if len(hist) < 30: continue
        
        # Metric 1: Efficiency Ratio (ER)
        # Price path over last 30 mins
        closes = hist['close'].tail(30) # 30 mins
        er = calculate_er(closes, period=29)
        
        # Metric 2: Volume Expansion
        vol_now = hist['volume'].tail(30).mean()
        vol_prev = hist['volume'].iloc[-60:-30].mean()
        vol_ratio = vol_now / vol_prev if vol_prev > 0 else 0
        
        # FILTER RULES (Institutional)
        # Block if ER < 0.3 (Choppy/Churn)
        # Block if Vol Ratio < 1.0 (Drying Up)
        
        blocked = False
        reason = ""
        
        if er < 0.3:
            blocked = True
            reason = f"Churn (ER {er:.2f})"
        elif vol_ratio < 0.8: # Allow slight drop but not cliff
            blocked = True
            reason = f"Vol Dryup ({vol_ratio:.2f})"
            
        results.append({
            'symbol': sym,
            'er': er,
            'vol_ratio': vol_ratio,
            'blocked': blocked,
            'reason': reason
        })
        
    # Stats
    df_res = pd.DataFrame(results)
    blocked = df_res[df_res['blocked']]
    
    print("-" * 50)
    print("🛡 PROACTIVE FILTER TEST (At 11:00 AM)")
    print("-" * 50)
    print(f"Total Signals Checked: {len(df_res)}")
    print(f"🚫 BLOCKED:           {len(blocked)} ({len(blocked)/len(df_res)*100:.1f}%)")
    print(f"✅ ALLOWED:           {len(df_res) - len(blocked)}")
    print("-" * 50)
    print("Top Reason Breakdown:")
    print(blocked['reason'].apply(lambda x: x.split('(')[0]).value_counts())
    
    print("\n📉 Sample Blocked Trades (Stagnant Prevention):")
    print(blocked[['symbol', 'er', 'vol_ratio', 'reason']].head(5))

    print("\n📈 Sample Allowed Trades (Quality?):")
    print(df_res[~df_res['blocked']][['symbol', 'er', 'vol_ratio']].head(5))

if __name__ == "__main__":
    test_filters()
