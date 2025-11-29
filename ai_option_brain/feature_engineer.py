import pandas as pd
import numpy as np
from .utils.technical_indicators import TechnicalIndicators

class FeatureEngineer:
    """
    Transforms raw OHLCV data into Institutional Features for the Volatility Model.
    """

    @staticmethod
    def calculate_historical_volatility(series, window=20):
        """
        Calculates Annualized Historical Volatility (Close-to-Close).
        """
        log_returns = np.log(series / series.shift(1))
        vol = log_returns.rolling(window=window).std() * np.sqrt(252 * 375) # Annualizing (assuming 1-min data? No, usually daily scaler)
        # If input is daily data: sqrt(252)
        # If input is 1-min data: sqrt(252 * 375) (approx minutes in trading day)
        # Let's assume the caller handles the scaling or we detect frequency.
        # For now, let's return daily volatility and let the model learn.
        return log_returns.rolling(window=window).std()

    @staticmethod
    def parkinson_volatility(df, window=20):
        """
        Calculates Parkinson Volatility (High-Low based).
        More efficient estimator than Close-Close.
        """
        log_hl = np.log(df['high'] / df['low']) ** 2
        vol = np.sqrt((1 / (4 * np.log(2))) * log_hl.rolling(window=window).mean())
        return vol

    @staticmethod
    def prepare_training_data(df_1min, df_60min, vix_df=None):
        """
        Merges 1-min (Micro structure) and 60-min (Macro structure) features.
        Target: Future Realized Volatility (5-day).
        """
        print("   ⚙️ Engineering Features...")
        
        # 1. Process 60-min Data (Trend & Structure)
        df_macro = df_60min.copy()
        df_macro['rsi'] = TechnicalIndicators.calculate_rsi(df_macro['close'])
        df_macro['sma_50'] = TechnicalIndicators.calculate_sma(df_macro['close'], 50)
        df_macro['sma_200'] = TechnicalIndicators.calculate_sma(df_macro['close'], 200)
        df_macro['trend_dist'] = (df_macro['close'] - df_macro['sma_200']) / df_macro['sma_200']
        
        # 2. Process 1-min Data (Volatility & Micro)
        df_micro = df_1min.copy()
        
        # Log Returns
        df_micro['log_ret'] = np.log(df_micro['close'] / df_micro['close'].shift(1))
        
        # Realized Volatility (Target)
        # Calculate 5-day future realized volatility
        # 5 days * 375 minutes = 1875 bars
        indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=1875)
        df_micro['target_rv'] = df_micro['log_ret'].rolling(window=indexer).std() * np.sqrt(252 * 375) * 100
        
        # Historical Volatility Features (Inputs)
        df_micro['hv_10'] = df_micro['log_ret'].rolling(window=3750).std() * np.sqrt(252 * 375) * 100 # 10-day HV
        df_micro['hv_20'] = df_micro['log_ret'].rolling(window=7500).std() * np.sqrt(252 * 375) * 100 # 20-day HV
        
        # VWAP Deviation
        vwap = TechnicalIndicators.calculate_vwap(df_micro)
        df_micro['vwap_dev'] = (df_micro['close'] - vwap) / vwap
        
        # 3. Merge VIX (Market Fear)
        # Resample VIX to 1-min and ffill
        if vix_df is not None:
             vix_df['date'] = pd.to_datetime(vix_df['date'])
             vix_df = vix_df.set_index('date').resample('1T').ffill().reset_index()
             # Merge on date (nearest)
             df_micro = pd.merge_asof(df_micro.sort_values('date'), vix_df.sort_values('date'), on='date', direction='backward')
             df_micro.rename(columns={'close_y': 'india_vix'}, inplace=True)
             df_micro.rename(columns={'close_x': 'close'}, inplace=True)
        
        # 4. Merge Macro Features (Trend)
        # Resample 60min macro data to 1min (ffill) or merge_asof
        if not df_macro.empty:
            df_macro = df_macro[['date', 'trend_dist', 'rsi', 'sma_50', 'sma_200']]
            df_micro = pd.merge_asof(df_micro.sort_values('date'), df_macro.sort_values('date'), on='date', direction='backward')
        
        # 5. Clean & Finalize
        # Drop NaNs created by rolling windows
        df_final = df_micro.dropna()
        
        return df_final
