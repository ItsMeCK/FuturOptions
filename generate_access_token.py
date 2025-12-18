import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("ZERODHA_API_KEY")
api_secret = os.getenv("ZERODHA_API_SECRET")

if not api_key or not api_secret:
    print("❌ Error: ZERODHA_API_KEY or ZERODHA_API_SECRET not found in .env file.")
    print("Please ensure you have a .env file with these keys.")
    exit()

kite = KiteConnect(api_key=api_key)

print("="*60)
print("🔐 Zerodha Token Generator")
print("="*60)

# 1. Generate Login URL
login_url = kite.login_url()
print("\n1️⃣  Step 1: Login to Zerodha")
print(f"👉 Click this URL: {login_url}")

# 2. Input Request Token
print("\n2️⃣  Step 2: Copy Request Token")
print("   - After login, you will be redirected to a URL like: https://127.0.0.1/?request_token=xyz...")
print("   - Copy the 'request_token' value (e.g., xyz...)")

request_token = input("\n📝 Paste Request Token here: ").strip()

if request_token:
    try:
        # 3. Generate Access Token
        print("\n3️⃣  Step 3: Generating Access Token...")
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        print("\n✅ SUCCESS! Here is your Access Token:")
        print("="*60)
        print(access_token)
        print("="*60)
        print("👉 Copy this token and paste it into the Dashboard.")
        
    except Exception as e:
        print(f"\n❌ Error generating session: {e}")
else:
    print("\n❌ No request token provided.")
