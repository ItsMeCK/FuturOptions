import pandas as pd
import numpy as np

import glob
import os

def calculate_roi():
    # Constants
    CAPITAL = 30000 
    TARGET_CONTRACT_VALUE = 750000 # NSE Standard approx
    
    # Dynamic Exit Rules
    TAKE_PROFIT_PCT = 0.30  # Exit if Premium gains 30%
    STOP_LOSS_PCT = -0.15   # Exit if Premium loses 15%
    
    results_dir = "ai_option_brain/results"
    leaderboard = []
    all_trades_log = []
    
    print(f"💰 Generatng Nifty 50 Leaderboard (Stress Tested)...")
    print(f"   Capital: ₹{CAPITAL} (+SIP)")
    print("="*60)
    
    # Scan for all backtest results
    files = glob.glob(f"{results_dir}/*_backtest.csv")
    print(f"   Found {len(files)} backtest files.")
    
    for file_path in files:
        filename = os.path.basename(file_path)
        symbol = filename.replace("_backtest.csv", "")
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"⚠️ Error loading {symbol}: {e}")
            continue
            
        # Estimate Lot Size
        # Use the first close price to estimate lot size
        if df.empty: continue
        avg_price = df['close'].mean()
        lot = int(TARGET_CONTRACT_VALUE / avg_price)
        
        # We need to simulate the path
        trades = []
        i = 0
        total_rows = len(df)
        
        while i < total_rows - 2000: # Buffer for lookahead
            row = df.iloc[i]
            
            # Entry Signal
            if row['signal'] == 1:
                entry_price = row['close']
                entry_iv = row['market_iv_proxy'] / 100
                entry_time = i
                
                # Black-Scholes Model
                def black_scholes(S, K, T, r, sigma, option_type="call"):
                    import scipy.stats as si
                    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
                    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
                    if option_type == "call":
                        return (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
                    if option_type == "put":
                        return (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))
                        
                # Entry Price Calculation (Exact BS)
                r = 0.07 # Risk Free Rate
                t_expiry = 7/365 # 7 Days to expiry (Avg)
                premium_paid = black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "call") + \
                               black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "put")
                
                # Capital Injection Logic (User Request)
                # Start 30k, +5k every month, Max 50k.
                month_idx = int(entry_time / 11250)
                current_capital = min(50000, CAPITAL + (month_idx * 5000))
                
                # Cost Check
                total_cost = premium_paid * lot
                if total_cost > current_capital:
                    i += 1
                    continue
                
                # Trade Loop (Look ahead minute by minute)
                exit_pnl = 0
                held_minutes = 0
                
                for j in range(1, 1875): # Max 5 days
                    current_idx = i + j
                    if current_idx >= total_rows: break
                    
                    curr_row = df.iloc[current_idx]
                    curr_price = curr_row['close']
                    curr_iv = curr_row['market_iv_proxy'] / 100 # Dynamic IV (Crucial for Vol Crush)
                    
                    # Current Straddle Value (Exact BS)
                    t_remaining = max(0.0001, t_expiry - (j / (375*365))) # Days remaining in years
                    
                    current_premium = black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "call") + \
                                      black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "put")
                    
                    pnl_per_share = current_premium - premium_paid
                    pnl_pct = pnl_per_share / premium_paid
                    
                    # Check Exits
                    if pnl_pct >= TAKE_PROFIT_PCT:
                        exit_pnl = pnl_per_share * lot
                        held_minutes = j
                        break # TAKE PROFIT
                    
                    if pnl_pct <= STOP_LOSS_PCT:
                        exit_pnl = pnl_per_share * lot
                        held_minutes = j
                        break # STOP LOSS
                
                # If loop finishes without exit
                if exit_pnl == 0:
                     exit_pnl = pnl_per_share * lot
                     held_minutes = 1875
                
                # Log Trade
                all_trades_log.append({
                    "Symbol": symbol,
                    "Entry Date": row['date'],
                    "Entry Price": entry_price,
                    "Exit Date": df.iloc[min(i + held_minutes, total_rows - 1)]['date'],
                    "Exit Price": df.iloc[min(i + held_minutes, total_rows - 1)]['close'],
                    "Duration (Mins)": held_minutes,
                    "Cost": total_cost,
                    "P&L (INR)": exit_pnl,
                    "ROI (%)": (exit_pnl / total_cost) * 100 if total_cost > 0 else 0
                })

                trades.append(exit_pnl)
                i += held_minutes
            else:
                i += 1
                
        # Aggregate
        num_trades = len(trades)
        if num_trades == 0: continue
        
        net_profit = sum(trades)
        roi = (net_profit / CAPITAL) * 100
        
        leaderboard.append({
            "Symbol": symbol,
            "Trades": num_trades,
            "Profit (INR)": net_profit,
            "ROI (%)": roi,
            "Win Rate": 0 # TODO: Calculate win rate
        })
        
        print(f"   ✅ {symbol}: ROI {roi:.1f}% ({num_trades} trades)")

    # Save Log
    log_df = pd.DataFrame(all_trades_log)
    log_df.to_csv("ai_option_brain/results/final_trades_log.csv", index=False)
    print(f"💾 Trade Log saved to: ai_option_brain/results/final_trades_log.csv")

    # Save Leaderboard
    lb_df = pd.DataFrame(leaderboard)
    if not lb_df.empty:
        lb_df = lb_df.sort_values("ROI (%)", ascending=False)
        lb_df.to_csv("ai_option_brain/results/nifty50_leaderboard.csv", index=False)
        print("="*60)
        print("🏆 TOP 10 PERFORMERS:")
        print(lb_df.head(10))
        print(f"💾 Leaderboard saved to: ai_option_brain/results/nifty50_leaderboard.csv")
    else:
        print("⚠️ No trades found for any stock.")

if __name__ == "__main__":
    calculate_roi()
