
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def calculate_atr(df, period=14):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['atr'] = df['tr'].rolling(period).mean()
    return df['atr']

def calculate_bollinger_bandwidth(df, period=20, std_dev=2):
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    bandwidth = (upper - lower) / sma
    return bandwidth, upper, lower, sma

def run_v10_simulation():
    print(f"\n🚀 STARTING v10.0 SIMULATION (Risk Geometry)")
    
    days = ['2025-12-24', '2025-12-26']
    
    # Use Focus List for Speed/Relevance
    FOCUS_LIST = [
        'RVNL', 'ADANIENT', 'ADANIPORTS', 'BEL', 'HAL', 
        'TATASTEEL', 'VEDL', 'DLF', 'TRENT', 'ZOMATO',
        'BHEL', 'RECLTD', 'PFC', 'CANBK', 'SBIN', 'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'
    ]
        
    # Stitch Data for Continuity (Solve Warmup Issue)
    print(f"🔄 Stitching Data: {days}...")
    full_market_data = {}
    
    for date_str in days:
        try:
            file_path = f"daily_data/{date_str}_spot_full.csv"
            if not os.path.exists(file_path): continue
            
            daily_df = pd.read_csv(file_path)
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            
            # Group by Symbol
            for sym in FOCUS_LIST:
                if sym not in full_market_data: full_market_data[sym] = []
                sym_day_df = daily_df[daily_df['symbol'] == sym]
                full_market_data[sym].append(sym_day_df)
        except: pass
        
    trades = []
    
    # Iterate Focus List
    for sym in FOCUS_LIST:
        if sym not in full_market_data or not full_market_data[sym]: continue
        
        # Concat and Sort
        s_df = pd.concat(full_market_data[sym]).set_index('date').sort_index()
        if len(s_df) < 50: continue
        
        # Resample to 5min
        df = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        # Technicals (Now continuous across days)
        df['atr'] = calculate_atr(df)
        df['bw'], df['upper'], df['lower'], df['sma20'] = calculate_bollinger_bandwidth(df)
        df['sma50'] = df['close'].rolling(50).mean()
        
        # Volume
        df['vol_sma'] = df['volume'].rolling(20).mean()
        df['rvol'] = df['volume'] / df['vol_sma']
        
        # Define Analysis Window (Only trade Dec 26, using Dec 24 as context)
        # Actually trade both days to see full picture
        
        in_trade = False
        entry_price = 0
        entry_time = None
        stop_loss = 0
        strategy = ""
        
        for i in range(50, len(df)):
            curr = df.iloc[i]
            now = curr.name # DateTime Index
            
            # Skip Market Close/Pre Market (Only trade 9:15-15:30)
            if now.time() < datetime.strptime("09:15", "%H:%M").time() or now.time() > datetime.strptime("15:30", "%H:%M").time():
                in_trade = False # Force close eod
                continue

            if not in_trade:
                # 1. LOGIC CHECKS
                is_green = curr['close'] > curr['open']
                is_structure = curr['close'] > curr['sma50']
                
                # Squeeze Logic
                bw = curr['bw']
                rvol = curr['rvol']
                
                detected_strategy = None
                
                # A. SNIPER
                if bw < 0.15 and rvol > 1.5 and is_green and is_structure:
                    detected_strategy = "SNIPER"
                    target_delta = 0.30
                    
                # B. GAMMA
                elif bw < 0.20 and rvol > 1.5 and is_green and is_structure:
                    detected_strategy = "GAMMA"
                    target_delta = 0.55
                
                if detected_strategy:
                    in_trade = True
                    entry_price = curr['close']
                    entry_time = now
                    strategy = detected_strategy
                    delta = target_delta
                    
                    # --- RISK GEOMETRY (v10.0) ---
                    atr_val = curr['atr']
                    # Stop = Entry - 2 * ATR
                    stop_loss = entry_price - (2.0 * atr_val)
                    
                    print(f"  Entry {sym} [{strategy}] @ {entry_price:.2f} | Time: {entry_time}")
                    
            else:
                # MANAGE TRADE
                curr_price = curr['close']
                time_in_trade = (now - entry_time).total_seconds() / 60
                
                # PnL Calculation (Stock)
                stock_pnl_pct = (curr_price - entry_price) / entry_price
                
                # --- v10.0 EXIT LOGIC ---
                
                exit_reason = None
                
                # 1. ATR Stop Loss
                if curr_price < stop_loss:
                    exit_reason = "ATR Stop"
                
                # 2. Time Stop (The Kill Switch)
                # If > 30 mins and Stock PnL < 0.3% (Stagnant)
                elif time_in_trade > 30 and stock_pnl_pct < 0.003: 
                    exit_reason = "Time Decay Kill"
                    
                # 3. Profit Taking (End of Day or Trail)
                # Simple Trail: If Stock > 2% move, move SL to Breakeven
                elif stock_pnl_pct > 0.02:
                    stop_loss = max(stop_loss, entry_price)
                    
                # EOD Exit
                if i == len(df) - 1 and not exit_reason:
                    exit_reason = "EOD"
                    
                if exit_reason:
                    trades.append({
                        'Symbol': sym,
                        'Strategy': strategy,
                        'Entry': entry_price,
                        'Exit': curr_price,
                        'Stock_ROI': stock_pnl_pct,
                        'Reason': exit_reason,
                        'Time_Mins': time_in_trade,
                        'Date': now.date() 
                    })
                    in_trade = False

    # Validation Report
    res_df = pd.DataFrame(trades)
    if res_df.empty:
        print("No Trades Found.")
        return

    print(f"\n📊 RESULTS: v10.0 Stimulation")
    print(f"Total Trades: {len(res_df)}")
    
    # Group by Strategy
    print("\n--- Strategy Performance (Stock ROI) ---")
    print(res_df.groupby('Strategy')['Stock_ROI'].describe())
    
    # Reason Breakdown
    print("\n--- Exit Reasons ---")
    print(res_df['Reason'].value_counts())
    
    # Winners (Stock ROI > 0.5%)
    winners = res_df[res_df['Stock_ROI'] > 0.005]
    print(f"\n✅ True Winners (>0.5% Stock Move): {len(winners)}")
    
    # Time Kills
    kills = res_df[res_df['Reason'] == 'Time Decay Kill']
    print(f"💀 Time Kills (Saved Capital): {len(kills)}")
    
    # Calculate Hypothetical Option PnL
    # Sniper: Stock * 25 (Delta 0.3 OTM Leverage approx)
    # Gamma: Stock * 15 (Delta 0.55 ATM Leverage approx)
    res_df['Est_Option_ROI'] = res_df.apply(lambda x: x['Stock_ROI'] * 25 if x['Strategy'] == 'SNIPER' else x['Stock_ROI'] * 15, axis=1)
    
    print("\n--- Estimated Option ROI (Avg) ---")
    print(res_df.groupby('Strategy')['Est_Option_ROI'].mean())


if __name__ == "__main__":
    run_v10_simulation()
