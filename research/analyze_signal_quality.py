import pandas as pd
import re
import datetime

def load_spot_data(date_str):
    """Load spot data and return as dict of dataframe per symbol."""
    file = f"daily_data/{date_str}_spot_full.csv"
    try:
        df = pd.read_csv(file)
        df['date'] = pd.to_datetime(df['date'])
        # Rename date to datetime for easier lookup
        return df
    except Exception as e:
        print(f"Error loading {file}: {e}")
        return pd.DataFrame()

def analyze_signals():
    log_file = "trend_sim_v2.txt"
    with open(log_file, 'r') as f:
        lines = f.readlines()
        
    # Regex to capture: Date, Time, Symbol, Score, Signal, Reasons
    # Line format from log:
    # 2025-12-26 14:07:47,231 - INFO - 🚨 POTENTIAL SIGNAL: LT | Score: 65 | Signal: CALL | Reasons: [...]
    # But wait, the timestamp `2025-12-26 14:07:47` is LOG time, not SIM time.
    # We need SIM time.
    # The Log *preceding* the signal line usually has the time:
    # 2025-12-26 14:07:42,972 - INFO - ⏳ Sim Sweep: [...] | Time: 15:10:00 | Quotes: 44
    # This is tricky regex work. The signals appear in a batch *after* a sweep log?
    # Actually, in `backtest_today_robust.py`, `scan_market` prints Sweep info *after* scanning? no, *before*.
    # Wait, `scan_market` iterates universe. The log "POTENTIAL SIGNAL" happens *inside* the loop.
    # But `Sim Sweep` log happens *inside* `run_backtest` loop, which calls `scan_market`.
    # So "Sim Sweep: ... Time: 15:10:00" prints, THEN `scan_market` runs, THEN "POTENTIAL SIGNAL" prints.
    # So the "Time" for a signal is the *most recently seen* Sim Sweep time.
    
    signals = []
    current_sim_time = None
    current_date = "2025-12-24" # Start date of sim
    
    for line in lines:
        if "Simulation Complete for 2025-12-24" in line:
            current_date = "2025-12-26"
        
        # Capture Sim Time
        # INFO - ⏳ Sim Sweep: [0:55] | Time: 11:52:00 | Quotes: 53
        if "Sim Sweep:" in line and "Time:" in line:
            try:
                t_str = line.split("Time:")[1].split("|")[0].strip()
                current_sim_time = t_str
            except: pass
            
        if "POTENTIAL SIGNAL" in line and current_sim_time:
            # Parse Signal
            try:
                # 🚨 POTENTIAL SIGNAL: LT | Score: 65 | Signal: CALL | Reasons: ['...']
                parts = line.split("POTENTIAL SIGNAL:")[1]
                p_split = parts.split("|")
                sym = p_split[0].strip()
                score = int(p_split[1].split(":")[1].strip())
                sig_type = p_split[2].split(":")[1].strip()
                reasons = p_split[3].split(":")[1].strip()
                
                signals.append({
                    'date': current_date,
                    'time': current_sim_time,
                    'symbol': sym,
                    'score': score,
                    'signal': sig_type,
                    'reasons': reasons
                })
            except Exception as e:
                # print(f"Parse error: {e}")
                pass

    print(f"Extracted {len(signals)} signals.")
    
    # Analyze Outcomes
    results = []
    
    # Load Data Cache
    spot_data = {
        "2025-12-24": load_spot_data("2025-12-24"),
        "2025-12-26": load_spot_data("2025-12-26")
    }
    
    for sig in signals:
        date = sig['date']
        time_str = sig['time']
        sym = sig['symbol']
        direction = sig['signal']
        
        # If signal is NEUTRAL, try to infer from reasons
        if direction == "NEUTRAL":
            if "Above SMA50" in sig['reasons']: direction = "CALL"
            elif "Below SMA50" in sig['reasons']: direction = "PUT"
            # Trend Drift usually implies following trend, but which way?
            # We can check price vs SMA50 using data or just skip NEUTRALs.
            # Let's Skip NEUTRALs as "Invalid Signal" for now to check quality of *confirmed* ones.
            # Actually, user wants to know "how many were false". If NEUTRAL triggers high score, it's a bug or feature?
            # It's a "Wait" signal. So not a trade.
            if direction == "NEUTRAL":
                continue

        df = spot_data.get(date)
        if df.empty: continue
        
        # Filter for Symbol
        sym_df = df[df['symbol'] == sym].sort_values('date')
        if sym_df.empty: continue
        
        # Find Entry Candle
        # Parse datetime: 2025-12-24 11:52:00
        # Timezone in CSV is +05:30.
        entry_dt_str = f"{date} {time_str}"
        entry_dt = pd.to_datetime(entry_dt_str).tz_localize("Asia/Kolkata")
        
        # Find row at or immediately after entry_dt
        entry_row = sym_df[sym_df['date'] >= entry_dt].head(1)
        if entry_row.empty: continue
        
        entry_price = entry_row.iloc[0]['close']
        
        # Evaluate Outcome (End of Day or Next 60 mins?)
        # Let's say we hold until End of Day (15:15) or Stop Loss.
        # Simplistic: Compare Entry to Close.
        
        future_df = sym_df[sym_df['date'] > entry_dt]
        if future_df.empty:
            outcome = "No Data"
            pnl_pct = 0
        else:
            final_price = future_df.iloc[-1]['close']
            
            if direction == "CALL":
                pnl_pct = (final_price - entry_price) / entry_price
            else: # PUT
                pnl_pct = (entry_price - final_price) / entry_price
                
            if pnl_pct > 0.005: outcome = "WIN" # > 0.5%
            elif pnl_pct < -0.005: outcome = "LOSS" # < -0.5%
            else: outcome = "FLAT"
            
        results.append({
            'symbol': sym,
            'date': date,
            'time': time_str,
            'type': direction,
            'pnl': round(pnl_pct * 100, 2),
            'outcome': outcome,
            'score': sig['score']
        })

    # Summary
    res_df = pd.DataFrame(results)
    if res_df.empty:
        print("No valid trades extracted.")
        return

    print("\n" + "="*40)
    print(" 📊 SIGNAL QUALITY ANALYSIS (Trend Logic)")
    print("="*40)
    
    total = len(res_df)
    wins = len(res_df[res_df['outcome'] == 'WIN'])
    losses = len(res_df[res_df['outcome'] == 'LOSS'])
    flat = len(res_df[res_df['outcome'] == 'FLAT'])
    
    print(f"Total Trades Analyzed: {total}")
    print(f"✅ Wins (>0.5%):  {wins} ({wins/total*100:.1f}%)")
    print(f"❌ Losses (<-0.5%): {losses} ({losses/total*100:.1f}%)")
    print(f"➖ Flat:            {flat} ({flat/total*100:.1f}%)")
    
    print("\n🔍 Breakdown by Date:")
    for d in sorted(res_df['date'].unique()):
        day_df = res_df[res_df['date'] == d]
        w = len(day_df[day_df['outcome'] == 'WIN'])
        l = len(day_df[day_df['outcome'] == 'LOSS'])
        print(f"  {d}: {len(day_df)} Trades | Wins: {w} | Losses: {l}")
        
    print("\n📉 Top 5 Worst Failures:")
    failures = res_df.sort_values('pnl').head(5)
    print(failures[['date', 'symbol', 'time', 'type', 'pnl']])
    
    print("\n📈 Top 5 Best Winners:")
    winners = res_df.sort_values('pnl', ascending=False).head(5)
    print(winners[['date', 'symbol', 'time', 'type', 'pnl']])

if __name__ == "__main__":
    analyze_signals()
