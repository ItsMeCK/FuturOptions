import os
import pandas as pd
from ai_option_brain.data_loader import YFinanceDataFetcher

def fetch_pilot_data():
    stocks = ["RELIANCE.NS", "ADANIENT.NS", "HDFCBANK.NS", "SBIN.NS", "TATAMOTORS.NS", "^INDIAVIX"]
    data_dir = "ai_option_brain/data/raw"
    os.makedirs(data_dir, exist_ok=True)
    
    print("🚀 Starting Pilot Data Fetch (Source: yfinance)...")
    print("="*60)
    
    for stock in stocks:
        # Fetch 2 Years of Hourly Data (Good for Swing/Intraday Structure training)
        df = YFinanceDataFetcher.fetch_historical_data(stock, period="2y", interval="1h")
        
        if not df.empty:
            filename = f"{data_dir}/{stock.replace('.NS', '').replace('^', '')}_1h.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Saved {stock} to {filename} ({len(df)} rows)")
        else:
            print(f"❌ Failed to fetch {stock}")

    print("="*60)
    print("🏁 Data Fetch Complete.")

if __name__ == "__main__":
    fetch_pilot_data()
