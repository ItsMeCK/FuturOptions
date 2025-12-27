
import pandas as pd
import numpy as np

def generate_dataset():
    print("🤖 Building ML Dataset (Features @ 09:45 vs Target MaxReturn)...")
    
    # 1. Load Ground Truth (Target)
    gt_df = pd.read_csv("research/ground_truth_movers.csv")
    gt_df = gt_df[gt_df['Date'] == '2025-12-26']
    
    # Map Symbol to Max Return
    import re
    def get_sym(s):
        m = re.match(r"([A-Z&]+)", s)
        return m.group(1) if m else s
    gt_df['StockSymbol'] = gt_df['OptionSymbol'].apply(get_sym)
    
    target_map = gt_df.groupby('StockSymbol')['MaxReturn%'].max().to_dict()
    
    # 2. Load Spot Data (Universe)
    spot_df = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
    spot_df['date'] = pd.to_datetime(spot_df['date'])
    
    dataset = []
    
    # 3. Feature Extraction Loop
    # We want features visible EARLY in the day (e.g., 09:45)
    cutoff_time = pd.Timestamp("2025-12-26 09:45:00+05:30")
    
    symbols = spot_df['symbol'].unique()
    
    for sym in symbols:
        s_df = spot_df[spot_df['symbol'] == sym].sort_values('date').set_index('date')
        
        # Slice Morning Data (09:15 - 09:45)
        morning = s_df[s_df.index <= cutoff_time]
        if len(morning) < 15: continue
        
        # Feature 1: Gap Up %
        try:
            prev_close = morning['open'].iloc[0] # Approx
            open_price = morning['open'].iloc[0] 
            gap = (open_price - prev_close)/prev_close # Need prev day data for real gap. 
            # Proxy: Just use 9:45 performance vs Open
            curr_price = morning['close'].iloc[-1]
            morning_return = (curr_price - open_price)/open_price
        except:
            morning_return = 0
            
        # Feature 2: Volume Velocity (Last 5 mins vs First 5 mins)
        # 09:40-09:45 vol vs 09:15-09:20 vol
        try:
            early_vol = morning['volume'].head(5).mean()
            late_vol = morning['volume'].tail(5).mean()
            vol_accel = late_vol / early_vol if early_vol > 0 else 1.0
        except:
            vol_accel = 1.0
            
        # Feature 3: Efficiency Ratio (The Current Blocker)
        try:
            closes = morning['close']
            net = abs(closes.iloc[-1] - closes.iloc[0])
            path = np.sum(np.abs(np.diff(closes)))
            er = net/path if path > 0 else 0.5
        except:
            er = 0.5
            
        # Feature 4: Range Consolidation (High - Low) / Open
        try:
            h = morning['high'].max()
            l = morning['low'].min()
            range_pct = (h - l) / open_price
        except:
            range_pct = 0.0
            
        # Feature 5: Option Volume Spike (Hard to get without option data per stock here)
        # We'll use Spot Volume as proxy for now.
        
        # TARGET variable
        max_ret = target_map.get(sym, 0.0)
        
        dataset.append({
            'Symbol': sym,
            'Morning_Ret': morning_return,
            'Vol_Accel': vol_accel,
            'Efficiency_Ratio': er,
            'Range_Pct': range_pct,
            'Target_Max_Return': max_ret
        })
        
    # Save
    out = pd.DataFrame(dataset)
    out.to_csv("research/ml_dataset_dec26.csv", index=False)
    print(f"✅ ML Dataset Generated: {len(out)} Samples")
    print(out.head())

if __name__ == "__main__":
    generate_dataset()
