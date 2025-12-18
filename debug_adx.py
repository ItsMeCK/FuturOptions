import pandas as pd
import ta

def debug_adx():
    # Create dummy data
    df = pd.DataFrame({
        'high': [10 + i for i in range(100)],
        'low': [8 + i for i in range(100)],
        'close': [9 + i for i in range(100)]
    })
    
    print("Dummy Data Length:", len(df))
    
    try:
        adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        print("\nADX Output Type:", type(adx))
        print("\nADX Output Columns/Name:")
        if isinstance(adx, pd.DataFrame):
            print(adx.columns.tolist())
            print(adx.head())
        else:
            print(adx.name)
            print(adx.head())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_adx()
