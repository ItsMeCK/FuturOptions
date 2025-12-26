import re

def analyze():
    log_file = "trend_sim_v2.txt"
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except:
        print("Log file not found.")
        return

    dec24_syms = set()
    dec26_syms = set()
    current_day = "24" # Start with 24
    
    for line in lines:
        if "Simulation Complete for 2025-12-24" in line:
            current_day = "26"
            continue
            
        if "POTENTIAL SIGNAL" in line:
            # Extract Symbol: ... POTENTIAL SIGNAL: LT | Score ...
            try:
                parts = line.split("POTENTIAL SIGNAL:")[1]
                sym = parts.split("|")[0].strip()
                if current_day == "24":
                    dec24_syms.add(sym)
                else:
                    dec26_syms.add(sym)
            except: pass

    print(f"Dec 24 Unique Signals: {len(dec24_syms)}")
    print(f"Stocks: {sorted(list(dec24_syms))}")
    print("-" * 50)
    print(f"Dec 26 Unique Signals: {len(dec26_syms)}")
    print(f"Stocks: {sorted(list(dec26_syms))}")

if __name__ == "__main__":
    analyze()
