import json
from .news_agent import NewsAgent
from .sentiment_engine import SentimentEngine

class AlternativeDataAgent:
    def __init__(self, brave_key=None, openai_key=None):
        self.news_agent = NewsAgent(api_key=brave_key)
        self.sentiment_engine = SentimentEngine(api_key=openai_key)

    def fetch_alternative_data(self, ticker, sector):
        """
        Fetches alternative data signals: Supply Chain & Employee Morale.
        """
        print(f"📡 Fetching Alternative Data for {ticker} ({sector})...")
        
        return {
            'Supply_Chain': self._check_supply_chain(ticker, sector),
            'Employee_Morale': self._check_employee_morale(ticker)
        }

    def _check_supply_chain(self, ticker, sector):
        # Dynamic query based on sector
        commodity = "raw material"
        if "Power" in sector or "Energy" in sector: commodity = "Coal price"
        elif "Paint" in sector: commodity = "Crude oil price"
        elif "Auto" in sector: commodity = "Steel and Aluminum price"
        elif "Chemical" in sector: commodity = "Chemical commodity prices"
        
        query = f"{commodity} trend India last 3 months impact on {ticker}"
        news = self.news_agent.fetch_news(query, count=3)
        return self._analyze_signal(ticker, "Supply Chain/Input Costs", news)

    def _check_employee_morale(self, ticker):
        query = f"{ticker} attrition rate hiring freeze layoffs glassdoor reviews 2024"
        news = self.news_agent.fetch_news(query, count=3)
        return self._analyze_signal(ticker, "Employee Morale", news)

    def _analyze_signal(self, ticker, signal_type, news_items):
        if not news_items:
            return {'signal': 'Neutral', 'details': 'No data found'}
            
        text = "\n".join([f"- {item['title']}: {item['description']}" for item in news_items])
        
        prompt = f"""
        You are an Alternative Data Analyst. Analyze these search results for {ticker} regarding '{signal_type}'.
        
        Search Results:
        {text}
        
        Task:
        1. Determine the Signal: 'Bullish' (Good for stock), 'Bearish' (Bad for stock), 'Neutral'.
           - For Supply Chain: Input costs dropping is Bullish.
           - For Employees: High attrition/Layoffs is Bearish. Hiring spree is Bullish.
        2. Provide a brief summary.
        
        Output JSON:
        {{
            "signal": "Bullish/Bearish/Neutral",
            "details": "string summary"
        }}
        """
        
        try:
            response = self.sentiment_engine.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {'signal': 'Error', 'details': str(e)}
