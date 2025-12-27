
import pandas as pd
import numpy as np

def calculate_er(close_series, period=6):
    if len(close_series) < period+1: return 1.0
    net_change = abs(close_series.iloc[-1] - close_series.iloc[-period-1])
    diffs = np.diff(close_series.iloc[-period-1:])
    total_path = np.sum(np.abs(diffs))
    if total_path == 0: return 1.0
    return net_change / total_path

def verify_today():
    print("🔍 Loading Dec 26 Data...")
    try:
        df = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        df['date'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata')
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    symbols = df['symbol'].unique()
    print(f"📊 Analyzing {len(symbols)} Stocks Intraday Structure...")

    blocked_count = 0
    total_samples = 0
    
    # We will sample the "Afternoon Session" (13:00 - 15:00) where stagnation occurs
    # Just like the live logs
    
    results = []
    
    for sym in symbols:
        s_df = df[df['symbol'] == sym].sort_values('date').set_index('date')
        if len(s_df) < 30: continue
        
        # Sample at 2:00 PM (14:00) - Typical Churn Time
        cutoff = pd.to_datetime("2025-12-26 14:00:00").tz_localize("Asia/Kolkata")
        
        hist = s_df[s_df.index <= cutoff]
        if len(hist) < 30: continue
        
        # Replicate LiveBrain Logic
        er = calculate_er(hist['close'].tail(30), period=6) # 30 min window? Wait, period=6 is 30m if 5min candles?
        # Data is minute level in spot_full.csv usually? Or 5 min?
        # Let's check granularity. Assuming minute for forensic.
        # If minute, period=30 is 30 mins.
        # In LiveBrain we us 5-min candles, so period=6 is 30 mins.
        # Here we have likely MINUTE data (from forensic fetch). 
        # So we should use period=30.
        
        # Check frequency
        if len(hist) > 1:
            diff = (hist.index[1] - hist.index[0]).seconds
            if diff < 100: # Minute data
                period = 30
            else: # 5 Min Data
                period = 6
        else:
             period = 30
             
        er = calculate_er(hist['close'], period=period)
        
        # Volume Ratio
        vol_ratio = 1.0
        if len(hist) > period*2:
            curr = hist['volume'].tail(period).mean()
            prev = hist['volume'].iloc[-period*2:-period].mean()
            vol_ratio = curr/prev if prev > 0 else 0
            
        status = "ALLOWED"
        reason = "Clean"
        
        if er < 0.3:
            status = "BLOCKED"
            reason = f"Churn (ER {er:.2f})"
            blocked_count += 1
        elif vol_ratio < 0.8:
            status = "BLOCKED"
            reason = f"Vacuum (Ratio {vol_ratio:.2f})"
            blocked_count += 1
            
        results.append({
            'symbol': sym,
            'time': '14:00',
            'er': er,
            'vol_ratio': vol_ratio,
            'status': status,
            'reason': reason
        })
        total_samples += 1
        
    res_df = pd.DataFrame(results)
    blocked = res_df[res_df['status'] == "BLOCKED"]
    allowed = res_df[res_df['status'] == "ALLOWED"]
    
    print("-" * 60)
    print(f"🛡 SMART BOT VERIFICATION (Dec 26 - 14:00 PM Snapshot)")
    print("-" * 60)
    print(f"Total Stocks Scanned: {total_samples}")
    print(f"🚫 BLOCKED (Stagnant): {len(blocked)} ({len(blocked)/total_samples*100:.1f}%)")
    print(f"✅ ALLOWED (Active):   {len(allowed)}")
    print("-" * 60)
    print("\n📉 Sample Blocked (Correctly Identified Churn):")
    print(blocked.sort_values('er').head(10)[['symbol', 'er', 'reason']])
    
    print("\n📈 Sample Allowed (Real Movement):")
    print(allowed.sort_values('er', ascending=False).head(10)[['symbol', 'er', 'vol_ratio']])

if __name__ == "__main__":
    verify_today()
