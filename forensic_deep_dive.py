import os
import json
from dotenv import load_dotenv
from ai_stock_picker.agents.forensic_agent import ForensicAgent
from ai_stock_picker.agents.alternative_data_agent import AlternativeDataAgent

# Load environment variables
load_dotenv()

def run_deep_dive(ticker="ADANIENT.NS", sector="Energy/Infrastructure"):
    print(f"\n🔬 STARTING INSTITUTIONAL DEEP DIVE ON: {ticker} 🔬")
    print("="*60)
    
    # API Keys
    brave_key = os.getenv("BRAVE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not brave_key or not openai_key:
        print("❌ Error: API Keys missing. Cannot run deep dive.")
        return

    # Initialize Agents
    forensic_agent = ForensicAgent(brave_key, openai_key)
    alt_data_agent = AlternativeDataAgent(brave_key, openai_key)
    
    # 1. Forensic Audit
    print("\n[PHASE 1] 🕵️‍♂️ FORENSIC AUDIT (The 'Kill' Switch)")
    forensic_report = forensic_agent.perform_forensic_audit(ticker)
    print(json.dumps(forensic_report, indent=2))
    
    risk_score = forensic_report.get('Forensic_Risk_Score', 0)
    if risk_score >= 50:
        print(f"\n🚨 CRITICAL WARNING: Forensic Risk Score is {risk_score}/100. RECOMMENDATION: AVOID.")
    else:
        print(f"\n✅ Forensic Check Passed. Risk Score: {risk_score}/100.")

    # 2. Alternative Data
    print("\n[PHASE 2] 📡 ALTERNATIVE DATA (The Engineer's Edge)")
    alt_data = alt_data_agent.fetch_alternative_data(ticker, sector)
    print(json.dumps(alt_data, indent=2))
    
    print("\n" + "="*60)
    print("🏁 DEEP DIVE COMPLETE 🏁")

if __name__ == "__main__":
    # User can change ticker here
    target_ticker = "ADANIENT.NS" 
    target_sector = "Energy/Infrastructure"
    run_deep_dive(target_ticker, target_sector)
