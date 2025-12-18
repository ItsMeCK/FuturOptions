import pandas as pd
import numpy as np
import os

def analyze_day_of_week():
    print("🎓 University Study: The 'Wednesday Rule' Hypothesis")
    print("="*60)
    
    file_path = "ai_option_brain/results/final_trades_log.csv"
    if not os.path.exists(file_path):
        print("❌ Trade log not found.")
        return

    df = pd.read_csv(file_path)
    
    # Convert Entry Date to Datetime
    df['Entry Date'] = pd.to_datetime(df['Entry Date'])
    df['Day'] = df['Entry Date'].dt.day_name()
    
    # Group by Day
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    print(f"{'Day':<12} | {'Trades':<8} | {'Win Rate':<10} | {'Avg ROI':<10} | {'Total P&L':<15}")
    print("-" * 70)
    
    for day in days:
        day_data = df[df['Day'] == day]
        count = len(day_data)
        if count == 0: continue
        
        wins = len(day_data[day_data['P&L (INR)'] > 0])
        win_rate = (wins / count) * 100
        avg_roi = day_data['ROI (%)'].mean()
        total_pnl = day_data['P&L (INR)'].sum()
        
        print(f"{day:<12} | {count:<8} | {win_rate:>8.1f}% | {avg_roi:>8.1f}% | ₹{total_pnl:>12.2f}")
        
    print("-" * 70)
    
    # Hypothesis Check
    wed_thu = df[df['Day'].isin(["Wednesday", "Thursday"])]
    mon_tue_fri = df[~df['Day'].isin(["Wednesday", "Thursday"])]
    
    wt_roi = wed_thu['ROI (%)'].mean()
    mtf_roi = mon_tue_fri['ROI (%)'].mean()
    
    print("\n🧪 Hypothesis Test:")
    print(f"   Wed/Thu Avg ROI: {wt_roi:.1f}%")
    print(f"   Mon/Tue/Fri Avg ROI: {mtf_roi:.1f}%")
    
    if wt_roi > mtf_roi:
        print("✅ CONCLUSION: The 'Wednesday Rule' is VALID. Mid-week trades perform better.")
    else:
        print("❌ CONCLUSION: The 'Wednesday Rule' is NOT supported by data.")

if __name__ == "__main__":
    analyze_day_of_week()
