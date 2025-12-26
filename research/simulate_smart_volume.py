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

# Institutional Lot Sizes (Expanded for Nifty 50 coverage)
LOT_SIZES = {
    "RELIANCE": 250, "TCS": 175, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700,
    "SBIN": 1500, "TATAMOTORS": 1425, "ITC": 1600, "AXISBANK": 625, "LT": 300,
    "BAJFINANCE": 125, "MARUTI": 50, "KOTAKBANK": 400, "SUNPHARMA": 700,
    "TITAN": 175, "ULTRACEMCO": 100, "ASIANPAINT": 200, "BHARTIARTL": 950,
    "ADANIENT": 300, "INDUSINDBK": 500, "BEL": 5700, "TATASTEEL": 5500,
    "HINDUNILVR": 300, "HINDALCO": 1400, "BAJAJFINSV": 500, "JSWSTEEL": 675,
    "GRASIM": 475, "POWERGRID": 3600, "NTPC": 3000, "ONGC": 3850,
    "COALINDIA": 2100, "BRITANNIA": 200, "NESTLEIND": 40, "CIPLA": 650,
    "DRREDDY": 125, "APOLLOHOSP": 125, "DIVISLAB": 200, "WIPRO": 1500,
    "TECHM": 600, "LTIM": 150, "HCLTECH": 700, "HEROMOTOCO": 300,
    "EICHERMOT": 175, "M&M": 350, "BPCL": 1800, "TATACONSUM": 900
}

