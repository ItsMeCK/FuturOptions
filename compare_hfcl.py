
import pandas as pd
import logging
import os

def compare_hfcl():
    print("🔬 Analyzing HFCL Strategy: Scalp vs Trend")
    
    # Load Cache
    cache_file = "sim_cache/HFCL_dec29.csv"
    if not os.path.exists(cache_file):
        print("❌ HFCL Data not found.")
        return
        
    df = pd.read_csv(cache_file)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Indicator Setup
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift())
    df['tr2'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()
    
    # Filter Data to 09:30 Start
    start_dt = pd.to_datetime("2025-12-29 09:30:00")
    if df.index.tz: start_dt = start_dt.tz_localize(df.index.tz)
    
    # Find Entry (First valid breakout)
    # Assuming valid entry at 09:30 based on previous report
    entry_row = df[df.index >= start_dt].iloc[0]
    entry_price = entry_row['open']
    atr = df.loc[entry_row.name]['atr']
    if pd.isna(atr): atr = entry_price * 0.005
    
    print(f"🟢 Entry at 09:30 | Price: {entry_price} | ATR: {atr:.2f}")
    
    # --- SCENARIO A: Fixed Target (What happened) ---
    print("\n🅰️ Scenario A: Fixed Target (3x ATR)")
    balance_a = 0
    curr_pos = None
    
    trades_a = 0
    
    sim_df = df[df.index >= start_dt].copy()
    
    for _, candle in sim_df.iterrows():
        # logic: if flat, enter. if target hit, exit.
        if curr_pos is None:
            # Re-enter immediately? (Assuming signal persists)
            curr_pos = {
                'entry': candle['open'], 
                'target': candle['open'] + (3*atr),
                'stop': candle['open'] - (2*atr)
            }
            trades_a += 1
            
        # Check Exit
        if candle['high'] >= curr_pos['target']:
            gain = (curr_pos['target'] - curr_pos['entry'])
            balance_a += gain
            # print(f"   💰 Win: +{gain:.2f}")
            curr_pos = None # Closed
        elif candle['low'] <= curr_pos['stop']:
            loss = (curr_pos['stop'] - curr_pos['entry'])
            balance_a += loss
            # print(f"   ❌ Loss: {loss:.2f}")
            curr_pos = None
            
    # --- SCENARIO B: Trailing Stop (Trend) ---
    print("\n🅱️ Scenario B: Trailing Stop (Let it Run)")
    balance_b = 0
    curr_pos = {
        'entry': entry_price,
        'stop': entry_price - (2*atr),
        'high': entry_price
    }
    trades_b = 1
    status_b = "OPEN"
    
    for _, candle in sim_df.iterrows():
        if status_b == "CLOSED": break
        
        # Update High
        if candle['high'] > curr_pos['high']:
            curr_pos['high'] = candle['high']
            # Trail: Stop is always High - 2 ATR
            new_stop = curr_pos['high'] - (2*atr)
            if new_stop > curr_pos['stop']:
                curr_pos['stop'] = new_stop
                
        # Check Stop
        if candle['low'] <= curr_pos['stop']:
            exit_p = curr_pos['stop']
            balance_b = exit_p - curr_pos['entry']
            status_b = "CLOSED"
            print(f"   🛑 Stopped Out at {candle.name.time()}")
            
    if status_b == "OPEN":
        # MTM at Last Close
        last_close = sim_df.iloc[-1]['close']
        balance_b = last_close - curr_pos['entry']
        print(f"   🏃 Still Running at {sim_df.index[-1].time()} (Stopped at {last_close})")

    print("\n--- COMPARISON ---")
    print(f"Strategy A (Scalping): {trades_a} Trades | ROI: {(balance_a/entry_price)*100:.2f}%")
    print(f"Strategy B (Trailing): {trades_b} Trade  | ROI: {(balance_b/entry_price)*100:.2f}%")
    
    if balance_a > balance_b:
        print("👉 A (Scalping) won because it captured multiple swings.")
    else:
        print("👉 B (Trailing) won because it held the trend.")
    
    print("\n✅ Recommendation for 'Combining':")
    print("To get result B, simply REMOVE the 'Take Profit' target and rely ONLY on the Trailing Stop.")

if __name__ == "__main__":
    compare_hfcl()
