import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Env
load_dotenv()

class VolumeEfficacyResearcher:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        self.fetcher = ZerodhaDataFetcher(self.api_key, self.access_token)
        try:
            df = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
            self.alpha_list = df['Symbol'].tolist()
            logging.info(f"Loaded {len(self.alpha_list)} stocks from Nifty 50 Leaderboard.")
        except Exception as e:
            logging.error(f"Error loading Nifty 50 list: {e}")
            self.alpha_list = []
        
    def calculate_pivots(self, high, low, close):
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        return r1, s1

    def run_study(self, days=14):
        logging.info(f"🔬 Starting Volume Efficacy Study for last {days} days...")
        
        study_data = []
        
        for symbol in self.alpha_list:
            logging.info(f"Analyzing {symbol}...")
            try:
                # 1. Fetch Daily Data (for Pivots)
                token = self.fetcher.get_instrument_token(symbol)
                daily_df = self.fetcher.fetch_latest_data(token, days=days+5, interval="day")
                
                if daily_df.empty:
                    continue
                    
                daily_df['date'] = pd.to_datetime(daily_df['date'])
                daily_df.set_index('date', inplace=True)
                
                trading_dates = daily_df.index.date
                
                for i in range(1, len(trading_dates)):
                    curr_date = trading_dates[i]
                    prev_date = trading_dates[i-1]
                    
                    if curr_date == datetime.now().date():
                        continue
                        
                    # Get Pivots
                    prev_day = daily_df.loc[daily_df.index.date == prev_date].iloc[0]
                    r1, s1 = self.calculate_pivots(prev_day['high'], prev_day['low'], prev_day['close'])
                    
                    # Fetch Intraday Data
                    from_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=9, minutes=15)
                    to_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=15, minutes=30)
                    
                    intraday_data = self.fetcher.kite.historical_data(token, from_date, to_date, "5minute")
                    intra_df = pd.DataFrame(intraday_data)
                    
                    if intra_df.empty:
                        continue
                        
                    # Calculate RVOL
                    # 1. Calculate Volume SMA (20 period)
                    intra_df['vol_sma'] = intra_df['volume'].rolling(window=20).mean()
                    intra_df['rvol'] = intra_df['volume'] / intra_df['vol_sma']
                    
                    # Analyze Breakouts
                    self.analyze_day(symbol, curr_date, intra_df, r1, s1, study_data)
                    
            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")
                
        # Save Results
        results_df = pd.DataFrame(study_data)
        results_df.to_csv("volume_efficacy_study.csv", index=False)
        self.print_analysis(results_df)

    def analyze_day(self, symbol, date, df, r1, s1, study_data):
        triggered = False
        
        for i in range(20, len(df)): # Start after SMA window
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Check Long Breakout (First trigger only per day for simplicity)
            if not triggered and prev_row['close'] <= r1 and row['close'] > r1:
                self.record_trade(symbol, date, df, i, 'LONG', row['rvol'], study_data)
                triggered = True
                
            # Check Short Breakdown
            elif not triggered and prev_row['close'] >= s1 and row['close'] < s1:
                self.record_trade(symbol, date, df, i, 'SHORT', row['rvol'], study_data)
                triggered = True

    def record_trade(self, symbol, date, df, index, type, rvol, study_data):
        entry_price = df.iloc[index]['close']
        
        # Look forward 6 candles (30 mins)
        future_window = df.iloc[index+1 : index+7]
        
        if future_window.empty:
            return
            
        if type == 'LONG':
            max_price = future_window['high'].max()
            end_price = future_window.iloc[-1]['close']
            max_gain = (max_price - entry_price) / entry_price * 100
            final_pnl = (end_price - entry_price) / entry_price * 100
        else:
            min_price = future_window['low'].min()
            end_price = future_window.iloc[-1]['close']
            max_gain = (entry_price - min_price) / entry_price * 100
            final_pnl = (entry_price - end_price) / entry_price * 100
            
        is_win = final_pnl > 0
        
        study_data.append({
            "Symbol": symbol,
            "Date": date,
            "Time": df.iloc[index]['date'],
            "Type": type,
            "RVOL": rvol,
            "Max_Gain_30m": max_gain,
            "Final_PnL_30m": final_pnl,
            "Is_Win": is_win
        })

    def print_analysis(self, df):
        if df.empty:
            print("No data to analyze.")
            return
            
        print("\n" + "="*50)
        print("📊 VOLUME EFFICACY STUDY RESULTS")
        print("="*50)
        
        # Binning
        bins = [0, 1.0, 1.5, 2.0, 5.0, 100]
        labels = ["Very Low (<1.0)", "Low (1.0-1.5)", "Medium (1.5-2.0)", "High (2.0-5.0)", "Extreme (>5.0)"]
        
        df['Vol_Category'] = pd.cut(df['RVOL'], bins=bins, labels=labels)
        
        summary = df.groupby('Vol_Category').agg(
            Trades=('Is_Win', 'count'),
            Win_Rate=('Is_Win', 'mean'),
            Avg_PnL=('Final_PnL_30m', 'mean')
        )
        
        # Format
        summary['Win_Rate'] = (summary['Win_Rate'] * 100).map('{:.1f}%'.format)
        summary['Avg_PnL'] = summary['Avg_PnL'].map('{:.2f}%'.format)
        
        print(summary)
        print("\n" + "="*50)

if __name__ == "__main__":
    researcher = VolumeEfficacyResearcher()
    researcher.run_study(days=14)
