import streamlit as st
import pandas as pd
import json
import os
import time
import subprocess
import signal

# Page Config
st.set_page_config(
    page_title="Sniper Options Dashboard",
    page_icon="🎯",
    layout="wide",
)

# Title
st.title("🎯 Sniper Options Dashboard (Nifty 50)")

# Sidebar - Controls
st.sidebar.header("⚙️ Control Panel")
access_token = st.sidebar.text_input("Zerodha Access Token", type="password")

if st.sidebar.button("🚀 Start Scanner"):
    if not access_token:
        st.sidebar.error("Please enter Access Token!")
    else:
        # Save Token to Env (Temporary) or Pass as Arg
        # We will pass it as an environment variable to the subprocess
        env = os.environ.copy()
        env["ZERODHA_ACCESS_TOKEN"] = access_token
        
        # Start Process
        try:
            # Check if already running
            if os.path.exists("scanner.pid"):
                st.sidebar.warning("Scanner is already running!")
            else:
                proc = subprocess.Popen(
                    ["python3", "live_brain.py"],
                    env=env,
                    stdout=open("scanner.log", "a"),
                    stderr=open("scanner.error.log", "a"),
                    preexec_fn=os.setsid # Detach
                )
                with open("scanner.pid", "w") as f:
                    f.write(str(proc.pid))
                st.sidebar.success(f"Scanner Started! PID: {proc.pid}")
        except Exception as e:
            st.sidebar.error(f"Failed to start: {e}")

if st.sidebar.button("🛑 Stop Scanner"):
    if os.path.exists("scanner.pid"):
        try:
            with open("scanner.pid", "r") as f:
                pid = int(f.read())
            os.killpg(os.getpgid(pid), signal.SIGTERM) # Kill Group
            os.remove("scanner.pid")
            st.sidebar.success("Scanner Stopped.")
        except Exception as e:
            st.sidebar.error(f"Error stopping: {e}")
            if os.path.exists("scanner.pid"): os.remove("scanner.pid") # Cleanup force
    else:
        st.sidebar.warning("Scanner is not running.")

# Main Area - Status
st.header("📡 System Status")

# Heartbeat Check
is_online = False
if os.path.exists("heartbeat.txt"):
    try:
        with open("heartbeat.txt", "r") as f:
            last_beat = float(f.read())
        if time.time() - last_beat < 120: # 2 Mins tolerance
            is_online = True
    except:
        pass

if is_online:
    st.success("🟢 SYSTEM ONLINE (Heartbeat Detected)")
else:
    st.error("🔴 SYSTEM OFFLINE")

# Active Trades
st.header("💰 Active Trades")
if os.path.exists("active_trades.json"):
    try:
        with open("active_trades.json", "r") as f:
            trades = json.load(f)
        
        if trades:
            df = pd.DataFrame.from_dict(trades, orient='index')
            st.dataframe(df)
            
            # P&L Summary
            total_pnl = df['pnl'].sum() if 'pnl' in df.columns else 0
            st.metric("Total Unrealized P&L", f"₹{total_pnl:.2f}")
        else:
            st.info("No active trades.")
    except Exception as e:
        st.error(f"Error reading trades: {e}")
else:
    st.info("No active trades file found.")

# Live Scanner Status
st.header("📡 Live Scanner Feed")
if os.path.exists("scan_status.json"):
    try:
        status_df = pd.read_json("scan_status.json")
        
        # Apply Styling
        # Apply Styling
        def color_score(val):
            if isinstance(val, (int, float)):
                if val >= 75: return 'background-color: #28a745; color: white' # Green
                if val < 60: return 'background-color: #dc3545; color: white' # Red
                return 'background-color: #ffc107; color: black' # Yellow
            return ''

        # Rename Score to Smoothed Score for display if needed, but the column name in JSON is "Score"
        # We will just keep "Score" but know it is smoothed.
        st.dataframe(status_df.style.map(color_score, subset=['Score']), use_container_width=True)
        st.caption("Note: Score is a 5-minute smoothed average to reduce volatility.")
    except Exception as e:
        st.error(f"Error reading status: {e}")
else:
    st.info("Waiting for scanner data...")

# Logs
st.header("📜 System Logs")
if os.path.exists("scanner.log"):
    with open("scanner.log", "r") as f:
        lines = f.readlines()
        last_lines = lines[-50:] # Show last 50
        log_text = "".join(last_lines)
        st.text_area("Logs", log_text, height=200) # Scrollable Area
else:
    st.text("No logs yet.")

# Auto-Refresh
time.sleep(5)
st.rerun()
