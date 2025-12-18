import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.news_fetcher import NewsFetcher
from ai_option_brain.llm_judge import LLMJudge
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

# Load Env
load_dotenv()

class AnalystBrain:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        self.fetcher = ZerodhaDataFetcher(self.api_key, self.access_token)
        self.news_fetcher = NewsFetcher()
        self.llm_judge = LLMJudge()
        
        self.top_20 = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
            "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT",
            "AXISBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI", "ASIANPAINT",
            "TITAN", "SUNPHARMA", "ULTRACEMCO", "TATASTEEL", "NTPC"
        ]

    def run_morning_briefing(self):
        print("☕️ Starting Morning Briefing...")
        candidates = []
        # --- ALPHA LIST (Backtest Winners) ---
        # These stocks showed >100% ROI in the 6-month backtest.
        alpha_list = [
            "ADANIENT", "INDUSINDBK", "INFY", "BEL", "TATASTEEL",
            "BAJAJFINSV", "HINDUNILVR", "HINDALCO", "MARUTI", "BHARTIARTL"
        ]
        print(f"🎯 Analyst Brain: Locking onto Alpha List ({len(alpha_list)} Stocks)")
        
        # Override top_20 with our Alpha List
        top_20 = alpha_list
        
        # --- OLD LOGIC (Disabled for Alpha Mode) ---
        # top_20 = self.get_top_20_momentum() 
        
        print(f"📋 Focus List: {top_20}")
                
        for symbol in top_20:
            try:
                print(f"🔍 Analyzing {symbol}...")
                
                # 1. Fetch Daily Data (Last 30 Days)
                token = self.fetcher.get_instrument_token(symbol)
                df = self.fetcher.fetch_latest_data(token, days=30, interval="day")
                
                if df.empty:
                    continue
                    
                # Selection Criteria (The "Sniper" Logic):
                # 1.  News Catalyst: Earnings, Mergers, or Scandals are #1.
                # 2.  Technical Setup: Look for "Coiled Springs" (Low Bandwidth) ready to explode.
                # 3.  Avoid "Chasing": If a stock is already up 5% today, ignore it (Risk/Reward is bad).
                # 4.  Volume: Rising volume is a plus.
                
                # 2. Technical Summary
                last_price = df['close'].iloc[-1]
                
                # Bollinger Bands
                upper, lower = TechnicalIndicators.calculate_bollinger_bands(df['close'])
                bandwidth = ((upper.iloc[-1] - lower.iloc[-1]) / df['close'].rolling(20).mean().iloc[-1])
                
                # Trend (SMA 50)
                sma_50 = df['close'].rolling(50).mean().iloc[-1]
                trend = "Bullish" if last_price > sma_50 else "Bearish"
                
                # Key Levels (Pivot Points & Recent High/Low)
                # CRITICAL: Use YESTERDAY'S data for Today's Pivots
                # Check if last row is Today
                last_date = df['date'].iloc[-1].date()
                today_date = datetime.now().date()
                
                if last_date == today_date:
                    # Last row is today (incomplete), use previous row
                    prev_day = df.iloc[-2]
                else:
                    # Last row is yesterday (completed)
                    prev_day = df.iloc[-1]
                
                # Calculate Standard Pivots
                p_high = prev_day['high']
                p_low = prev_day['low']
                p_close = prev_day['close']
                
                pivot = (p_high + p_low + p_close) / 3
                r1 = (2 * pivot) - p_low
                s1 = (2 * pivot) - p_high
                
                # Breakout Level: R1 (Aggressive Intraday)
                breakout_level = r1
                
                # Breakdown Level: S1 (Aggressive Intraday)
                breakdown_level = s1
                
                tech_summary = f"Price: {last_price:.1f}, Trend: {trend}, BB Bandwidth: {bandwidth:.2f} (Squeeze < 0.15)"
                
                # 3. News Summary
                news = self.news_fetcher.get_news_summary(symbol)
                
                candidates.append({
                    "symbol": symbol,
                    "tech_summary": tech_summary,
                    "news_summary": news,
                    "key_levels": {
                        "pivot": float(round(pivot, 2)),
                        "resistance_1": float(round(r1, 2)),
                        "support_1": float(round(s1, 2)),
                        "support_1": float(round(s1, 2)),
                        "breakout_level": float(round(breakout_level, 2)),
                        "breakdown_level": float(round(breakdown_level, 2)),
                        "trend": str(trend)
                    }
                })
                
            except Exception as e:
                print(f"⚠️ Error analyzing {symbol}: {e}")
                
        # 4. Ask CIO (LLM) to Rank
        print("\n🧠 Asking CIO to pick Top 10...")
        verdict = self.llm_judge.rank_stocks(candidates)
        
        # 5. Save Focus List
        # Merge LLM Verdict with Technical Data (Key Levels)
        final_focus_list = []
        for symbol in verdict['focus_list']:
            # Find the original candidate data
            candidate = next((c for c in candidates if c['symbol'] == symbol), None)
            if candidate:
                final_focus_list.append({
                    "symbol": symbol,
                    "key_levels": candidate.get('key_levels', {}),
                    "tech_summary": candidate.get('tech_summary', ""),
                    "news_summary": candidate.get('news_summary', "")
                })
            else:
                # Fallback if LLM hallucinates a symbol not in candidates
                final_focus_list.append({"symbol": symbol})

        output = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "focus_list": final_focus_list, # Now a list of DICTS
            "reasoning": verdict['reasoning'],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "last_update": datetime.now().strftime("%H:%M:%S")
        }
        
        with open("focus_list.json", "w") as f:
            json.dump(output, f, indent=4)
            
        print("\n🎯 Focus List Generated:")
        print(json.dumps(output, indent=4))
        return output

if __name__ == "__main__":
    analyst = AnalystBrain()
    analyst.run_morning_briefing()
