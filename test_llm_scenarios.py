from ai_option_brain.llm_judge import LLMJudge
import pandas as pd

def run_scenario_test():
    judge = LLMJudge()
    
    print("🧪 Running LLM Scenario Tests (The 'Time Machine' Test)...\n")
    
    scenarios = [
        {
            "name": "The 'Adani Hindenburg' Scenario (Panic)",
            "symbol": "ADANIENT",
            "tech_data": {"edge": 25.0, "adx": 45.0, "market_iv": 60.0, "pred_rv": 85.0},
            "news": "Hindenburg Research accuses Adani Group of stock manipulation. Stocks crash 10%. Regulatory probe likely.",
            "expected": "APPROVE"
        },
        {
            "name": "The 'Boring Earnings' Scenario (IV Crush Risk)",
            "symbol": "INFY",
            "tech_data": {"edge": 18.0, "adx": 20.0, "market_iv": 30.0, "pred_rv": 35.0},
            "news": "Infosys reports stable Q3 earnings, meeting expectations. CEO says demand environment is 'stable'. No surprises.",
            "expected": "REJECT"
        },
        {
            "name": "The 'Merger Rumor' Scenario (Event Vol)",
            "symbol": "ZEEL",
            "tech_data": {"edge": 22.0, "adx": 30.0, "market_iv": 40.0, "pred_rv": 55.0},
            "news": "Sony-Zee merger talks enter final stage. Deal likely to be announced this week. Stock surges 5%.",
            "expected": "APPROVE"
        },
        {
            "name": "The 'Market Crash' Scenario (Systemic Risk)",
            "symbol": "NIFTY",
            "tech_data": {"edge": 16.0, "adx": 60.0, "market_iv": 25.0, "pred_rv": 30.0},
            "news": "Global markets sell off as inflation data comes in hot. Nifty breaks key support level of 18000.",
            "expected": "APPROVE"
        }
    ]
    
    for s in scenarios:
        print(f"🔹 Scenario: {s['name']}")
        print(f"   News: {s['news']}")
        
        verdict = judge.evaluate_trade(s['symbol'], s['tech_data'], s['news'])
        
        print(f"   🤖 Decision: {verdict['decision']} ({verdict['confidence']}%)")
        print(f"   📝 Reasoning: {verdict['reasoning']}")
        print("-" * 60)

if __name__ == "__main__":
    run_scenario_test()
