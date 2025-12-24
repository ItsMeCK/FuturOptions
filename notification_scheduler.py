import time
import json
import os
import logging
from datetime import datetime
from notifications.whatsapp_bot import WhatsAppBot

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NotificationScheduler:
    def __init__(self):
        self.bot = WhatsAppBot()
        self.last_pnl_alert = 0
        self.last_scan_alert = 0
        
        # Frequencies (Seconds)
        self.PNL_FREQ = 900  # 15 Mins
        self.SCAN_FREQ = 3600 # 60 Mins
        
    def check_pnl(self):
        if not os.path.exists("active_trades.json"): return
        
        try:
            with open("active_trades.json", "r") as f:
                trades = json.load(f)
                
            if not trades: return
            
            total_pnl = sum([t.get('pnl', 0) for t in trades.values()])
            count = len(trades)
            
            msg = f"📊 *Live P&L Update*\n\nActive Trades: {count}\nTotal P&L: ₹{total_pnl:.2f}\n"
            for sym, data in trades.items():
                p = data.get('pnl', 0)
                icon = "🟢" if p > 0 else "🔴"
                msg += f"{icon} {sym}: ₹{p:.2f}\n"
                
            self.bot.send_message(msg)
            
        except Exception as e:
            logging.error(f"PnL Check Error: {e}")

    def check_scan(self):
        if not os.path.exists("latest_scan.json"): return
        
        try:
            with open("latest_scan.json", "r") as f:
                data = json.load(f)
                
            # data format expected: {"timestamp": "...", "top_picks": [{"symbol": "INFY", "score": 85}, ...]}
            top = data.get("top_picks", [])
            if not top: return
            
            msg = "🔭 *Hourly Market Scan*\n\nTop Opportunities:\n"
            for item in top[:5]:
                # Use .get() with fallback to handle potential casing differences
                symbol = item.get('Symbol', item.get('symbol', 'Unknown'))
                score = item.get('Score', item.get('score', 0))
                msg += f"⭐ {symbol} (Score: {score})\n"
            
            self.bot.send_message(msg)
            
        except Exception as e:
            logging.error(f"Scan Check Error: {e}")

    def run(self):
        logging.info("🕰️ Notification Scheduler Started.")
        
        while True:
            now = time.time()
            
            # PnL Check
            if now - self.last_pnl_alert > self.PNL_FREQ:
                logging.info("Checking PnL...")
                self.check_pnl()
                self.last_pnl_alert = now
                
            # Scan Check
            if now - self.last_scan_alert > self.SCAN_FREQ:
                logging.info("Checking Scan...")
                self.check_scan()
                self.last_scan_alert = now
                
            time.sleep(60) # Loop tick

if __name__ == "__main__":
    scheduler = NotificationScheduler()
    scheduler.run()
