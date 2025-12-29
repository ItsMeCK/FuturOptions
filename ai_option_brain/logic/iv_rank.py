import pandas as pd
import numpy as np
import os
import logging

class IVRankCalculator:
    def __init__(self, history_dir="daily_data/history_3yr"):
        self.history_dir = history_dir
        self.cache = {}
        
    def load_history(self, symbol):
        """Load 3-year daily history for a symbol."""
        if symbol in self.cache:
            return self.cache[symbol]
            
        path = f"{self.history_dir}/{symbol}.csv"
        if not os.path.exists(path):
            # Try finding without suffix if naming varies
            return None
            
        try:
            df = pd.read_csv(path)
            df['date'] = pd.to_datetime(df['date'])
            # Normalize to Naive (Local Time) if offset exists
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
                
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # Pre-calculate Log Returns
            df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
            
            # Pre-calculate Rolling 20-day HV (Annualized)
            # HV = StdDev * sqrt(252) * 100
            df['hv_20'] = df['log_ret'].rolling(20).std() * np.sqrt(252) * 100
            
            self.cache[symbol] = df
            return df
        except Exception as e:
            logging.error(f"Error loading history for {symbol}: {e}")
            return None
            
    def get_rank_metrics(self, symbol, current_date=None):
        """
        Calculate Volatility Rank metrics for a given date.
        If current_date is None, uses the latest available date in history.
        """
        df = self.load_history(symbol)
        if df is None or df.empty:
            return None
            
        # Filter data strictly BEFORE the current_date to avoid lookahead bias
        if current_date:
            try:
                # Ensure we are comparing against the 'past Year' relative to that date
                cutoff = pd.to_datetime(current_date)
                past_year_start = cutoff - pd.Timedelta(days=365)
                
                # Slice: Last 1 Year window
                mask = (df.index >= past_year_start) & (df.index < cutoff)
                window_df = df[mask]
                
                if window_df.empty:
                    return None
                    
                # Latest 'known' value (yesterday's close)
                # If we are calculating for 'today', we use 'yesterday's' HV as the base
                # OR if we have live data, we pass it in. 
                # Here we just return the stats of the WINDOW.
                
                hv_series = window_df['hv_20'].dropna()
                if hv_series.empty:
                    return None
                    
                min_hv = hv_series.min()
                max_hv = hv_series.max()
                current_hv = hv_series.iloc[-1] # The HV entering the day
                
                # HV Rank
                hv_rank = 0
                if max_hv > min_hv:
                    hv_rank = ((current_hv - min_hv) / (max_hv - min_hv)) * 100
                    
                # HV Percentile (More robust)
                # % of days where hv < current_hv
                hv_percentile = (hv_series < current_hv).mean() * 100
                
                return {
                    "hv_current": current_hv,
                    "hv_min": min_hv,
                    "hv_max": max_hv,
                    "hv_rank": hv_rank,
                    "hv_percentile": hv_percentile,
                    "count": len(hv_series)
                }
                
            except Exception as e:
                logging.error(f"Error calc rank for {symbol}: {e}")
                return None
        else:
            # Stats for the latest available year
            return self.get_rank_metrics(symbol, df.index[-1])

    def calculate_iv_rank_manual(self, symbol, current_iv, current_date):
        """
        If we have a Live IV value, rank it against the Historical HV/IV proxy.
        """
        metrics = self.get_rank_metrics(symbol, current_date)
        if not metrics:
            return 50.0 # Neutral fallback
            
        # Comparing Live IV against Historical HV
        # IV is usually > HV. 
        # So we should compare Live IV against (Historical HV * PremiumFactor)?
        # Or just use the raw values. If IV is low (near HV lows), it's cheap.
        
        # We can just return the percentile of this IV value within the HV distribution.
        # If IV is within the bottom 20% of HV observations, it's insanely cheap.
        # But IV is usually higher.
        
        # Let's assume implied vol has a similar range structure.
        # We return the Percentile of this specific 'current_iv' value against the 'hv_history'.
        
        df = self.load_history(symbol)
        cutoff = pd.to_datetime(current_date)
        past_year_start = cutoff - pd.Timedelta(days=365)
        mask = (df.index >= past_year_start) & (df.index < cutoff)
        hv_series = df.loc[mask, 'hv_20'].dropna()
        
        if hv_series.empty: return 50.0
        
        # Percentile of 'current_iv' in the 'hv_series' distribution
        # If current_iv is 15, and hv_series has many values < 15, rank is high.
        # If hv_series is mostly > 15, rank is low.
        
        percentile = (hv_series < current_iv).mean() * 100
        
        # Note: This is "IV vs HV Percentile". 
        # A low value means IV is lower than most HVs of the past year -> SUPER CHEAP.
        # A high value means IV is higher than HV -> Normal/Expensive.
        
        return percentile
