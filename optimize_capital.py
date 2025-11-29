import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def optimize_capital():
    print("💰 Capital Optimization Analysis (Top 20 Stocks)")
    print("="*60)
    
    # 1. Load Data
    try:
        trades_df = pd.read_csv("ai_option_brain/results/final_trades_log.csv")
        lb_df = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Filter for Top 20 Stocks
    top_20_stocks = lb_df.head(20)['Symbol'].tolist()
    print(f"🎯 Analyzing Top 20 Stocks: {top_20_stocks}")
    
    df = trades_df[trades_df['Symbol'].isin(top_20_stocks)].copy()
    
    # 3. Sort by Time
    df['Entry Date'] = pd.to_datetime(df['Entry Date'])
    df['Exit Date'] = pd.to_datetime(df['Exit Date'])
    df = df.sort_values('Entry Date')
    
    print(f"   Total Trades: {len(df)}")
    print(f"   Date Range: {df['Entry Date'].min()} to {df['Exit Date'].max()}")
    
    # 4. Simulation Function
    def simulate_portfolio(initial_capital):
        cash = initial_capital
        portfolio_value = initial_capital
        active_trades = [] # List of {'exit_time': timestamp, 'release_cash': amount}
        
        missed_trades = 0
        min_cash = initial_capital
        max_drawdown = 0
        peak_value = initial_capital
        
        # We need to iterate through time or events.
        # Event-based simulation is faster.
        # Events: Trade Entry, Trade Exit.
        
        events = []
        for idx, row in df.iterrows():
            events.append({'time': row['Entry Date'], 'type': 'ENTRY', 'cost': row['Cost'], 'pnl': row['P&L (INR)'], 'exit_time': row['Exit Date']})
            # We don't add exit event here because it depends on entry success
            
        # Sort events? No, we need to process exits dynamically.
        # Actually, let's just iterate through the sorted trades and manage a heap of exits.
        
        import heapq
        exit_heap = [] # (exit_time, cash_to_release)
        
        history = []
        
        for idx, row in df.iterrows():
            current_time = row['Entry Date']
            
            # Process Exits before this Entry
            while exit_heap and exit_heap[0][0] <= current_time:
                exit_time, cash_back = heapq.heappop(exit_heap)
                cash += cash_back
                portfolio_value = cash + sum(c for t, c in exit_heap) # Approx
            
            # Try to Enter
            cost = row['Cost']
            if cash >= cost:
                cash -= cost
                heapq.heappush(exit_heap, (row['Exit Date'], cost + row['P&L (INR)']))
            else:
                missed_trades += 1
            
            # Track Metrics
            min_cash = min(min_cash, cash)
            
        # Process remaining exits
        while exit_heap:
            exit_time, cash_back = heapq.heappop(exit_heap)
            cash += cash_back
            
        final_value = cash
        roi = ((final_value - initial_capital) / initial_capital) * 100
        
        return missed_trades, min_cash, final_value, roi

    # 5. Find Optimal Capital (Binary Search / Iterative)
    # We want 0 missed trades.
    
    print("-" * 60)
    print(f"{'Capital':<15} | {'Missed':<10} | {'Min Cash':<15} | {'Final Value':<15} | {'ROI':<10}")
    print("-" * 60)
    
    capitals = [100000, 200000, 300000, 400000, 500000, 750000, 1000000, 1500000, 2000000]
    
    optimal_cap = None
    
    for cap in capitals:
        missed, min_c, final_v, roi = simulate_portfolio(cap)
        print(f"₹{cap:<14,.0f} | {missed:<10} | ₹{min_c:<14,.0f} | ₹{final_v:<14,.0f} | {roi:.1f}%")
        
        if missed == 0 and optimal_cap is None:
            optimal_cap = cap
            
    print("="*60)
    if optimal_cap:
        print(f"✅ Optimal Minimum Capital: ₹{optimal_cap:,.0f}")
        print(f"   (To take ALL trades in Top 20 without running out of cash)")
    else:
        print(f"⚠️ Even ₹20L is not enough? Check logic.")

if __name__ == "__main__":
    optimize_capital()
