import pandas as pd
import numpy as np
import os
import glob
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class WinnerForensics:
    def __init__(self, data_dir="daily_data"):
        self.data_dir = data_dir
        
    def load_spot_data(self, date_str):
        # Load Spot Data for Indicators
        f = f"{self.data_dir}/{date_str}_nifty50_intraday.csv"
        if not os.path.exists(f):
            return None
        df = pd.read_csv(f)
        df.rename(columns={'date': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df.sort_values('timestamp', inplace=True)
        
        # Calculate Indicators (RVOL, Bands)
        df['SMA20'] = df['close'].rolling(20).mean()
        df['STD20'] = df['close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (2 * df['STD20'])
        df['Lower'] = df['SMA20'] - (2 * df['STD20'])
        df['RVOL'] = df['volume'] / (df['volume'].rolling(50).mean() + 1e-9)
        return df

    def find_option_winners(self, date_str):
        f = f"{self.data_dir}/{date_str}_options_intraday.csv"
        if not os.path.exists(f):
            return []
            
        try:
            df = pd.read_csv(f)
            df['timestamp'] = pd.to_datetime(df['date']) # Assuming 'date' column
        except Exception as e:
            return []

        winners = []
        # Group by Trading Symbol (Option Contract)
        if 'tradingsymbol' not in df.columns: return []
        
        for token, group in df.groupby('tradingsymbol'):
            group = group.sort_values('timestamp')
            if len(group) < 30: continue # Skip illiquid
            
            open_price = group.iloc[0]['open']
            max_price = group['high'].max()
            
            if open_price > 5: # Ignore cheap OTM dust
                gain = (max_price - open_price) / open_price
                
                if gain > 0.50: # > 50% Return
                    # Find WHERE it broke out (e.g. crossed 20%)
                    breakout_row = group[group['close'] > open_price * 1.20].head(1)
                    if not breakout_row.empty:
                        ts = breakout_row.iloc[0]['timestamp']
                        winners.append({
                            'token': token,
                            'symbol': group.iloc[0].get('tradingsymbol', str(token)), # Might need mapping
                            'gain': gain,
                            'breakout_time': ts,
                            'breakout_price': breakout_row.iloc[0]['close']
                        })
        return winners

    def analyze(self):
        spot_files = glob.glob(f"{self.data_dir}/*_nifty50_intraday.csv")
        results = []
        
        print(f"Scanning {len(spot_files)} days for winners...")
        
        for f in spot_files:
            date_str = os.path.basename(f).split("_")[0]
            
            # 1. Find Winners
            winners = self.find_option_winners(date_str)
            if not winners:
                continue
                
            # 2. Load Spot Data
            spot_df = self.load_spot_data(date_str)
            if spot_df is None: continue
            
            # 3. Correlate
            for w in winners: # Analyze ALL winners
                ts = w['breakout_time']
                opt_sym = w['symbol']
                
                # Heuristic: Take first 4-5 chars or split numbers
                import re
                match = re.match(r"([A-Z]+)", opt_sym)
                spot_sym = match.group(1) if match else "UNKNOWN"
                    
                # Find row
                spot_row = spot_df[(spot_df['timestamp'] == ts) & (spot_df['symbol'] == spot_sym)]
                
                decision = "UNKNOWN"
                reason = "No Data"
                rvol_val = 0.0
                loc_val = "Mid"
                close_price = 0.0
                
                if not spot_row.empty:
                    row = spot_row.iloc[0]
                    rvol_val = row['RVOL']
                    close_price = row['close']
                    
                    # Check Band Location
                    if row['close'] > row['Upper']: loc_val = "AboveUpper"
                    elif row['close'] < row['Lower']: loc_val = "BelowLower"
                    elif row['close'] > row['SMA20']: loc_val = "UpperHalf"
                    else: loc_val = "LowerHalf"
                    
                    # Brain Logic Simulation (Current Strict Rules)
                    reasons = []
                    if rvol_val < 2.5: # Current Strict Threshold
                        reasons.append(f"Low Vol (RVOL {rvol_val:.1f} < 2.5)")
                    
                    if loc_val not in ["AboveUpper", "BelowLower"]:
                        reasons.append(f"No Breakout ({loc_val})")
                        
                    if not reasons:
                        decision = "POSSIBLE"
                        reason = "Criteria Met"
                    else:
                        decision = "REJECT"
                        reason = " + ".join(reasons)
                else:
                    decision = "No Spot Data"

                results.append({
                    'Date': date_str,
                    'Option': opt_sym,
                    'Gain_Pct': w['gain'] * 100,
                    'Time': ts.strftime('%H:%M'),
                    'Spot_RVOL': rvol_val,
                    'Spot_Loc': loc_val,
                    'Decision': decision,
                    'Reason': reason
                })

        # Save to CSV
        if results:
            df_res = pd.DataFrame(results)
            df_res.sort_values(['Date', 'Time'], inplace=True)
            df_res.to_csv("winners_analysis_38.csv", index=False)
            print(f"\n✅ Analysis Complete. Saved {len(df_res)} rows to 'winners_analysis_38.csv'.")
            print(df_res.head(10).to_string(index=False))
        else:
            print("No winners found to analyze.")

if __name__ == "__main__":
    wf = WinnerForensics()
    wf.analyze()
