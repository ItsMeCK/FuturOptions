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

    def analyze_sentiment(self, symbol, spot_price):
        """
        Analyze Option Chain Sentiment.
        Returns: 'BULLISH', 'BEARISH', 'NEUTRAL' and Details.
        """
        if not self.fetcher or not self.fetcher.kite:
            return "NEUTRAL", {"reason": "No Data"}
            
        # Use Data Fetcher's Smart Lookup (Correct Source of Truth)
        # Note: get_option_symbol returns (tradingsymbol, strike)
        ce_sym_raw, strike = self.fetcher.get_option_symbol(symbol, spot_price, "CE")
        pe_sym_raw, _ = self.fetcher.get_option_symbol(symbol, spot_price, "PE")
        
        if not ce_sym_raw or not pe_sym_raw:
             return "NEUTRAL", {"reason": "Smart Lookup Failed"}
             
        # Add NFO: prefix if needed (Smart Lookup returns tradingsymbol e.g. "ADANIENT25DEC...")
        ce_sym = f"NFO:{ce_sym_raw}"
        pe_sym = f"NFO:{pe_sym_raw}"
        
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
