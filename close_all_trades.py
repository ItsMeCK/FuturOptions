from trade_manager import TradeManager

def close_all():
    tm = TradeManager()
    active_trades = tm.get_active_trades()
    
    if not active_trades:
        print("No active trades to close.")
        return

    symbols = list(active_trades.keys())
    print(f"Closing {len(symbols)} trades...")

    for symbol in symbols:
        trade = active_trades[symbol]
        # Use last known current_price as exit, or entry_price if missing
        exit_price = trade.get('current_price', trade.get('entry_price'))
        tm.close_trade(symbol, exit_price, "Manual Reset - EOD Close")
        print(f"Closed {symbol} at {exit_price}")

    print("All trades closed and moved to history.")

if __name__ == "__main__":
    close_all()
