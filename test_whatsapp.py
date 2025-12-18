from notifications.whatsapp_bot import WhatsAppBot
import os
from dotenv import load_dotenv

import logging

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

load_dotenv()

bot = WhatsAppBot()
print(f"Testing Message from {bot.from_num} to {bot.to_nums}")
bot.send_message("👋 Hello to ALL! Multi-user test.")
