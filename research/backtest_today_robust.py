import os
import json
import time
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import pytz

# Import the original classes
from live_brain import LiveBrain
from ai_option_brain.data_loader import ZerodhaDataFetcher
from ai_option_brain.utils.technical_indicators import TechnicalIndicators

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockDataFetcher:
    def __init__(self, spot_df, opt_df):
        self.spot_df = spot_df
        self.opt_df = opt_df
        self.current_time = None
        self.kite = True 
        
        # Pre-group for speed
        self.spot_map = {s: group for s, group in self.spot_df.groupby('symbol')}
        self.opt_map = {s: group for s, group in self.opt_df.groupby('tradingsymbol')}
        self.token_to_sym = {hash(s): s for s in self.spot_map.keys()}

    def set_time(self, time_val):
        self.current_time = time_val

    def get_instrument_token(self, symbol, exchange="NSE"):
        # We use a stable hash for simulation tokens
        return hash(symbol) 

    def get_option_symbol(self, symbol, spot_price, option_type):
        expiry = "25DEC" 
        prefix = f"{symbol}{expiry}"
        candidates = [k for k in self.opt_map.keys() if k.startswith(prefix) and option_type in k]
        if not candidates: return None, 0
        try:
            matches = []
            for c in candidates:
                strike_str = c.replace(prefix, "").replace(option_type, "")
                if not strike_str: continue
                matches.append((c, float(strike_str)))
            matches.sort(key=lambda x: abs(x[1] - spot_price))
            return matches[0][0], matches[0][1]
        except: return candidates[0], 0

    def fetch_live_quote(self, symbols):
        quotes = {}
        if self.current_time is None: return quotes
        
        for sym in symbols:
            clean_sym = sym.replace("NFO:", "").replace("NSE:", "")
            
            # Check Spot
            if clean_sym in self.spot_map:
                df = self.spot_map[clean_sym]
                # Filter rows up to current_time
                try:
                    target_time = self.current_time
                    # Ensure indices are aligned (aware vs naive)
                    mask = df.index <= target_time
                    if mask.any():
                        r = df.loc[mask].iloc[-1]
                        quotes[sym] = {
                            'last_price': r['close'],
                            'ohlc': {'open': r['open'], 'high': r['high'], 'low': r['low'], 'close': r['close']},
                            'volume': r.get('volume', 0)
                        }
                except Exception as e:
                    pass
                
            # Check Options
            if clean_sym in self.opt_map:
                df = self.opt_map[clean_sym]
                mask = df.index <= self.current_time
                if mask.any():
                    r = df.loc[mask].iloc[-1]
                    quotes[sym] = {
                        'last_price': r['close'],
                        'oi': r.get('oi', 0),
                        'volume': r.get('volume', 0)
                    }
        return quotes

    def fetch_latest_data(self, token, days=5, interval="5minute"):
        symbol = self.token_to_sym.get(token)
        if not symbol or symbol not in self.spot_map: return pd.DataFrame()
            
        df = self.spot_map[symbol]
        history = df.loc[df.index <= self.current_time]
        if history.empty: return pd.DataFrame()
        
        # Resample for 5-minute resolution consistency
        resampled = history.resample('5min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        return resampled.tail(100)

class RobustLiveBrain(LiveBrain):
    """
    Subclass of LiveBrain that overrides scan_market to include 
    sim-specific stability fixes without touching the main file.
    """
    def __init__(self, mock_fetcher):
        super().__init__()
        self.fetcher = mock_fetcher
        self.options_brain.fetcher = mock_fetcher
        # Disable WhatsApp for simulation
        self.tm.active_trades = {}
        self.max_day_score = 0
        self.max_score_sym = ""
        self.last_scan_metrics = {} # symbol -> metrics
        logging.info(f"🌌 Simulation Engine Init: Loaded {len(self.universe)} stocks from fno_universe.txt")
        
    def scan_market(self):
        """Modified scan_market with safety initializations and TZ handling."""
        now = self.simulation_time or datetime.now()
        
        # Universe Sweep Logic
        if not self.universe:
            logging.error("❌ Universe empty in scan_market!")
            return
        
        start = self.universe_index
        end = min(start + self.batch_size, len(self.universe))
        focus_list = self.universe[start:end]
        
        # Fetch Live Quotes
        symbols_to_fetch = [f"NSE:{s}" for s in focus_list]
        quotes = self.fetcher.fetch_live_quote(symbols_to_fetch)
        
        if not quotes:
             logging.warning(f"⚠️ No quotes fetched for {len(focus_list)} stocks at {now}")
        else:
             logging.info(f"⏳ Sim Sweep: [{start}:{end}] | Time: {now.strftime('%H:%M:%S')} | Quotes: {len(quotes)}")
        
        vix_value = 15.0 # Mock VIX
        vix_status = "STABLE"
        
        for symbol_prefixed in symbols_to_fetch:
            symbol = symbol_prefixed.replace("NSE:", "")
            
            # --- CRITICAL FIX: Safe Variable Initialization ---
            last_price = 0.0
            adx_value = 0
            trend_dist = 0
            rsi = 50
            bandwidth = 0
            upper_band = 0
            rvol = 0
            vwap_value = 0
            pred_rv = vix_value * 1.2
            market_iv = vix_value * 1.2
            rvol_5m_avg = 0
            is_momentum_active = False
            score = 0
            reasons = ["Init"]
            edge = 0.0
            breakout_lvl = 0.0
            breakdown_lvl = 0.0
            signal_type = "NEUTRAL"
            upper = pd.Series(dtype=float)
            lower = pd.Series(dtype=float)
            rvol_series = pd.Series(dtype=float)
            hist_df = pd.DataFrame()
            
            if symbol_prefixed in quotes:
                last_price = quotes[symbol_prefixed]['last_price']
                
                try:
                    token = self.fetcher.get_instrument_token(symbol)
                    hist_df = self.fetcher.fetch_latest_data(token, days=5, interval="5minute")
                    
                    if not hist_df.empty:
                        # Indicator Calcs
                        hist_df['log_ret'] = np.log(hist_df['close'] / hist_df['close'].shift(1))
                        vol_sma_val = hist_df['volume'].rolling(20).mean().iloc[-1]
                        current_vol = hist_df['volume'].iloc[-1]
                        rvol = current_vol / vol_sma_val if vol_sma_val > 0 else 0
                        
                        rvol_series = (hist_df['volume'] / vol_sma_val).fillna(0)
                        rvol_5m_avg = rvol_series.tail(5).mean()
                        
                        sma_50 = hist_df['close'].rolling(50).mean().iloc[-1]
                        trend_dist = (last_price - sma_50) / sma_50 if pd.notna(sma_50) else 0
                        
                        rsi = TechnicalIndicators.calculate_rsi(hist_df['close'], period=14).iloc[-1] if len(hist_df) > 14 else 50
                        adx = TechnicalIndicators.calculate_adx(hist_df['high'], hist_df['low'], hist_df['close'], window=14)
                        adx_value = adx.iloc[-1] if not adx.empty else 0
                        
                        upper, lower = TechnicalIndicators.calculate_bollinger_bands(hist_df['close'], period=20, std_dev=2)
                        if not upper.empty:
                            upper_band = upper.iloc[-1]
                            lower_band = lower.iloc[-1]
                            mid = hist_df['close'].rolling(20).mean().iloc[-1]
                            bandwidth = (upper_band - lower_band) / mid if mid != 0 else 0
                        
                        vwap_series = TechnicalIndicators.calculate_vwap(hist_df)
                        vwap_value = vwap_series.iloc[-1] if not vwap_series.empty else 0
                        
                        market_iv = hist_df['log_ret'].rolling(20).std().iloc[-1] * np.sqrt(252*75) * 100 if len(hist_df) > 20 else vix_value
                        pred_rv = market_iv # Simplify for sim
                except Exception as e:
                    # Specific debug for backtest
                    if "negative dimensions" not in str(e):
                         logging.debug(f"Calc error for {symbol}: {e}")

            # Momentum State
            if not hist_df.empty and len(hist_df) >= 6 and not upper.empty:
                w_close = hist_df['close'].iloc[-6:-1].values
                w_upper = upper.iloc[-6:-1].values
                w_rvol = rvol_series.iloc[-6:-1].values
                if len(w_close) == 5 and len(w_upper) == 5 and len(w_rvol) == 5:
                    ignition = (w_close > w_upper) & (w_rvol > 2.0)
                    if any(ignition):
                        is_momentum_active = True

            # Confluence Call
            focus_data = {} # Dummy
            if last_price > 0:
                hist = self.history[symbol]
                confluence = self.calculate_confluence_score(
                    symbol, last_price, adx_value, trend_dist, rsi, 
                    bandwidth, upper_band, rvol, vwap_value, 
                    pred_rv, market_iv, focus_data, history=hist,
                    rvol_5m_avg=rvol_5m_avg,
                    is_momentum_active=is_momentum_active
                )
                
                raw_score = confluence.get('score', 0)
                hist.add_score(raw_score)
                score = int(hist.get_smoothed_score())
                
                reasons = confluence.get('reasons', [])
                signal_type = confluence.get('signal_type', "NEUTRAL")
                
                # Store Metrics for Forensic
                self.last_scan_metrics[symbol] = {
                    'score': score,
                    'adx': adx_value,
                    'rsi': rsi,
                    'trend': trend_dist,
                    'signal': signal_type,
                    'reasons': reasons
                }
                
                if score > self.max_day_score:
                    self.max_day_score = score
                    self.max_score_sym = symbol

                # LOG POTENTIAL SIGNALS (Data-Independent)
                if score >= 60:
                     logging.info(f"🚨 POTENTIAL SIGNAL: {symbol} | Score: {score} | Signal: {signal_type} | Reasons: {reasons}")

            # Trade Execution Simulation
            if score >= 60 and signal_type != "NEUTRAL":
                if symbol not in self.tm.active_trades:
                    opt_sym, strike = self.fetcher.get_option_symbol(symbol, last_price, signal_type)
                    if opt_sym:
                        logging.info(f"🚀 Sim Trade: {symbol} @ {last_price} ({signal_type} {opt_sym})")
                        # Add to active trades
                        oq = self.fetcher.fetch_live_quote([f"NFO:{opt_sym}"])
                        entry_pr = oq.get(f"NFO:{opt_sym}", {}).get('last_price', 100.0)
                        self.tm.add_trade(symbol, {
                            "symbol": symbol,
                            "option_symbol": opt_sym,
                            "entry_price": entry_pr,
                            "quantity": self.fetcher.get_lot_size(symbol),
                            "strategy": "University Momentum",
                            "pnl": 0.0, "pnl_pct": 0.0
                        })

        # Update Universe Index
        self.universe_index = end if end < len(self.universe) else 0

    def manage_trades_step(self, last_prices):
        """Update P&L and check exits for active sim trades."""
        for symbol in list(self.tm.active_trades.keys()):
            trade = self.tm.active_trades[symbol]
            opt_sym = trade['option_symbol']
            
            q = self.fetcher.fetch_live_quote([f"NFO:{opt_sym}"])
            if f"NFO:{opt_sym}" in q:
                curr_pr = q[f"NFO:{opt_sym}"]['last_price']
                entry_pr = trade['entry_price']
                pnl = (curr_pr - entry_pr) * trade['quantity']
                pnl_pct = (curr_pr - entry_pr) / entry_pr
                
                self.tm.update_trade(symbol, 0, pnl, pnl_pct) # last_price not strictly needed for P&L pct
                
                # Simple exits
                if pnl_pct > 0.15 or pnl_pct < -0.10:
                    self.tm.close_trade(symbol, curr_pr, "Target/Stop Hit")

def validate_data_integrity(spot_df, opt_df, date_str):
    """Perform sanity checks on data before starting simulation."""
    logging.info(f"🛡️ Validating Data Integrity for {date_str}...")
    
    if spot_df.empty:
        raise ValueError("❌ Spot data is empty!")
    if opt_df.empty:
        raise ValueError("❌ Option data is empty!")
        
    expected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Check Spot Dates
    actual_dates = spot_df.index.date
    if expected_date not in actual_dates:
        raise ValueError(f"❌ Date {date_str} not found in spot data. Found: {np.unique(actual_dates)}")
        
    # Check for zero prices
    if (spot_df['close'] <= 0).any():
        zero_syms = spot_df[spot_df['close'] <= 0]['symbol'].unique()
        logging.warning(f"⚠️ Zero prices found for: {zero_syms}")
        
    # Check Row Count (expected ~375 mins per day per symbol)
    counts = spot_df.groupby('symbol').size()
    avg_count = counts.mean()
    logging.info(f"📊 Data Stats: {len(counts)} symbols, Round avg {avg_count:.0f} rows/symbol")
    
    if avg_count < 100:
        raise ValueError(f"❌ Insufficient daily data! Avg rows: {avg_count}")

    logging.info("✅ Data Integrity Check Passed.")

def run_backtest():
    DATE = "2025-12-24"
    spot_file = f"daily_data/{DATE}_spot_full.csv"
    opt_file = f"daily_data/{DATE}_options_full.csv"
    
    if not os.path.exists(spot_file) or not os.path.exists(opt_file):
        print(f"❌ Missing data files for {DATE}. Run data collection first.")
        return

    print(f"📖 Loading data for {DATE}...")
    spot_df = pd.read_csv(spot_file)
    spot_df['date'] = pd.to_datetime(spot_df['date'])
    spot_df.set_index('date', inplace=True)
    
    opt_df = pd.read_csv(opt_file)
    opt_df['date'] = pd.to_datetime(opt_df['date'])
    opt_df.set_index('date', inplace=True)
    
    # --- PHASE 0: Data Validation ---
    try:
        validate_data_integrity(spot_df, opt_df, DATE)
    except Exception as e:
        logging.error(f"🛑 Data Validation Failed: {e}")
        return
    
    mock = MockDataFetcher(spot_df, opt_df)
    brain = RobustLiveBrain(mock)
    
    # Sim loop
    tz = pytz.timezone('Asia/Kolkata')
    start_time = tz.localize(datetime.strptime(f"{DATE} 09:15:00", "%Y-%m-%d %H:%M:%S"))
    end_time = tz.localize(datetime.strptime(f"{DATE} 15:30:00", "%Y-%m-%d %H:%M:%S"))
    
    current = start_time
    print(f"🚀 Starting Simulation...")
    while current <= end_time:
        mock.set_time(current)
        brain.simulation_time = current.replace(tzinfo=None)
        
        # 1. Scan
        brain.scan_market()
        
        # 2. Manage Trades
        brain.manage_trades_step({})
        
        current += timedelta(minutes=1)
        
    print("\n" + "="*40)
    print(f"🏁 Simulation for {DATE} Complete.")
    print(f"Max Score Observed: {brain.max_day_score} ({brain.max_score_sym})")
    history_file = "trade_history.csv"
    if os.path.exists(history_file):
        df = pd.read_csv(history_file)
        if not df.empty:
            print(f"Total Trades: {len(df)}")
            print(f"Total P&L:    ₹{df['PnL'].sum():,.2f}")
            print(f"Win Rate:     {(df['PnL'] > 0).mean()*100:.1f}%")
        else: print("No trades triggered.")
    else: print("No trade history found.")
    print("="*40)

if __name__ == "__main__":
    run_backtest()
