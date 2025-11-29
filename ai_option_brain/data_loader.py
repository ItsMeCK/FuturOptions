import logging
from kiteconnect import KiteConnect
import pandas as pd
import os
from datetime import datetime, timedelta

class ZerodhaDataFetcher:
    """
    Fetches historical data for Stocks, Futures, and Options using Zerodha Kite Connect API.
    """
    def __init__(self, api_key=None, access_token=None):
        self.api_key = api_key or os.getenv("ZERODHA_API_KEY")
        self.access_token = access_token or os.getenv("ZERODHA_ACCESS_TOKEN")
        
        if self.api_key and self.access_token:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
        else:
            print("⚠️ Zerodha API Key/Token not found. Live data fetching will fail.")
            self.kite = None

    def fetch_historical_data(self, instrument_token, from_date, to_date, interval="minute"):
        """
        Fetch historical candle data with chunking support.
        :param interval: minute, day, 3minute, 5minute...
        """
        if not self.kite:
            return pd.DataFrame()

        all_data = []
        current_from = pd.to_datetime(from_date)
        end_date = pd.to_datetime(to_date)
        
        # Define chunk size based on interval
        # Zerodha limits: minute (60 days), 3/5/10/15/30min (100 days), 60min (365 days), day (2000 days)
        if interval == "minute":
            chunk_days = 60
        elif interval == "day":
            chunk_days = 2000
        elif "minute" in interval:
            chunk_days = 100
        else:
            chunk_days = 365

        while current_from < end_date:
            current_to = min(current_from + timedelta(days=chunk_days), end_date)
            try:
                print(f"   Fetching {interval} data from {current_from.date()} to {current_to.date()}...")
                data = self.kite.historical_data(instrument_token, current_from, current_to, interval)
                if data:
                    all_data.extend(data)
            except Exception as e:
                print(f"   Error fetching chunk: {e}")
            
            current_from = current_to + timedelta(seconds=1) # Avoid overlap? Zerodha handles it usually, but let's be safe
            
        df = pd.DataFrame(all_data)
        return df

    def get_instrument_token(self, symbol, exchange="NSE"):
        """
        Get instrument token for a symbol (e.g., 'RELIANCE', 'NIFTY23OCT19000CE').
        This requires fetching the full instrument dump (heavy operation, should be cached).
        """
        # TODO: Implement caching mechanism for instruments list
        if not self.kite:
            return None
            
        try:
            instruments = self.kite.instruments(exchange)
            for instr in instruments:
                if instr['tradingsymbol'] == symbol:
                    return instr['instrument_token']
        except Exception as e:
            print(f"Error fetching instrument token: {e}")
            return None
        return None

class YFinanceDataFetcher:
    """
    Fetches historical data using yfinance (Backup/Pilot).
    Note: yfinance 1m data is limited to 7 days. We will use 1h/1d for long-term training.
    """
    @staticmethod
    def fetch_historical_data(symbol, period="2y", interval="1h"):
        """
        Fetch data from Yahoo Finance.
        :param symbol: Ticker symbol (e.g., 'RELIANCE.NS')
        :param period: '1y', '2y', '5y', 'max'
        :param interval: '1d', '1h', '1m'
        """
        import yfinance as yf
        try:
            print(f"📥 Fetching {symbol} data via yfinance ({period}, {interval})...")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            # Normalize columns to match Zerodha format (lowercase)
            df.reset_index(inplace=True)
            df.rename(columns={
                "Date": "date", "Datetime": "date",
                "Open": "open", "High": "high", "Low": "low", 
                "Close": "close", "Volume": "volume"
            }, inplace=True)
            
            # Ensure date is timezone-naive or consistent
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
                
            return df[['date', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"Error fetching yfinance data for {symbol}: {e}")
            return pd.DataFrame()
