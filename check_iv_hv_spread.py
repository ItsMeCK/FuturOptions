import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def analyze_iv_hv_spread():
    print("🔬 Analyzing IV (VIX) vs HV (Realized Volatility) Spread...")
    print("="*60)
    
    # 1. Load Reliance Data
    try:
        df_rel = pd.read_csv("data/RELIANCE.NS_2y_1d.csv")
        df_rel['date'] = pd.to_datetime(df_rel['date'])
        df_rel.set_index('date', inplace=True)
        
        # Resample to Daily to match VIX roughly
        df_daily = df_rel.resample('D').agg({'close': 'last'}).dropna()
        
        # Calculate HV (20-day annualized)
        df_daily['log_ret'] = np.log(df_daily['close'] / df_daily['close'].shift(1))
        df_daily['hv_20'] = df_daily['log_ret'].rolling(window=20).std() * np.sqrt(252) * 100
        
    except Exception as e:
        print(f"❌ Error loading Reliance data: {e}")
        return

    # 2. Load India VIX
    try:
        df_vix = pd.read_csv("ai_option_brain/data/raw/INDIA VIX_1min.csv")
        df_vix['date'] = pd.to_datetime(df_vix['date'])
        df_vix.set_index('date', inplace=True)
        
        # Resample to Daily Close
        vix_daily = df_vix.resample('D').agg({'close': 'last'}).dropna()
        vix_daily.rename(columns={'close': 'vix'}, inplace=True)
        
    except Exception as e:
        print(f"❌ Error loading VIX data: {e}")
        return

    # 3. Merge
    merged = df_daily.join(vix_daily, how='inner')
    
    if merged.empty:
        print("⚠️ No overlapping data found between Reliance and VIX.")
        return

    # 4. Calculate Spread/Ratio
    # Ratio = VIX / HV
    # If Ratio > 1, Market is pricing in fear (Premium).
    # If Ratio < 1, Market is complacent (Discount).
    
    merged['ratio'] = merged['vix'] / merged['hv_20']
    
    avg_ratio = merged['ratio'].mean()
    median_ratio = merged['ratio'].median()
    
    print(f"📊 Data Points: {len(merged)} days")
    print(f"   Average VIX: {merged['vix'].mean():.2f}")
    print(f"   Average HV:  {merged['hv_20'].mean():.2f}")
    print("-" * 40)
    print(f"🎯 IV/HV Ratio (The Fear Factor):")
    print(f"   Mean:   {avg_ratio:.2f}x")
    print(f"   Median: {median_ratio:.2f}x")
    print("-" * 40)
    
    # Conclusion
    if avg_ratio > 1.0:
        print(f"✅ Conclusion: Options are typically {((avg_ratio-1)*100):.1f}% more expensive than actual movement.")
    else:
        print(f"❓ Conclusion: Options are actually cheaper than movement? (Rare)")

if __name__ == "__main__":
    analyze_iv_hv_spread()
