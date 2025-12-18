import pandas as pd
import numpy as np
import os
import glob
from datetime import timedelta
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class ParameterOptimizer:
    def __init__(self, data_dir="daily_data"):
        self.data_dir = data_dir
        self.results = []

    def load_data(self):
        files = glob.glob(f"{self.data_dir}/*_nifty50_intraday.csv")
        data_map = {}
        for f in files:
            date_str = os.path.basename(f).split("_")[0]
            try:
                df = pd.read_csv(f)
                df.rename(columns={'date': 'timestamp'}, inplace=True)
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df.dropna(subset=['timestamp'], inplace=True)
                df.sort_values('timestamp', inplace=True)
                data_map[date_str] = df
            except Exception as e:
                logging.error(f"Error loading {f}: {e}")
        return data_map

    def calculate_indicators(self, df):
        # Simplified Technicals for Speed
        df['SMA20'] = df['close'].rolling(20).mean()
        df['STD20'] = df['close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (2 * df['STD20'])
        df['Lower'] = df['SMA20'] - (2 * df['STD20'])
        df['RVOL'] = df['volume'] / (df['volume'].rolling(50).mean() + 1e-9) # Simple approx
        df['RVOL'] = df['RVOL'].fillna(0)
        return df

    def simulate_strategy(self, date, df, rvol_thresh, score_thresh, target_pts, stop_pts):
        trades = 0
        pnl = 0
        
        # Avoid chaining
        df = df.copy()
        df = self.calculate_indicators(df)
        
        # Logic: 
        # Long if Price > Upper Band AND RVOL > Threshold
        # Short if Price < Lower Band AND RVOL > Threshold
        # Exit: Fixed Target/Stop (Scalping Mode) OR End of Day
        
        in_position = False
        entry_price = 0
        direction = 0 # 1 Long, -1 Short
        
        for i, row in df.iterrows():
            if in_position:
                # check exit
                curr_price = row['close']
                
                if direction == 1:
                    gain = curr_price - entry_price
                    if gain >= target_pts:
                        pnl += target_pts
                        trades += 1
                        in_position = False
                    elif gain <= -stop_pts:
                        pnl -= stop_pts
                        trades += 1
                        in_position = False
                elif direction == -1:
                    gain = entry_price - curr_price
                    if gain >= target_pts:
                        pnl += target_pts
                        trades += 1
                        in_position = False
                    elif gain <= -stop_pts:
                        pnl -= stop_pts
                        trades += 1
                        in_position = False
                        
            # Entry Logic (only if flat)
            else:
                # Determine Signal
                # Note: 'Score' is hard to replicate exactly without full Brain logic.
                # We use RVOL + Band Breakout as proxy for "High Score"
                
                is_breakout = row['close'] > row['Upper']
                is_breakdown = row['close'] < row['Lower']
                has_vol = row['RVOL'] > rvol_thresh
                
                # Mock Score based on volatility
                # If Breakout + Vol, we assume Score > score_thresh
                
                if has_vol:
                    if is_breakout:
                        in_position = True
                        direction = 1
                        entry_price = row['close']
                    elif is_breakdown:
                        in_position = True
                        direction = -1
                        entry_price = row['close']

        return trades, pnl

    def run_optimization(self):
        data_map = self.load_data()
        if not data_map:
            print("No data found!")
            return

        print(f"Loaded {len(data_map)} days of data.")
        
        # Grid Search
        rvol_params = [0.5, 0.8, 1.0, 1.2, 1.5]
        target_params = [10, 20, 30] # Points
        stop_params = [10, 20] # Points
        
        summary = []
        
        print(f"{'RVOL':<5} | {'TGT':<5} | {'SL':<5} | {'Trades':<6} | {'Total PnL':<10} | {'Avg PnL/Day':<10}")
        print("-" * 60)
        
        for rvol in rvol_params:
            for tgt in target_params:
                for sl in stop_params:
                    # Run across all days
                    total_trades = 0
                    total_pnl = 0
                    days_counted = 0
                    
                    for date, df in data_map.items():
                        t, p = self.simulate_strategy(date, df, rvol, 0, tgt, sl)
                        total_trades += t
                        total_pnl += p
                        days_counted += 1
                        
                    avg_pnl = total_pnl / days_counted if days_counted > 0 else 0
                    
                    print(f"{rvol:<5} | {tgt:<5} | {sl:<5} | {total_trades:<6} | {total_pnl:<10.2f} | {avg_pnl:<10.2f}")
                    summary.append({
                        'rvol': rvol, 'tgt': tgt, 'sl': sl, 
                        'trades': total_trades, 'pnl': total_pnl
                    })
        
        # Suggest Best
        best = max(summary, key=lambda x: x['pnl'])
        print("\n🏆 BEST PARAMETERS:")
        print(best)

if __name__ == "__main__":
    opt = ParameterOptimizer()
    opt.run_optimization()
