import os
import pandas as pd
import glob

# Nifty 50 List
NIFTY_50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL",
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB",
    "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK",
    "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND",
    "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE",
    "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TCS", "TECHM", "TITAN", "ULTRACEMCO", "WIPRO"
]

def validate_data():
    data_dir = "data"
    print("🕵️‍♂️ Validating Nifty 50 Data...")
    print("="*60)
    
    valid_count = 0
    invalid_count = 0
    missing_count = 0
    
    found_symbols = []
    
    for symbol in NIFTY_50:
        file_path = f"{data_dir}/{symbol}.NS_2y_1d.csv"
        
        if not os.path.exists(file_path):
            print(f"❌ Missing: {symbol}")
            missing_count += 1
            continue
            
        try:
            # Check file size
            if os.path.getsize(file_path) < 100: # Empty or header only
                print(f"⚠️ Invalid (Empty): {symbol}")
                invalid_count += 1
                continue
                
            # Check CSV content
            df = pd.read_csv(file_path)
            
            # Check Columns
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                print(f"⚠️ Invalid (Columns): {symbol} - Found {df.columns.tolist()}")
                invalid_count += 1
                continue
                
            # Check Rows
            if len(df) < 1000:
                print(f"⚠️ Invalid (Too Few Rows): {symbol} - {len(df)} rows")
                invalid_count += 1
                continue
                
            # Valid
            # print(f"✅ Valid: {symbol} ({len(df)} rows)")
            valid_count += 1
            found_symbols.append(symbol)
            
        except Exception as e:
            print(f"❌ Corrupt: {symbol} - {e}")
            invalid_count += 1
            
    print("="*60)
    print(f"📊 Summary:")
    print(f"   ✅ Valid:   {valid_count}")
    print(f"   ❌ Invalid: {invalid_count}")
    print(f"   🚫 Missing: {missing_count}")
    print("="*60)
    
    # List Missing/Invalid for Retry
    retry_list = [s for s in NIFTY_50 if s not in found_symbols]
    if retry_list:
        print(f"🔄 Retry List ({len(retry_list)}): {retry_list}")

if __name__ == "__main__":
    validate_data()
