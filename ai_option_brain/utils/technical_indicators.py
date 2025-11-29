import pandas as pd
import numpy as np
import ta

class TechnicalIndicators:
    """
    Calculates technical indicators and handles multi-timeframe resampling 
    for the Institutional Option Brain.
    """

    @staticmethod
    def calculate_vwap(df):
        """
        Calculates Volume Weighted Average Price (VWAP).
        Expects a DataFrame with 'high', 'low', 'close', 'volume' columns.
        VWAP is typically reset daily for intraday charts.
        """
        try:
            # Typical Price
            df['tp'] = (df['high'] + df['low'] + df['close']) / 3
            # VWAP = Cumulative(TP * Volume) / Cumulative(Volume)
            # Grouping by Date to reset VWAP daily if data spans multiple days
            # Assuming 'date' is the index or a column. If index is datetime:
            
            # Create a copy to avoid SettingWithCopy warnings on the original df
            df = df.copy()
            
            if isinstance(df.index, pd.DatetimeIndex):
                df['date_only'] = df.index.date
            elif 'date' in df.columns:
                df['date_only'] = pd.to_datetime(df['date']).dt.date
            else:
                # If no date info, calculate cumulative for the whole dataset
                df['cum_vol'] = df['volume'].cumsum()
                df['cum_vol_price'] = (df['tp'] * df['volume']).cumsum()
                return df['cum_vol_price'] / df['cum_vol']

            # Group by day for intraday VWAP
            df['cum_vol'] = df.groupby('date_only')['volume'].cumsum()
            df['cum_vol_price'] = df.groupby('date_only').apply(lambda x: (x['tp'] * x['volume']).cumsum()).reset_index(level=0, drop=True)
            
            return df['cum_vol_price'] / df['cum_vol']
            
        except Exception as e:
            print(f"Error calculating VWAP: {e}")
            return pd.Series(dtype='float64')

    @staticmethod
    def calculate_rsi(series, period=14):
        """
        Calculates Relative Strength Index (RSI).
        """
        return ta.momentum.rsi(series, window=period)

    @staticmethod
    def calculate_sma(series, period):
        """
        Calculates Simple Moving Average (SMA).
        """
        return ta.trend.sma_indicator(series, window=period)

    @staticmethod
    def calculate_ema(series, period):
        """
        Calculates Exponential Moving Average (EMA).
        """
        return ta.trend.ema_indicator(series, window=period)

    @staticmethod
    def calculate_bollinger_bands(series, period=20, std_dev=2):
        """
        Calculates Bollinger Bands.
        Returns (High Band, Low Band)
        """
        indicator = ta.volatility.BollingerBands(close=series, window=period, window_dev=std_dev)
        return indicator.bollinger_hband(), indicator.bollinger_lband()

    @staticmethod
    def resample_data(df, interval):
        """
        Resamples OHLCV data to a different timeframe.
        :param df: DataFrame with DatetimeIndex and OHLCV columns
        :param interval: Pandas offset string (e.g., '15T', '1H', '1D', '1W')
        """
        try:
            conversion = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            # Ensure columns exist
            available_cols = {col: conversion[col] for col in conversion if col in df.columns}
            
            resampled_df = df.resample(interval).agg(available_cols)
            # Drop rows with NaN (e.g., non-trading hours/days)
            return resampled_df.dropna()
        except Exception as e:
            print(f"Error resampling data: {e}")
            return pd.DataFrame()
