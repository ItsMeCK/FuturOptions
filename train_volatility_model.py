import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import os
import matplotlib.pyplot as plt

import glob

def train_model():
    data_dir = "ai_option_brain/data/processed"
    model_dir = "ai_option_brain/models"
    os.makedirs(model_dir, exist_ok=True)
    
    print("🧠 Starting Volatility Model Training (Random Forest) - Nifty 50...")
    print("="*60)
    
    # Scan for all processed training data
    files = glob.glob(f"{data_dir}/*_training_data.csv")
    print(f"   Found {len(files)} datasets.")
    
    for file_path in files:
        # Extract Symbol
        filename = os.path.basename(file_path)
        symbol = filename.replace("_training_data.csv", "")
        
        print(f"📉 Training for {symbol}...")
            
        print(f"📉 Training for {symbol}...")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        
        # Features & Target
        # Drop non-feature columns
        drop_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'target_rv', 'log_ret']
        features = [c for c in df.columns if c not in drop_cols]
        target = 'target_rv'
        
        # Train/Test Split (Date Based)
        # Train: Dec 2024 - May 2025
        # Test: Jun 2025 - Present (Nov 2025)
        split_date = pd.Timestamp("2025-06-01")
        
        train_df = df[df['date'] < split_date]
        test_df = df[df['date'] >= split_date]
        
        print(f"   📅 Train: {len(train_df)} rows | Test: {len(test_df)} rows")
        
        X_train, y_train = train_df[features], train_df[target]
        X_test, y_test = test_df[features], test_df[target]
        
        # Random Forest Regressor
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        mae = mean_absolute_error(y_test, preds)
        
        print(f"   ✅ Model Trained.")
        print(f"   📊 RMSE: {rmse:.4f} | MAE: {mae:.4f}")
        print(f"   Mean Target RV: {y_test.mean():.4f}")
        
        # Save Model
        joblib.dump(model, f"{model_dir}/{symbol}_rf_vol.pkl")

        
        # Feature Importance
        # importance = model.feature_importances_
        # print(f"   Top Feature: {features[np.argmax(importance)]}")

    print("="*60)
    print("🏁 Training Complete.")

if __name__ == "__main__":
    train_model()
