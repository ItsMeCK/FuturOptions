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

def research_entries():
    print("🎓 University Study: Entry Filter Optimization")
    print("="*60)
    
    # 1. Load Top 5 Stocks
    top_5 = ["ADANIENT", "INDUSINDBK", "INFY", "BEL", "TATASTEEL"]
    data_dir = "ai_option_brain/results"
    
    results = []
    
    # Define Filters to Test
    filters = {
        "Baseline (10% Edge)": lambda row: (row['predicted_rv'] > row['market_iv_proxy'] * 1.10),
        "High Edge (25%)":     lambda row: (row['predicted_rv'] > row['market_iv_proxy'] * 1.25),
        "Strong Trend (>2%)":  lambda row: (abs(row['trend_dist']) > 0.02),
        "RSI Momentum (40-60)": lambda row: (40 < row['rsi'] < 60),
        "Combo (Edge+Trend)":  lambda row: (row['predicted_rv'] > row['market_iv_proxy'] * 1.15) and (abs(row['trend_dist']) > 0.015)
    }
    
    for symbol in top_5:
        file_path = f"{data_dir}/{symbol}_backtest.csv"
        if not os.path.exists(file_path): continue
        
        print(f"🔬 Analyzing {symbol}...")
        df = pd.read_csv(file_path)
        total_rows = len(df)
        
        # We need to re-simulate based on filters
        # To save time, we will just iterate and check filters
        
        for filter_name, filter_func in filters.items():
            i = 0
            trades = 0
            wins = 0
            total_roi = 0
            
            while i < total_rows - 2000:
                row = df.iloc[i]
                
                # Check Filter
                # Note: Original signal logic was:
                # raw_signal = np.where(test_df['predicted_rv'] > (test_df['market_iv_proxy'] * 1.1), 1, ...)
                # trend_active = np.where(abs(test_df['trend_dist']) > 0.01, 1, 0)
                # signal = (raw_signal == 1) & (trend_active == 1)
                
                # We are refining the "Buy" decision.
                # So we first check if the BASE logic (Brain) even considered it a buy candidate?
                # Actually, let's apply the filter directly to the row data.
                
                is_entry = False
                try:
                    if filter_func(row):
                        is_entry = True
                except:
                    pass
                    
                if is_entry:
                    # Simulate Trade (Trailing Stop Logic)
                    entry_price = row['close']
                    entry_iv = row['market_iv_proxy'] / 100
                    r = 0.07
                    t_expiry = 7/365
                    
                    premium_paid = black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "call") + \
                                   black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "put")
                    
                    exit_pnl = 0
                    high_water_mark = 0
                    trailing_active = False
                    
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
                        
                        if pnl_pct > high_water_mark: high_water_mark = pnl_pct
                        
                        if pnl_pct >= 0.20: trailing_active = True
                        
                        if trailing_active:
                            if pnl_pct <= (high_water_mark - 0.10):
                                exit_pnl = pnl_pct; break
                        elif pnl_pct <= -0.15:
                            exit_pnl = -0.15; break
                            
                    # End of trade
                    if exit_pnl == 0: exit_pnl = pnl_pct # Time exit
                    
                    trades += 1
                    if exit_pnl > 0: wins += 1
                    total_roi += exit_pnl
                    
                    i += 1875 # Skip ahead
                else:
                    i += 1
            
            results.append({
                "Symbol": symbol,
                "Filter": filter_name,
                "Trades": trades,
                "Win Rate": (wins/trades)*100 if trades > 0 else 0,
                "Total ROI": total_roi * 100
            })

    # Aggregated Analysis
    res_df = pd.DataFrame(results)
    print("-" * 80)
    print(f"{'Filter Strategy':<25} | {'Avg Trades':<10} | {'Win Rate':<10} | {'Avg ROI':<10}")
    print("-" * 80)
    
    for filter_name in filters.keys():
        subset = res_df[res_df['Filter'] == filter_name]
        avg_trades = subset['Trades'].mean()
        avg_win = subset['Win Rate'].mean()
        avg_roi = subset['Total ROI'].mean()
        
        print(f"{filter_name:<25} | {avg_trades:>10.1f} | {avg_win:>9.1f}% | {avg_roi:>9.0f}%")
        
    print("-" * 80)

if __name__ == "__main__":
    research_entries()
