import json
from .news_agent import NewsAgent
from .sentiment_engine import SentimentEngine

class ManagementAgent:
    def __init__(self, brave_key=None, openai_key=None):
        self.news_agent = NewsAgent(api_key=brave_key)
        self.sentiment_engine = SentimentEngine(api_key=openai_key)

    def analyze_management(self, ticker):
        """
        Analyzes management quality by searching for CEO letters/interviews
        and processing them with LLM.
        """
        print(f"Analyzing management for {ticker}...")
        
        # 1. Search for relevant text
        # We look for recent interviews or annual report excerpts
        queries = [
            f"{ticker} annual report 2024 CEO letter",
            f"{ticker} management discussion and analysis 2024",
            f"{ticker} CEO interview transcript 2024"
        ]
        
        combined_text = ""
        for q in queries:
            results = self.news_agent.fetch_news(q, count=2) # Fetch top 2 results
            for item in results:
                combined_text += f"\nTitle: {item['title']}\nSnippet: {item['description']}\n"
        
        if not combined_text:
            return {'integrity_score': 0, 'capital_allocation_score': 0, 'summary': "No data found"}

        # 2. Analyze with LLM
        return self._evaluate_text(ticker, combined_text)

    def _evaluate_text(self, ticker, text):
        if not self.sentiment_engine.client:
            return {'integrity_score': 0, 'capital_allocation_score': 0, 'summary': "LLM disabled"}

        prompt = f"""
        You are a forensic investment analyst (Buffett style). Analyze the following text snippets related to {ticker}'s management.
        
        Text:
        {text}
        
        Task:
        1. Rate "Management Integrity" (1-10): Do they admit mistakes? Are they transparent?
        2. Rate "Capital Allocation" (1-10): Do they focus on ROE, FCF, and prudent growth?
        3. Provide a brief summary of their tone.
        
        Output JSON:
        {{
            "integrity_score": int,
            "capital_allocation_score": int,
            "summary": "string"
        }}
        """
        
        try:
            response = self.sentiment_engine.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a skeptical value investor."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error in management analysis: {e}")
            return {'integrity_score': 0, 'capital_allocation_score': 0, 'summary': "Error"}
