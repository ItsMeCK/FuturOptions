
import pandas as pd
import matplotlib.pyplot as plt

def diagnose_losers():
    print("🕵️‍♂️ Forensic Analysis: Why did BAJFINANCE/ABCAPITAL fail?")
    
    # 1. Load Data
    df = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    targets = ['BAJFINANCE', 'ABCAPITAL']
    
    for sym in targets:
        print(f"\n📉 Diagnosing {sym}...")
        s_df = df[df['symbol'] == sym]
        
        # 2. Reconstruct Timeframes
        # 5-min (Signal TF)
        tf_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        # 60-min (Context TF)
        tf_60m = s_df.resample('60min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last'}).dropna()
        
        # 3. Find the Failed Entry
        # We know from report:
        # BAJFINANCE Entry approx 09:55? (Need to check report, or just look for the loss)
        # Let's just assume the "High Volatility" event.
        
        # Check standard indicators at 10:00 - 12:00
        print(f"   Context at 10:00 - 12:00:")
        
        subset_60 = tf_60m.between_time('09:15', '14:00')
        print(subset_60[['open', 'high', 'low', 'close']].tail(5).to_string())
        
        # 4. Check VWAP Alignment
        vwap = (s_df['close'] * s_df['volume']).cumsum() / s_df['volume'].cumsum()
        last_price = s_df['close'].iloc[-1]
        vwap_val = vwap.iloc[-1]
        
        print(f"   Price vs VWAP: {last_price:.2f} vs {vwap_val:.2f}")
        if last_price < vwap_val:
            print("   ⚠️ BEARISH: Price below VWAP (Institutional Sell Control)")
            
        # 5. Check Structure
        # Simple Logic: Is High < Prev Hourly High?
        last_h = subset_60['high'].iloc[-1]
        prev_h = subset_60['high'].iloc[-2]
        if last_h < prev_h:
            print("   ⚠️ STRUCTURE: Lower Highs (Downtrend on Hourly)")
            
        print("-" * 40)

if __name__ == "__main__":
    diagnose_losers()
