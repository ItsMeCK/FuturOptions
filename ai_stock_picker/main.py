import pandas as pd
from utils.data_manager import DataManager
from utils.indicators import TechnicalIndicators
from strategies.smart_swing import SmartSwingStrategy
import warnings

# Suppress pandas warnings
warnings.filterwarnings("ignore")

def main():
    print("Starting AI Stock Picker - Smart Swing System...")
    
    # Initialize Data Manager
    dm = DataManager(use_zerodha=False)
    tickers = dm.get_nifty50_tickers()
    
    # Limit to first 5 tickers for quick testing if needed, or run all
    # tickers = tickers[:5] 
    
    results = []
    
    print(f"Backtesting on {len(tickers)} stocks...")
    
    for ticker in tickers:
        # Fetch Data (1 Year, Daily)
        df = dm.fetch_data(ticker, period="2y", interval="1d")
        
        if df is None or len(df) < 200:
            continue
            
        # Add Indicators
        df = TechnicalIndicators.add_all_indicators(df)
        df = df.dropna()
        
        # Run Strategy
        strategy = SmartSwingStrategy(df)
        final_capital, trades, signal_df = strategy.run_backtest(initial_capital=100000)
        
        # Calculate Metrics
        return_pct = ((final_capital - 100000) / 100000) * 100
        num_trades = len(trades)
        win_trades = len([t for t in trades if t['Capital'] > 100000]) # Simplified win check logic needs refinement based on trade list
        # Actually, trade list stores capital AFTER trade. We need to check diff.
        
        wins = 0
        losses = 0
        if num_trades > 0:
            # Re-calculate wins/losses properly
            # We need to track individual trade PnL. 
            # The current backtest engine returns a list of trades with 'Capital' snapshot.
            # Let's infer PnL from capital changes.
            prev_cap = 100000
            for t in trades:
                if t['Type'].startswith('Sell'):
                    if t['Capital'] > prev_cap:
                        wins += 1
                    else:
                        losses += 1
                    prev_cap = t['Capital'] # Update for next trade cycle (simplified, assumes full capital reinvestment)
                    # Note: The simple backtest engine reinvests full capital.
        
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
        
        results.append({
            'Ticker': ticker,
            'Return %': round(return_pct, 2),
            'Trades': num_trades,
            'Win Rate %': round(win_rate, 2),
            'Final Capital': round(final_capital, 2)
        })
        
        print(f"{ticker}: Return: {return_pct:.2f}%, Trades: {num_trades}, Win Rate: {win_rate:.2f}%")

    # Summary
    results_df = pd.DataFrame(results)
    print("\n--- Overall Performance Summary ---")
    print(results_df.describe())
    
    # Top Performers
    print("\n--- Top 5 Performers ---")
    print(results_df.sort_values(by='Return %', ascending=False).head(5))
    
    # Save results
    results_df.to_csv("backtest_results.csv", index=False)
    print("\nResults saved to backtest_results.csv")

if __name__ == "__main__":
    main()
