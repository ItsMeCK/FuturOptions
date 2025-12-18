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

class BreakoutBacktester:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        self.fetcher = ZerodhaDataFetcher(self.api_key, self.access_token)
        self.alpha_list = [
            "ADANIENT", "INDUSINDBK", "INFY", "BEL", "TATASTEEL",
            "BAJAJFINSV", "HINDUNILVR", "HINDALCO", "MARUTI", "BHARTIARTL"
        ]
        
    def calculate_pivots(self, high, low, close):
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        return r1, s1

    def run_backtest(self, days=30):
        logging.info(f"🚀 Starting Backtest for last {days} days...")
        
        results = []
        
        for symbol in self.alpha_list:
            logging.info(f"Analyzing {symbol}...")
            try:
                # 1. Fetch Daily Data (for Pivots)
                token = self.fetcher.get_instrument_token(symbol)
                daily_df = self.fetcher.fetch_latest_data(token, days=days+5, interval="day")
                
                if daily_df.empty:
                    logging.warning(f"No daily data for {symbol}")
                    continue
                    
                # Set Date as Index
                daily_df['date'] = pd.to_datetime(daily_df['date'])
                daily_df.set_index('date', inplace=True)
                
                # We need to iterate day by day to simulate "Live" trading
                # Get list of trading dates from daily_df
                trading_dates = daily_df.index.date
                
                # We start from index 1 because we need prev day for pivot
                for i in range(1, len(trading_dates)):
                    curr_date = trading_dates[i]
                    prev_date = trading_dates[i-1]
                    
                    # Skip if current date is today (incomplete)
                    if curr_date == datetime.now().date():
                        continue
                        
                    # Get Prev Day Data
                    prev_day = daily_df.loc[daily_df.index.date == prev_date].iloc[0]
                    r1, s1 = self.calculate_pivots(prev_day['high'], prev_day['low'], prev_day['close'])
                    
                    # Get 5-Day High (Current Logic)
                    # Window of 5 days ending at prev_date
                    five_day_window = daily_df.loc[daily_df.index.date <= prev_date].tail(5)
                    five_day_high = five_day_window['high'].max()
                    five_day_low = five_day_window['low'].min()
                    
                    # Fetch Intraday Data for Current Date
                    # We need start and end datetime for this specific day
                    from_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=9, minutes=15)
                    to_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=15, minutes=30)
                    
                    # Use kite.historical_data directly for precise range
                    intraday_data = self.fetcher.kite.historical_data(token, from_date, to_date, "5minute")
                    intra_df = pd.DataFrame(intraday_data)
                    
                    if intra_df.empty:
                        continue
                        
                    # Simulate Strategy: R1/S1 Breakout
                    self.simulate_day(symbol, curr_date, intra_df, r1, s1, "Pivot_R1_S1", results)
                    
                    # Simulate Strategy: 5-Day High Breakout
                    self.simulate_day(symbol, curr_date, intra_df, five_day_high, five_day_low, "5_Day_High", results)
                    
            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")
                
        # Analyze Results
        self.print_summary(results)

    def simulate_day(self, symbol, date, df, upper_level, lower_level, strategy_name, results):
        entry_price = 0
        exit_price = 0
        position = None # 'LONG' or 'SHORT'
        
        for index, row in df.iterrows():
            # Check Entry
            if position is None:
                # Long Entry
                if row['close'] > upper_level:
                    position = 'LONG'
                    entry_price = row['close']
                    # logging.info(f"[{strategy_name}] {symbol} {date} BUY at {entry_price} (Level: {upper_level})")
                
                # Short Entry
                elif row['close'] < lower_level:
                    position = 'SHORT'
                    entry_price = row['close']
                    # logging.info(f"[{strategy_name}] {symbol} {date} SELL at {entry_price} (Level: {lower_level})")
            
            # Check Exit (Stop Loss / Target) - Simplified: Exit at End of Day
            # In a real backtest, we'd check SL/TP every candle. 
            # For "Aggressiveness" check, let's just see if it ends green or red.
            
        # End of Day Exit
        if position:
            exit_price = df.iloc[-1]['close']
            pnl = 0
            if position == 'LONG':
                pnl = exit_price - entry_price
            else:
                pnl = entry_price - exit_price
            
            pnl_pct = (pnl / entry_price) * 100
            
            results.append({
                "Strategy": strategy_name,
                "Symbol": symbol,
                "Date": date,
                "Type": position,
                "Entry": entry_price,
                "Exit": exit_price,
                "PnL": pnl,
                "PnL_Pct": pnl_pct
            })

    def print_summary(self, results):
        df = pd.DataFrame(results)
        if df.empty:
            print("No trades generated.")
            return

        print("\n" + "="*50)
        print("BACKTEST RESULTS SUMMARY")
        print("="*50)
        
        for strategy in df['Strategy'].unique():
            strat_df = df[df['Strategy'] == strategy]
            total_trades = len(strat_df)
            wins = len(strat_df[strat_df['PnL'] > 0])
            losses = len(strat_df[strat_df['PnL'] <= 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_pnl = strat_df['PnL_Pct'].mean()
            total_pnl_points = strat_df['PnL'].sum()
            
            print(f"\nStrategy: {strategy}")
            print(f"Total Trades: {total_trades}")
            print(f"Win Rate: {win_rate:.1f}% ({wins} W / {losses} L)")
            print(f"Avg PnL per Trade: {avg_pnl:.2f}%")
            print(f"Total Points Captured: {total_pnl_points:.2f}")

if __name__ == "__main__":
    tester = BreakoutBacktester()
    tester.run_backtest(days=14) # Test last 2 weeks
