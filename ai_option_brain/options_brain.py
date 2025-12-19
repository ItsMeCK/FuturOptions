import logging
import math
from datetime import datetime
import pandas as pd

class OptionsBrain:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.current_expiry = self._get_current_expiry()
        
    def _get_current_expiry(self):
        # TODO: Dynamic Expiry Logic
        # For now, hardcoding to DEC 2025 based on user context (INFY25DEC...)
        # In prod, this should find the nearest monthly expiry
        return "25DEC" 

    def get_atm_strike(self, spot_price, step=50):
        return round(spot_price / step) * step

    def construct_option_symbols(self, symbol, spot_price, step=None):
        """
        Construct ATM, OTM, ITM symbols for analysis.
        """
        # Step sizes map (approx)
        step_map = {
            "NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50,
            "RELIANCE": 20, "INFY": 20, "TCS": 50, "SBIN": 10,
            "HDFCBANK": 10, "ICICIBANK": 10, "LT": 50, "AXISBANK": 10,
            "HINDUNILVR": 20, "MARUTI": 100, "ADANIENT": 50, "KOTAKBANK": 20,
            "BHARTIARTL": 10, "BAJFINANCE": 50, "TITAN": 20, "TATASTEEL": 2.5,
            "HINDALCO": 10, "BEL": 5, "ASIANPAINT": 20, "ULTRACEMCO": 100
        }
        
        strike_step = step if step else step_map.get(symbol, 10) # Default 10 for stocks
        if symbol == "NIFTY": strike_step = 50
        
        atm_strike = self.get_atm_strike(spot_price, strike_step)
        
        # Construct Symbols (e.g., INFY25DEC1600CE)
        # Zerodha Format: SYMBOL + YY + MMM + STRIKE + CE/PE
        # Example: INFY25DEC1600CE
        
        # We need to handle the strike format. 
        # NIFTY 24500 -> 24500
        # Stock 1600 -> 1600
        # Stock 1600.5 -> Not supported usually in symbol string directly without checking format
        
        base = f"{symbol}{self.current_expiry}"
        
        # Format strike: 167.5 -> "167.5", 160.0 -> "160"
        if atm_strike % 1 == 0:
            str_strike = str(int(atm_strike))
        else:
            str_strike = str(atm_strike)
            
        ce_symbol = f"NFO:{base}{str_strike}CE"
        pe_symbol = f"NFO:{base}{str_strike}PE"
        
        return ce_symbol, pe_symbol, atm_strike

    def analyze_sentiment(self, symbol, spot_price):
        """
        Analyze Option Chain Sentiment.
        Returns: 'BULLISH', 'BEARISH', 'NEUTRAL' and Details.
        """
        if not self.fetcher or not self.fetcher.kite:
            return "NEUTRAL", {"reason": "No Data"}
            
        ce_sym, pe_sym, strike = self.construct_option_symbols(symbol, spot_price)
        
        try:
            logging.info(f"🧠 OptionsBrain Requesting: {ce_sym}, {pe_sym}")
            quotes = self.fetcher.fetch_live_quote([ce_sym, pe_sym])
            # logging.info(f"🧠 OptionsBrain Received Keys: {list(quotes.keys())}")
            
            ce_data = quotes.get(ce_sym)
            pe_data = quotes.get(pe_sym)
            
            if not ce_data or not pe_data:
                return "NEUTRAL", {"reason": "Quote Missing"}
                
            ce_oi = ce_data.get('oi', 0)
            pe_oi = pe_data.get('oi', 0)
            
            if ce_oi == 0 and pe_oi == 0:
                 return "NEUTRAL", {"reason": "Zero OI"}

            pcr = pe_oi / ce_oi if ce_oi > 0 else 10.0 # High PCR if no calls
            
            # Sentiment Logic
            # PCR > 1.0 -> Bullish (More Puts sold = Support)
            # PCR < 0.7 -> Bearish (More Calls sold = Resistance)
            
            sentiment = "NEUTRAL"
            reason = f"PCR {pcr:.2f}"
            
            if pcr >= 1.2:
                sentiment = "BULLISH"
                reason = f"High PCR ({pcr:.2f}) - Strong Support"
            elif pcr <= 0.6:
                sentiment = "BEARISH"
                reason = f"Low PCR ({pcr:.2f}) - Strong Resistance"
            else:
                # Check OI Dominance
                total_oi = ce_oi + pe_oi
                ce_pct = (ce_oi / total_oi) * 100
                pe_pct = (pe_oi / total_oi) * 100
                
                if ce_pct > 60:
                    sentiment = "BEARISH"
                    reason = "Call Writers Dominating (>60%)"
                elif pe_pct > 60:
                    sentiment = "BULLISH"
                    reason = "Put Writers Dominating (>60%)"
                    
            return sentiment, {
                "pcr": pcr,
                "ce_oi": ce_oi,
                "pe_oi": pe_oi,
                "atm_strike": strike,
                "reason": reason
            }
            
        except Exception as e:
            logging.error(f"Options Brain Error: {e}")
            return "NEUTRAL", {"reason": f"Error: {str(e)}"}
