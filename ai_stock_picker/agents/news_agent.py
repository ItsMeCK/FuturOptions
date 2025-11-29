import requests
import os
import json

class NewsAgent:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            print("Warning: BRAVE_API_KEY not found. News fetching will be disabled.")
        self.base_url = "https://api.search.brave.com/res/v1/news/search"

    def fetch_news(self, query, count=10):
        """
        Fetches news articles for a given query using Brave Search.
        """
        if not self.api_key:
            return []
            
        # Rate Limiting (1 req/sec)
        import time
        time.sleep(1.1)

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": count,
            "freshness": "pw" # Past week
        }

        try:
            print(f"Fetching news for: {query}...")
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            news_items = []
            for item in results:
                news_items.append({
                    'title': item.get('title'),
                    'description': item.get('description'),
                    'url': item.get('url'),
                    'published_time': item.get('age')
                })
            return news_items
            
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

if __name__ == "__main__":
    # Test
    agent = NewsAgent()
    news = agent.fetch_news("Reliance Industries stock news")
    print(json.dumps(news, indent=2))
