import os
import pandas as pd
import numpy as np
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def fetch_and_validate():
    print("🔬 Fetching Real Option Data (Zerodha) for Validation...")
    print("="*60)
    
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    
    if not api_key or not access_token:
        print("❌ API Key/Token missing.")
        return

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    
    # 1. Get Spot Price of Reliance on a specific date
    # Let's pick Nov 29, 2025 (Today/Yesterday)
    target_date = "2025-11-28" # Friday
    expiry_month = "25DEC" # Format: YYMMM
    
    print(f"   Target Date: {target_date}")
    print(f"   Expiry: {expiry_month}")
    
    # Fetch Spot Data to find ATM
    instruments = kite.instruments("NSE")
    rel_token = None
    for instr in instruments:
        if instr['tradingsymbol'] == 'RELIANCE':
            rel_token = instr['instrument_token']
            break
            
    if not rel_token:
        print("❌ Reliance token not found.")
        return
        
    print(f"   Reliance Token: {rel_token}")
    
    from_date = f"{target_date} 09:15:00"
    to_date = f"{target_date} 15:30:00"
    
    spot_data = kite.historical_data(rel_token, from_date, to_date, "minute")
    if not spot_data:
        print("❌ No spot data found.")
        return
        
    spot_df = pd.DataFrame(spot_data)
    spot_price = spot_df['close'].iloc[0] # Opening minute close
    print(f"   Spot Price (09:15): {spot_price}")
    
    # 2. Determine ATM Strike
    # Round to nearest 20
    strike = round(spot_price / 20) * 20
    print(f"   ATM Strike: {strike}")
    
    # 3. Find Option Tokens (CE & PE)
    print("   Fetching NFO Instruments...")
    nfo_instruments = kite.instruments("NFO")
    
    # Debug: Print first 5 Reliance options
    print("   Debug: Sample NFO Symbols:")
    samples = [i['tradingsymbol'] for i in nfo_instruments if i['name'] == 'RELIANCE'][:5]
    print(f"   {samples}")
    
    ce_symbol = f"RELIANCE{expiry_month}{strike}CE"
    pe_symbol = f"RELIANCE{expiry_month}{strike}PE"
    
    print(f"   Looking for: {ce_symbol} & {pe_symbol}")
    
    ce_token = None
    pe_token = None
    
    for instr in nfo_instruments:
        if instr['tradingsymbol'] == ce_symbol:
            ce_token = instr['instrument_token']
        if instr['tradingsymbol'] == pe_symbol:
            pe_token = instr['instrument_token']
            
    if not ce_token or not pe_token:
        print("❌ Option tokens not found. Check symbol format.")
        return
        
    print(f"   Found Tokens: CE={ce_token}, PE={pe_token}")
    
    # 4. Fetch Option Data
    ce_data = kite.historical_data(ce_token, from_date, to_date, "minute")
    pe_data = kite.historical_data(pe_token, from_date, to_date, "minute")
    
    if not ce_data or not pe_data:
        print("❌ Option data missing.")
        return
        
    ce_df = pd.DataFrame(ce_data).set_index('date')
    pe_df = pd.DataFrame(pe_data).set_index('date')
    
    # 5. Compare Real vs Calculated
    print("-" * 60)
    print(f"{'Time':<20} | {'Spot':<8} | {'Real Straddle':<15} | {'Calc (HV)':<15} | {'Calc (VIX)':<15} | {'Error (HV)':<10}")
    print("-" * 60)
    
    # Need HV and VIX for calculation
    # Assume fixed HV/VIX for this single day demo
    # From previous analysis: HV ~ 19%, VIX ~ 13%
    hv = 0.19
    vix = 0.13
    t_expiry = 27 / 365 # Approx 27 days left (Nov 28 to Dec 25)
    
    for i in range(0, len(spot_df), 30): # Every 30 mins
        row = spot_df.iloc[i]
        dt = row['date']
        spot = row['close']
        
        if dt not in ce_df.index or dt not in pe_df.index: continue
        
        real_ce = ce_df.loc[dt]['close']
        real_pe = pe_df.loc[dt]['close']
        real_straddle = real_ce + real_pe
        
        # Calculator Formula: 0.8 * S * IV * sqrt(T)
        calc_hv = 0.8 * spot * hv * np.sqrt(t_expiry)
        calc_vix = 0.8 * spot * vix * np.sqrt(t_expiry)
        
        error_hv = ((calc_hv - real_straddle) / real_straddle) * 100
        
        print(f"{dt.strftime('%H:%M')} | {spot:<8.1f} | {real_straddle:<15.1f} | {calc_hv:<15.1f} | {calc_vix:<15.1f} | {error_hv:+.1f}%")
        
    print("="*60)
    print("Interpretation:")
    print("If 'Calc (HV)' is close to 'Real Straddle', our current logic is fine.")
    print("If 'Real Straddle' is much higher, we are underestimating cost (need Fear Factor).")

if __name__ == "__main__":
    fetch_and_validate()
