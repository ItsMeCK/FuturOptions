import os
import pandas as pd
import logging
from backtest_today_robust import RobustLiveBrain, MockDataFetcher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrendBrain(RobustLiveBrain):
    def calculate_confluence_score(self, symbol, price, adx, trend_dist, rsi, bandwidth, upper_band, rvol, vwap_value, pred_rv, market_iv, focus_data, history=None, rvol_5m_avg=0, is_momentum_active=False):
        # Base score from parent? No, we need to REWRITE it to inject logic in the middle.
        # Copy-paste logic from LiveBrain but add the Trend feature.
        
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
            
        # 1. Trend Quality (ADX)
        if adx < 25:
            reasons.append("ADX < 25 (Choppy)")
        else:
            score += 15
            reasons.append(f"Strong Trend (ADX {adx:.1f})")
            if history: history.update_persistence('trend')
            
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
            
        # 4. Volume Flow
        effective_rvol = max(rvol, rvol_5m_avg)
        
        if effective_rvol > 2.0:
            score += 30 
            reasons.append(f"IGNITION Vol ({effective_rvol:.1f}x)")
        elif is_momentum_active and effective_rvol > 0.5:
             score += 20 
             reasons.append(f"Momentum Active ({effective_rvol:.1f}x)")
        elif effective_rvol > 1.5:
             score += 15
             reasons.append(f"High Vol ({effective_rvol:.1f}x)")
             
        # --- NEW TREND FOLLOWING LOGIC ---
        # If Trend is VERY strong (ADX > 30) and Volume is at least Normal (> 0.8),
        # we treat it as valid drift even without Ignition.
        if adx > 30 and effective_rvol > 0.8:
            score += 35 # Huge boost to cross 75 threshold
            reasons.append(f"Trend Drift (ADX {adx:.0f}+)")
        # ---------------------------------
            
        if pred_rv > market_iv * 1.1:
            edge = (pred_rv - market_iv)
            score += 20
            reasons.append(f"AI Edge ({edge:.1f})")
            
        # Determine Signal Type (Simplistic for Sim)
        signal_type = "NEUTRAL"
        if score >= 60: # Lowered threshold from 75 for Sim
            if abs(trend_dist) > 0:
                if trend_dist > 0: signal_type = "CALL"
                elif trend_dist < 0: signal_type = "PUT"
            elif vwap_value > 0:
                # Fallback to VWAP if SMA50 not ready
                if price > vwap_value: signal_type = "CALL"
                else: signal_type = "PUT"
            
        return {
            'score': score,
            'reasons': reasons,
            'edge': edge,
            'breakout_lvl': breakout_lvl,
            'breakdown_lvl': breakdown_lvl,
            'signal_type': signal_type
        }

