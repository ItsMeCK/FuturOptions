
import pandas as pd
import numpy as np
import sys
import os

# Add root to path
sys.path.append(os.getcwd())
from live_brain import LiveBrain
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def test_squeeze_logic():
    print("🧪 Validating v4.0 Squeeze Logic (RVNL vs Adani)...")
    
    # Load Data (Stitched)
    # We will simulate the exact moment of 'Ignition' for both
    try:
        df_24 = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        df_26 = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        df = pd.concat([df_24, df_26]).sort_values(['symbol', 'date'])
        df['date'] = pd.to_datetime(df['date'])
    except:
        print("❌ Data not found.")
        return

    brain = LiveBrain()
    targets = [
        {'symbol': 'RVNL', 'time': '2025-12-26 09:20:00'}, # The Breakout
        {'symbol': 'ADANIPORTS', 'time': '2025-12-26 10:20:00'} # The Fakeout
    ]
    
    for t in targets:
        sym = t['symbol']
        chk_time = pd.Timestamp(t['time'], tz='Asia/Kolkata') # Adjust based on data tz
        
        print(f"\n🔍 Analyzing {sym} at {t['time']}...")
        
        s_df = df[df['symbol'] == sym].set_index('date').sort_index()
        s_5m = s_df.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        
        # Locate the specific candle index
        # We need raw timestamp match
        try:
            # Basic lookback slice
            # Find closest time
            idx = s_5m.index.get_indexer([chk_time], method='nearest')[0]
            # Get history up to that point
            hist = s_5m.iloc[:idx+1]
            
            # Manually Calculate Indicators passed to Brain
            upper, lower = TechnicalIndicators.calculate_bollinger_bands(hist['close'], 20, 2)
            bw = TechnicalIndicators.calculate_bollinger_bandwidth(hist['close'], 20, 2)
            
            curr_bw = bw.iloc[-1]
            prev_bw = bw.iloc[-2] if len(bw)>1 else 0
            
            print(f"   📊 Metrics:")
            print(f"      - Bandwidth (Curr): {curr_bw:.3f}")
            print(f"      - Bandwidth (Prev): {prev_bw:.3f}")
            
            # Check Score
            # Mock other inputs
            price = hist['close'].iloc[-1]
            rvol = 5.0 # Force High RVOL to test suppression
            er = 0.4
            
            score_res = brain.calculate_confluence_score(
                sym, price, 30, 0, 60, curr_bw, upper.iloc[-1], rvol, 
                0, 0, 15, {}, history=None,
                rvol_5m_avg=rvol, er_value=er, vol_ratio=1.0, vwap_value=price-1,
                range_pct=1.0, htf_trend="BULLISH", relative_strength=0.5
            )
            
            print(f"   🎯 Confluence Score: {score_res['score']}")
            print(f"   📝 Reasons: {score_res['reasons']}")
            
            if curr_bw < 0.15:
                print("   ✅ Squeeze Detected: PASSED.")
            else:
                print("   ⚠️ No Squeeze (High Volatility): FAILED.")
                
            if "Exhaustion Volume" in str(score_res['reasons']):
                print("   ⚠️ Exhaustion Capped: PASSED.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_squeeze_logic()
