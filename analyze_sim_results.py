
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_results():
    try:
        df = pd.read_csv("sim_dec29.csv")
    except FileNotFoundError:
        print("❌ 'sim_dec29.csv' not found. Run simulation first.")
        return

    print("📊 --- ANALYSIS OF FALSE POSITIVES ---")
    print(f"Total Signals: {len(df)}")
    print(f"Unique Symbols: {df['Symbol'].nunique()}")
    
    # 1. Bandwidth Analysis
    avg_bw = df['BW'].mean()
    print(f"\n1. 📉 Bandwidth (Squeeze Tightness)")
    print(f"   Average BW: {avg_bw:.4f}")
    print(f"   Min BW: {df['BW'].min()}")
    print(f"   Max BW: {df['BW'].max()}")
    print(f"   Signals with BW < 0.02 (Dead?): {len(df[df['BW'] < 0.02])} ({len(df[df['BW'] < 0.02])/len(df)*100:.1f}%)")
    
    # 2. RVOL Analysis
    avg_rvol = df['RVOL'].mean()
    print(f"\n2. 🔊 Volume (RVOL)")
    print(f"   Average RVOL: {avg_rvol:.2f}")
    print(f"   Signals with RVOL < 2.0 (Weak Power): {len(df[df['RVOL'] < 2.0])}")
    
    # 3. Time Analysis
    # Convert Time to Hour
    df['Hour'] = df['Time'].apply(lambda x: x.split(':')[0])
    print(f"\n3. ⏰ Time Distribution")
    print(df['Hour'].value_counts().sort_index())
    
    # 4. Repeat Offenders
    print(f"\n4. 🔄 Top Churners (Repeats)")
    print(df['Symbol'].value_counts().head(10))
    
    # Common Patterns
    print("\n--- COMMON REASONS HYPOTHESIS ---")
    if avg_bw < 0.03:
        print("👉 EXTREME LOW VOLATILITY: Many stocks are likely in 'Dead Zones' (BW < 0.03).")
        print("   The Squeeze logic is triggering on stocks that are just flatlining, not actually coiling.")
        
    if len(df[df['RVOL'] < 2.0]) > len(df) * 0.5:
        print("👉 WEAK VOLUME BREAKOUTS: Many signals have low relative volume.")
        
    if df['Hour'].mode()[0] in ['09', '10']:
        print("👉 MORNING CHOP: Most signals are in the first 90 mins (Opening Range).")

if __name__ == "__main__":
    analyze_results()
