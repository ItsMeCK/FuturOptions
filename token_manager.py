from flask import Flask, request, render_template_string, jsonify
import os
import logging
import json
import time
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Basic Auth
AUTH_PIN = os.environ.get("TOKEN_PIN", "123456") 

# Zerodha Config
API_KEY = os.getenv("ZERODHA_API_KEY")
API_SECRET = os.getenv("ZERODHA_API_SECRET")

# --- DATA HELPERS ---
def load_json_safe(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading {filename}: {e}")
    return {}

def write_token_file(new_token):
    try:
        with open("zerodha_hot_token.txt", "w") as f:
            f.write(new_token.strip())
        os.chmod("zerodha_hot_token.txt", 0o666)
        return True
    except Exception as e:
        logging.error(f"Error writing token file: {e}")
        return False

# --- UI TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sniper Bot Dashboard 🎯</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #2563eb; --bg: #0f172a; --card: #1e293b; --text: #f1f5f9; --green: #22c55e; --red: #ef4444; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 20px; margin: 0; }
        .container { max_width: 1000px; margin: 0 auto; }
        
        /* TABS */
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: var(--card); border-radius: 8px; cursor: pointer; font-weight: 600; opacity: 0.7; }
        .tab.active { background: var(--primary); opacity: 1; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* CARDS */
        .card { background: var(--card); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h2 { margin-top: 0; color: var(--primary); font-size: 1.2rem; display: flex; justify-content: space-between; align-items: center; }
        h3 { margin: 10px 0 5px 0; font-size: 1rem; color: #94a3b8; }
        
        /* TABLES */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { text-align: left; color: #94a3b8; font-size: 0.85rem; padding: 10px; border-bottom: 1px solid #334155; }
        td { padding: 12px 10px; border-bottom: 1px solid #334155; font-size: 0.95rem; }
        tr:last-child td { border-bottom: none; }
        
        .tag { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
        .tag.green { background: rgba(34, 197, 94, 0.2); color: var(--green); }
        .tag.red { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .tag.gray { background: #334155; color: #cbd5e1; }
        
        .pnl-pos { color: var(--green); font-weight: bold; }
        .pnl-neg { color: var(--red); font-weight: bold; }

        /* SETTINGS FORM */
        input { width: 100%; padding: 12px; margin: 5px 0 15px 0; background: #334155; border: 1px solid #475569; color: white; border-radius: 6px; }
        button { width: 100%; padding: 12px; background: var(--primary); color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        button.secondary { background: #475569; margin-top: 10px; }
        
        .toast { padding: 10px; border-radius: 6px; margin-top: 10px; text-align: center; font-weight: bold; }
        .success { background: rgba(34, 197, 94, 0.2); color: var(--green); border: 1px solid var(--green); }
        .error { background: rgba(239, 68, 68, 0.2); color: var(--red); border: 1px solid var(--red); }
        
        .refresh-btn { font-size: 0.8rem; background: #334155; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('dashboard')">📊 Dashboard</div>
            <div class="tab" onclick="switchTab('settings')">⚙️ Token Generator</div>
        </div>

        <!-- DASHBOARD TAB -->
        <div id="dashboard" class="tab-content active">
            
            <!-- ACTIVE TRADES -->
            <div class="card">
                <h2>⚡ Active Trades <span class="refresh-btn" onclick="fetchData()">Refresh</span></h2>
                <div id="trades-container">Loading...</div>
            </div>

            <!-- LIVE LEADERBOARD -->
            <div class="card">
                <h2>🏆 Live Opportunities <span id="scan-time" style="font-size:0.8rem; color:#64748b"></span></h2>
                <div id="scan-container">Loading...</div>
            </div>

        </div>

        <!-- SETTINGS TAB -->
        <div id="settings" class="tab-content">
            <div class="card" style="max-width: 600px; margin: 0 auto;">
                <h2>🔑 Zerodha Token Automation</h2>
                
                {% if message %}
                    <div class="toast {{ status }}">{{ message }}</div>
                    <br>
                {% endif %}

                <form method="POST">
                    <input type="hidden" name="action" value="generate">
                    <label>Security PIN (Required for any action):</label>
                    <input type="password" name="pin" placeholder="Enter PIN" required>
                    
                    <hr style="border-color: #334155; margin: 20px 0;">

                    <!-- STEP 1 -->
                    <h3>1️⃣ Step 1: Login & Get Code</h3>
                    <p style="font-size: 0.9em; color: #cbd5e1;">Click below to login. You will be redirected to a page that fails to load. <b>Copy the 'request_token=xyz...' part from the URL bar.</b></p>
                    <a href="{{ login_url }}" target="_blank" style="display:block; text-align:center; padding:10px; background:#475569; color:white; text-decoration:none; border-radius:6px; font-weight:bold;">👉 Open Zerodha Login</a>
                    
                    <br>

                    <!-- STEP 2 -->
                    <h3>2️⃣ Step 2: Paste Request Token</h3>
                    <input type="text" name="request_token" placeholder="Paste Request Token here (e.g., 3RlwB5...)">
                    <button type="submit">🔄 Generate & Save Access Token</button>

                    <hr style="border-color: #334155; margin: 20px 0;">
                    
                    <!-- MANUAL OVERRIDE -->
                    <h3>⚠️ Manual Override (Optional)</h3>
                    <p style="font-size: 0.9em; color: #cbd5e1;">If the generator fails, paste the final Access Token directly.</p>
                    <input type="text" name="manual_token" placeholder="Paste Full Access Token">
                    <button type="submit" name="action" value="manual" class="secondary">💾 Save Manually</button>
                    
                </form>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Activate clicked
            if(tabId === 'dashboard') document.querySelector('.tab:nth-child(1)').classList.add('active');
            else document.querySelector('.tab:nth-child(2)').classList.add('active');
            
            document.getElementById(tabId).classList.add('active');
        }

        async function fetchData() {
            // 1. Fetch Trades
            try {
                const resTrades = await fetch('/api/trades');
                const trades = await resTrades.json();
                renderTrades(trades);
            } catch(e) { console.error(e); }

            // 2. Fetch Scan
            try {
                const resScan = await fetch('/api/scan');
                const scan = await resScan.json();
                renderScan(scan);
            } catch(e) { console.error(e); }
        }

        function renderTrades(tradesData) {
            const container = document.getElementById('trades-container');
            if (Object.keys(tradesData).length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:20px; color:#64748b">No Active Trades</div>';
                return;
            }

            let html = '<table><thead><tr><th>Symbol</th><th>Entry</th><th>Current</th><th>PnL</th><th>Status</th></tr></thead><tbody>';
            
            for (const [symbol, trade] of Object.entries(tradesData)) {
                const pnlClass = trade.pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
                const pnlSign = trade.pnl >= 0 ? '+' : '';
                html += `<tr>
                    <td><b>${symbol}</b><br><span style="font-size:0.7em;color:#64748b">${trade.option_symbol || '-'}</span></td>
                    <td>${trade.entry_price || 0}</td>
                    <td>${trade.current_price || trade.entry_price}</td>
                    <td class="${pnlClass}">${pnlSign}${parseFloat(trade.pnl).toFixed(2)} (${(trade.pnl_pct*100).toFixed(1)}%)</td>
                    <td><span class="tag green">${trade.status}</span></td>
                </tr>`;
            }
            html += '</tbody></table>';
            container.innerHTML = html;
        }

        function renderScan(scanData) {
            const container = document.getElementById('scan-container');
            if (!scanData.top_picks || scanData.top_picks.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:20px; color:#64748b">No Opportunities Found</div>';
                return;
            }
            
            // Update Time
            document.getElementById('scan-time').innerText = `Updated: ${scanData.timestamp || ''}`;

            let html = '<table><thead><tr><th>Symbol</th><th>Score</th><th>Signal</th><th>RVOL</th><th>Stats</th></tr></thead><tbody>';
            
            scanData.top_picks.forEach(item => {
                const signalClass = item.Signal === 'LONG' ? 'green' : (item.Signal === 'SHORT' ? 'red' : 'gray');
                const scoreColor = item.Score >= 75 ? 'green' : (item.Score >= 60 ? '#fbbf24' : '#64748b');
                
                html += `<tr>
                    <td><b>${item.Symbol}</b><br><span style="font-size:0.7em;color:#64748b">${item.Price}</span></td>
                    <td><b style="color:${scoreColor}">${item.Score}</b></td>
                    <td><span class="tag ${signalClass}">${item.Signal}</span></td>
                    <td>${item.RVOL}</td>
                    <td style="font-size:0.8em; color:#94a3b8">
                        Edge: ${item.Edge}<br>
                        ${item.Reason ? item.Reason.substring(0,20) + '...' : ''}
                    </td>
                </tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }

        // Auto Refresh every 60s
        setInterval(fetchData, 60000);
        fetchData(); 
        
        {% if message %}
            switchTab('settings');
        {% endif %}
    </script>
</body>
</html>
"""

# --- ROUTES ---

@app.route("/", methods=["GET", "POST"])
def home():
    message = ""
    status = ""
    
    # Generate Link using Kite SDK
    login_url = "#"
    if API_KEY:
        try:
            kite = KiteConnect(api_key=API_KEY)
            login_url = kite.login_url()
        except:
            pass

    if request.method == "POST":
        pin = request.form.get("pin")
        action = request.form.get("action")
        
        if pin != AUTH_PIN:
             message = "❌ Invalid PIN!"
             status = "error"
        else:
            # 1. GENERATE FROM REQUEST TOKEN
            if action == "generate":
                req_token = request.form.get("request_token")
                if not req_token:
                    message = "❌ Request Token Missing!"
                    status = "error"
                elif not API_KEY or not API_SECRET:
                    message = "❌ API Key/Secret missing in .env!"
                    status = "error"
                else:
                    try:
                        kite = KiteConnect(api_key=API_KEY)
                        data = kite.generate_session(req_token, api_secret=API_SECRET)
                        access_token = data["access_token"]
                        
                        if write_token_file(access_token):
                            message = "✅ SUCCESS! Access Token Generated & Saved. Brain will reload."
                            status = "success"
                        else:
                            message = "❌ Generated token but failed to save file."
                            status = "error"
                    except Exception as e:
                        message = f"❌ Error Generating Session: {e}"
                        status = "error"

            # 2. MANUAL SAVE
            else:
                manual_token = request.form.get("manual_token")
                if not manual_token:
                     message = "❌ Token cannot be empty!"
                     status = "error"
                elif write_token_file(manual_token):
                     message = "✅ Manual Token Saved!"
                     status = "success"
                else:
                    message = "❌ Failed to write token file."
                    status = "error"

    return render_template_string(HTML_TEMPLATE, message=message, status=status, login_url=login_url)

@app.route("/api/scan")
def get_scan():
    data = load_json_safe("scan_status.json")
    if isinstance(data, list):
         return jsonify({"top_picks": data, "timestamp": "Live"})
    return jsonify(data)

@app.route("/api/trades")
def get_trades():
    return jsonify(load_json_safe("active_trades.json"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
