import os
import logging
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.options_brain import OptionsBrain

# Setup Logging
logging.basicConfig(level=logging.INFO)
load_dotenv()

def verify_two_brains():
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    if not access_token:
        print("❌ No Access Token")
        return

    fetcher = ZerodhaDataFetcher(access_token=access_token)
    brain = OptionsBrain(fetcher)
    
    # Debug: Search for correct symbol format for BEL and TATASTEEL
    print("🔍 Searching for BEL CE Instruments...")
    try:
        instruments = fetcher.kite.instruments("NFO")
        
        # BEL
        bel_ce = [i for i in instruments if i['name'] == 'BEL' and i['instrument_type'] == 'CE']
        if bel_ce:
            print(f"✅ Found {len(bel_ce)} BEL instruments. Examples:")
            for i in bel_ce[:5]:
                print(f"  - {i['tradingsymbol']}")
                
        # TATASTEEL
        tata_ce = [i for i in instruments if i['name'] == 'TATASTEEL' and i['instrument_type'] == 'CE']
        if tata_ce:
            print(f"✅ Found {len(tata_ce)} TATASTEEL instruments. Examples:")
            for i in tata_ce[:5]:
                print(f"  - {i['tradingsymbol']}")
            
    except Exception as e:
        print(f"❌ Error searching instruments: {e}")
        
    return

if __name__ == "__main__":
    verify_two_brains()
