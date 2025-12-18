import pandas as pd
import numpy as np
import os
import scipy.stats as si
from datetime import datetime, time as dt_time

def black_scholes(S, K, T, r, sigma, option_type="call"):
    if T <= 0: return max(0, S - K) if option_type == "call" else max(0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == "call":
        return (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
    if option_type == "put":
        return (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))

def research_intraday_micro_sniper():
    print("🎓 University Study: Micro-Sniper (Intraday + OTM) Validation")
    print("="*60)
    
    # Top 5 Stocks
    top_5 = ["ADANIENT", "INDUSINDBK", "INFY", "BEL", "TATASTEEL"]
    data_dir = "ai_option_brain/results"
    
    results = []
    
    for symbol in top_5:
        file_path = f"{data_dir}/{symbol}_backtest.csv"
        if not os.path.exists(file_path): continue
        
        print(f"🔬 Analyzing {symbol}...")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        
        total_rows = len(df)
        i = 0
        
        while i < total_rows:
            row = df.iloc[i]
            
            # 1. Check Signal
            # We use the raw signal from the file (which is based on 10% edge)
            if row['signal'] == 1:
                current_time = row['date'].time()
                day_name = row['date'].day_name()
                
                # 2. Apply Micro-Sniper Timing Rules
                valid_entry = False
                
                if day_name == "Wednesday":
                    if current_time >= dt_time(14, 0): # After 2 PM
                        valid_entry = True
                elif day_name == "Thursday":
                    valid_entry = True # All day
                
                if valid_entry:
                    # 3. Simulate OTM Strangle Trade
                    entry_price = row['close']
                    entry_iv = row['market_iv_proxy'] / 100
                    r = 0.07
                    t_expiry = 7/365 # Approx
                    
                    # OTM Strikes (1% away)
                    call_strike = entry_price * 1.01
                    put_strike = entry_price * 0.99
                    
                    # Entry Premium
                    ce_price = black_scholes(entry_price, call_strike, t_expiry, r, entry_iv, "call")
                    pe_price = black_scholes(entry_price, put_strike, t_expiry, r, entry_iv, "put")
                    premium_paid = ce_price + pe_price
                    
                    # Intraday Loop (Exit by 15:20)
                    exit_pnl = 0
                    exit_reason = "Held"
                    
                    # Find index of 15:20 same day
                    # We iterate minute by minute
                    
                    for j in range(1, 375): # Max 1 day
                        current_idx = i + j
                        if current_idx >= total_rows: break
                        
                        curr_row = df.iloc[current_idx]
                        curr_time = curr_row['date'].time()
                        
                        # Check if day changed (Should not happen in intraday loop but safety)
                        if curr_row['date'].date() != row['date'].date():
                            exit_pnl = -0.50 # Forced close at bad price? Or just use last price
                            exit_reason = "EOD Force"
                            break
                        
                        # Update Price
                        curr_price = curr_row['close']
                        curr_iv = curr_row['market_iv_proxy'] / 100
                        t_remaining = max(0.0001, t_expiry - (j / (375*365)))
                        
                        curr_ce = black_scholes(curr_price, call_strike, t_remaining, r, curr_iv, "call")
                        curr_pe = black_scholes(curr_price, put_strike, t_remaining, r, curr_iv, "put")
                        curr_premium = curr_ce + curr_pe
                        
                        pnl_pct = (curr_premium - premium_paid) / premium_paid
                        
                        # Check Exits
                        if pnl_pct >= 0.25: # Target +25%
                            exit_pnl = 0.25
                            exit_reason = "Target"
                            break
                        elif pnl_pct <= -0.20: # Stop -20%
                            exit_pnl = -0.20
                            exit_reason = "Stop"
                            break
                        
                        # Time Exit (15:20)
                        if curr_time >= dt_time(15, 20):
                            exit_pnl = pnl_pct
                            exit_reason = "Time (3:20 PM)"
                            break
                    
                    results.append({
                        "Symbol": symbol,
                        "Day": day_name,
                        "Entry Time": str(current_time),
                        "Exit Reason": exit_reason,
                        "ROI": exit_pnl * 100
                    })
                    
                    # Skip to next day to avoid re-entry same day? 
                    # Or just skip the duration of trade.
                    i += j 
                else:
                    i += 1
            else:
                i += 1

    # Analysis
    res_df = pd.DataFrame(results)
    if res_df.empty:
        print("❌ No trades found matching criteria.")
        return

    print("-" * 80)
    print(f"📊 Micro-Sniper Analysis (Wed > 2PM | Thu All Day | No Overnight)")
    print("-" * 80)
    
    print(f"{'Metric':<20} | {'Value':<10}")
    print("-" * 40)
    print(f"{'Total Trades':<20} | {len(res_df)}")
    print(f"{'Win Rate':<20} | {len(res_df[res_df['ROI'] > 0]) / len(res_df) * 100:.1f}%")
    print(f"{'Avg ROI':<20} | {res_df['ROI'].mean():.1f}%")
    print("-" * 40)
    
    print("\n📋 Breakdown by Exit Reason:")
    print(res_df['Exit Reason'].value_counts())
    
    print("\n🗓️ Breakdown by Day:")
    print(res_df.groupby('Day')['ROI'].mean())

if __name__ == "__main__":
    research_intraday_micro_sniper()
