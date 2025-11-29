import numpy as np
import scipy.stats as si
import matplotlib.pyplot as plt

def black_scholes(S, K, T, r, sigma, option_type="call"):
    # S: Spot price
    # K: Strike price
    # T: Time to maturity (years)
    # r: Risk-free interest rate
    # sigma: Volatility of underlying asset
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == "call":
        option_price = (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
    if option_type == "put":
        option_price = (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))
        
    return option_price

def validate_pricing():
    print("🔬 Validating Pricing Model: Heuristic vs Black-Scholes")
    print("="*60)
    
    # Parameters
    S0 = 1000 # Entry Price
    K = 1000  # Strike (ATM)
    T_days = 7
    T = T_days / 365
    r = 0.07 # 7% Risk Free
    sigma = 0.20 # 20% IV
    
    # 1. Calculate Initial Premium (Entry)
    bs_call = black_scholes(S0, K, T, r, sigma, "call")
    bs_put = black_scholes(S0, K, T, r, sigma, "put")
    real_entry_premium = bs_call + bs_put
    
    heuristic_entry_premium = 0.8 * S0 * sigma * np.sqrt(T)
    
    print(f"🔹 Entry (ATM):")
    print(f"   Black-Scholes: {real_entry_premium:.2f}")
    print(f"   Heuristic:     {heuristic_entry_premium:.2f}")
    print(f"   Diff:          {((heuristic_entry_premium - real_entry_premium)/real_entry_premium)*100:.1f}%")
    print("-" * 60)
    
    # 2. Simulate Price Moves (0% to 5%)
    moves = np.linspace(0, 0.05, 11) # 0% to 5%
    
    print(f"{'Move':<8} | {'Price':<8} | {'Real Value':<12} | {'Heuristic':<12} | {'Error':<8}")
    print("-" * 60)
    
    for pct in moves:
        S_new = S0 * (1 + pct)
        
        # A. Real Value (BS)
        # Assume 1 day passed (T - 1/365)
        T_new = (T_days - 1) / 365
        bs_call_new = black_scholes(S_new, K, T_new, r, sigma, "call")
        bs_put_new = black_scholes(S_new, K, T_new, r, sigma, "put")
        real_value = bs_call_new + bs_put_new
        
        # B. Heuristic Value (From calculate_roi.py)
        # current_premium = intrinsic + current_time_value
        intrinsic = abs(S_new - S0)
        
        # Time Value Decay
        # entry_time_value = premium_paid
        # Decay factors: Time, Moneyness
        
        entry_time_value = heuristic_entry_premium # Use heuristic base for consistency
        
        # Time Decay
        time_decay = np.sqrt(T_new / T)
        
        # Moneyness Decay
        pct_move = abs(S_new - S0) / S0
        moneyness_decay = 1 / (1 + pct_move * 20)
        
        current_time_value = entry_time_value * time_decay * moneyness_decay
        
        heuristic_value = intrinsic + current_time_value
        
        error = ((heuristic_value - real_value) / real_value) * 100
        
        print(f"{pct*100:.1f}%     | {S_new:<8.1f} | {real_value:<12.2f} | {heuristic_value:<12.2f} | {error:+.1f}%")

    print("="*60)
    print("Interpretation:")
    print("If Error is POSITIVE (+), we are OVERESTIMATING profit (Bad).")
    print("If Error is NEGATIVE (-), we are UNDERESTIMATING profit (Conservative/Good).")

if __name__ == "__main__":
    validate_pricing()
