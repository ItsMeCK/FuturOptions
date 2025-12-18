from duckduckgo_search import DDGS
from datetime import datetime, timedelta

class NewsFetcher:
    def __init__(self):
        self.ddgs = DDGS()
        self.cache = {} # {symbol: {'summary': str, 'time': datetime}}
        self.cache_duration = timedelta(hours=1) # Cache news for 1 hour

    def get_news_summary(self, symbol):
        """
        Fetches recent news for the symbol. Uses cache if available and fresh.
        """
        # Check Cache
        if symbol in self.cache:
            last_fetch = self.cache[symbol]['time']
            if datetime.now() - last_fetch < self.cache_duration:
                return self.cache[symbol]['summary']

        try:
            print(f"🌍 Fetching fresh news for {symbol}...")
            query = f"{symbol} stock news india"
            results = self.ddgs.news(query, max_results=5)
            
            if not results:
                summary = "No recent news found."
            else:
                summary = ""
                for r in results:
                    title = r.get('title', '')
                    source = r.get('source', '')
                    date = r.get('date', '')
                    summary += f"- [{date}] {source}: {title}\n"
            
            # Update Cache
            self.cache[symbol] = {
                'summary': summary,
                'time': datetime.now()
            }
                
            return summary
            
        except Exception as e:
            print(f"⚠️ News Fetch Error: {e}")
            return "Error fetching news."
