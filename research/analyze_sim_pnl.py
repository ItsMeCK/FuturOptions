
def analyze():
    log_file = "trend_sim_v5.txt"
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except:
        print("Log file not found.")
        return

    dec24_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'open': 0}
    dec26_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'open': 0}
    
    current_day = "24"
    
    for line in lines:
        if "Simulation Complete for 2025-12-24" in line:
            current_day = "26"
            continue
            
        stats = dec24_stats if current_day == "24" else dec26_stats
        
        if "🚀 Sim Trade:" in line:
            stats['trades'] += 1
        elif "💰 TARGET HIT:" in line:
            stats['wins'] += 1
        elif "🛑 STOP HIT:" in line:
            stats['losses'] += 1
            
    # Calculate Open
    dec24_stats['open'] = dec24_stats['trades'] - dec24_stats['wins'] - dec24_stats['losses']
    dec26_stats['open'] = dec26_stats['trades'] - dec26_stats['wins'] - dec26_stats['losses']
    
    print("-" * 50)
    print("📊 REALISTIC SIMULATION RESULTS (30% Profit / 10% Stop)")
    print("-" * 50)
    
    # Dec 24
    d = dec24_stats
    print(f"📅 DEC 24:")
    print(f"   Trades Executed: {d['trades']}")
    print(f"   ✅ Target Hit:   {d['wins']}")
    print(f"   🛑 Stop Hit:     {d['losses']}")
    print(f"   ⏳ Open EOD:     {d['open']}")
    
    # Dec 26
    d = dec26_stats
    print(f"\n📅 DEC 26:")
    print(f"   Trades Executed: {d['trades']}")
    print(f"   ✅ Target Hit:   {d['wins']}")
    print(f"   🛑 Stop Hit:     {d['losses']}")
    print(f"   ⏳ Open EOD:     {d['open']}")

if __name__ == "__main__":
    analyze()
