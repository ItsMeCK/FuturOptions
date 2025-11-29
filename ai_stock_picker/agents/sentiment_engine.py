import os
from openai import OpenAI
import json

class SentimentEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found. Sentiment analysis will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def analyze_sentiment(self, ticker, news_items):
        """
        Analyzes a list of news items for a specific ticker using GPT-4o.
        Returns a dictionary with sentiment score, summary, and key topics.
        """
        if not self.client or not news_items:
            return {'score': 0, 'summary': "No data", 'topics': []}

        # Prepare prompt
        news_text = "\n".join([f"- {item['title']}: {item['description']}" for item in news_items])
        
        prompt = f"""
        You are a hedge fund sentiment analyst. Analyze the following news for the stock '{ticker}'.
        
        News:
        {news_text}
        
        Task:
        1. Determine the overall sentiment score from -1 (Extreme Fear/Negative) to +1 (Extreme Greed/Positive).
        2. Summarize the key drivers (Earnings, Regulation, Macro, Product, etc.).
        3. Identify any "Red Flags" (Fraud, Governance issues).
        
        Output JSON format:
        {{
            "score": float,
            "summary": "string",
            "topics": ["topic1", "topic2"],
            "red_flag": boolean
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful financial assistant."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            return result
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {'score': 0, 'summary': "Error", 'topics': []}

if __name__ == "__main__":
    # Test
    engine = SentimentEngine()
    # Mock news
    mock_news = [
        {'title': 'Reliance reports record profits', 'description': 'Q3 net profit up 20% YoY driven by retail and oil.'},
        {'title': 'Jio gains 5 million subscribers', 'description': 'Telecom arm continues to grow market share.'}
    ]
    analysis = engine.analyze_sentiment("Reliance Industries", mock_news)
    print(json.dumps(analysis, indent=2))
