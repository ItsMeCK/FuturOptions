import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

class DataManager:
    def __init__(self, storage_path="data", use_zerodha=False, zerodha_api_key=None):
        self.storage_path = storage_path
        self.use_zerodha = use_zerodha
        self.zerodha_api_key = zerodha_api_key
        
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def fetch_data(self, ticker, period="1y", interval="1d"):
        """
        Fetches data for a given ticker.
        Args:
            ticker (str): Stock symbol (e.g., 'RELIANCE').
            period (str): Data period (e.g., '1y', '5y', 'max').
            interval (str): Data interval (e.g., '1d', '1wk').
        Returns:
            pd.DataFrame: OHLCV data.
        """
        if self.use_zerodha:
            return self._fetch_from_zerodha(ticker, period, interval)
        else:
            return self._fetch_from_yfinance(ticker, period, interval)

    def _fetch_from_yfinance(self, ticker, period, interval):
        # Append .NS for NSE if not present
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker = f"{ticker}.NS"
        
        print(f"Fetching data for {ticker} from yfinance...")
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                print(f"Warning: No data found for {ticker}")
                return None
            
            # Save to CSV for caching
            file_path = os.path.join(self.storage_path, f"{ticker}_{period}_{interval}.csv")
            df.to_csv(file_path)
            return df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None

    def _fetch_from_zerodha(self, ticker, period, interval):
        # Placeholder for Zerodha implementation
        print("Zerodha fetching not implemented yet. Please provide API key.")
        return None

    def get_nifty50_tickers(self):
        # Hardcoded list of Nifty 50 tickers for testing
        return [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
            "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LTIM", "AXISBANK", 
            "LT", "BAJFINANCE", "MARUTI", "HCLTECH", "ASIANPAINT", "SUNPHARMA", 
            "TITAN", "ULTRACEMCO", "BAJAJFINSV", "WIPRO", "NESTLEIND", "JSWSTEEL", 
            "TATASTEEL", "POWERGRID", "M&M", "ADANIENT", "NTPC", "TATAMOTORS", 
            "GRASIM", "ONGC", "HINDALCO", "COALINDIA", "TECHM", "ADANIPORTS", 
            "BRITANNIA", "HEROMOTOCO", "CIPLA", "DIVISLAB", "DRREDDY", "EICHERMOT", 
            "INDUSINDBK", "BPCL", "APOLLOHOSP", "TATACONSUM", "SBILIFE", "UPL"
        ]
