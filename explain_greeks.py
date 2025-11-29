import numpy as np
import scipy.stats as si

def black_scholes_greeks(S, K, T, r, sigma, option_type="call"):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == "call":
        price = S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0)
        delta = si.norm.cdf(d1, 0.0, 1.0)
    if option_type == "put":
        price = K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0)
        delta = si.norm.cdf(d1, 0.0, 1.0) - 1
        
    return price, delta

def explain_convexity():
    print("🎓 Option Greeks Class: Why Straddles Make Money")
    print("="*60)
    
    S0 = 1000 # Start Price
    K = 1000  # Strike
    T = 7/365 # 7 Days
    r = 0.07
    sigma = 0.20 # 20% IV
    
    ce_price, ce_delta = black_scholes_greeks(S0, K, T, r, sigma, "call")
    pe_price, pe_delta = black_scholes_greeks(S0, K, T, r, sigma, "put")
    
    print(f"1️⃣ START (ATM): Price {S0}")
    print(f"   CE: ₹{ce_price:.2f} (Delta: {ce_delta:.2f})")
    print(f"   PE: ₹{pe_price:.2f} (Delta: {pe_delta:.2f})")
    print(f"   Total Cost: ₹{ce_price + pe_price:.2f}")
    print("-" * 60)
    
    # Move Price UP by 2% (₹20)
    S_new = 1020
    
    ce_new, ce_new_delta = black_scholes_greeks(S_new, K, T, r, sigma, "call")
    pe_new, pe_new_delta = black_scholes_greeks(S_new, K, T, r, sigma, "put")
    
    print(f"2️⃣ MOVE UP (2%): Price {S_new}")
    print(f"   CE: ₹{ce_new:.2f} (New Delta: {ce_new_delta:.2f}) 🚀 GAINED SPEED!")
    print(f"   PE: ₹{pe_new:.2f} (New Delta: {pe_new_delta:.2f}) 🐢 SLOWED DOWN!")
    print("-" * 60)
    
    ce_profit = ce_new - ce_price
    pe_loss = pe_new - pe_price
    net_pnl = ce_profit + pe_loss
    
    print(f"📊 The Math:")
    print(f"   CE Profit: +₹{ce_profit:.2f}")
    print(f"   PE Loss:   -₹{abs(pe_loss):.2f}")
    print(f"   NET P&L:   +₹{net_pnl:.2f} ✅")
    print("-" * 60)
    print("💡 WHY?")
    print("   As price goes UP:")
    print("   1. CE becomes ITM -> Delta goes to 1.0 (Moves dollar for dollar)")
    print("   2. PE becomes OTM -> Delta goes to 0.0 (Stops losing value)")
    print("   This 'Convexity' (Gamma) is why the Winner runs faster than the Loser walks.")

if __name__ == "__main__":
    explain_convexity()
