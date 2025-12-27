
import pandas as pd
import numpy as np

def analyze_gap():
    print("🕵️‍♂️ Starting Institutional Gap Analysis...")
    
    # 1. Load Datasets
    try:
        ground_truth = pd.read_csv("research/ground_truth_movers.csv") # 2198 rows
        our_trades = pd.read_csv("research/recent_trades_report.csv")  # 222 rows
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return

    print(f"📚 Data Loaded:")
    print(f"   - Market Reality (Ground Truth): {len(ground_truth)} Options hit +30% gain.")
    print(f"   - Our Strategy (Simulated):      {len(our_trades)} Trades taken.")
    
    # 2. Extract Stock Symbols from Option Symbols
    # ground_truth['OptionSymbol'] e.g., 'RVNL25DEC380CE' -> 'RVNL'
    # Heuristic: Remove digits and expiry suffix. 
    # Or simpler: Match known symbols from our universe if possible.
    # Regex extraction of the leading alpha part?
    # 'ABB25DEC...' -> 'ABB'
    # 'M&M25DEC...' -> 'M&M' (Wait, M&M usually has special handling)
    # Let's try splitting by first digit
    
    import re
    def extract_sym(opt_sym):
        match = re.search(r"^[A-Z&]+", opt_sym)
        if match: return match.group(0)
        return opt_sym
        
    ground_truth['StockSymbol'] = ground_truth['OptionSymbol'].apply(extract_sym)
    
    # FILTER: Only consider Movers > 50% for "Monster" check? Or stick to 30%?
    # User said "went up 30% = trade". So 30%.
    
    # 3. Compare Sets (Stock Level)
    # Did we pick the right STOCK? (We don't pick strikes in SIM, we pick Symbol)
    
    movers_set = set(ground_truth['StockSymbol'].unique())
    our_set = set(our_trades['Symbol'].unique())
    
    # INTERSECTION (True Positives)
    # Stocks we traded that HAD at least one option hitting 30%
    valid_picks = our_set.intersection(movers_set)
    
    # FALSE POSITIVES
    # Stocks we traded that NEVER had a 30% mover option that day?
    # Need to match by DATE too!
    
    # Date Alignment
    # ground_truth 'Date' format '2025-12-24'
    # our_trades 'Date' format '2025-12-24'
    
    # Match Key: Date_Symbol
    ground_truth['Key'] = ground_truth['Date'] + "_" + ground_truth['StockSymbol']
    our_trades['Key'] = our_trades['Date'] + "_" + our_trades['Symbol']
    
    gt_keys = set(ground_truth['Key'].unique())
    our_keys = set(our_trades['Key'].unique())
    
    true_positives = our_keys.intersection(gt_keys) # Good Trades (Opportunity existed)
    false_positives = our_keys - gt_keys            # Bad Trades (Opportunity didn't exist)
    missed_opps = gt_keys - our_keys                # Missed Trades
    
    tp_count = len(true_positives)
    fp_count = len(false_positives)
    miss_count = len(missed_opps)
    total_traded = len(our_keys)
    
    print("-" * 60)
    print("📊 GAP ANALYSIS REPORT")
    print("-" * 60)
    
    print(f"1. PRECISION (Did we pick movers?)")
    print(f"   - Trades Taken:      {total_traded} (Unique Stock/Day)")
    print(f"   - Valid Picks (TP):  {tp_count} ({tp_count/total_traded*100:.1f}%)")
    print(f"   - False Alarms (FP): {fp_count} ({fp_count/total_traded*100:.1f}%)")
    print(f"   Interpretation: {tp_count/total_traded*100:.0f}% of our picks had real option juice (>30%).")
    
    print(f"\n2. RECALL (Did we capture the universe?)")
    print(f"   - Total Opportunities: {len(gt_keys)} (Stock/Days with >30% options)")
    print(f"   - Captured:            {tp_count}")
    print(f"   - Missed:              {miss_count}")
    print(f"   Capture Rate:          {tp_count/len(gt_keys)*100:.1f}%")
    
    print("-" * 60)
    
    # 4. Deep Dive: The FALSE POSITIVES (Why did we enter?)
    # List top 5 False Positives (high Score, but no Option check)
    print("🔍 DIAGNOSING FALSE POSITI VES (Why did we enter these LOSERS?)")
    fp_list = list(false_positives)
    # Get details from our_trades
    fp_details = our_trades[our_trades['Key'].isin(fp_list)]
    # We don't save 'Score' in trade table, but we know they were > 65.
    print(fp_details['Symbol'].value_counts().head(5))
    
    # 5. Deep Dive: The MISSED MONSTERS
    # Which stocks moved the most but we missed?
    print("\n🦖 MISSED MONSTERS (Top Movers we ignored):")
    # Identify max return per Key in GT
    gt_best = ground_truth.groupby('Key')['MaxReturn%'].max()
    missed_df = pd.DataFrame(gt_best).reset_index()
    missed_df = missed_df[missed_df['Key'].isin(missed_opps)]
    print(missed_df.sort_values('MaxReturn%', ascending=False).head(10))

if __name__ == "__main__":
    analyze_gap()
