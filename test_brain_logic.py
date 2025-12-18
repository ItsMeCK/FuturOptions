import unittest
from live_brain import LiveBrain

class TestInstitutionalBrain(unittest.TestCase):
    def setUp(self):
        # Mock LiveBrain - we only need the calculate_confluence_score method
        # We can instantiate it, but we need to mock dependencies if __init__ fails
        # Actually LiveBrain.__init__ tries to connect to Zerodha.
        # Let's monkeypatch __init__ to do nothing.
        original_init = LiveBrain.__init__
        LiveBrain.__init__ = lambda self: None
        self.brain = LiveBrain()
        LiveBrain.__init__ = original_init # Restore

    def test_strong_trend_breakout(self):
        """Test a perfect 'Sniper' setup: Strong Trend + Breakout + Volume"""
        print("\n🧪 Testing Strong Trend + Breakout...")
        
        # Inputs
        symbol = "RELIANCE"
        last_price = 2550
        adx_value = 30 # Strong Trend (+15)
        trend_dist = 0.05 # Above SMA50 (+15)
        rsi = 60 # Bullish (+10)
        bandwidth = 0.10 # Squeeze (+10)
        upper_band = 2540 # Breakout (+10)
        rvol = 2.0 # High Vol (+10)
        vwap_value = 2500 # Above VWAP (+10)
        pred_rv = 20
        market_iv = 15 # Edge > 15% (+20)
        
        focus_data = {
            "RELIANCE": {
                "key_levels": {"breakout_level": 2545}
            }
        } # Breakout > Level (+20)
        
        # Expected Score: 15+15+10+10+10+10+10+20+20 = 120 (Capped at 100?)
        # Let's see what it returns.
        
        result = self.brain.calculate_confluence_score(
            symbol, last_price, adx_value, trend_dist, rsi,
            bandwidth, upper_band, rvol, vwap_value,
            pred_rv, market_iv, focus_data
        )
        
        print(f"   Score: {result['score']}")
        print(f"   Reasons: {result['reasons']}")
        
        self.assertGreaterEqual(result['score'], 90)
        self.assertIn("BREAKOUT > 2545", result['reasons'])

    def test_weak_setup(self):
        """Test a weak setup that should be rejected"""
        print("\n🧪 Testing Weak Setup...")
        
        result = self.brain.calculate_confluence_score(
            "TCS", last_price=3000, adx_value=15, trend_dist=-0.01, rsi=45,
            bandwidth=0.20, upper_band=3100, rvol=0.8, vwap_value=3050,
            pred_rv=15, market_iv=15, focus_data={}
        )
        
        print(f"   Score: {result['score']}")
        self.assertLess(result['score'], 40)

    def test_stalking_phase(self):
        """Test a setup that is 'building' (Stalking Mode)"""
        print("\n🧪 Testing Stalking Phase...")
        
        # Good Trend but no Breakout yet
        result = self.brain.calculate_confluence_score(
            "INFY", last_price=1500, adx_value=26, trend_dist=0.02, rsi=55,
            bandwidth=0.08, upper_band=1510, rvol=1.1, vwap_value=1490,
            pred_rv=18, market_iv=16, focus_data={}
        )
        
        print(f"   Score: {result['score']}")
        # Trend(30) + RSI(10) + Squeeze(10) + VWAP(10) = 60
        self.assertGreaterEqual(result['score'], 60)
        self.assertLess(result['score'], 75)

if __name__ == '__main__':
    unittest.main()
