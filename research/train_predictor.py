
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

def train_predictor():
    print("🧠 AI Training: Finding Predictive Features for >100% Returns...")
    
    # 1. Load Data
    try:
        df = pd.read_csv("research/ml_dataset_dec26.csv")
    except:
        print("Dataset missing.")
        return
        
    print(f"Data Shape: {df.shape}")
    
    # 2. Preprocess
    # Drop NaNs
    df = df.dropna()
    
    # Define Target: We care about MAGNITUDE of return.
    X = df[['Morning_Ret', 'Vol_Accel', 'Efficiency_Ratio', 'Range_Pct']]
    y = df['Target_Max_Return']
    
    # 3. Train Model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # 4. Feature Importance
    importance = pd.DataFrame({
        'Feature': X.columns,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    print("\n🏆 FEATURE IMPORTANCE (What actually predicts the 8000% move?):")
    print(importance)
    
    # 5. Correlation Check
    print("\n📈 Correlation Matrix:")
    numeric_df = df.drop(columns=['Symbol'])
    print(numeric_df.corr()['Target_Max_Return'].sort_values(ascending=False))
    
    # 6. Conclusion
    top_feature = importance.iloc[0]['Feature']
    print(f"\n💡 AI Insight: The #1 Predictor of massive returns is '{top_feature}'.")
    print("   (We should UPWEIGHT this in scoring and DOWNWEIGHT the others).")

if __name__ == "__main__":
    train_predictor()
