import os
import subprocess
import time

def run_step(script_name, description):
    print("="*60)
    print(f"🚀 Starting: {description} ({script_name})")
    print("="*60)
    start_time = time.time()
    
    try:
        result = subprocess.run(["python3", script_name], check=True)
        duration = time.time() - start_time
        print(f"✅ Completed: {description} in {duration:.1f}s")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}. Error: {e}")
        exit(1)

def main():
    print("🧠 AI Option Brain: NIFTY 50 MASS SIMULATION")
    print("="*60)
    
    # 1. Feature Engineering
    run_step("run_feature_pipeline.py", "Feature Engineering Pipeline")
    
    # 2. Model Training
    run_step("train_volatility_model.py", "Volatility Model Training")
    
    # 3. Mass Backtest
    run_step("backtest_engine.py", "Mass Backtest Engine")
    
    # 4. Leaderboard
    run_step("calculate_roi.py", "Leaderboard Generation")
    
    print("="*60)
    print("🏁 Full Pipeline Complete.")
    print("   Check ai_option_brain/results/nifty50_leaderboard.csv")

if __name__ == "__main__":
    main()
