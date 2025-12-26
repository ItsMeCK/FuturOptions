import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import pytz

# Import Robust Engine components
from backtest_today_robust import RobustLiveBrain, MockDataFetcher
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

def forensic_hcl():
    DATE = "2025-12-26"
    SYMBOL = "HCLTECH"
    spot_file = f"daily_data/{DATE}_spot_full.csv"
    opt_file = f"daily_data/{DATE}_options_full.csv"
    
    spot_df = pd.read_csv(spot_file)
    spot_df['date'] = pd.to_datetime(spot_df['date'])
    spot_df.set_index('date', inplace=True)
    
    opt_df = pd.read_csv(opt_file)
    opt_df['date'] = pd.to_datetime(opt_df['date'])
    opt_df.set_index('date', inplace=True)
    
    # Configure Mock to match full universe flow roughly
    mock = MockDataFetcher(spot_df, opt_df)
    brain = RobustLiveBrain(mock)
    brain.universe = [SYMBOL]
    brain.batch_size = 1
    brain.universe_index = 0

    # FORCE 1-MINUTE INTERVAL FOR HIGH RES FORENSIC
    # We patch the instance method on the mock object created above
    def mock_fetch_1m(token, days=5, interval="5minute"):
        # Return original 1m data without resampling
        # Note: 'token' here is the hash, so we map back to symbol
        sym = mock.token_to_sym.get(token)
        if not sym or sym not in mock.spot_map: return pd.DataFrame()
        
        df = mock.spot_map[sym]
        # Just return the tail 100 1-minute bars up to current time
        return df.loc[df.index <= mock.current_time].tail(100)
        
    mock.fetch_latest_data = mock_fetch_1m

    # Target window: Full Day
    tz = pytz.timezone('Asia/Kolkata')
    start_time = tz.localize(datetime.strptime(f"{DATE} 09:30:00", "%Y-%m-%d %H:%M:%S"))
    end_time = tz.localize(datetime.strptime(f"{DATE} 15:30:00", "%Y-%m-%d %H:%M:%S"))
    
    current = start_time
    print(f"🕵️ Forensic Analysis for {SYMBOL} (Dec 24)...")
    print(f"{'Time':<10} | {'Price':<10} | {'Score':<5} | {'ADX':<5} | {'Signal':<8} | {'Reasons'}")
    print("-" * 110)
    
    while current <= end_time:
        mock.set_time(current)
        brain.simulation_time = current.replace(tzinfo=None)
        
        # Reset index to scan SYMBOL every minute for high res forensic
        brain.universe_index = 0
        brain.scan_market()
        
        m = brain.last_scan_metrics.get(SYMBOL, {})
        if m:
            # Re-fetch technicals manually for print
            token = mock.get_instrument_token(SYMBOL)
            h = mock.fetch_latest_data(token)
            u, l = TechnicalIndicators.calculate_bollinger_bands(h['close'])
            upper_val = u.iloc[-1]
            lower_val = l.iloc[-1]
            bw = (upper_val - lower_val) / h['close'].rolling(20).mean().iloc[-1]
            
            # Calculate RVOL
            rvol = h['volume'].iloc[-1] / (h['volume'].rolling(20).mean().iloc[-1] + 1)
            
            clean_sym = f"NSE:{SYMBOL}"
            q = mock.fetch_live_quote([clean_sym])
            price = q.get(clean_sym, {}).get('last_price', 0)
            
            print(f"{current.strftime('%H:%M'):<10} | {price:<10.2f} | Score: {m.get('score', 0):<3} | ADX: {int(m.get('adx', 0)):<2} | RVOL: {rvol:.2f} | {m.get('signal', 'NEUTRAL'):<8} | BB:[{lower_val:.1f}-{upper_val:.1f}] | BW:{bw:.3f} | {', '.join(m.get('reasons', []))}")
            
        current += timedelta(minutes=1)

if __name__ == "__main__":
    forensic_hcl()
