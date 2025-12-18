import os
import logging
from twilio.rest import Client

class WhatsAppBot:
    def __init__(self):
        self.sid = os.environ.get("TWILIO_SID")
        self.token = os.environ.get("TWILIO_TOKEN")
        self.from_num = os.environ.get("TWILIO_FROM") # e.g., 'whatsapp:+14155238886'
        self.to_nums = [n.strip() for n in os.environ.get("TWILIO_TO", "").split(',')] if os.environ.get("TWILIO_TO") else []
        
        self.client = None
        if self.sid and self.token:
            try:
                self.client = Client(self.sid, self.token)
                logging.info(f"📱 Twilio Client Initialized. Recipients: {len(self.to_nums)}")
            except Exception as e:
                logging.error(f"❌ Twilio Init Failed: {e}")
        else:
            logging.warning("⚠️ Twilio Credentials Missing in .env")

    def send_message(self, body):
        if not self.client or not self.to_nums: return
        
        for recipient in self.to_nums:
            try:
                # Ensure whatsapp: prefix
                to_addr = recipient if recipient.startswith('whatsapp:') else f"whatsapp:{recipient}"
                
                message = self.client.messages.create(
                    from_=self.from_num,
                    body=body,
                    to=to_addr
                )
                logging.info(f"📤 Sent to {recipient}: {body[:20]}... (SID: {message.sid})")
            except Exception as e:
                logging.error(f"❌ Failed to send to {recipient}: {e}")

    def send_trade_alert(self, symbol, order_type, price, reason):
        msg = (
            f"🚨 *TRADE ALERT* 🚨\n\n"
            f"Symbol: *{symbol}*\n"
            f"Type: {order_type}\n"
            f"Price: {price}\n"
            f"Reason: {reason}\n\n"
            f"Time: {os.path.basename(os.getcwd())}" # Just context filler
        )
        self.send_message(msg)

    def send_close_alert(self, symbol, exit_price, pnl, reason):
        emoji = "✅" if pnl > 0 else "❌"
        msg = (
            f"{emoji} *TRADE CLOSED* {emoji}\n\n"
            f"Symbol: *{symbol}*\n"
            f"Exit: {exit_price}\n"
            f"P&L: ₹{pnl:.2f}\n"
            f"Reason: {reason}"
        )
        self.send_message(msg)
