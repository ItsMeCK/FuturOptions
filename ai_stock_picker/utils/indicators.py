import pandas as pd
import ta

class TechnicalIndicators:
    """
    Calculates technical indicators for a given DataFrame.
    Expects 'Close', 'High', 'Low' columns.
    """
    
    @staticmethod
    def add_all_indicators(df):
        """
        Adds all relevant indicators to the dataframe.
        """
        df = TechnicalIndicators.add_rsi(df)
        df = TechnicalIndicators.add_macd(df)
        df = TechnicalIndicators.add_bollinger_bands(df)
        df = TechnicalIndicators.add_moving_averages(df)
        df = TechnicalIndicators.add_atr(df)
        return df

    @staticmethod
    def add_rsi(df, window=14):
        indicator_rsi = ta.momentum.RSIIndicator(close=df["Close"], window=window)
        df["RSI"] = indicator_rsi.rsi()
        return df

    @staticmethod
    def add_macd(df, window_slow=26, window_fast=12, window_sign=9):
        indicator_macd = ta.trend.MACD(close=df["Close"], window_slow=window_slow, window_fast=window_fast, window_sign=window_sign)
        df["MACD"] = indicator_macd.macd()
        df["MACD_Signal"] = indicator_macd.macd_signal()
        df["MACD_Diff"] = indicator_macd.macd_diff()
        return df

    @staticmethod
    def add_bollinger_bands(df, window=20, window_dev=2):
        indicator_bb = ta.volatility.BollingerBands(close=df["Close"], window=window, window_dev=window_dev)
        df["BB_High"] = indicator_bb.bollinger_hband()
        df["BB_Low"] = indicator_bb.bollinger_lband()
        df["BB_Mid"] = indicator_bb.bollinger_mavg()
        df["BB_Width"] = indicator_bb.bollinger_wband()
        return df

    @staticmethod
    def add_moving_averages(df):
        df["SMA_50"] = ta.trend.SMAIndicator(close=df["Close"], window=50).sma_indicator()
        df["SMA_200"] = ta.trend.SMAIndicator(close=df["Close"], window=200).sma_indicator()
        return df

    @staticmethod
    def add_atr(df, window=14):
        indicator_atr = ta.volatility.AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=window)
        df["ATR"] = indicator_atr.average_true_range()
        return df
