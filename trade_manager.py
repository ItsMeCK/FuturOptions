import json
import os
from datetime import datetime

# Switched to Email Bot (v11.0)
from notifications.email_bot import EmailBot

class TradeManager:
    def __init__(self, state_file="active_trades.json"):
        self.state_file = state_file
        self.active_trades = {}
        self.bot = EmailBot() # Initialize Email Bot
        self.load_state()

    def load_active_trades(self):
        """Public method to reload and return active trades."""
        self.load_state()
        return self.active_trades

    def load_state(self):
        """Load active trades from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.active_trades = json.load(f)
                print(f"💾 Loaded {len(self.active_trades)} active trades from {self.state_file}")
            except Exception as e:
                print(f"⚠️ Error loading state: {e}")
                self.active_trades = {}
        else:
            print("✨ No previous state found. Starting fresh.")
            self.active_trades = {}

    def save_state(self):
        """Save active trades to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.active_trades, f, indent=4)
            # print(f"💾 State saved. Active Trades: {len(self.active_trades)}") # Verbose
        except Exception as e:
            print(f"❌ Error saving state: {e}")

    def add_trade(self, symbol, entry_data):
        """
        Add a new trade.
        entry_data should include: entry_price, entry_time, quantity, strategy, etc.
        """
        if symbol in self.active_trades:
            print(f"⚠️ Trade already active for {symbol}. Skipping.")
            return False
        
        self.active_trades[symbol] = entry_data
        self.active_trades[symbol]['status'] = 'OPEN'
        self.active_trades[symbol]['last_update'] = str(datetime.now())
        self.save_state()
        print(f"✅ New Trade Logged: {symbol} @ {entry_data.get('entry_price')}")
        
        # 🔔 Send Notification
        try:
            self.bot.send_trade_alert(
                symbol, 
                entry_data.get('strategy', 'Unknown'), 
                entry_data.get('entry_price'), 
                "Signal Detected",
                option_symbol=entry_data.get('option_symbol'),
                signal_type=entry_data.get('signal_type', 'LONG')
            )
        except Exception as e:
            print(f"⚠️ Notification Failed: {e}")
            
        return True

    def update_trade(self, symbol, current_price, pnl, pnl_pct):
        """Update live stats of a trade."""
        if symbol in self.active_trades:
            self.active_trades[symbol]['current_price'] = current_price
            self.active_trades[symbol]['pnl'] = pnl
            self.active_trades[symbol]['pnl_pct'] = pnl_pct
            self.active_trades[symbol]['last_update'] = str(datetime.now())
            
            # Update High Water Mark for Trailing Stop
            current_hwm = self.active_trades[symbol].get('high_water_mark', -999)
            if pnl_pct > current_hwm:
                self.active_trades[symbol]['high_water_mark'] = pnl_pct
                
            self.save_state()

    def close_trade(self, symbol, exit_price, exit_reason):
        """Close a trade and remove from active list (move to log)."""
        if symbol in self.active_trades:
            trade = self.active_trades.pop(symbol)
            trade['exit_price'] = exit_price
            trade['exit_time'] = str(datetime.now())
            trade['exit_reason'] = exit_reason
            trade['status'] = 'CLOSED'
            
            self.save_state()
            self.log_closed_trade(trade)
            print(f"🚫 Trade Closed: {symbol} | Reason: {exit_reason} | P&L: {trade.get('pnl', 0)}")
            
            # 🔔 Send Notification
            try:
                self.bot.send_close_alert(
                    symbol, 
                    exit_price, 
                    trade.get('pnl', 0), 
                    exit_reason
                )
            except Exception as e:
                print(f"⚠️ Notification Failed: {e}")

            return True
        return False

    def log_closed_trade(self, trade):
        """Append closed trade to a DAILY CSV log."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        folder = "trade_history"
        os.makedirs(folder, exist_ok=True)
        filename = f"{folder}/trades_{today_str}.csv"
        
        file_exists = os.path.exists(filename)
        try:
            with open(filename, "a") as f:
                # Simple CSV format with Strategy column
                if not file_exists:
                    f.write("Symbol,EntryTime,EntryPrice,ExitTime,ExitPrice,PnL,Reason,Strategy\n")
                
                line = f"{trade.get('symbol')},{trade.get('entry_time')},{trade.get('entry_price')}," \
                       f"{trade.get('exit_time')},{trade.get('exit_price')},{trade.get('pnl')},{trade.get('exit_reason')},{trade.get('strategy', 'Unknown')}\n"
                f.write(line)
        except Exception as e:
            print(f"❌ Error logging to CSV: {e}")

    def get_active_trades(self):
        return self.active_trades

if __name__ == "__main__":
    # Test
    tm = TradeManager("test_state.json")
    tm.add_trade("RELIANCE", {"symbol": "RELIANCE", "entry_price": 2500, "entry_time": str(datetime.now()), "quantity": 100})
    tm.update_trade("RELIANCE", 2550, 5000, 0.02)
    print("Active:", tm.get_active_trades())
    tm.close_trade("RELIANCE", 2540, "Trailing Stop")
    print("Active after close:", tm.get_active_trades())
    # Cleanup
    if os.path.exists("test_state.json"): os.remove("test_state.json")
    if os.path.exists("trade_history.csv"): os.remove("trade_history.csv")
