import os
import pandas as pd
import numpy as np
import scipy.stats as si
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def black_scholes(S, K, T, r, sigma, option_type="call"):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == "call":
        return (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
    if option_type == "put":
        return (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))

def validate_top20():
    print("🔬 Validating Pricing for Top 20 Stocks (Dec Expiry)...")
    print("="*80)
    
    # 1. Load Top 20
    try:
        lb_df = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
        top_20 = lb_df.head(20)['Symbol'].tolist()
    except:
        print("❌ Leaderboard not found.")
        return

    # 2. Setup Kite
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    if not api_key or not access_token:
        print("❌ API Key/Token missing.")
        return
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    
    # 3. Fetch Instruments
    print("   Fetching NFO Instruments...")
    instruments = kite.instruments("NFO")
    nse_instruments = kite.instruments("NSE")
    
    results = []
    
    # Parameters
    target_date = "2025-11-28" # Last trading day
    expiry_month = "25DEC"
    r = 0.07
    t_expiry = 27 / 365 # Approx days to Dec 25
    
    print(f"{'Symbol':<12} | {'Spot':<8} | {'Real Straddle':<15} | {'BS Price':<15} | {'Diff':<8}")
    print("-" * 80)
    
    for symbol in top_20:
        # A. Get Spot Token
        spot_token = next((i['instrument_token'] for i in nse_instruments if i['tradingsymbol'] == symbol), None)
        if not spot_token: continue
        
        # B. Get Spot Price
        from_date = f"{target_date} 15:15:00"
        to_date = f"{target_date} 15:30:00"
        spot_data = kite.historical_data(spot_token, from_date, to_date, "minute")
        if not spot_data: continue
        spot_price = spot_data[-1]['close'] # Closing price
        
        # C. Find ATM Strike
        # Step size varies (e.g. 10, 20, 50, 100). 
        # Simple heuristic: Round to nearest 0.5% or check instrument list.
        # Let's try to match exact symbol in instruments list to find valid strikes
        
        # Filter instruments for this symbol and expiry
        sym_instrs = [i for i in instruments if i['name'] == symbol and i['expiry'].strftime('%Y-%m-%d') == '2025-12-24'] # Dec expiry is usually last Thu
        # Actually expiry date might vary. Let's filter by tradingsymbol contains 25DEC
        
        # Construct expected symbol start
        # e.g. RELIANCE25DEC...
        prefix = f"{symbol}{expiry_month}"
        candidates = [i for i in instruments if i['tradingsymbol'].startswith(prefix)]
        
        if not candidates: continue
        
        # Find strike closest to spot
        # Parse strike from tradingsymbol? Or use 'strike' field if available (it is!)
        # Kite instrument dump has 'strike' field.
        
        closest_instr = min(candidates, key=lambda x: abs(x['strike'] - spot_price))
        strike = closest_instr['strike']
        
        # D. Get Option Tokens
        ce_symbol = f"{symbol}{expiry_month}{int(strike)}CE"
        pe_symbol = f"{symbol}{expiry_month}{int(strike)}PE"
        
        # Some strikes might be float? usually int for Nifty stocks
        # Check if strike has decimal
        if strike % 1 != 0:
             ce_symbol = f"{symbol}{expiry_month}{strike}CE"
             pe_symbol = f"{symbol}{expiry_month}{strike}PE"
        
        ce_token = next((i['instrument_token'] for i in candidates if i['tradingsymbol'] == ce_symbol), None)
        pe_token = next((i['instrument_token'] for i in candidates if i['tradingsymbol'] == pe_symbol), None)
        
        if not ce_token or not pe_token: continue
        
        # E. Get Option Prices
        ce_data = kite.historical_data(ce_token, from_date, to_date, "minute")
        pe_data = kite.historical_data(pe_token, from_date, to_date, "minute")
        
        if not ce_data or not pe_data: continue
        
        real_ce = ce_data[-1]['close']
        real_pe = pe_data[-1]['close']
        real_straddle = real_ce + real_pe
        
        # F. Calculate BS Price
        # We need IV. We'll use HV (20-day) as proxy for now, or just solve for IV?
        # The user wants to validate our *calculator*. Our calculator uses HV.
        # So let's calculate HV for this stock first.
        
        # Fetch 30 days of spot data for HV
        hv_from = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=40)).strftime("%Y-%m-%d")
        hv_data = kite.historical_data(spot_token, hv_from, target_date, "day")
        hv_df = pd.DataFrame(hv_data)
        hv_df['log_ret'] = np.log(hv_df['close'] / hv_df['close'].shift(1))
        hv = hv_df['log_ret'].tail(20).std() * np.sqrt(252)
        
        bs_val = black_scholes(spot_price, strike, t_expiry, r, hv, "call") + \
                 black_scholes(spot_price, strike, t_expiry, r, hv, "put")
                 
        diff = ((bs_val - real_straddle) / real_straddle) * 100
        
        print(f"{symbol:<12} | {spot_price:<8.1f} | {real_straddle:<15.1f} | {bs_val:<15.1f} | {diff:+.1f}%")
        
        import time
        time.sleep(1) # Avoid Rate Limits
        
    print("="*80)

if __name__ == "__main__":
    validate_top20()
