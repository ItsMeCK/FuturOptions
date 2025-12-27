
import pandas as pd
import sys
import os

def check_adani_failure():
    print("🕵️‍♂️ Diagnosing ADANIPORTS Failure on Dec 26...")
    
    # 1. Load Stitched Data
    try:
        df_24 = pd.read_csv("daily_data/2025-12-24_spot_full.csv")
        df_26 = pd.read_csv("daily_data/2025-12-26_spot_full.csv")
        
        df_24['date'] = pd.to_datetime(df_24['date'])
        df_26['date'] = pd.to_datetime(df_26['date'])
        
        # Filter ADANIPORTS
        adani_24 = df_24[df_24['symbol'] == 'ADANIPORTS']
        adani_26 = df_26[df_26['symbol'] == 'ADANIPORTS']
        
        adani = pd.concat([adani_24, adani_26]).sort_values('date').set_index('date')
    except:
        print("❌ Data loading failed")
        return

    # 2. Resample
    # 5m for triggers
    adani_5m = adani.resample('5min').agg({'close':'last', 'volume':'sum'}).dropna()
    
    # 1H for Context (Grandmaster Filter)
    adani_1h = adani.resample('60min').agg({'close':'last'}).dropna()
    adani_1h['sma20'] = adani_1h['close'].rolling(20).mean()
    
    # 3. Analyze The "Trade Time"
    # We need to find when the "Ignition/Entry" happened on Dec 26.
    # Let's verify standard indicators briefly to find the trigger.
    adani_5m['vol_sma'] = adani_5m['volume'].rolling(20).mean()
    
    # Check Dec 26 morning
    start_26 = pd.Timestamp("2025-12-26 09:15").tz_localize(adani_5m.index.tz)
    
    print("\n⏱ TIMELINE (ADANIPORTS Dec 26):")
    for i in range(len(adani_5m)):
        curr_time = adani_5m.index[i]
        if curr_time < start_26: continue
        if curr_time.hour > 13: break # Scanning morning
        
        price = adani_5m.iloc[i]['close']
        vol = adani_5m.iloc[i]['volume']
        
        # Get Hourly Context at this time
        # We need the Hourly Bar that *completed* before this or is forming?
        # Usually "Trend" is defined by closed hourly bars.
        # Find the latest available hourly close <= current_time
        latest_hour = adani_1h.loc[:curr_time].iloc[-1]
        hourly_sma = latest_hour['sma20']
        hourly_price = latest_hour['close']
        
        trend = "BULLISH" if hourly_price > hourly_sma else "BEARISH"
        
        # Ignition? (Approx check)
        vol_sma = adani_5m['vol_sma'].iloc[i]
        rvol = vol / vol_sma if vol_sma > 0 else 0
        
        if rvol > 3.0: # Potential Trigger
            print(f"{curr_time.strftime('%H:%M')} | Price: {price:.2f} | Hourly SMA20: {hourly_sma:.2f} | Trend: {trend} | RVOL: {rvol:.1f}x")
            if trend == "BEARISH":
                print("   ➡️ IGNITION FAILED because Context is BEARISH (Hourly < SMA20).")
                print("   ✅ The 'Grandmaster Filter' would have BLOCKED this Loser.")
                return

if __name__ == "__main__":
    check_adani_failure()
