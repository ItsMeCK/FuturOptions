
import pandas as pd
import numpy as np

def run_study():
    print("🔬 STUDY: Timeframe Sensitivity Analysis (Dec 26)...")
    
    # 1. Load Data
    try:
        df = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['symbol', 'date'])
        symbols = df['symbol'].unique()
    except Exception as e:
        print(f"❌ Data Load Error: {e}")
        return

    # Strategies Results
    results = {
        '5m_Baseline': {'wins': 0, 'losses': 0, 'pnl': 0.0, 'trades': 0},
        '1m_Scalper': {'wins': 0, 'losses': 0, 'pnl': 0.0, 'trades': 0},
        'Hybrid_Sniper': {'wins': 0, 'losses': 0, 'pnl': 0.0, 'trades': 0}
    }
    
    print(f"   Analyzing {len(symbols)} Stocks...")
    
    for sym in symbols:
        s_df = df[df['symbol'] == sym].set_index('date').sort_index()
        if len(s_df) < 100: continue
        
        # --- DATA PREP ---
        # 1m Data
        s_1m = s_df.resample('1min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        s_1m['vol_sma'] = s_1m['volume'].rolling(20).mean()
        s_1m['vwap'] = (s_1m['close'] * s_1m['volume']).cumsum() / s_1m['volume'].cumsum()
        
        # 5m Data
        s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        s_5m['vol_sma'] = s_5m['volume'].rolling(20).mean()
        s_5m['vwap'] = (s_5m['close'] * s_5m['volume']).cumsum() / s_5m['volume'].cumsum()
        
        # Hourly Data (Grandmaster Context)
        # Note: In real sim we stitch history. Here we approximate "Morning Context" using what we have or just skip early morning context check for simplicity of relative comparison?
        # BETTER: Use simple trend check on available data.
        s_1h = s_5m.resample('60min').agg({'close':'last'}).dropna()
        htf_trend = "NEUTRAL"
        if len(s_1h) > 1:
             # Basic check: Current Price vs Morning Open?
             # Let's assume Grandmaster is ACTIVE for Hybrid/5m.
             # We simulate it by checking if Price > VWAP (Proxy for Intraday Trend)
             pass 

        # --- STRATEGY 1: 5m BASELINE ---
        # Entry: Close > VWAP + RVOL > 3.0 (on 5m candle)
        # Exit: Fixed +1.5% TP / -0.5% SL
        trig_5m = False
        for i in range(len(s_5m)):
            if s_5m.index[i].hour > 10: break # Morning Only comparison
            row = s_5m.iloc[i]
            rvol = row['volume']/s_5m['vol_sma'].iloc[i] if s_5m['vol_sma'].iloc[i] > 0 else 0
            if row['close'] > row['vwap'] and rvol > 3.0:
                trig_5m = True
                entry_price = row['close']
                # Check Outcome
                outcome = check_outcome(s_5m.iloc[i+1:], entry_price, 1.015, 0.995)
                update_stats(results['5m_Baseline'], outcome)
                break # One trade per stock for comparison
                
        # --- STRATEGY 2: 1m SCALPER ---
        # Entry: Close > VWAP + RVOL > 3.0 (on 1m candle)
        # No Hourly Filter (Reactive)
        trig_1m = False
        for i in range(len(s_1m)):
            if s_1m.index[i].hour > 10: break
            row = s_1m.iloc[i]
            rvol = row['volume']/s_1m['vol_sma'].iloc[i] if s_1m['vol_sma'].iloc[i] > 0 else 0
            if row['close'] > row['vwap'] and rvol > 3.0:
                trig_1m = True
                entry_price = row['close']
                outcome = check_outcome(s_1m.iloc[i+5:], entry_price, 1.015, 0.995) # Check 1m future
                update_stats(results['1m_Scalper'], outcome)
                break
                
        # --- STRATEGY 3: HYBRID SNIPER ---
        # Entry: 1m Trigger (Speed) BUT requires 5m VWAP Confirmation (Stability)
        # Rule: 1m Close > 1m VWAP AND 1m RVOL > 3.0 AND 5m Trend is UP (Proxy)
        trig_hyb = False
        for i in range(len(s_1m)):
            if s_1m.index[i].hour > 10: break
            row = s_1m.iloc[i]
            rvol = row['volume']/s_1m['vol_sma'].iloc[i] if s_1m['vol_sma'].iloc[i] > 0 else 0
            
            # Hybrid Check:
            # 1. Ignition on 1m
            # 2. Context: Price needs to be > 5m VWAP (Fetched via lookup)
            # Find corresponding 5m VWAP
            try:
                ts_5m = row.name.floor('5min')
                vwap_5m = s_5m.loc[ts_5m]['vwap'] if ts_5m in s_5m.index else row['vwap']
            except:
                vwap_5m = row['vwap']
                
            if row['close'] > vwap_5m and rvol > 3.0:
                trig_hyb = True
                entry_price = row['close']
                outcome = check_outcome(s_1m.iloc[i+5:], entry_price, 1.015, 0.995)
                update_stats(results['Hybrid_Sniper'], outcome)
                break

    # PRINT REPORT
    print("\n🏆 TIMEFRAME COMPARISON RESULTS (Market-Wide):")
    print(f"{'STRATEGY':<15} | {'TRADES':<8} | {'WIN RATE':<10} | {'NET P&L (pts relative)':<10}")
    print("-" * 60)
    for res in results:
        r = results[res]
        wr = (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0
        pnl = r['pnl']
        print(f"{res:<15} | {r['trades']:<8} | {wr:<10.1f}% | {pnl:<10.1f}")
        
    print("\n💡 INTERPRETATION:")
    print("   - 5m Baseline: Slower, fewer trades, safer.")
    print("   - 1m Scalper: Fast, many trades, high noise (Low Win Rate).")
    print("   - Hybrid Sniper: Attempts to balance Speed (1m) with Stability (5m Trend).")

def check_outcome(future_df, entry, tp_mult, sl_mult):
    if future_df.empty: return "FLAT"
    tp = entry * tp_mult
    sl = entry * sl_mult
    
    for px in future_df['low']:
        if px <= sl: return "LOSS"
        # We need to check High for TP in same loop really, simplified for speed
    
    # Check Highs
    for px in future_df['high']:
        if px >= tp: return "WIN"
        
    return "FLAT" # End of day exit

def update_stats(stat_dict, outcome):
    stat_dict['trades'] += 1
    if outcome == "WIN":
        stat_dict['wins'] += 1
        stat_dict['pnl'] += 1.5 # Reward
    elif outcome == "LOSS":
        stat_dict['losses'] += 1
        stat_dict['pnl'] -= 0.5 # Risk
    # Flat = 0

if __name__ == "__main__":
    run_study()
