import os
import json
import time
import pandas as pd
import numpy as np
import logging
import sys
from datetime import datetime, timedelta
from trade_manager import TradeManager
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.utils.technical_indicators import TechnicalIndicators
from ai_option_brain.llm_judge import LLMJudge
from ai_option_brain.news_fetcher import NewsFetcher
from ai_option_brain.options_brain import OptionsBrain
import joblib
from collections import deque, defaultdict

# --- STABILITY LAYER ---
class ScoreHistory:
    def __init__(self, max_len=5):
        self.scores = deque(maxlen=max_len)
        self.persistence = {} # {factor: timestamp}
        
    def add_score(self, score):
        self.scores.append(score)
        
    def get_smoothed_score(self):
        if not self.scores:
            return 0
        return sum(self.scores) / len(self.scores)
        
    def update_persistence(self, factor):
        self.persistence[factor] = datetime.now()
        
    def is_persistent(self, factor, duration_minutes=15):
        if factor not in self.persistence:
            return False
        elapsed = (datetime.now() - self.persistence[factor]).total_seconds() / 60
        return elapsed < duration_minutes

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scanner.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

from dotenv import load_dotenv

# Load Env
load_dotenv()

class LiveBrain:
    def __init__(self):
        self.tm = TradeManager()
        self.llm_judge = LLMJudge()
        self.news_fetcher = NewsFetcher()
        self.news_fetcher = NewsFetcher()
        
        # Load Token (Priority: Hot File > Env)
        self.access_token = self.load_initial_token()
        
        if self.access_token:
            # Initialize Fetcher with explicit token
            self.fetcher = ZerodhaDataFetcher(access_token=self.access_token)
            self.options_brain = OptionsBrain(self.fetcher)
        else:
            logging.warning("⚠️ No Access Token found! Running in Simulation/Fallback Mode.")
            self.fetcher = ZerodhaDataFetcher() # Will likely fail or be empty
            self.options_brain = OptionsBrain(self.fetcher)

        self.top_20 = self.load_top_20()
        self.models = self.load_models()
        self.history = defaultdict(ScoreHistory) # Symbol -> ScoreHistory
        self.running = True
        self.simulation_time = None
        self.last_processed_candle = {} # Track last processed candle timestamp per symbol
        self.last_leaderboard_update = 0 # Unix timestamp of last scan
        self.universe_index = 0 # For rolling sweep
        self.batch_size = 55    # Stocks per minute
        self.all_scan_results = {} # Master Memory for Dashboard (Persistent)
        
        # Load F&O Universe
        self.universe = []
        if os.path.exists("fno_universe.txt"):
            with open("fno_universe.txt") as f:
                self.universe = [line.strip() for line in f if line.strip()]
            logging.info(f"🌌 Loaded F&O Universe: {len(self.universe)} items")
            
        self.focus_list = ['ADANIENT', 'SBIN', 'ICICIBANK', 'INFY', 'TATASTEEL']  # Default Fallback

    def calculate_efficiency_ratio(self, close_series, period=6):
        """
        Efficiency Ratio = Abs(Net Change) / Sum(Abs(Change))
        Measures directional efficiency vs noise.
        """
        if len(close_series) < period+1: return 1.0
        
        net_change = abs(close_series.iloc[-1] - close_series.iloc[-period-1])
        diffs = np.diff(close_series.iloc[-period-1:])
        total_path = np.sum(np.abs(diffs))
        
        if total_path == 0: return 1.0
        return net_change / total_path

    def load_initial_token(self):
        """Load token with priority: File > Env."""
        hot_file = "zerodha_hot_token.txt"
        if os.path.exists(hot_file):
            try:
                with open(hot_file, "r") as f:
                    token = f.read().strip()
                if token:
                    logging.info("hj Access Token loaded from Hot File.")
                    return token
            except Exception as e:
                logging.error(f"Error reading hot file in init: {e}")
        
        # Fallback to Env
        logging.info("📂 Access Token loaded from .env (Fallback).")
        return os.environ.get("ZERODHA_ACCESS_TOKEN")

        self.top_20 = self.load_top_20()
        self.models = self.load_models()
        self.history = defaultdict(ScoreHistory) # Symbol -> ScoreHistory
        self.running = True
        self.simulation_time = None
        self.last_processed_candle = {} # Track last processed candle timestamp per symbol


    def pre_scan_market(self):
        """
        Efficiently scan the full F&O Universe (200+ stocks) using Quote API.
        Returns: Top 25 Most Active/Volatile stocks to deep-scan.
        """
        if not self.universe or not self.fetcher:
            return self.top_20
            
        try:
            # Batch Fetch (Zerodha allows large batches)
            # Prefix with NSE:
            exchange_symbols = [f"NSE:{s}" for s in self.universe]
            
            # Split into chunks of 500 (API Limit) - Though universe is ~200
            quotes = self.fetcher.fetch_live_quote(exchange_symbols)
            
            if not quotes:
                return self.top_20
                
            # Filter & Sort
            # Criteria: High Volume AND % Change > 0.5%
            candidates = []
            
            for sym, data in quotes.items():
                clean_sym = sym.replace('NSE:', '')
                ohlc = data.get('ohlc', {})
                last_price = data.get('last_price', 0)
                open_price = ohlc.get('open', 0)
                volume = data.get('volume', 0)
                
                # Calculate % Change
                pct_change = 0
                if open_price > 0:
                    pct_change = abs((last_price - open_price) / open_price) * 100
                    
                candidates.append({
                    'symbol': clean_sym,
                    'volume': volume,
                    'pct_change': pct_change,
                    'last_price': last_price
                })
            
            # Sort by Activity (% Change is Opportunity)
            candidates.sort(key=lambda x: x['pct_change'], reverse=True)
            
            # Select Top 20 Movers
            top_movers = [x['symbol'] for x in candidates[:20]]
            
            # Also ensure Top 5 Volume Leaders are present
            candidates.sort(key=lambda x: x['volume'], reverse=True)
            top_volume = [x['symbol'] for x in candidates[:5]]
            
            # Combine Unique
            final_list = list(set(top_movers + top_volume))
            
            logging.info(f"🌌 Universe Scan: Selected {len(final_list)} Active Stocks (Top Mover: {candidates[0]['symbol']})")
            return final_list
            
        except Exception as e:
            logging.error(f"Pre-Scan Failed: {e}")
            return self.top_20

    def update_leaderboard(self):
        """Refreshes the Focus List based on Market Activity."""
        logging.info("↻ Update Leaderboard Triggered...")
        
        # Method 1: Use Pre-Scan (Internal Data)
        if self.universe:
            logging.info("Running Pre-Scan on F&O Universe...")
            self.focus_list = self.pre_scan_market()
            # Update top_20 reference too for consistency
            self.top_20 = self.focus_list
            return
            
        # Method 2: External Scraping (Fallback)
        try: 
            new_list = self.fetch_leaderboard_data() 
            if new_list:
                self.focus_list = new_list
                self.top_20 = new_list
                logging.info(f"✅ Leaderboard Updated: {len(self.focus_list)} stocks")
            else:
                logging.warning("⚠️ Leaderboard fetch failed. Retaining old list.")
        except Exception as e:
            logging.error(f"Error updating leaderboard: {e}")

    def load_top_20(self):
        try:
            df = pd.read_csv("ai_option_brain/results/nifty50_leaderboard.csv")
            top_20 = df.head(20)['Symbol'].tolist()
            logging.info(f"🏆 Loaded Top 20 Stocks: {top_20}")
            return top_20
        except Exception as e:
            logging.error(f"❌ Error loading leaderboard: {e}")
            return []

    def load_models(self):
        models = {}
        for symbol in self.top_20:
            try:
                model_path = f"ai_option_brain/models/{symbol}_vol_model.pkl"
                if os.path.exists(model_path):
                    models[symbol] = joblib.load(model_path)
            except Exception as e:
                logging.error(f"❌ Error loading model for {symbol}: {e}")
        logging.info(f"🧠 Loaded {len(models)} Volatility Models.")
        return models

    def calculate_confluence_score(self, symbol, price, adx, trend_dist, rsi, bandwidth, upper_band, rvol, vwap_dist, pred_rv, market_iv, focus_data, history=None, rvol_5m_avg=0, is_momentum_active=False, er_value=1.0, vol_ratio=1.0, vwap_value=0):
        score = 0
        reasons = []
        edge = 0.0
        
        # 0. ANALYST BIAS
        analyst_bias = False
        breakout_lvl = 0.0
        breakdown_lvl = 0.0
        
        if symbol in focus_data:
            data = focus_data[symbol]
            breakout_lvl = float(data.get('breakout_level', 0))
            breakdown_lvl = float(data.get('breakdown_level', 0))
            
            if breakout_lvl > 0:
                dist_to_breakout = (breakout_lvl - price) / price
                if 0 < dist_to_breakout < 0.005: 
                    score += 20
                    reasons.append(f"Near Breakout {breakout_lvl}")
                    analyst_bias = True
            
            if breakdown_lvl > 0:
                dist_to_breakdown = (price - breakdown_lvl) / price
                if 0 < dist_to_breakdown < 0.005:
                    score += 20
                    reasons.append(f"Near Breakdown {breakdown_lvl}")
                    analyst_bias = True
            
        # 1. Trend Quality (ADX) - UNIVERSITY FILTER
        # Optimization showed ADX < 25 leads to negative expectancy.
        if adx < 25:
            reasons.append("ADX < 25 (Choppy)")
            # Soft penalty: No trend points (15), but keep other score components
        else:
            # If passed, give points
            score += 15
            reasons.append(f"Strong Trend (ADX {adx:.1f})")
            if history: history.update_persistence('trend')

        # --- SMART FILTERS (INSTITUTIONAL) ---
        # 1. Churn Block
        if er_value < 0.3:
            # Harsh Penalty to Block Entry
            score = 0 
            reasons = [f"BLOCKED: Churn (ER {er_value:.2f})"]
            return {'score': 0, 'reasons': reasons, 'signal_type': 'NEUTRAL'}
            
        # 2. Vacuum Block
        if vol_ratio < 0.8:
            score = 0
            reasons = [f"BLOCKED: Vol Dryup (Ratio {vol_ratio:.2f})"]
            return {'score': 0, 'reasons': reasons, 'signal_type': 'NEUTRAL'}
            
        # 2. Momentum (Price vs SMA50)
        threshold = 0.02
        if trend_dist > threshold:
            score += 10
            reasons.append("Above SMA50")
        elif trend_dist < -threshold:
            score += 10
            reasons.append("Below SMA50")
            
        # 3. Volatility Squeeze
        if bandwidth < 0.10:
            score += 15
            reasons.append("Vol Squeeze")
            if history: history.update_persistence('squeeze')
            
        # 4. Volume Flow - UNIVERSITY LOGIC
        # Priority 1: Ignition (Fresh Breakout)
        effective_rvol = max(rvol, rvol_5m_avg)
        
        if effective_rvol > 2.0:
            score += 30 # Massive Bonus
            reasons.append(f"IGNITION Vol ({effective_rvol:.1f}x)")
        elif is_momentum_active and effective_rvol > 0.5:
             score += 20 # Continuation Bonus
             reasons.append(f"Momentum Active ({effective_rvol:.1f}x)")
        elif effective_rvol > 1.5:
             score += 15
             reasons.append(f"High Vol ({effective_rvol:.1f}x)")
            
        # 5. AI Edge
        if pred_rv > market_iv * 1.1:
            edge = (pred_rv - market_iv)
            score += 20
            reasons.append(f"AI Edge (+{edge:.1f}%)")
            
        # 6. VWAP Reversion
        if price > vwap_dist:
             score += 5
        
        # DETERMINE DIRECTION
        signal_type = "NEUTRAL"
        
        # Safety: Force NEUTRAL if trend is weak (ADX < 25)
        if adx < 25:
            signal_type = "NEUTRAL"
        elif price > upper_band or (breakout_lvl > 0 and price > breakout_lvl):
            signal_type = "LONG"
        elif price < (upper_band - (upper_band * bandwidth)) or (breakdown_lvl > 0 and price < breakdown_lvl):
            signal_type = "SHORT"
            
        return {
            "score": score,
            "reasons": reasons,
            "edge": edge,
            "breakout_lvl": breakout_lvl,
            "breakdown_lvl": breakdown_lvl,
            "signal_type": signal_type
        }

    def get_now(self):
        """Return current time (or simulation time)."""
        if hasattr(self, 'simulation_time') and self.simulation_time:
            return self.simulation_time
        return datetime.now()

    def heartbeat(self):
        """Update heartbeat file for Dashboard."""
        with open("heartbeat.txt", "w") as f:
            f.write(str(time.time()))

    def run(self):
        logging.info("🚀 Sniper Engine STARTED.")
        
        # Define Timezone
        try:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
        except ImportError:
            logging.error("pytz not found. Using system time.")
            ist = None
        
        while self.running:
            try:
                self.heartbeat() # Pulse check
                
                # --- MARKET HOURS CHECK (IST) ---
                if ist:
                    now = datetime.now(ist)
                else:
                    now = datetime.now() # Fallback
                    
                current_time = now.time()
                
                start_time = datetime.strptime("09:00", "%H:%M").time()
                end_time = datetime.strptime("15:30", "%H:%M").time()
                
                # Simulation Mode Bypass
                if getattr(self, 'simulation_time', None):
                    self.scan_market()
                    continue
                    
                # Market Closed Logic
                market_open = start_time <= current_time <= end_time
                
                if not market_open:
                    logging.info(f"🌙 Market Closed (IST: {current_time.strftime('%H:%M:%S')}). Sleeping...")
                    time.sleep(300) # Sleep 5 Minutes
                    continue
                
                # Market Open
                self.check_hot_reload()
                
                # --- DYNAMIC SCANNER TRIGGER ---
                # Run update whenever market opens, and then every 15 mins
                if (time.time() - self.last_leaderboard_update) > 900: # 15 minutes
                    self.update_leaderboard()
                    self.last_leaderboard_update = time.time()
                
                self.scan_market()
                time.sleep(60)
                    
            except KeyboardInterrupt:
                logging.info("🛑 Brain Stopped.")
                break
            except Exception as e:
                logging.error(f"🔥 Critical Error in Main Loop: {e}")
                time.sleep(10)

    def check_hot_reload(self):
        """Check for fresh token in hot file and reload if found."""
        hot_file = "zerodha_hot_token.txt"
        
        if os.path.exists(hot_file):
            try:
                with open(hot_file, "r") as f:
                    new_token = f.read().strip()
                
                # Debug Logging (Masked)
                current_masked = f"{self.access_token[:6]}...{self.access_token[-4:]}" if self.access_token else "None"
                new_masked = f"{new_token[:6]}...{new_token[-4:]}" if new_token else "Empty"
                
                logging.info(f"🔎 Hot Reload Check: Current={current_masked} New={new_masked}")
                
                if new_token and new_token != self.access_token:
                    logging.info(f"🔄 Hot Reload Triggered! Updating Token...")
                    logging.info(f"   Old: {current_masked}")
                    logging.info(f"   New: {new_masked}")
                    
                    # Update Internal State
                    self.access_token = new_token
                    
                    # Re-Initialize Fetcher & Brain
                    self.fetcher = ZerodhaDataFetcher(access_token=self.access_token)
                    self.options_brain = OptionsBrain(self.fetcher)
                    
                    # Verify Fetcher
                    if self.fetcher.kite:
                         logging.info(f"   ✅ Fetcher Re-initialized with Token: {self.fetcher.access_token[:6]}...")
                    else:
                         logging.error("   ❌ Fetcher Init Failed (Kite object is None)")
                    
                    logging.info("✅ Hot Reload Complete. New Token Active.")
                    
                    # Clear the file to prevent repeated re-init (optional, but good practice to avoid file IO every loop if logic is buggy)
                    # Actually, we rely on equality check (new != current). So keeping file is fine.
                    
            except Exception as e:
                logging.error(f"⚠️ Hot Reload Failed: {e}")
        else:
             logging.warning(f"⚠️ Hot Token File Not Found: {os.path.abspath(hot_file)}")

    def scan_market(self):
        """Single iteration of the scanning logic."""
        now = self.get_now()
        
        logging.info(f"⏳ Scanning Market... {now.strftime('%H:%M:%S')}")
        
        # 0. ROLLING UNIVERSE SWEEP (60 stocks per loop)
        full_universe = getattr(self, 'universe', [])
        
        if full_universe:
            # Slice the next batch
            start = self.universe_index
            end = start + self.batch_size
            
            # Extract batch (with wrapping)
            focus_list = full_universe[start:end]
            
            # If we didn't get a full batch (reached end), wrap around
            if len(focus_list) < self.batch_size:
                remainder = self.batch_size - len(focus_list)
                focus_list += full_universe[0:remainder]
                self.universe_index = remainder
            else:
                self.universe_index = (self.universe_index + self.batch_size) % len(full_universe)
                
            logging.info(f"🔄 Rolling Sweep: Batch [{start}:{end}] | Stocks: {len(focus_list)}")
        else:
            focus_list = getattr(self, 'focus_list', [])
            
        focus_data = {} 
        focus_reason = "Rolling Sweep"
        
        # Fallback to Analyst's JSON only if we have NO universe and NO selection
        if not focus_list and os.path.exists("focus_list.json"):
            try:
                with open("focus_list.json", "r") as f:
                    data = json.load(f)
                    # Check if list is from today (or same date as simulation)
                    current_date_str = now.strftime("%Y-%m-%d")
                    
                    if data.get('date') == current_date_str:
                        raw_list = data.get('focus_list', [])
                        # Handle new list of dicts format
                        if raw_list and isinstance(raw_list[0], dict):
                            focus_list = [item['symbol'] for item in raw_list]
                            focus_data = {item['symbol']: item for item in raw_list}
                        else:
                            # Fallback for old format (list of strings)
                            focus_list = raw_list
                            focus_data = {}
                            
                        focus_reason = data.get('reasoning', "Analyst Picks")
                        logging.info(f"🎯 Using Focus List ({len(focus_list)} stocks): {focus_list}")
                    else:
                        logging.warning(f"⚠️ Focus List is outdated (Date: {data.get('date')} vs Now: {current_date_str}). Using Leaderboard.")
                        focus_list = [] # STRICT: No fallback
            except Exception as e:
                logging.error(f"Error reading focus list: {e}")
        
        # FALLBACK LOGIC
        if not focus_list:
            if self.top_20:
                focus_list = self.top_20[:20] # Take top 20
                focus_reason = "Fallback to Leaderboard"
                logging.info(f"⚠️ Focus List Missing/Outdated. Falling back to Top 20 Leaderboard: {focus_list}")
            else:
                 logging.warning("⚠️ No Focus List AND No Leaderboard. Snoozing...")
                 time.sleep(10)
                 return
                 
        if not focus_list: # Double check
            logging.info("💤 No active Focus List. Snoozing...")
            time.sleep(10)
            return
        # 1. Batch Fetch Live Quotes (For Focus List + VIX)
        # Ensure we fetch what we need!
        symbols_to_fetch = list(set(focus_list + ['INDIA VIX']))
        
        try:
            quotes = self.fetcher.fetch_live_quote(symbols_to_fetch)
            logging.info(f"Fetched {len(quotes)} quotes. Keys: {list(quotes.keys())}")
        except Exception as e:
            logging.error(f"Error fetching quotes: {e}")
            quotes = {}

        # Get VIX
        vix_value = 0
        if 'INDIA VIX' in quotes:
            vix_value = quotes['INDIA VIX']['last_price']
        
        # Regime Filter: Goldilocks Zone (11-20)
        vix_status = "OK"
        if vix_value < 11: vix_status = "LOW (Complacency)"
        elif vix_value > 20: vix_status = "HIGH (Panic)"

        # No local scan_results initialization here to keep all_scan_results persistent
        
        for symbol in focus_list:
            # Default Values
            market_iv = 0.0
            pred_rv = 0.0
            trend = "Neutral"
            adx_value = 0
            last_price = 0.0
            trend_dist = 0.0
            rsi = 50.0  # Default neutral
            upper_band = 0.0
            middle_band = 0.0 # Added critical default
            bandwidth = 0.0
            vwap_value = 0.0
            rvol = 0.0
            
            llm_conf = "-"
            llm_decision = "-"
            
            # Additional defaults needed for confluence call
            # ... initialized above already
            
            if symbol in quotes:
                last_price = quotes[symbol]['last_price']
                ohlc = quotes[symbol]['ohlc']
                
                # 1. Market IV Initial Proxy (Fallback)
                market_iv = vix_value * 1.2 
                
                # 2. Fetch Historical Data & Calculate Technicals
                try:
                    token = self.fetcher.get_instrument_token(symbol)
                    
                    # --- 5-MINUTE STRATEGY UPGRADE ---
                    hist_df = self.fetcher.fetch_latest_data(token, days=5, interval="5minute")
                    
                    if hist_df is not None and not hist_df.empty:
                        # NEW CANDLE CHECK
                        last_candle_time = hist_df.index[-1]
                        

                        # Mark this candle as processed
                        self.last_processed_candle[symbol] = last_candle_time
                        
                        # Use the candle as is (It is the latest completed candle)
                        # We do NOT drop the last row here because we are gating by timestamp uniqueness.
                        # If API returns forming candle, we might trade early, but deduplication prevents re-trading same candle.
                        # Ideally we want COMPLETED candle. 
                        # Assuming Zerodha Historical returns completed or we accept the slight noise of forming 5-min count.
                        
                        # Calculate Features
                        # Debug: Check Data Integrity
                        if not hist_df.empty:
                             # logging.info(f"🐛 {symbol} Data Head: {hist_df.head(1).to_dict()}")
                             if 'volume' not in hist_df.columns:
                                 logging.error(f"❌ {symbol}: 'volume' column missing! Cols: {hist_df.columns}")
                        
                        hist_df['close'] = hist_df['close']
                        hist_df['log_ret'] = np.log(hist_df['close'] / hist_df['close'].shift(1))
                        # ... rest of calc ...

                        # ...
                        
                        # RVOL (Relative Volume)
                        # Ensure volume is numeric
                        hist_df['volume'] = pd.to_numeric(hist_df['volume'], errors='coerce').fillna(0)
                        
                        vol_sma = hist_df['volume'].rolling(20).mean().iloc[-1]
                        current_vol = hist_df['volume'].iloc[-1]
                        rvol = current_vol / vol_sma if vol_sma > 0 else 0
                        
                        # logging.info(f"📊 {symbol} Vol: {current_vol}, SMA: {vol_sma}, RVOL: {rvol}")

                        # ...


                        hist_df['hv_10'] = hist_df['log_ret'].rolling(10).std() * np.sqrt(252*375) * 100
                        hist_df['hv_20'] = hist_df['log_ret'].rolling(20).std() * np.sqrt(252*375) * 100
                        
                        # Update Market IV Proxy
                        market_iv = hist_df['hv_20'].iloc[-1]
                        
                        # Trend Dist
                        sma_50 = hist_df['close'].rolling(50).mean().iloc[-1]
                        trend_dist = (last_price - sma_50) / sma_50 if pd.notna(sma_50) else 0
                        
                        # RSI
                        rsi = TechnicalIndicators.calculate_rsi(hist_df['close'], period=14).iloc[-1] if len(hist_df) > 14 else 50
                        
                        # ADX
                        adx = TechnicalIndicators.calculate_adx(hist_df['high'], hist_df['low'], hist_df['close'], window=14)
                        adx_value = adx.iloc[-1] if not adx.empty else 0
                        
                        # Bollinger Bands
                        upper, lower = TechnicalIndicators.calculate_bollinger_bands(hist_df['close'], period=20, std_dev=2)
                        upper_band = upper.iloc[-1]
                        middle_band = hist_df['close'].rolling(20).mean().iloc[-1]
                        lower_band = lower.iloc[-1]
                        bandwidth = (upper_band - lower_band) / middle_band if middle_band != 0 else 0
                        
                        # VWAP (Intraday)
                        vwap_series = TechnicalIndicators.calculate_vwap(hist_df)
                        vwap_value = vwap_series.iloc[-1] if not vwap_series.empty else 0
                        # RVOL (Relative Volume)
                        vol_sma = hist_df['volume'].rolling(20).mean().iloc[-1]
                        current_vol = hist_df['volume'].iloc[-1]
                        rvol = current_vol / vol_sma if vol_sma > 0 else 0
                        
                        # Smart Volume
                        rvol_rolling = (hist_df['volume'] / vol_sma) 
                        rvol_5m_avg = rvol_rolling.tail(5).mean() if len(hist_df) >= 5 else rvol
                        
                        # --- SMART METRICS ---
                        # Efficiency Ratio (Last 30m = 6 bars)
                        er_value = self.calculate_efficiency_ratio(hist_df['close'], period=6)
                        
                        # Volume Ratio (Current 30m vs Prev 30m)
                        # We need at least 12 bars (60 mins)
                        vol_ratio = 1.0
                        if len(hist_df) >= 12:
                            curr_vol30 = hist_df['volume'].tail(6).mean()
                            prev_vol30 = hist_df['volume'].iloc[-12:-6].mean()
                            vol_ratio = curr_vol30 / prev_vol30 if prev_vol30 > 0 else 0
                        
                        logging.info(f"🔍 {symbol}: RVOL={rvol:.2f}, ER={er_value:.2f}, VolRatio={vol_ratio:.2f}")

                        # Trend Status
                        if adx_value > 25:
                            trend = "Strong 🟢"
                        else:
                            trend = "Weak 🔴"

                        # 3. Predict RV 
                        if symbol in self.models:
                            features = pd.DataFrame([{
                                'hv_10': hist_df['hv_10'].iloc[-1],
                                'hv_20': hist_df['hv_20'].iloc[-1],
                                'log_ret': hist_df['log_ret'].iloc[-1],
                                'trend_dist': trend_dist,
                                'rsi': rsi,
                                'india_vix': vix_value
                            }])
                            pred_rv = self.models[symbol].predict(features)[0]
                        else:
                            pred_rv = market_iv 
                            rejection_reason = "Model Missing (Using HV)"

                    else:
                        trend = "No Data ⚠️"
                        rejection_reason = "Data Fetch Failed"
                        
                except Exception as e:
                    logging.error(f"Calc Error {symbol}: {e}")
                    trend = "Error ⚠️"
                
            else:
                trend = "Data Error ⚠️"
                rejection_reason = "Quote Missing"

            # 3. INSTITUTIONAL CONFLUENCE SCORE (0-100)
            if last_price > 0:
                hist = self.history[symbol]
                # Momentum State (University Logic)
                # Check last 5 candles (excluding current forming one at -1) for Ignition
                is_momentum_active = False
                if len(hist_df) > 6:
                    # Recalculate rolling series for context
                    # Note: vol_sma is a scalar at -1. We need series.
                    vol_sma_series = hist_df['volume'].rolling(20).mean()
                    rvol_series = hist_df['volume'] / vol_sma_series
                    
                    # Slice: Last 5 COMPLETED candles (-6 to -1)
                    # Actually just check lookback window=5
                    window_close = hist_df['close'].iloc[-6:-1]
                    window_upper = upper.iloc[-6:-1]
                    window_rvol = rvol_series.iloc[-6:-1]
                    
                    # Condition: Close > Upper AND RVOL > 2.0
                    ignition_mask = (window_close > window_upper) & (window_rvol > 2.0)
                    if ignition_mask.any():
                        is_momentum_active = True

                confluence = self.calculate_confluence_score(
                    symbol, last_price, adx_value, trend_dist, rsi, 
                    bandwidth, upper_band, rvol, 0, pred_rv, market_iv, focus_data, 
                    history=self.history[symbol],
                    rvol_5m_avg=rvol_5m_avg,
                    is_momentum_active=False,
                    er_value=er_value,
                    vol_ratio=vol_ratio,
                    vwap_value=vwap_value
                )
                
                raw_score = confluence['score']
                hist.add_score(raw_score)
                score = int(hist.get_smoothed_score())
                
                reasons = confluence['reasons']
                edge = confluence['edge']
                breakout_lvl = confluence['breakout_lvl']
                breakdown_lvl = confluence['breakdown_lvl']
                signal_type = confluence['signal_type'] 
            else:
                score = 0
                reasons = ["No Price"]
                edge = 0.0
                breakout_lvl = 0.0
                breakdown_lvl = 0.0
                signal_type = "NEUTRAL" 
            
            # LOGGING UNIVERSITY LOGIC FOR USER VISIBILITY
            if score > 0 or is_momentum_active:
                state_str = "🔥 IGNITION/ACTIVE" if is_momentum_active else "💤 WAIT"
                logging.info(f"📊 {symbol} {state_str} | Score: {score} | {reasons}")

            # DECISION LOGIC
            signal = False
            status = "WAIT"
            rejection_reason = f"Score {score}/100: {', '.join(reasons)}"
            
            if score < 60:
                status = "WAIT"
            elif 60 <= score < 75:
                status = "STALKING"
                logging.info(f"👀 Stalking {symbol} (Score {score})...")

                # Brain 1 (Technical) says: BUY (Score >= 75) -> Wait, logic below says check anyway? No, check if >60 for Stalking.
                # Logic below:
                
            # --- PHASE 21: HYBRID BRAIN (Type A + Type B + Type C) ---
            opt_sentiment, opt_data = self.options_brain.analyze_sentiment(symbol, last_price)
            logging.info(f"🧠 Options Brain for {symbol}: {opt_sentiment} ({opt_data['reason']})")
            
            # Feature Extraction
            is_breakout = last_price > upper_band
            is_lower_half = last_price < middle_band # Below SMA20
            
            # STRATEGY SELECTION (Hybrid Architecture)
            # 1. Type A: Breakout (Trend Following)
            # 2. Type B: Reversion (Mean Reversion in Range)
            # 3. Type D: Trend Continuation (Catching the Crash)
            
            selected_strategy = None
            
            # 1. TYPE A: CLASSIC BREAKOUT (Safety First)
            if score >= 70 and rvol > 2.5 and is_breakout and opt_sentiment != "BEARISH":
                selected_strategy = "Type A (Breakout)"
                
            # 2. TYPE B: REVERSION MONSTER (Buy the Dip)
            # Conditions: High Exhaustion Vol (RVOL > 3.0) + Low ADX (< 25)
            elif score >= 75 and rvol > 3.0 and is_lower_half and opt_sentiment != "BEARISH" and adx_value < 25:
                selected_strategy = "Type B (Reversion)"
            
            # 3. TYPE D: TREND CONTINUATION (Ride the Crash)
            # Conditions: Moderate Vol (RVOL > 2.0) + High ADX (> 25) -> Force SHORT
            elif score >= 75 and rvol > 2.0 and is_lower_half and adx_value >= 25:
                signal_type = "SHORT" # Override for Put Entry
                selected_strategy = "Type D (Trend Crash)"
                
            # 4. TYPE C: GAMMA HUNTER (Disabled - Pending Phase 25)
            # elif rvol < 1.5 and opt_data.get('ce_vol', 0) > 100000: 
            #     pass
                
            # FILTERING LOGIC
            if selected_strategy:
                # Common Filters
                if signal_type == "LONG" and opt_sentiment == "BEARISH":
                    status = "FILTERED"
                    rejection_reason = "Options Bearish in Long Setup"
                elif signal_type == "SHORT" and opt_sentiment == "BULLISH":
                    status = "FILTERED"
                    rejection_reason = "Options Bullish in Short Setup"
                else: 
                    # ALL SYSTEMS GO!
                    verdict = {'decision': "APPROVE", 'confidence': 100, 'reasoning': f"Matched {selected_strategy}"}
                    
                    if verdict['decision'] == "APPROVE":
                        signal = True
                        status = f"SIGNAL ({selected_strategy})"
                        rejection_reason = f"APPROVED! {selected_strategy}"
            else:
                # Detailed Rejection Reason for Logging
                if rvol < 1.2:
                    status = "FILTERED"
                    rejection_reason = f"Low Vol (RVOL {rvol:.2f})"
                elif not is_breakout and not is_lower_half:
                     status = "WAIT"
                     rejection_reason = "Mid-Range (No Setup)"
                else:
                    status = "WAIT"
                    rejection_reason = f"Score {score}/100 (Threshold not met)"
                    
            llm_conf = "100%"
            
            if signal:
                status = "SIGNAL"
                logging.info(f"✅ SIGNAL DETECTED for {symbol}! Placing Trade...")
                
                # EXECUTE TRADE (Log to TradeManager)
                if signal_type not in ["LONG", "SHORT"]:
                    logging.warning(f"⚠️ High Score ({score}) but NO Directional Signal. Skipping.")
                    status = "SKIPPED (No Direction)"
                    signal = False
                else:
                    option_type = "CE" if signal_type == "LONG" else "PE"
                
                    # 1. Get Option Symbol & Price
                    opt_symbol, strike = self.fetcher.get_option_symbol(symbol, last_price, option_type)
                    lot_size = self.fetcher.get_lot_size(symbol)
                    
                    # Fetch Option Quote
                    opt_price = 0.0
                    try:
                        nfo_opt_symbol = f"NFO:{opt_symbol}"
                        opt_quote = self.fetcher.fetch_live_quote([nfo_opt_symbol])
                        if nfo_opt_symbol in opt_quote:
                            opt_price = opt_quote[nfo_opt_symbol]['last_price']
                        else:
                            logging.error(f"❌ Abort: Symbol {nfo_opt_symbol} not found in quote response.")
                    except Exception as e:
                        logging.error(f"Failed to fetch option quote for {opt_symbol}: {e}")
                    
                    if opt_price == 0:
                        logging.error(f"❌ ABORTING TRADE: No Price for {opt_symbol}")
                        status = "ABORTED (No Price)"
                        rejection_reason = "Option Price Unavailable"
                        signal = False 
                    else:
                        entry_data = {
                            "symbol": symbol,
                            "option_symbol": opt_symbol,
                            "underlying_price": last_price,
                            "entry_price": opt_price,
                            "entry_time": now.strftime('%Y-%m-%d %H:%M:%S'),
                            "quantity": lot_size * 1,
                            "lot_size": lot_size,
                            "strategy": f"Sniper {signal_type}",
                            "status": "OPEN",
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "high_water_mark": 0.0,
                            "last_update": datetime.now().isoformat()
                        }
                        self.tm.add_trade(symbol, entry_data)
            
            # Collect Data (Update Master Memory)
            self.all_scan_results[symbol] = {
                "Symbol": symbol,
                "Score": score, 
                "Status": status,
                "Signal": signal_type,
                "Price": last_price,
                "Breakout": breakout_lvl,
                "Breakdown": breakdown_lvl,
                "Edge": f"{edge:.0f}%",
                "RVOL": f"{rvol:.1f}x",
                "VWAP": f"{vwap_value:.1f}",
                "LLM Conf": llm_conf,
                "Reason": rejection_reason,
                "Last Update": now.strftime('%H:%M:%S')
            }
            
            
            
        # Post-Loop: Save Scan Result for WhatsApp Notification
            

        for symbol in focus_list:
            # 4. Manage Active Trades (New Indentation Level - actually wait, the loop above was single iteration per symbol)
            # My previous view showed the loop ends after appending to scan_results?
            # Im misreading the indentation.
            pass
            
            # 4. Manage Active Trades
            if symbol in self.tm.active_trades:
                trade = self.tm.active_trades[symbol]
                # PnL Calc based on Underlying Move approx (Delta 0.5) because sim fetching option PnL is complex 
                # (Need to fetch option quote every loop for active trades)
                
                # Ideally:
                opt_sym = trade.get('option_symbol')
                curr_opt_price = trade.get('entry_price') 
                entry_opt_price = trade.get('entry_price')
                qty = trade.get('quantity')
                
                # Fetch Current Option Price
                try:
                    nfo_opt_sym = f"NFO:{opt_sym}"
                    q = self.fetcher.fetch_live_quote([nfo_opt_sym])
                    if nfo_opt_sym in q:
                        curr_opt_price = q[nfo_opt_sym]['last_price']
                except Exception as e:
                    logging.error(f"Failed to fetch live P&L for {opt_sym}: {e}")
                
                current_pnl = (curr_opt_price - entry_opt_price) * qty
                current_pnl_pct = (curr_opt_price - entry_opt_price) / entry_opt_price if entry_opt_price > 0 else 0

                self.tm.update_trade(symbol, last_price, current_pnl, current_pnl_pct)
                
                # Check Exits
                # 1. Trailing Stop (Activate > 1.5% Option Gain, Trail 0.5%) - Scalping!
                # Or use Original: Activate > 15%, Trail...
                
                # Let's keep original for now:
                hwm = self.tm.active_trades[symbol].get('high_water_mark', 0)
                
                # Trail Activation: 10%
                if current_pnl_pct > 0.10:
                    # Trail by 5%
                    pass 
                
                if hwm > 0.15 and current_pnl_pct < (hwm - 0.05):
                    logging.info(f"🛑 Trailing Stop Hit for {symbol}!")
                    self.tm.close_trade(symbol, curr_opt_price, "Trailing Stop")
                    
                # 2. Hard Stop (-10%)
                elif current_pnl_pct < -0.10:
                    logging.info(f"💀 Hard Stop Hit for {symbol}!")
                    self.tm.close_trade(symbol, curr_opt_price, "Hard Stop Loss")
        
        # Save latest_scan.json for WhatsApp Scheduler
        # Save latest_scan.json
        try:
             # Get full list from Master Memory
             cumulative_results = list(self.all_scan_results.values())
             # Sort by Score (Desc)
             cumulative_results.sort(key=lambda x: x['Score'] if isinstance(x['Score'], int) else 0, reverse=True)
             
             if cumulative_results:
                 # Atomic Write to prevent race conditions (UI reading empty file)
                 temp_file = "latest_scan.tmp"
                 with open(temp_file, "w") as f:
                     json.dump({
                         "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                         "top_picks": cumulative_results
                     }, f)
                 os.replace(temp_file, "latest_scan.json")
                 os.chmod("latest_scan.json", 0o666)
                 logging.info("✅ Saved latest_scan.json successfully.")
             else:
                 logging.warning("⚠️ Scan Results Empty. Skipping JSON write.")

        except Exception as e:
            logging.error(f"Failed to save latest_scan.json: {e}")

        # 5. Save Scan to Dashboard
        try:
            cumulative_results = list(self.all_scan_results.values())
            if cumulative_results:
                df_res = pd.DataFrame(cumulative_results)
                new_row = {"Symbol": "INDIA VIX", "Price": vix_value, "Status": vix_status, "Reason": "Market Gauge"}
                df_res = pd.concat([df_res, pd.DataFrame([new_row])], ignore_index=True)
                
                # Atomic Write
                temp_status = "scan_status.tmp"
                df_res.to_json(temp_status, orient='records')
                os.replace(temp_status, "scan_status.json")
                os.chmod("scan_status.json", 0o666)
                logging.info(f"✅ Scan Complete. Checked {len(focus_list)} stocks. Live Prices Updated.")
            else:
                 logging.warning("⚠️ Scan Results Empty. Preserving old Dashboard Data.")
                 
        except Exception as e:
            logging.error(f"Error saving dashboard feed: {e}")

if __name__ == "__main__":
    brain = LiveBrain()
    brain.run()
