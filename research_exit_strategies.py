import pandas as pd
import numpy as np
import glob
import os
import scipy.stats as si

def black_scholes(S, K, T, r, sigma, option_type="call"):
    if T <= 0: return max(0, S - K) if option_type == "call" else max(0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == "call":
        return (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
    if option_type == "put":
        return (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))

def research_exits():
    print("🎓 University Study: Dynamic Exit Strategies vs Fixed 30%")
    print("="*60)
    
    # 1. Load Top 5 Stocks (The "Elite")
    top_5 = ["APOLLOHOSP", "INDUSINDBK", "ADANIENT", "TATASTEEL", "TITAN"]
    data_dir = "ai_option_brain/results"
    
    results = []
    
    for symbol in top_5:
        file_path = f"{data_dir}/{symbol}_backtest.csv"
        if not os.path.exists(file_path): continue
        
        print(f"🔬 Analyzing {symbol}...")
        df = pd.read_csv(file_path)
        
        # We need to re-simulate the path for every signal
        # Logic copied from calculate_roi.py but modified for research
        
        i = 0
        total_rows = len(df)
        
        while i < total_rows - 2000:
            row = df.iloc[i]
            
            if row['signal'] == 1:
                entry_price = row['close']
                entry_iv = row['market_iv_proxy'] / 100
                r = 0.07
                t_expiry = 7/365
                
                # Entry Premium
                premium_paid = black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "call") + \
                               black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "put")
                
                # Track Path
                max_profit_pct = 0
                max_loss_pct = 0
                
                # Strategies
                # 1. Fixed 30% (Baseline)
                pnl_fixed = 0
                
                # 2. Trailing Stop (Activate at +20%, Trail by 10%)
                pnl_trailing = 0
                high_water_mark = 0
                trailing_active = False
                
                # 3. Volatility Target (Target = 1.5 * IV)
                # e.g. IV 20% -> Target 30%. IV 40% -> Target 60%.
                pnl_vol_target = 0
                vol_target_pct = entry_iv * 1.5 
                
                # 4. Time Decay (Theta) Exit
                # If profit < 10% after 2 days, exit.
                pnl_time = 0
                
                # Simulation Loop
                exit_fixed = False
                exit_trailing = False
                exit_vol = False
                exit_time = False
                
                for j in range(1, 1875): # 5 Days
                    current_idx = i + j
                    if current_idx >= total_rows: break
                    
                    curr_row = df.iloc[current_idx]
                    curr_price = curr_row['close']
                    curr_iv = curr_row['market_iv_proxy'] / 100
                    t_remaining = max(0.0001, t_expiry - (j / (375*365)))
                    
                    curr_premium = black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "call") + \
                                   black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "put")
                                   
                    pnl_pct = (curr_premium - premium_paid) / premium_paid
                    
                    # Update Stats
                    max_profit_pct = max(max_profit_pct, pnl_pct)
                    max_loss_pct = min(max_loss_pct, pnl_pct)
                    
                    # 1. Fixed 30% / -15%
                    if not exit_fixed:
                        if pnl_pct >= 0.30: pnl_fixed = 0.30; exit_fixed = True
                        elif pnl_pct <= -0.15: pnl_fixed = -0.15; exit_fixed = True
                        
                    # 2. Trailing Stop
                    if not exit_trailing:
                        if pnl_pct > 0.20: trailing_active = True
                        
                        if trailing_active:
                            high_water_mark = max(high_water_mark, pnl_pct)
                            if pnl_pct <= (high_water_mark - 0.10): # Trail by 10%
                                pnl_trailing = pnl_pct
                                exit_trailing = True
                        elif pnl_pct <= -0.15: # Hard SL
                            pnl_trailing = -0.15
                            exit_trailing = True
                            
                    # 3. Vol Target
                    if not exit_vol:
                        if pnl_pct >= vol_target_pct: pnl_vol_target = pnl_pct; exit_vol = True
                        elif pnl_pct <= -0.15: pnl_vol_target = -0.15; exit_vol = True
                        
                    # 4. Time Exit
                    if not exit_time:
                        if j > 750 and pnl_pct < 0.10: # 2 Days (375*2)
                            pnl_time = pnl_pct; exit_time = True
                        elif pnl_pct >= 0.30: pnl_time = 0.30; exit_time = True # Still cap at 30? No let it run? Let's cap for fairness
                        elif pnl_pct <= -0.15: pnl_time = -0.15; exit_time = True
                
                # End of Loop Cleanup
                if not exit_fixed: pnl_fixed = pnl_pct
                if not exit_trailing: pnl_trailing = pnl_pct
                if not exit_vol: pnl_vol_target = pnl_pct
                if not exit_time: pnl_time = pnl_pct
                
                results.append({
                    "Symbol": symbol,
                    "Max Potential": max_profit_pct,
                    "Fixed (30%)": pnl_fixed,
                    "Trailing (10%)": pnl_trailing,
                    "Vol Target (1.5x)": pnl_vol_target,
                    "Time Exit": pnl_time
                })
                
                i += 1875 # Skip ahead
            else:
                i += 1
                
    # Analysis
    res_df = pd.DataFrame(results)
    print("-" * 60)
    print(f"📊 Analyzed {len(res_df)} Trades across Top 5 Stocks")
    print("-" * 60)
    
    print(f"{'Strategy':<20} | {'Avg Return':<10} | {'Win Rate':<10} | {'Total ROI (Sim)':<15}")
    print("-" * 60)
    
    strategies = ["Fixed (30%)", "Trailing (10%)", "Vol Target (1.5x)", "Time Exit"]
    
    for strat in strategies:
        avg_ret = res_df[strat].mean() * 100
        win_rate = len(res_df[res_df[strat] > 0]) / len(res_df) * 100
        total_roi = res_df[strat].sum() * 100 # Simple sum for comparison
        
        print(f"{strat:<20} | {avg_ret:>6.1f}%    | {win_rate:>6.1f}%    | {total_roi:>10.0f}%")
        
    print("-" * 60)
    print("💡 MFE Analysis (How much did we leave on table?)")
    avg_mfe = res_df['Max Potential'].mean() * 100
    print(f"   Average Max Potential Profit: {avg_mfe:.1f}%")
    print(f"   (We captured {((res_df['Fixed (30%)'].mean()*100) / avg_mfe)*100:.1f}% of the potential move)")

if __name__ == "__main__":
    research_exits()
