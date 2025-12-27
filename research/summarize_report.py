
import pandas as pd

def summarize():
    try:
        df = pd.read_csv("research/recent_trades_report.csv")
    except:
        print("No report found.")
        return

    print(f"📊 SUMMARY REPORT (Dec 24 & 26)")
    print("-" * 50)
    print(f"Total Trades: {len(df)}")
    
    # Calculate Theoretical Options P&L
    # Logic: Spot 1% ~ Option 20-30% (Delta 0.6 + Gamma)
    # Conservative Multiplier: 20x for winners, 20x for losers
    # Capped at Target/Stop logic if status is explicit
    
    def calc_opt_pnl(row):
        if row['Status'] == 'TARGET_HIT': return 30.0 # Fixed Target
        if row['Status'] == 'STOP_LOSS': return -10.0 # Fixed Stop
        
        # Time Exit: Apply Leverage
        return row['Spot P&L %'] * 20.0 

    df['Options P&L %'] = df.apply(calc_opt_pnl, axis=1)

    # Win Rate (Options P&L > 0)
    wins = df[df['Options P&L %'] > 0]
    losses = df[df['Options P&L %'] <= 0]
    win_rate = len(wins) / len(df) * 100
    
    print(f"Win Rate:     {win_rate:.1f}%")
    print(f"Avg Opt P&L:  {df['Options P&L %'].mean():.2f}% per trade")
    print(f"Total ROI:    {df['Options P&L %'].sum():.2f}% (Sum of all trades)")
    print(f"Risk/Reward:  {abs(df[df['Options P&L %'] > 0]['Options P&L %'].mean() / df[df['Options P&L %'] < 0]['Options P&L %'].mean()):.2f}")
    
    print("\n🏆 TOP 10 WINNERS (Options Est):")
    print(df.sort_values('Options P&L %', ascending=False).head(10)[['Date', 'Symbol', 'Entry Time', 'Spot P&L %', 'Options P&L %']].to_string(index=False))
    
    print("\n📉 TOP 5 LOSERS (Options Est):")
    print(df.sort_values('Options P&L %', ascending=True).head(5)[['Date', 'Symbol', 'Spot P&L %', 'Options P&L %']].to_string(index=False))

if __name__ == "__main__":
    summarize()
