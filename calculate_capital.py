import pandas as pd
import numpy as np

# Institutional Lot Sizes (Same as simulation)
LOT_SIZES = {
    "RELIANCE": 250, "TCS": 175, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700,
    "SBIN": 1500, "TATAMOTORS": 1425, "ITC": 1600, "AXISBANK": 625, "LT": 300,
    "BAJFINANCE": 125, "MARUTI": 50, "KOTAKBANK": 400, "SUNPHARMA": 700,
    "TITAN": 175, "ULTRACEMCO": 100, "ASIANPAINT": 200, "BHARTIARTL": 950,
    "ADANIENT": 300, "INDUSINDBK": 500, "BEL": 5700, "TATASTEEL": 5500,
    "HINDUNILVR": 300, "HINDALCO": 1400, "BAJAJFINSV": 500, "JSWSTEEL": 675,
    "GRASIM": 475, "POWERGRID": 3600, "NTPC": 3000, "ONGC": 3850,
    "COALINDIA": 2100, "BRITANNIA": 200, "NESTLEIND": 40, "CIPLA": 650,
    "DRREDDY": 125, "APOLLOHOSP": 125, "DIVISLAB": 200, "WIPRO": 1500,
    "TECHM": 600, "LTIM": 150, "HCLTECH": 700, "HEROMOTOCO": 300,
    "EICHERMOT": 175, "M&M": 350, "BPCL": 1800, "TATACONSUM": 900
}

def calculate_capital():
    try:
        df = pd.read_csv("smart_volume_simulation.csv")
    except FileNotFoundError:
        print("Error: smart_volume_simulation.csv not found.")
        return

    # 1. Calculate Capital per Trade (Option Buying)
    # Estimate Premium = 1.5% of Spot Price
    # Capital = Premium * Lot Size
    
    def get_capital(row):
        symbol = row['Symbol']
        entry = row['Entry']
        lot_size = LOT_SIZES.get(symbol, 500)
        premium = entry * 0.015
        return premium * lot_size

    df['Capital_Required'] = df.apply(get_capital, axis=1)

    # 2. Calculate Max Daily Capital (Assuming all trades overlap for worst case)
    daily_capital = df.groupby('Date')['Capital_Required'].sum()
    
    max_daily_capital = daily_capital.max()
    avg_daily_capital = daily_capital.mean()
    total_pnl = df['Total_Profit'].sum()
    
    print("\n" + "="*50)
    print("💰 CAPITAL ANALYSIS (Option Buying)")
    print("="*50)
    print(f"Total Trades: {len(df)}")
    print(f"Total PnL: ₹{total_pnl:,.2f}")
    print(f"Max Capital Deployed (Worst Case Day): ₹{max_daily_capital:,.2f}")
    print(f"Avg Daily Capital: ₹{avg_daily_capital:,.2f}")
    
    roi = (total_pnl / max_daily_capital) * 100
    print(f"ROI (on Max Capital): {roi:.2f}%")
    
    print("\n--- Daily Breakdown ---")
    print(daily_capital.sort_values(ascending=False).head(5))

if __name__ == "__main__":
    calculate_capital()
