
import logging
import sys
from live_brain import LiveBrain

# Setup logging to show what user would see
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

def demo_log():
    print("\n🧐 RE-RUNNING YOUR CRASHED TRADE (ADANIENSOL)...")
    print("-" * 50)
    
    brain = LiveBrain()
    
    # Simulate the exact data from your log
    # Dec 26 15:15:07 ... ADANIENSOL: RVOL=0.00, ER=0.15, VolRatio=1.18
    
    symbol = "ADANIENSOL"
    price = 1000
    er_val = 0.15  # Your log showed 0.15 (Which is < 0.3 threshold)
    vol_ratio = 1.18
    
    # Call the SCORING ENGINE directly
    result = brain.calculate_confluence_score(
        symbol=symbol, price=price, adx=20, trend_dist=0, rsi=50, 
        bandwidth=0.1, upper_band=1005, rvol=0.5, vwap_dist=0, 
        pred_rv=20, market_iv=20, focus_data={}, 
        history=None, 
        rvol_5m_avg=0.5,
        is_momentum_active=False,
        # THE NEW PARAMS
        er_value=er_val,
        vol_ratio=vol_ratio,
        vwap_value=1000
    )
    
    print(f"🔍 {symbol}: RVOL=0.50, ER={er_val:.2f}, VolRatio={vol_ratio:.2f}")
    
    reasons = result['reasons']
    score = result['score']
    
    if score == 0 and "BLOCKED" in reasons[0]:
        print(f"✅ RESULT: 🛡 {reasons[0]}")
        print("   (This trade is now KILLED instantly. No Option Check. No Entry.)")
    else:
        print(f"❌ FAILED: {reasons}")

if __name__ == "__main__":
    demo_log()
