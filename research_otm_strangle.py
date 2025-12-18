import pandas as pd
import numpy as np
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

def research_otm_strangle():
    print("🎓 University Study: ATM Straddle vs OTM Strangle")
    print("="*60)
    
    top_5 = ["ADANIENT", "INDUSINDBK", "INFY", "BEL", "TATASTEEL"]
    data_dir = "ai_option_brain/results"
    
    results = []
    
    for symbol in top_5:
        file_path = f"{data_dir}/{symbol}_backtest.csv"
        if not os.path.exists(file_path): continue
        
        print(f"🔬 Analyzing {symbol}...")
        df = pd.read_csv(file_path)
        total_rows = len(df)
        i = 0
        
        while i < total_rows - 2000:
            row = df.iloc[i]
            
            if row['signal'] == 1:
                entry_price = row['close']
                entry_iv = row['market_iv_proxy'] / 100
                r = 0.07
                t_expiry = 7/365
                
                # 1. ATM Straddle (Baseline)
                atm_ce = black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "call")
                atm_pe = black_scholes(entry_price, entry_price, t_expiry, r, entry_iv, "put")
                atm_cost = atm_ce + atm_pe
                
                # 2. OTM Strangle (1% OTM)
                otm_call_k = entry_price * 1.01
                otm_put_k = entry_price * 0.99
                
                otm_ce = black_scholes(entry_price, otm_call_k, t_expiry, r, entry_iv, "call")
                otm_pe = black_scholes(entry_price, otm_put_k, t_expiry, r, entry_iv, "put")
                otm_cost = otm_ce + otm_pe
                
                # Simulation
                atm_pnl = 0
                otm_pnl = 0
                
                # ATM State
                atm_hwm = 0
                atm_trailing = False
                atm_exit = False
                
                # OTM State
                otm_hwm = 0
                otm_trailing = False
                otm_exit = False
                
                for j in range(1, 1875): # 5 Days
                    current_idx = i + j
                    if current_idx >= total_rows: break
                    
                    curr_row = df.iloc[current_idx]
                    curr_price = curr_row['close']
                    curr_iv = curr_row['market_iv_proxy'] / 100
                    t_remaining = max(0.0001, t_expiry - (j / (375*365)))
                    
                    # Update ATM
                    if not atm_exit:
                        curr_atm = black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "call") + \
                                   black_scholes(curr_price, entry_price, t_remaining, r, curr_iv, "put")
                        atm_pct = (curr_atm - atm_cost) / atm_cost
                        
                        if atm_pct > atm_hwm: atm_hwm = atm_pct
                        if atm_pct >= 0.20: atm_trailing = True
                        
                        if atm_trailing and atm_pct <= (atm_hwm - 0.10):
                            atm_pnl = atm_pct; atm_exit = True
                        elif atm_pct <= -0.15:
                            atm_pnl = -0.15; atm_exit = True
                            
                    # Update OTM
                    if not otm_exit:
                        curr_otm = black_scholes(curr_price, otm_call_k, t_remaining, r, curr_iv, "call") + \
                                   black_scholes(curr_price, otm_put_k, t_remaining, r, curr_iv, "put")
                        otm_pct = (curr_otm - otm_cost) / otm_cost
                        
                        if otm_pct > otm_hwm: otm_hwm = otm_pct
                        if otm_pct >= 0.25: otm_trailing = True # Higher target for OTM
                        
                        if otm_trailing and otm_pct <= (otm_hwm - 0.10):
                            otm_pnl = otm_pct; otm_exit = True
                        elif otm_pct <= -0.20: # Wider stop for OTM
                            otm_pnl = -0.20; otm_exit = True
                            
                    if atm_exit and otm_exit: break
                
                # Force Close
                if not atm_exit: atm_pnl = atm_pct
                if not otm_exit: otm_pnl = otm_pct
                
                results.append({
                    "Symbol": symbol,
                    "ATM ROI": atm_pnl * 100,
                    "OTM ROI": otm_pnl * 100,
                    "ATM Cost": atm_cost,
                    "OTM Cost": otm_cost
                })
                
                i += 1875
            else:
                i += 1

    # Analysis
    res_df = pd.DataFrame(results)
    print("-" * 80)
    print(f"{'Metric':<20} | {'ATM Straddle':<15} | {'OTM Strangle':<15}")
    print("-" * 80)
    
    print(f"{'Avg Cost (Points)':<20} | {res_df['ATM Cost'].mean():<15.2f} | {res_df['OTM Cost'].mean():<15.2f}")
    print(f"{'Avg ROI':<20} | {res_df['ATM ROI'].mean():<15.1f}% | {res_df['OTM ROI'].mean():<15.1f}%")
    print(f"{'Win Rate':<20} | {len(res_df[res_df['ATM ROI']>0])/len(res_df)*100:<15.1f}% | {len(res_df[res_df['OTM ROI']>0])/len(res_df)*100:<15.1f}%")
    print(f"{'Total ROI (Sim)':<20} | {res_df['ATM ROI'].sum():<15.0f}% | {res_df['OTM ROI'].sum():<15.0f}%")
    
    print("-" * 80)
    cost_reduction = (1 - res_df['OTM Cost'].mean() / res_df['ATM Cost'].mean()) * 100
    print(f"💡 OTM Strangle is {cost_reduction:.1f}% cheaper than ATM Straddle.")

if __name__ == "__main__":
    research_otm_strangle()
