import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestRegressor

def train_production_models():
    data_dir = "ai_option_brain/data/processed"
    model_dir = "ai_option_brain/models"
    os.makedirs(model_dir, exist_ok=True)
    
    # Load ALL available data files
    files = [f for f in os.listdir(data_dir) if f.endswith("_training_data.csv")]
    print(f"🏆 Found {len(files)} datasets to train.")

    print("="*60)
    
    for filename in files:
        symbol = filename.replace("_training_data.csv", "")
        file_path = os.path.join(data_dir, filename)
            
        print(f"🧠 Training {symbol}...", end=" ")
        
        # 1. Load Data
        df = pd.read_csv(file_path)
        
        # 2. Features & Target
        # Matched with actual CSV columns
        features = ['hv_10', 'hv_20', 'log_ret', 'trend_dist', 'rsi', 'india_vix']
        target = 'target_rv'
        
        # Drop NaNs
        df.dropna(subset=features + [target], inplace=True)
        
        if df.empty:
            print("Skipped (Empty Data)")
            continue
            
        X = df[features]
        y = df[target]
        
        # 3. Train Model (Full Dataset - No Split)
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X, y)
        
        # 4. Save Model
        joblib.dump(model, f"{model_dir}/{symbol}_vol_model.pkl")
        print(f"✅ Saved (Rows: {len(df)})")

    print("="*60)
    print("🎉 All Production Models Trained & Saved!")

if __name__ == "__main__":
    train_production_models()
