
import pandas as pd
import sys

def check_rvnl_option():
    print("🕵️‍♂️ Forensic Check: RVNL Option Price at 09:30...")
    
    try:
        # Load Options Data
        df = pd.read_csv("daily_data/2025-12-26_options_full.csv")
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter for the specific contract in 'tradingsymbol'
        # The 'symbol' column is just the underlying name (e.g. RVNL)
        target = df[
            (df['symbol'] == 'RVNL') & 
            (df['tradingsymbol'].str.contains('380')) & 
            (df['tradingsymbol'].str.contains('CE'))
        ]
        
        if target.empty:
            print("❌ Contract RVNL 380 CE not found!")
            # List unique RVNL tradingsymbols
            rvnl_opts = df[df['symbol'] == 'RVNL']['tradingsymbol'].unique()
            print(f"Available RVNL Options: {rvnl_opts[:10]}")
            return

        symbol = target['tradingsymbol'].iloc[0]
        print(f"✅ Found Contract: {symbol}")
        
        s_df = target.sort_values('date').set_index('date')
        
        # Resample to 1min just in case
        s_1m = s_df.resample('1min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        # Get Price at 09:15 (Low)
        low_price = s_1m['low'].min()
        high_price = s_1m['high'].max()
        
        # Get Price at 09:30 (Entry)
        try:
            entry_row = s_1m.between_time('09:30', '09:30').iloc[0]
            entry_price = entry_row['close']
            entry_time = entry_row.name.strftime('%H:%M')
        except:
            print("❌ No data for 09:30 exactly. Searching nearest...")
            entry_row = s_1m.between_time('09:30', '09:35').iloc[0]
            entry_price = entry_row['close']
            entry_time = entry_row.name.strftime('%H:%M')
            
        # Calculate Stats
        total_move = (high_price - low_price)
        missed_move = (entry_price - low_price)
        captured_move = (high_price - entry_price)
        
        missed_pct = (missed_move / total_move) * 100
        captured_pct = (captured_move / entry_price) * 100
        
        print("\n📊 OPTION FORENSICS:")
        print(f"   Low (09:15):   {low_price:.2f}")
        print(f"   Entry ({entry_time}): {entry_price:.2f}")
        print(f"   High:          {high_price:.2f}")
        print("-" * 30)
        print(f"   Missed Points: {missed_move:.2f} ({missed_pct:.1f}% of range)")
        print(f"   Captured Pts:  {captured_move:.2f}")
        print(f"   Potential ROI: {captured_pct:.0f}%")
        
        if missed_pct > 80:
            print("\n⚠️ VERDICT: User is RIGHT. We missed most of the move.")
        else:
            print(f"\n✅ VERDICT: User is WRONG. We captured {captured_pct:.0f}% ROI.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_rvnl_option()
