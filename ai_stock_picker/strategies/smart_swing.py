import pandas as pd
import numpy as np

class SmartSwingStrategy:
    def __init__(self, df):
        self.df = df

    def generate_signals(self):
        """
        Generates Buy/Sell signals based on the strategy logic.
        Adds 'Signal' column: 1 (Buy), -1 (Sell), 0 (Hold).
        """
        self.df['Signal'] = 0
        self.df['Reason'] = ""

        # Iterate through the dataframe (skipping first 200 rows for MA calculation)
        # Note: In a real backtest, we would step through time. 
        # Here we vectorize where possible or iterate for complex logic.
        
        for i in range(200, len(self.df)):
            current_row = self.df.iloc[i]
            prev_row = self.df.iloc[i-1]
            
            # --- ENTRY LOGIC ---
            # 1. Pullback Setup: Price > 200 SMA (Long term uptrend) AND RSI < 40 (Oversold/Pullback)
            is_uptrend = current_row['Close'] > current_row['SMA_200']
            is_pullback = current_row['RSI'] < 40
            
            # 2. RSI Divergence (Simplified): Price Low < Prev Low BUT RSI > Prev RSI
            # (This is hard to code perfectly in a simple loop without looking back further, 
            # so we use a proxy: RSI crossing above 30 from below)
            rsi_cross_up = prev_row['RSI'] < 30 and current_row['RSI'] > 30
            
            # 3. Bollinger Band Squeeze/Bounce: Price touches Lower Band and starts rising
            bb_bounce = prev_row['Close'] < prev_row['BB_Low'] and current_row['Close'] > current_row['BB_Low']

            if is_uptrend and (is_pullback or rsi_cross_up or bb_bounce):
                self.df.at[self.df.index[i], 'Signal'] = 1
                self.df.at[self.df.index[i], 'Reason'] = "Buy: Uptrend + Pullback/Bounce"

            # --- EXIT LOGIC ---
            # 1. Profit Taking: RSI > 75 or Price > Upper Band
            is_overbought = current_row['RSI'] > 75
            hit_upper_band = current_row['Close'] > current_row['BB_High']
            
            if is_overbought or hit_upper_band:
                 self.df.at[self.df.index[i], 'Signal'] = -1
                 self.df.at[self.df.index[i], 'Reason'] = "Sell: Overbought/Upper Band"

        return self.df

    def run_backtest(self, initial_capital=100000):
        """
        Simple vector/loop backtest to estimate performance.
        """
        capital = initial_capital
        position = 0 # 0 or 1 (holding)
        entry_price = 0
        trades = []
        
        df = self.generate_signals()
        
        for i in range(len(df)):
            row = df.iloc[i]
            price = row['Close']
            signal = row['Signal']
            date = df.index[i]
            
            # Check Stop Loss / Trailing Stop if holding
            if position > 0:
                # Stop Loss: -8%
                if price < entry_price * 0.92:
                    position = 0
                    capital = capital * (price / entry_price)
                    trades.append({'Date': date, 'Type': 'Sell (SL)', 'Price': price, 'Capital': capital})
                    continue
                
                # Exit Signal
                if signal == -1:
                    position = 0
                    capital = capital * (price / entry_price)
                    trades.append({'Date': date, 'Type': 'Sell (Signal)', 'Price': price, 'Capital': capital})
                    continue

            # Entry Signal
            if position == 0 and signal == 1:
                position = 1
                entry_price = price
                trades.append({'Date': date, 'Type': 'Buy', 'Price': price, 'Capital': capital})
        
        # Final value
        if position > 0:
            capital = capital * (df.iloc[-1]['Close'] / entry_price)
            
        return capital, trades, df
