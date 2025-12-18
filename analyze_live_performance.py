import pandas as pd
import json
import logging
import logging
from kiteconnect import KiteConnect

# Setup
ACCESS_TOKEN = "xeIzqsbfCH6xJy5fm6SYYIQER8p6V9VD"
API_KEY = "anywvvfkcyjhhqiy" # Assuming standard key from history

# Initialize Fetcher
class DirectFetcher:
    def __init__(self):
        self.kite = KiteConnect(api_key=API_KEY)
        self.kite.set_access_token(ACCESS_TOKEN)
    
    def fetch_quotes(self, symbols):
        try:
            return self.kite.quote(symbols)
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}

def analyze():
    print("📊 ANALYZING LIVE PERFORMANCE (Dec 17-18)")
    print("-" * 50)
    
    # 1. Load Closed Trades
    try:
        closed_df = pd.read_csv("trade_history.csv")
        closed_pnl = closed_df['PnL'].sum()
        print(f"✅ CLOSED TRADES P&L: ₹{closed_pnl:.2f}")
        print("\nBreakdown (Closed):")
        print(closed_df[['Symbol', 'Strategy', 'EntryTime', 'PnL', 'Reason']].to_string())
    except Exception as e:
        print(f"No history found: {e}")
        closed_pnl = 0

    # 2. Load Open Trades & Fetch Live Prices
    print("\n" + "-" * 50)
    print("⏳ ACTIVE TRADES (Fetching Real-Time Data...)")
    
    try:
        with open("active_trades.json", "r") as f:
            active = json.load(f)
            
        fetcher = DirectFetcher()
        option_symbols = [t['option_symbol'] for t in active.values()]
        quotes = fetcher.fetch_quotes(option_symbols)
        
        open_pnl = 0
        active_details = []
        
        for sym, trade in active.items():
            opt_sym = trade['option_symbol']
            entry = trade['entry_price']
            qty = trade['quantity']
            
            if opt_sym in quotes:
                curr_price = quotes[opt_sym]['last_price']
                pnl = (curr_price - entry) * qty
                open_pnl += pnl
                active_details.append({
                    "Symbol": sym,
                    "OptSym": opt_sym,
                    "Entry": entry,
                    "Current": curr_price,
                    "Qty": qty,
                    "PnL": pnl
                })
            else:
                print(f"⚠️ Quote missing for {opt_sym}")
                
        if active_details:
            df_active = pd.DataFrame(active_details)
            print(f"\n✅ OPEN TRADES UNREALIZED P&L: ₹{open_pnl:.2f}")
            print("\nBreakdown (Active):")
            print(df_active.to_string())
        else:
            print("No active trades found or quote fetch failed.")

        # 3. Total
        total_pnl = closed_pnl + open_pnl
        print("\n" + "=" * 50)
        print(f"💰 GRAND TOTAL P&L: ₹{total_pnl:.2f}")
        print("=" * 50)

    except Exception as e:
        print(f"Error processing active trades: {e}")

if __name__ == "__main__":
    analyze()
