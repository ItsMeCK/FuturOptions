import smtplib
import ssl
import os
from email.message import EmailMessage
import logging
from dotenv import load_dotenv

load_dotenv()

class EmailBot:
    def __init__(self):
        self.sender_email = "chandrakant7892@gmail.com"
        # We look for the password in env, or wait for user to provide it
        self.password = os.getenv("GOOGLE_APP_PASSWORD")
        self.recipients = ["chandrakant7892@gmail.com", "poonamsalke@gmail.com"]
        # macOS SSL Fix: Use unverified context to bypass certificate errors
        self.context = ssl._create_unverified_context()
        
        if not self.password:
             logging.warning("⚠️ EmailBot: GOOGLE_APP_PASSWORD not found in .env. Emails will NOT be sent.")

    def send_email(self, subject, body):
        if not self.password:
            # Try reloading in case user added it to .env hot
            load_dotenv()
            self.password = os.getenv("GOOGLE_APP_PASSWORD")
            if not self.password:
                print("❌ Email Skipped: 'GOOGLE_APP_PASSWORD' missing in .env")
                return

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(self.recipients)

        try:
            # Gmail SMTP SSL on 465
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=self.context) as server:
                server.login(self.sender_email, self.password)
                server.send_message(msg)
            print(f"📧 Email Sent to {len(self.recipients)} recipients: {subject}")
        except Exception as e:
            print(f"❌ Email Failed: {e}")

    def send_trade_alert(self, symbol, strategy, price, reason):
        subject = f"🚀 BUY ALERT: {symbol} [{strategy}]"
        body = f"""🚀 Trade Triggered!

Symbol: {symbol}
Strategy: {strategy}
Entry: {price}
Trigger: {reason}

System: v10.0 Risk Geometry
"""
        self.send_email(subject, body)

    def send_close_alert(self, symbol, price, pnl, reason):
        emoji = "🟢" if pnl >= 0 else "🔴"
        subject = f"{emoji} CLOSE: {symbol} | PnL: {pnl:.2f}"
        body = f"""Trade Closed.

Symbol: {symbol}
Exit Price: {price}
PnL: {pnl:.2f}
Reason: {reason}
"""
        self.send_email(subject, body)
