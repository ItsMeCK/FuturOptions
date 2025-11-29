import json
from .news_agent import NewsAgent
from .sentiment_engine import SentimentEngine

class ForensicAgent:
    def __init__(self, brave_key=None, openai_key=None):
        self.news_agent = NewsAgent(api_key=brave_key)
        self.sentiment_engine = SentimentEngine(api_key=openai_key)

    def perform_forensic_audit(self, ticker):
        """
        Performs a 'Forensic Deep Dive' on the company.
        Checks: RPTs, Auditor Remarks (CARO), Remuneration.
        """
        print(f"🕵️‍♂️ Running Forensic Audit for {ticker}...")
        
        report = {
            'RPT_Check': self._check_rpts(ticker),
            'Auditor_Check': self._check_auditor(ticker),
            'Remuneration_Check': self._check_remuneration(ticker)
        }
        
        # Aggregate Score (0 = Clean, 100 = Toxic)
        risk_score = 0
        if report['RPT_Check']['risk'] == 'High': risk_score += 40
        if report['Auditor_Check']['risk'] == 'High': risk_score += 50
        if report['Remuneration_Check']['risk'] == 'High': risk_score += 10
        
        report['Forensic_Risk_Score'] = risk_score
        return report

    def _check_rpts(self, ticker):
        query = f"{ticker} related party transactions percentage of revenue 2024 annual report"
        news = self.news_agent.fetch_news(query, count=3)
        return self._analyze_risk(ticker, "Related Party Transactions", news)

    def _check_auditor(self, ticker):
        query = f"{ticker} auditor qualified opinion CARO report 2024 fraud reporting"
        news = self.news_agent.fetch_news(query, count=3)
        return self._analyze_risk(ticker, "Auditor Remarks (CARO)", news)

    def _check_remuneration(self, ticker):
        query = f"{ticker} CEO salary growth vs net profit growth 2024 controversy"
        news = self.news_agent.fetch_news(query, count=3)
        return self._analyze_risk(ticker, "Management Remuneration", news)

    def _analyze_risk(self, ticker, check_type, news_items):
        if not news_items:
            return {'risk': 'Unknown', 'details': 'No data found'}
            
        text = "\n".join([f"- {item['title']}: {item['description']}" for item in news_items])
        
        prompt = f"""
        You are a Forensic Accountant. Analyze these search results for {ticker} regarding '{check_type}'.
        
        Search Results:
        {text}
        
        Task:
        1. Determine the Risk Level: 'Low' (Clean), 'Medium' (Some concerns), 'High' (Red Flags/Fraud allegations).
        2. Extract key details (e.g., "RPTs are 15% of sales", "Auditor resigned", "CEO salary up 50% while profit down").
        
        Output JSON:
        {{
            "risk": "Low/Medium/High",
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
            print(f"Error in forensic analysis: {e}")
            return {'risk': 'Error', 'details': str(e)}
