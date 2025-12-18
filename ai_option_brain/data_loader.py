import logging
from kiteconnect import KiteConnect
import pandas as pd
import os
from datetime import datetime, timedelta

# Institutional Lot Sizes (Approximate - Should be updated dynamically in prod)
LOT_SIZES = {
    "RELIANCE": 250, "TCS": 175, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700,
    "SBIN": 1500, "TATAMOTORS": 1425, "ITC": 1600, "AXISBANK": 625, "LT": 300,
    "BAJFINANCE": 125, "MARUTI": 50, "KOTAKBANK": 400, "SUNPHARMA": 700,
    "TITAN": 175, "ULTRACEMCO": 100, "ASIANPAINT": 200, "BHARTIARTL": 950,
    "NIFTY": 50, "BANKNIFTY": 15, "FINNIFTY": 40
}

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

    def fetch_live_quote(self, symbols):
        """
        Fetch live quotes for a list of symbols.
        :param symbols: List of symbols (e.g., ['RELIANCE', 'INFY'])
        :return: Dictionary of quotes
        """
        if not self.kite:
            return {}
        
        # Create a map of {prefixed: original} to restore keys
        symbol_map = {}
        prefixed_symbols = []
        for s in symbols:
            if s.startswith("NSE:") or s.startswith("NFO:"):
                prefixed = s
            else:
                prefixed = f"NSE:{s}"
            
            prefixed_symbols.append(prefixed)
            symbol_map[prefixed] = s
        
        try:
            quotes = self.kite.quote(prefixed_symbols)
            
            # Map back to original requested symbols
            clean_quotes = {}
            for p_sym, quote_data in quotes.items():
                original_sym = symbol_map.get(p_sym)
                if original_sym:
                    clean_quotes[original_sym] = quote_data
            
            return clean_quotes
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}

    def fetch_latest_data(self, instrument_token, days=5, interval="minute"):
        """
        Fetch the last N days of data for calculation.
        """
        if not self.kite:
            return pd.DataFrame()
            
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        try:
            data = self.kite.historical_data(instrument_token, from_date, to_date, interval)
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error fetching latest data: {e}")
            return pd.DataFrame()

    def get_instrument_token(self, symbol, exchange="NSE"):
        """
        Get instrument token for a symbol (e.g., 'RELIANCE', 'NIFTY23OCT19000CE').
        This requires fetching the full instrument dump (heavy operation, should be cached).
        """
        # TODO: Implement caching mechanism for instruments list
        if not self.kite:
            return None
            
        try:
            # Simple cache check (in-memory for now)
            if not hasattr(self, 'instrument_dump'):
                print("   Fetching instrument dump (once)...")
                self.instrument_dump = self.kite.instruments(exchange)
                
            for instr in self.instrument_dump:
                if instr['tradingsymbol'] == symbol:
                    return instr['instrument_token']
        except Exception as e:
            print(f"Error fetching instrument token: {e}")
            return None
        return None

    def get_lot_size(self, symbol):
        """Return lot size for the symbol."""
        return LOT_SIZES.get(symbol, 1) # Default to 1 if not found

    def get_option_symbol(self, symbol, spot_price, option_type="CE"):
        """
        Construct Zerodha Option Symbol.
        Format: SYMBOL + YY + MMM + STRIKE + CE/PE
        Example: RELIANCE24JAN2500CE
        """
        try:
            # 1. Calculate ATM Strike
            # Round to nearest strike step (Assuming 20/50/100 steps based on price)
            # Simple heuristic: < 500 -> 5, < 1000 -> 10, < 3000 -> 20, > 3000 -> 50
            step = 10
            if spot_price < 500: step = 5
            elif spot_price > 3000: step = 50
            elif spot_price > 1000: step = 20
            
            strike = round(spot_price / step) * step
            
            # 2. Get Date Components
            now = datetime.now()
            yy = str(now.year)[-2:] # '24'
            mmm = now.strftime("%b").upper() # 'JAN'
            
            # 3. Construct Symbol
            # Handle NIFTY/BANKNIFTY Weekly vs Monthly? 
            # For Stocks, it's always Monthly.
            
            # CRITICAL: Zerodha requires NFO: prefix for options
            opt_symbol = f"NFO:{symbol}{yy}{mmm}{strike}{option_type}"
            return opt_symbol, strike
        except Exception as e:
            print(f"Error constructing option symbol: {e}")
            return None, 0

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
