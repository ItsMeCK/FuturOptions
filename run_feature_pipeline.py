import os
import pandas as pd
from ai_option_brain.feature_engineer import FeatureEngineer

import glob

def run_pipeline():
    raw_dir = "data" # Where fetch_nifty50_data.py saves
    processed_dir = "ai_option_brain/data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    print("⚙️ Starting Feature Engineering Pipeline (Nifty 50)...")
    print("="*60)
    
    # 1. Load India VIX (Common Feature)
    # We might not have VIX for the exact same period, but let's try to load what we have
    vix_path = "ai_option_brain/data/raw/INDIA VIX_1min.csv"
    if os.path.exists(vix_path):
        print("   📊 Loading India VIX...")
        vix_df = pd.read_csv(vix_path)
    else:
        print("   ⚠️ India VIX data not found. Proceeding without VIX features.")
        vix_df = None

    # 2. Scan for all downloaded stocks
    files = glob.glob(f"{raw_dir}/*.NS_2y_1d.csv")
    print(f"   Found {len(files)} stock files.")
    
    for file_path in files:
        # Extract Symbol
        filename = os.path.basename(file_path)
        symbol = filename.replace(".NS_2y_1d.csv", "")
        
        print(f"🔍 Processing {symbol}...")
        
        try:
            # Load 1-min Data
            df_1m = pd.read_csv(file_path)
            df_1m['date'] = pd.to_datetime(df_1m['date'])
            
            # Create 60-min Data (Resample)
            df_1m.set_index('date', inplace=True)
            df_60m = df_1m.resample('60min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()
            df_1m.reset_index(inplace=True)
            
            # Run Engineer
            df_final = FeatureEngineer.prepare_training_data(df_1m, df_60m, vix_df)
            
            # Save Processed Data
            out_path = f"{processed_dir}/{symbol}_training_data.csv"
            df_final.to_csv(out_path, index=False)
            print(f"   ✅ Saved Training Data: {out_path} ({len(df_final)} rows)")
            
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")

    print("="*60)
    print("🏁 Pipeline Complete.")

if __name__ == "__main__":
    run_pipeline()
