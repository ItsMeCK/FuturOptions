import pandas as pd
import numpy as np
from .greeks_calculator import GreeksCalculator

class GEXEngine:
    """
    The GEX Engine (Market Physics).
    Calculates Gamma Exposure (GEX) to determine the Market Regime.
    """

    @staticmethod
    def calculate_gex(option_chain_df, spot_price):
        """
        Calculates Net Gamma Exposure (GEX) for the entire option chain.
        
        Formula: GEX = Gamma * Open Interest * 100 * Spot Price
        (Multiplied by 100 because 1 option contract = 100 shares usually, 
         but for Nifty it's 50 or 25. We should check lot size. 
         Standard GEX formula often uses 100 as a scaler or contract size).
         
        For Nifty, Lot Size is currently 25 (as of late 2024/2025). 
        Let's pass lot_size as a parameter or assume 25.
        
        :param option_chain_df: DataFrame with columns: 
               ['strike', 'type', 'oi', 'iv', 'expiry']
        :param spot_price: Current Underlying Price
        :return: Dictionary with 'net_gex', 'regime', 'gex_by_strike'
        """
        lot_size = 25 # Nifty Lot Size
        
        gex_data = []
        net_gex = 0
        
        # Assume we have a risk-free rate and time to expiry
        # In a real system, these come from the data loader
        r = 0.07 # 7% Risk Free Rate
        
        for index, row in option_chain_df.iterrows():
            strike = row['strike']
            opt_type = row['type'] # 'CE' or 'PE'
            oi = row['oi']
            iv = row['iv']
            expiry = row['expiry'] # String 'YYYY-MM-DD'
            
            if oi == 0 or iv == 0:
                continue
                
            t = GreeksCalculator.get_days_to_expiry(expiry)
            if t <= 0:
                t = 0.001 # Avoid division by zero
                
            # Calculate Gamma
            flag = 'c' if opt_type == 'CE' else 'p'
            greeks = GreeksCalculator.calculate_greeks(spot_price, strike, t, r, iv, flag)
            gamma = greeks['gamma']
            
            # Calculate GEX for this strike
            # Call GEX is Positive (Dealers Long Gamma)
            # Put GEX is Negative (Dealers Short Gamma) - typically.
            # Wait, standard theory:
            # Market Makers Sell Calls -> Short Gamma -> Need to Buy Underlying to hedge -> No, wait.
            # If MM Sells Call -> MM is Short Call -> MM is Short Gamma.
            # If MM Sells Put -> MM is Short Put -> MM is Long Gamma? No.
            # Short Call Gamma is Negative. Short Put Gamma is Negative.
            # Long Call Gamma is Positive. Long Put Gamma is Positive.
            
            # Assumption: Market Makers are the ones SELLING to Retail.
            # So if OI is high, MM is likely SHORT that option.
            # MM Short Option = MM Short Gamma.
            # So High OI = Negative GEX?
            
            # Let's stick to the SpotGamma / SqueezeMetrics definition:
            # Call OI adds to Positive GEX (Dealers Long Gamma - assuming they bought from overwriters?)
            # Put OI adds to Negative GEX (Dealers Short Gamma - assuming they sold to hedgers).
            
            # Convention:
            # Call GEX = Gamma * OI * Spot * LotSize
            # Put GEX = Gamma * OI * Spot * LotSize * -1
            
            strike_gex = gamma * oi * spot_price * lot_size
            
            if opt_type == 'PE':
                strike_gex *= -1
                
            net_gex += strike_gex
            gex_data.append({
                'strike': strike,
                'type': opt_type,
                'gex': strike_gex
            })
            
        regime = "Positive (Pinning)" if net_gex > 0 else "Negative (Trending)"
        
        return {
            "net_gex_inr_crores": net_gex / 10000000, # Convert to Crores
            "regime": regime,
            "details": gex_data
        }
