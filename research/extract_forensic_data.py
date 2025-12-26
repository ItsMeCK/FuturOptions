
import pandas as pd

def extract_case_study(date_str, symbol):
    spot_file = f"daily_data/{date_str}_spot_full.csv"
    opt_file = f"daily_data/{date_str}_options_full.csv"
    
    try:
        s_df = pd.read_csv(spot_file)
        o_df = pd.read_csv(opt_file)
    except:
        print(f"File not found for {date_str}")
        return

    # Filter Spot
    s_sym = s_df[s_df['symbol'] == symbol].copy()
    s_sym['date'] = pd.to_datetime(s_sym['date'])
    s_sym = s_sym.set_index('date').sort_index()
    
    # Filter Options (Just get the most active Call/Put)
    # Handle missing 'symbol' column in some CSVs
    if 'symbol' not in o_df.columns:
        # Regex to extract symbol from tradingsymbol (e.g. TATASTEEL25DEC...)
        # Assume standard format: SYMBOL + 2DIGITYEAR + MONTH... 
        # Actually simplest is startswith
        o_sym_all = o_df[o_df['tradingsymbol'].str.startswith(symbol)]
    else:
        o_sym_all = o_df[o_df['symbol'] == symbol]

    if o_sym_all.empty:
        print(f"No option data for {symbol}")
        return

    top_opt = o_sym_all.groupby('tradingsymbol')['volume'].sum().idxmax()
    o_sym = o_sym_all[o_sym_all['tradingsymbol'] == top_opt].copy()
    o_sym['date'] = pd.to_datetime(o_sym['date'])
    o_sym = o_sym.set_index('date').sort_index()

    print(f"\n📊 CASE STUDY: {symbol} ({date_str})")
    print(f"   Top Option: {top_opt}")
    
    # Resample to 15m to see shape
    s_15m = s_sym.resample('15min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'})
    print(s_15m.dropna().head(10)) # Morning session
    print("   ...")
    print(s_15m.dropna().tail(5)) # Afternoon Stagnation?

    # Calculate Intraday RVOL Profile?
    # Avg Vol of first 3 15m bars vs last 3?
    
    morning_vol = s_15m.iloc[0:4]['volume'].mean()
    mid_vol = s_15m.iloc[4:16]['volume'].mean()
    
    print(f"   Morning Avg Vol: {morning_vol:,.0f}")
    print(f"   Mid-Day Avg Vol: {mid_vol:,.0f}")
    print(f"   Dropoff: {(mid_vol - morning_vol)/morning_vol*100:.1f}%")

if __name__ == "__main__":
    print("--- FORENSIC EXTRACTION ---")
    extract_case_study("2025-12-26", "RELIANCE")
    extract_case_study("2025-12-26", "SBIN")
    extract_case_study("2025-12-24", "TATASTEEL")
