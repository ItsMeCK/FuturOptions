
import pandas as pd
import logging
from datetime import datetime, timedelta
from ai_option_brain.data_loader import ZerodhaDataFetcher
from dotenv import load_dotenv
import os

# Setup
logging.basicConfig(level=logging.INFO)
load_dotenv()

def load_initial_token():
    if os.path.exists("zerodha_hot_token.txt"):
        with open("zerodha_hot_token.txt") as f:
            return f.read().strip()
    return os.getenv("ZERODHA_ACCESS_TOKEN")

def simulate_outcomes():
    # 1. Load Signals
    try:
        signals_df = pd.read_csv("sim_dec29.csv")
    except:
        print("❌ sim_dec29.csv not found")
        return

    # 2. Init Fetcher
    token = load_initial_token()
    fetcher = ZerodhaDataFetcher(access_token=token)
    
    # Cache for Option Data (to avoid re-fetching same option multiple times)
    option_data_cache = {}
    
    results = []
    
    print(f"🚀 Simulating P&L for {len(signals_df)} Signals...")
    
    for idx, row in signals_df.iterrows():
        symbol = row['Symbol']
        strategy = row['Strategy']
        underlying_entry = row['Price']
        signal_time_str = row['Time'] # "09:15:00"
        
        # Parse Time
        # Assuming Date is Dec 29 2025 as per previous prompt context
        date_str = "2025-12-29" 
        entry_dt = pd.to_datetime(f"{date_str} {signal_time_str}")
        
        # 1. Get Option Symbol (LONG CE)
        # Note: In simulation we assume LONG CE for simplicity unless signal says otherwise
        opt_sym, strike = fetcher.get_option_symbol(symbol, underlying_entry, "CE", strategy)
        
        if not opt_sym:
            results.append({"Symbol": symbol, "Outcome": "Error", "PnL_Pct": 0})
            continue
            
        # 2. Fetch Option Data (Intraday Minute)
        if opt_sym not in option_data_cache:
            opt_token = fetcher.get_instrument_token(opt_sym, exchange="NFO")
            if opt_token:
                # Fetch full day minute data
                df = fetcher.fetch_latest_data(opt_token, days=1, interval="minute")
                if not df.empty and 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    option_data_cache[opt_sym] = df
                else:
                    option_data_cache[opt_sym] = None
            else:
                option_data_cache[opt_sym] = None
                
        opt_df = option_data_cache[opt_sym]
        
        if opt_df is None or opt_df.empty:
            # Fallback: Simulate on Underlying (Delta 0.5)
            # print(f"⚠️ No Option Data for {opt_sym}. Skipping.")
            results.append({"Symbol": symbol, "Outcome": "No_Data", "PnL_Pct": 0})
            continue
            
        # 3. Replay Trade
        # Slice data from Entry Time onwards
        # Localize entry_dt if needed or assume df index is tz-aware/naive match
        # Zerodha returns tz-aware usually (+05:30)
        try:
            # entry_dt is naive, localize it
            # entry_dt = entry_dt.tz_localize('Asia/Kolkata')
            # Look for nearest candle
            if opt_df.index.tz:
                 entry_dt_aware = entry_dt.tz_localize(opt_df.index.tz)
            else:
                 entry_dt_aware = entry_dt
                 
            trade_df = opt_df[opt_df.index >= entry_dt_aware]
        except Exception as e:
             # print(f"Comparison Error: {e}")
             # Last resort
             trade_df = opt_df[opt_df.index >= entry_dt]
             
        if trade_df.empty:
             results.append({"Symbol": symbol, "Outcome": "No_Data_Post_Entry", "PnL_Pct": 0})
             continue
             
        entry_price = trade_df.iloc[0]['open']
        
        # Logic Specs
        stop_loss_pct = 0.20 # -20%
        activation_pct = 0.30 # +30%
        trail_pct = 0.10 # 10%
        
        stop_price = entry_price * (1 - stop_loss_pct)
        activation_price = entry_price * (1 + activation_pct)
        
        outcome = "OPEN"
        exit_price = trade_df.iloc[-1]['close'] # Default to EOD
        max_pnl = 0.0
        trailing_active = False
        
        for i in range(len(trade_df)):
            curr_high = trade_df.iloc[i]['high']
            curr_low = trade_df.iloc[i]['low']
            curr_close = trade_df.iloc[i]['close']
            
            # Check Max Gain
            curr_gain = (curr_high - entry_price) / entry_price
            if curr_gain > max_pnl:
                max_pnl = curr_gain
                
            # 1. Check Activation
            if not trailing_active and curr_high >= activation_price:
                trailing_active = True
                # Initial Trail: High - 10% (dynamic) or Entry + locked profit?
                # User: "once above 30% trail by 10%" 
                # Interpretation: Stop becomes High Water Mark - 10%
                
            # 2. Trailing Logic
            if trailing_active:
                # Update Stop (HWM based)
                # If price went to +40%, stop is +30%.
                # If price went to +30%, stop is +20%.
                # Let's say dynamic stop = Max_Price * (1 - 0.10)
                dynamic_stop = curr_high * (1 - trail_pct)
                if dynamic_stop > stop_price:
                    stop_price = dynamic_stop
                    
            # 3. Check Stop Hit (Low touches Stop)
            if curr_low <= stop_price:
                exit_price = stop_price
                if trailing_active:
                    outcome = "WIN (Trail)"
                else:
                    outcome = "LOSS (Stop)"
                break
                
        pnl_pct = (exit_price - entry_price) / entry_price
        
        print(f"Trade {symbol} {signal_time_str}: {outcome} | PnL: {pnl_pct*100:.1f}% | Max: {max_pnl*100:.1f}%")
        
        results.append({
            "Symbol": symbol,
            "Entry_Time": signal_time_str,
            "Entry_Price": entry_price,
            "Exit_Price": exit_price,
            "Outcome": outcome,
            "PnL_Pct": pnl_pct * 100,
            "Max_Gain_Pct": max_pnl * 100
        })
        
    # Analysis
    res_df = pd.DataFrame(results)
    print("\n--- PERFORMANCE REPORT ---")
    print(f"Total Trades: {len(res_df)}")
    wins = res_df[res_df['PnL_Pct'] > 0]
    losses = res_df[res_df['PnL_Pct'] <= 0]
    
    print(f"✅ Wins: {len(wins)} ({len(wins)/len(res_df)*100:.1f}%)")
    print(f"❌ Losses: {len(losses)}")
    print(f"💰 Avg PnL: {res_df['PnL_Pct'].mean():.2f}%")
    print(f"🏆 Best Trade: {res_df['PnL_Pct'].max():.2f}%")
    print(f"💀 Worst Trade: {res_df['PnL_Pct'].min():.2f}%")
    
    res_df.to_csv("sim_pnl_analysis.csv", index=False)
    print("Saved to sim_pnl_analysis.csv")

if __name__ == "__main__":
    simulate_outcomes()
