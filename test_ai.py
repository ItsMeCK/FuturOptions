import os
from ai_stock_picker.agents.news_agent import NewsAgent
from ai_stock_picker.agents.sentiment_engine import SentimentEngine
import json

def test_ai_agents():
    print("Testing AI Agents...")
    
    # Check for keys
    brave_key = os.getenv("BRAVE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not brave_key:
        brave_key = input("Enter Brave API Key: ")
    if not openai_key:
        openai_key = input("Enter OpenAI API Key: ")
        
    # Initialize
    news_agent = NewsAgent(api_key=brave_key)
    sentiment_engine = SentimentEngine(api_key=openai_key)
    
    ticker = "Reliance Industries"
    print(f"\n1. Fetching news for {ticker}...")
    news = news_agent.fetch_news(f"{ticker} stock news India")
    
    if not news:
        print("No news found or API error.")
        return

    print(f"Found {len(news)} articles.")
    print(f"Sample: {news[0]['title']}")
    
    print(f"\n2. Analyzing sentiment...")
    analysis = sentiment_engine.analyze_sentiment(ticker, news)
    
    print("\n--- AI Analysis Result ---")
    print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    test_ai_agents()
