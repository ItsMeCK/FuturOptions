import pandas as pd
import os
from utils.data_manager import DataManager
from utils.fundamental_loader import FundamentalLoader
from agents.moat_agent import MoatAgent
from agents.management_agent import ManagementAgent
from agents.sentiment_engine import SentimentEngine
from agents.sentiment_engine import SentimentEngine
from agents.news_agent import NewsAgent
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("Starting AI Stock Picker - The Compounder Hunter (Buffett Protocol)...")
    
    # API Keys
    brave_key = os.getenv("BRAVE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not brave_key or not openai_key:
        print("Warning: API keys missing. AI analysis will be skipped.")
    
    # Initialize Components
    dm = DataManager()
    loader = FundamentalLoader()
    moat_agent = MoatAgent()
    mgmt_agent = ManagementAgent(brave_key, openai_key)
    
    # 1. Get Universe (Nifty 50 for now)
    tickers = dm.get_nifty50_tickers()
    # tickers = tickers[:10] # Limit for testing
    
    print(f"Scanning {len(tickers)} stocks for Moats...")
    
    # 2. Fetch Fundamentals & Apply Moat Filters
    fund_data = loader.fetch_batch(tickers)
    
    if fund_data.empty:
        print("No fundamental data found.")
        return

    print("\n--- Applying Quantitative Moat Filters ---")
    print(f"Initial Universe: {len(fund_data)}")
    
    quality_stocks = moat_agent.filter_stocks(fund_data)
    quality_stocks = moat_agent.analyze_valuation(quality_stocks)
    
    print(f"Passed Moat Filters: {len(quality_stocks)}")
    print(quality_stocks[['Ticker', 'ROE', 'DebtToEquity', 'Valuation']].head(10))
    
    # 3. Qualitative AI Analysis (The Boardroom Spy)
    print("\n--- Running AI Management Analysis (The Boardroom Spy) ---")
    
    final_picks = []
    
    for index, row in quality_stocks.iterrows():
        ticker = row['Ticker']
        print(f"Analyzing {ticker}...")
        
        # AI Analysis (Management Quality)
        mgmt_score = mgmt_agent.analyze_management(ticker)
        
        # AI Analysis (Fear/Greed - Contrarian Entry)
        print(f"Checking Fear/Greed for {ticker}...")
        news = mgmt_agent.news_agent.fetch_news(f"{ticker} stock news")
        sentiment = mgmt_agent.sentiment_engine.analyze_sentiment(ticker, news)
        
        # Combine Data
        stock_report = row.to_dict()
        stock_report.update(mgmt_score)
        stock_report['FearScore'] = sentiment.get('score', 0)
        stock_report['NewsSummary'] = sentiment.get('summary', 'No news')
        
        final_picks.append(stock_report)
        time.sleep(1) # Rate limit
        
    # 4. Final Ranking
    final_df = pd.DataFrame(final_picks)
    
    # Score = ROE * 100 + Integrity * 10 + CapitalAlloc * 10
    # (Simple weighting)
    if not final_df.empty and 'integrity_score' in final_df.columns:
        final_df['BuffettScore'] = (final_df['ROE'] * 100) + (final_df['integrity_score'] * 2) + (final_df['capital_allocation_score'] * 2)
        final_df = final_df.sort_values(by='BuffettScore', ascending=False)
        
        print("\n--- Final Buffett Portfolio Picks ---")
        cols = ['Ticker', 'BuffettScore', 'ROE', 'Valuation', 'integrity_score', 'capital_allocation_score', 'FearScore', 'summary']
        print(final_df[cols].head(10))
        
        final_df.to_csv("buffett_portfolio.csv", index=False)
        print("\nSaved to buffett_portfolio.csv")
    else:
        print("No stocks passed the filters or AI analysis failed.")

if __name__ == "__main__":
    main()
