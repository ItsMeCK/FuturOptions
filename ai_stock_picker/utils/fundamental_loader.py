import yfinance as yf
import pandas as pd

class FundamentalLoader:
    def __init__(self):
        pass

    def fetch_fundamentals(self, ticker):
        """
        Fetches fundamental data for a single ticker.
        Returns a dictionary with normalized metrics.
        """
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker = f"{ticker}.NS"
            
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Normalize Data
            # Note: yfinance debtToEquity is usually in %, e.g., 45.5 -> 0.455
            debt_to_equity = info.get('debtToEquity', 999)
            if debt_to_equity is not None:
                debt_to_equity = debt_to_equity / 100.0
            else:
                debt_to_equity = 999 # High default to fail filter

            data = {
                'Ticker': ticker,
                'Name': info.get('longName', ticker),
                'Sector': info.get('sector', 'Unknown'),
                'ROE': info.get('returnOnEquity', 0), # 0.15 = 15%
                'ROCE': 0, # yfinance often lacks ROCE, we might need to approximate or skip
                'DebtToEquity': debt_to_equity,
                'TrailingPE': info.get('trailingPE', 999),
                'PriceToBook': info.get('priceToBook', 999),
                'FreeCashFlow': info.get('freeCashflow', 0),
                'OperatingCashFlow': info.get('operatingCashflow', 0),
                'EBITDA': info.get('ebitda', 0),
                'RevenueGrowth': info.get('revenueGrowth', 0),
                'EarningsGrowth': info.get('earningsGrowth', 0),
                'MarketCap': info.get('marketCap', 0)
            }
            
            # ROCE Approximation: EBIT / (Total Assets - Current Liabilities)
            # This is hard without full balance sheet. 
            # We will use ROE as primary proxy for now, or try to calculate if data exists.
            
            return data
        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")
            return None

    def fetch_batch(self, tickers):
        """
        Fetches data for a list of tickers.
        """
        results = []
        for t in tickers:
            print(f"Loading fundamentals for {t}...")
            data = self.fetch_fundamentals(t)
            if data:
                results.append(data)
        return pd.DataFrame(results)
