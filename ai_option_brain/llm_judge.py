import os
import json
from openai import OpenAI

class LLMJudge:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("⚠️ OpenAI API Key not found! LLM Judge will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def evaluate_trade(self, symbol, technical_data, news_summary):
        """
        Asks the LLM to evaluate a trade proposal.
        Returns: { "decision": "APPROVE"|"REJECT", "confidence": 0-100, "reasoning": "..." }
        """
        if not self.client:
            return {"decision": "APPROVE", "confidence": 50, "reasoning": "LLM Disabled (No Key)"}

        prompt = f"""
        You are a Senior Risk Manager and Professor of Finance at a top university.
        You are evaluating a high-stakes options trade proposal from a quantitative model.

        **The Proposal:**
        *   **Symbol**: {symbol}
        *   **Strategy**: Long Volatility (Buying Straddle/Strangle)
        *   **Technical Edge**: {technical_data.get('edge', 0):.1f}% (Predicted RV > Market IV)
        *   **Trend Strength (ADX)**: {technical_data.get('adx', 0):.1f}
        *   **Market IV**: {technical_data.get('market_iv', 0):.1f}%
        *   **Predicted RV**: {technical_data.get('pred_rv', 0):.1f}%

        **Context (News & Sentiment):**
        {news_summary}

        **Your Task:**
        Analyze the proposal for a **Long Volatility** trade (Profits from Chaos/Big Moves).
        
        **Strategy Logic:**
        *   We WANT significant news (Good OR Bad).
        *   We WANT uncertainty, panic, or euphoria.
        *   We FEAR stability, boredom, and "priced-in" events.

        **Evaluation Criteria:**
        1.  **Volatility Drivers**: Does the news suggest a big move is coming? (e.g., Earnings surprise, CEO exit, Regulatory hit, Merger).
        2.  **The "Priced In" Risk**: Is the news already old? If everyone knows it, IV might crush. Reject if news is stale.
        3.  **Sentiment**: Negative news is GREAT for us (Panic selling). Positive news is GREAT for us (FOMO buying). Neutral news is BAD.
        4.  **TECHNICAL OVERRIDE**: If `Technical Edge` > 80% OR `Trend Strength (ADX)` > 40, you MAY approve even without news. Cite "Technical Breakout" as the reason.

        **Output Format (JSON Only):**
        {{
            "decision": "APPROVE" or "REJECT",
            "confidence": <0-100 integer>,
            "reasoning": "<Concise explanation focusing on Volatility potential>"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Volatility Trader. You love Chaos. You hate Stability."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {"decision": "REJECT", "confidence": 0, "reasoning": f"LLM Error: {e}"}

    def rank_stocks(self, candidates):
        """
        Asks the LLM to pick the Top 10 stocks from a list of candidates.
        candidates: list of dicts {symbol, tech_summary, news_summary}
        Returns: list of symbols ["INFY", "RELIANCE", ...]
        """
        if not self.client:
            return [c['symbol'] for c in candidates[:10]]

        prompt = f"""
        You are the Chief Investment Officer (CIO) starting the day.
        I have {len(candidates)} stocks on my watchlist.
        
        **Your Goal**: Pick the Top 10 stocks that are most likely to have a **Significant Volatility Expansion** today.
        
        **The Candidates**:
        {json.dumps(candidates, indent=2)}
        
        **Selection Criteria**:
        1.  **News Catalyst**: Earnings, Mergers, or Scandals are #1.
        2.  **Technical Setup**: "Squeeze", "Breakout", or "Trend" is #2.
        3.  **Avoid Dead Money**: If news is boring or technicals are flat, ignore it.
        
        **Output Format (JSON Only)**:
        {{
            "focus_list": ["SYMBOL1", "SYMBOL2", "SYMBOL3", "SYMBOL4", "SYMBOL5", "SYMBOL6", "SYMBOL7", "SYMBOL8", "SYMBOL9", "SYMBOL10"],
            "reasoning": "Brief explanation of why these 10 were chosen."
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an aggressive Hedge Fund Manager. You only care about Volatility."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"❌ LLM Ranking Error: {e}")
            return {"focus_list": [c['symbol'] for c in candidates[:10]], "reasoning": "Error fallback"}