def run_simulation(date_str):
    print(f"\n🚀 STARTING SIMULATION FOR: {date_str} (TREND MODE)")
    spot_file = f"daily_data/{date_str}_spot_full.csv"
    opt_file = f"daily_data/{date_str}_options_full.csv"
    
    if not os.path.exists(spot_file):
        print(f"❌ Missing data for {date_str}")
        return

    spot_df = pd.read_csv(spot_file)
    spot_df['date'] = pd.to_datetime(spot_df['date'])
    spot_df.set_index('date', inplace=True)
    
    opt_df = pd.read_csv(opt_file)
    opt_df['date'] = pd.to_datetime(opt_df['date'])
    opt_df.set_index('date', inplace=True)
    
    # Initialize Engine
    mock = MockDataFetcher(spot_df, opt_df)
    # Patch expiry detection if needed
    if "2025-12-26" in date_str:
        # Mock logic defaults to 25DEC, which works for 26th too as established
        pass
        
    brain = TrendBrain(mock)
    
    # Disable Notifications Gracefully
    from unittest.mock import Mock
    brain.tm.bot = Mock()
    
    # Run
    # We need to manually drive the loop or call run_backtest logic?
    # run_backtest in robust file is a standalone function.
    # We will copy the loop logic briefly here.
    
    # Time Window
    import pytz
    from datetime import datetime, timedelta
    tz = pytz.timezone('Asia/Kolkata')
    
    # -------------------------------------------------------------
    # 1. OVERRIDE EXIT LOGIC (+30% Profit, -10% Loss)
    # -------------------------------------------------------------
    def manage_trades_custom(self, last_prices):
        """Update P&L and check exits for active sim trades."""
        closed_trades = []
        for symbol in list(self.tm.active_trades.keys()):
            trade = self.tm.active_trades[symbol]
            opt_sym = trade['option_symbol']
            
            q = self.fetcher.fetch_live_quote([f"NFO:{opt_sym}"])
            if f"NFO:{opt_sym}" in q:
                curr_pr = q[f"NFO:{opt_sym}"]['last_price']
                entry_pr = trade['entry_price']
                pnl = (curr_pr - entry_pr) * trade['quantity']
                pnl_pct = (curr_pr - entry_pr) / entry_pr
                
                self.tm.update_trade(symbol, 0, pnl, pnl_pct)
                
                # CUSTOM RULES FROM USER
                if pnl_pct >= 0.30:
                    logging.info(f"💰 TARGET HIT: {symbol} (+{pnl_pct*100:.1f}%)")
                    self.tm.close_trade(symbol, curr_pr, "Target Hit (+30%)")
                    closed_trades.append(symbol)
                elif pnl_pct <= -0.10:
                    logging.info(f"🛑 STOP HIT: {symbol} ({pnl_pct*100:.1f}%)")
                    self.tm.close_trade(symbol, curr_pr, "Stop Hit (-10%)")
                    closed_trades.append(symbol)
                    
    # Patch the method
    TrendBrain.manage_trades_step = manage_trades_custom
    
    # -------------------------------------------------------------
    # 2. OVERRIDE OPTION LOOKUP (Fix Expiry)
    # -------------------------------------------------------------
    mock.strike_step_map = {} 
    
    def get_opt_custom(symbol, spot_price, signal_type):
        # Determine Step based on Price if not in map
        if symbol in mock.strike_step_map:
            strike_step = mock.strike_step_map[symbol]
        else:
            # Heuristic
            if spot_price < 500: strike_step = 5
            elif spot_price < 1000: strike_step = 10
            elif spot_price < 2500: strike_step = 20
            else: strike_step = 50
            
        strike = round(spot_price / strike_step) * strike_step
        
        expiry_str = "25DEC" 
        type_str = "CE" if signal_type == "CALL" else "PE"
        
        # Try int strike for symbol construction
        opt_sym = f"{symbol}{expiry_str}{int(strike)}{type_str}"
        return opt_sym, strike

    mock.get_option_symbol = get_opt_custom
    
    # Patch Lot Size
    mock.get_lot_size = lambda sym: 100
    
    start = tz.localize(datetime.strptime(f"{date_str} 09:15:00", "%Y-%m-%d %H:%M:%S"))
    end = tz.localize(datetime.strptime(f"{date_str} 15:30:00", "%Y-%m-%d %H:%M:%S"))
    
    current = start
    while current <= end:
        mock.set_time(current)
        brain.simulation_time = current.replace(tzinfo=None)
        
        # We need to run scan_market
        # RobustLiveBrain.scan_market uses batching
        # To get FULL results fast, let's force full sweep in fewer steps?
        # No, let's just loop normally.
        
        brain.scan_market()
        
        # Check Trades from Brain's internal trackers?
        # RobustLiveBrain doesn't persist trades to a file automatically unless specified.
        # But it does log.
        
        current += timedelta(minutes=1)
        
    print(f"🏁 Simulation Complete for {date_str}")
    print(f"Max Score: {brain.max_day_score} ({brain.max_score_sym})")
    
    # Extract Trades
    # Ideally we'd print them here.
    # We can inspect brain.tm.active_trades or similar? 
    # Actually RobustLiveBrain doesn't store history in memory well, it writes to 'trade_history.csv'.
    # Each run overwrites? No, appends.
    # We should specify a unique file.
    # But `TradeManager` init is hardcoded in base class...
    # We can rely on logs or parsing.
    
    # BETTER: TrendBrain stores hits in a list
    # We can't easily modify scan_market without copying IT too.
    # scan_market calls process_signals -> tm.manage_trade
    
    pass

if __name__ == "__main__":
    run_simulation("2025-12-24")
    run_simulation("2025-12-26")