class SmartVolumeSimulator:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        self.fetcher = ZerodhaDataFetcher(self.api_key, self.access_token)
        try:
            df = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
            self.symbol_list = df['Symbol'].tolist()
            # self.symbol_list = ["GRASIM"]
            logging.info(f"Loaded {len(self.symbol_list)} stocks from Nifty 50 Leaderboard.")
        except Exception as e:
            logging.error(f"Error loading Nifty 50 list: {e}")
            self.symbol_list = []
            
    def calculate_pivots(self, high, low, close):
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        return r1, s1

    def run_simulation(self, days=14):
        logging.info(f"🚀 Starting Smart Volume Simulation for last {days} days...")
        
        trades = []
        
        for symbol in self.symbol_list:
            logging.info(f"Simulating {symbol}...")
            try:
                # 1. Fetch Daily Data
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
                        
                    # Pivots
                    prev_day = daily_df.loc[daily_df.index.date == prev_date].iloc[0]
                    r1, s1 = self.calculate_pivots(prev_day['high'], prev_day['low'], prev_day['close'])
                    
                    # Intraday Data
                    from_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=9, minutes=15)
                    to_date = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=15, minutes=30)
                    
                    intraday_data = self.fetcher.kite.historical_data(token, from_date, to_date, "5minute")
                    intra_df = pd.DataFrame(intraday_data)
                    
                    if intra_df.empty:
                        continue
                        
                    # Indicators
                    intra_df['vol_sma'] = intra_df['volume'].rolling(window=20).mean()
                    intra_df['rvol'] = intra_df['volume'] / intra_df['vol_sma']
                    
                    self.simulate_day(symbol, curr_date, intra_df, r1, s1, trades)
                    
            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")
                
        self.print_results(trades)

    def simulate_day(self, symbol, date, df, r1, s1, trades):
        triggered = False
        
        for i in range(20, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            if triggered:
                break # One trade per day per stock for simplicity
            
            signal = None
            entry_price = row['close']
            rvol = row['rvol']
            
            # 1. Check Breakout/Breakdown
            if prev_row['close'] <= r1 and row['close'] > r1:
                signal = 'LONG'
            elif prev_row['close'] >= s1 and row['close'] < s1:
                signal = 'SHORT'
                
            if not signal:
                continue
                
            # 2. Smart Volume Logic
            zone = "NONE"
            if rvol > 2.5:
                zone = "DANGER" # Reject
                continue
            elif rvol >= 1.5:
                zone = "GOLD" # Accept
            elif rvol >= 1.0:
                zone = "QUIET" # Accept (Assuming AI Edge Pass for simulation)
            else:
                zone = "DEAD" # Reject
                continue
                
            # 3. Execute Trade
            triggered = True
            self.manage_trade(symbol, date, df, i, signal, entry_price, rvol, zone, trades)

    def manage_trade(self, symbol, date, df, start_index, type, entry_price, rvol, zone, trades):
        lot_size = LOT_SIZES.get(symbol, 500) # Default 500 if missing
        
        # Exit Rules (Sniper Mode)
        # SL: 0.5% Spot Loss (Tight)
        # Target: 1.0% Spot Gain (Quick Profit)
        # Time Limit: 60 Minutes (12 candles)
        
        sl_pct = 0.005
        target_pct = 0.01
        time_limit_candles = 12
        
        if type == 'LONG':
            stop_loss = entry_price * (1 - sl_pct)
            target_price = entry_price * (1 + target_pct)
        else:
            stop_loss = entry_price * (1 + sl_pct)
            target_price = entry_price * (1 - target_pct)
            
        exit_price = df.iloc[-1]['close'] # Default EOD
        exit_reason = "EOD"
        
        for i in range(start_index + 1, len(df)):
            curr_price = df.iloc[i]['close']
            
            # Check Time Limit
            if i > start_index + time_limit_candles:
                exit_price = curr_price
                exit_reason = "Time Limit (60m)"
                break
            
            if type == 'LONG':
                # Check SL
                if curr_price <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL Hit"
                    break
                # Check Target
                if curr_price >= target_price:
                    exit_price = target_price
                    exit_reason = "Target Hit"
                    break
                            
            else: # SHORT
                # Check SL
                if curr_price >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL Hit"
                    break
                # Check Target
                if curr_price <= target_price:
                    exit_price = target_price
                    exit_reason = "Target Hit"
                    break
                            
        # Calculate PnL
        spot_pnl_points = 0
        if type == 'LONG':
            spot_pnl_points = exit_price - entry_price
        else:
            spot_pnl_points = entry_price - exit_price
            
        # Option PnL Approximation (Delta 0.5)
        option_pnl_points = spot_pnl_points * 0.5
        total_profit = option_pnl_points * lot_size
        
        trades.append({
            "Symbol": symbol,
            "Date": date,
            "Type": type,
            "Zone": zone,
            "RVOL": rvol,
            "Entry": entry_price,
            "Exit": exit_price,
            "Reason": exit_reason,
            "Spot_PnL": spot_pnl_points,
            "Option_PnL": option_pnl_points,
            "Total_Profit": total_profit
        })

    def print_results(self, trades):
        if not trades:
            print("No trades generated.")
            return
            
        df = pd.DataFrame(trades)
        
        print("\n" + "="*50)
        print("💰 SMART VOLUME SIMULATION RESULTS (14 Days)")
        print("="*50)
        
        total_trades = len(df)
        total_profit = df['Total_Profit'].sum()
        wins = len(df[df['Total_Profit'] > 0])
        losses = len(df[df['Total_Profit'] <= 0])
        win_rate = (wins / total_trades) * 100
        avg_profit = df['Total_Profit'].mean()
        
        print(f"Total Trades: {total_trades}")
        print(f"Total Net Profit: ₹{total_profit:,.2f}")
        print(f"Win Rate: {win_rate:.1f}% ({wins} W / {losses} L)")
        print(f"Avg Profit per Trade: ₹{avg_profit:,.2f}")
        
        print("\n--- Zone Breakdown ---")
        print(df.groupby('Zone')['Total_Profit'].agg(['count', 'sum', 'mean']))
        
        print("\n--- Top 5 Winners ---")
        print(df.nlargest(5, 'Total_Profit')[['Symbol', 'Date', 'Type', 'Total_Profit']])
        
        df.to_csv("smart_volume_simulation.csv", index=False)

if __name__ == "__main__":
    sim = SmartVolumeSimulator()
    sim.run_simulation(days=14)
