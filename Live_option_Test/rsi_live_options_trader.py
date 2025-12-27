"""
RSI LIVE OPTIONS TRADER - Delta Exchange Demo
Trades BTC Options based on RSI signals

Strategy:
- BUY CALL when: RSI crosses ABOVE 30 (from oversold)
- BUY PUT when: RSI crosses BELOW 70 (from overbought)

Trailing Stop Logic:
- When 2x target hit → Trail SL to lock 60% profit
- Continues until trailing stop is hit
"""

import json
import time
import os
import hashlib
import hmac
import requests
import numpy as np
from datetime import datetime, timedelta
from colorama import init, Fore, Style

# Initialize colorama
try:
    init(autoreset=True)
    HAS_COLOR = True
except:
    HAS_COLOR = False

# =============================================================================
# API CONFIGURATION - DELTA EXCHANGE TESTNET (DEMO)
# =============================================================================
API_KEY = "hxHrRiP9O6CATdQoYKccuOaJbMz0Yj"
API_SECRET = "GE3If4w5WHrxuSCdMZjurpiMU2xf0ZIsoxa8kcNRoSZCyoDShQeuYLRGe9rk"

# Testnet URLs
BASE_URL = "https://cdn-ind.testnet.deltaex.org"

# =============================================================================
# RSI STRATEGY CONFIGURATION
# =============================================================================
RSI_PERIOD = 14             # RSI calculation period
RSI_OVERSOLD = 30           # Buy CALL when RSI crosses above this
RSI_OVERBOUGHT = 70         # Buy PUT when RSI crosses below this

TIMEFRAME = "45m"           # Candle timeframe (45 minutes)
CANDLES_TO_FETCH = 100      # Historical candles to fetch

# Trailing Stop Configuration
FIRST_TARGET_MULT = 2.0     # First target = 2x risk
TRAIL_LOCK_PCT = 0.60       # Lock 60% of profit when target hit

# Options Configuration
EXPIRY_DAYS_AHEAD = 2       # Expiry X days from today
ORDER_SIZE = 10              # Contracts per order

# Scan interval
SCAN_INTERVAL_SECONDS = 30  # Check for signals every 60 seconds

# =============================================================================
# FILE PATHS
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, "rsi_live_trades.json")

# Import unified storage (JSON + MongoDB)
import sys
parent_dir = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, parent_dir)
from utils.trade_storage import TradeStorage

# Initialize storage handler (JSON + MongoDB if configured)
storage = TradeStorage(
    json_file=TRADES_FILE,
    collection_name='rsi_options_trades'
)

# =============================================================================
# DASHBOARD LOGGER - Send logs to main.py dashboard
# =============================================================================
STRATEGY_NAME = "RSI Options Trader"
_dashboard_logger = None

def set_dashboard_logger(logger_func):
    """Set the dashboard logger function from main.py"""
    global _dashboard_logger
    _dashboard_logger = logger_func

def log_to_ui(message, level="info"):
    """Log message to dashboard if available"""
    if _dashboard_logger:
        _dashboard_logger(STRATEGY_NAME, message, level)
    # Always print locally too
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    print(f"[{timestamp}] {icons.get(level, 'ℹ️')} {message}")

# =============================================================================
# CURRENT STATE
# =============================================================================
current_position = None
candles = []
prev_rsi = None

# =============================================================================
# API FUNCTIONS
# =============================================================================

def generate_signature(method, endpoint, payload=""):
    """Generate HMAC signature for API authentication"""
    timestamp = str(int(time.time()))
    signature_data = method + timestamp + endpoint + payload
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature, timestamp


def api_request(method, endpoint, data=None):
    """Make authenticated API request"""
    url = BASE_URL + endpoint
    payload = json.dumps(data) if data else ""
    
    signature, timestamp = generate_signature(method, endpoint, payload)
    
    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def get_btc_price():
    """Get current BTC price"""
    try:
        r = requests.get(f"{BASE_URL}/v2/tickers/BTCUSD", timeout=10)
        if r.status_code == 200:
            return float(r.json().get("result", {}).get("mark_price", 0))
    except:
        pass
    return 0


def fetch_historical_candles():
    """Fetch historical OHLC candles from Delta Exchange
    For 45m: fetch 15m candles and resample (3 x 15min = 45min)
    """
    global candles
    
    print(f"📊 Fetching historical {TIMEFRAME} candles...")
    
    try:
        # Delta Exchange candle API
        CANDLE_API = "https://cdn.india.deltaex.org/v2/chart/history"
        end_time = int(time.time())
        
        # For 45m, we need to fetch 15m candles and resample
        if TIMEFRAME == "45m":
            # Fetch 15m candles (need 3x more for resampling)
            fetch_resolution = "15"
            resolution_seconds = 900  # 15 min
            fetch_count = CANDLES_TO_FETCH * 3  # Need 3x 15min candles
        else:
            # Direct fetch for other timeframes
            resolution_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
            fetch_resolution = resolution_map.get(TIMEFRAME, "15")
            resolution_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}.get(TIMEFRAME, 900)
            fetch_count = CANDLES_TO_FETCH
        
        start_time = end_time - (fetch_count * resolution_seconds)
        
        params = {
            "symbol": "BTCUSD",
            "resolution": fetch_resolution,
            "from": start_time,
            "to": end_time
        }
        
        print(f"   Fetching {fetch_count} x {fetch_resolution}m candles...")
        r = requests.get(CANDLE_API, params=params, timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            
            if "result" in data and data["result"].get("s") == "ok":
                res = data["result"]
                raw_candles = []
                
                for i in range(len(res.get("t", []))):
                    raw_candles.append({
                        'time': res["t"][i],
                        'open': float(res["o"][i]),
                        'high': float(res["h"][i]),
                        'low': float(res["l"][i]),
                        'close': float(res["c"][i]),
                        'volume': float(res["v"][i])
                    })
                
                # Sort by time
                raw_candles.sort(key=lambda x: x['time'])
                
                if TIMEFRAME == "45m" and raw_candles:
                    # Resample 15m to 45m (group every 3 candles)
                    print(f"   Resampling {len(raw_candles)} x 15m → 45m candles...")
                    candles = resample_to_45min(raw_candles)
                else:
                    candles = raw_candles
                
                print(f"✅ Loaded {len(candles)} candles ({TIMEFRAME})")
                if candles:
                    print(f"   Latest: ${candles[-1]['close']:,.2f}")
                return True
        
        print(f"⚠️ Failed to fetch candles: {r.status_code}")
        try:
            print(f"   Response: {r.text[:200]}")
        except:
            pass
        return False
        
    except Exception as e:
        print(f"❌ Error fetching candles: {e}")
        import traceback
        traceback.print_exc()
        return False


def resample_to_45min(raw_candles):
    """Resample 15-min candles to 45-min candles (group every 3)"""
    if len(raw_candles) < 3:
        return raw_candles
    
    resampled = []
    
    # Group every 3 candles
    for i in range(0, len(raw_candles) - 2, 3):
        c1, c2, c3 = raw_candles[i], raw_candles[i+1], raw_candles[i+2]
        
        resampled.append({
            'time': c1['time'],
            'open': c1['open'],
            'high': max(c1['high'], c2['high'], c3['high']),
            'low': min(c1['low'], c2['low'], c3['low']),
            'close': c3['close'],
            'volume': c1['volume'] + c2['volume'] + c3['volume']
        })
    
    return resampled


def update_candles_with_price(price):
    """Update candle data with latest price"""
    global candles
    
    if not candles:
        return
    
    # Update the last candle's close
    candles[-1]['close'] = price
    if price > candles[-1]['high']:
        candles[-1]['high'] = price
    if price < candles[-1]['low']:
        candles[-1]['low'] = price


# =============================================================================
# RSI CALCULATION (TradingView Compatible)
# =============================================================================

# RSI Smoothing Settings (to match TradingView)
RSI_SMOOTHING_TYPE = "SMA"  # SMA or EMA
RSI_SMOOTHING_LENGTH = 14   # Smoothing length for RSI line

# Store RSI history for smoothing
rsi_history = []

def calculate_rsi(closes, period=14):
    """Calculate RSI using Wilder's smoothing method"""
    if len(closes) < period + 1:
        return None
    
    closes = np.array(closes)
    deltas = np.diff(closes)
    
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Wilder's smoothing for average gain/loss
    avg_gain = np.zeros_like(closes[1:])
    avg_loss = np.zeros_like(closes[1:])
    
    # First average
    avg_gain[period-1] = np.mean(gains[:period])
    avg_loss[period-1] = np.mean(losses[:period])
    
    # Subsequent averages using Wilder's smoothing
    for i in range(period, len(gains)):
        avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period
    
    rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    return rsi[-1]


def get_current_rsi():
    """Calculate current RSI from candles with SMA smoothing (TradingView style)"""
    global rsi_history
    
    if len(candles) < RSI_PERIOD + 1:
        return None
    
    closes = [c['close'] for c in candles]
    raw_rsi = calculate_rsi(closes, RSI_PERIOD)
    
    if raw_rsi is None:
        return None
    
    # Add to history for smoothing
    rsi_history.append(raw_rsi)
    
    # Keep only what we need for smoothing
    if len(rsi_history) > RSI_SMOOTHING_LENGTH * 2:
        rsi_history = rsi_history[-RSI_SMOOTHING_LENGTH * 2:]
    
    # Apply SMA smoothing (like TradingView)
    if RSI_SMOOTHING_TYPE == "SMA" and len(rsi_history) >= RSI_SMOOTHING_LENGTH:
        smoothed_rsi = np.mean(rsi_history[-RSI_SMOOTHING_LENGTH:])
        return smoothed_rsi
    else:
        return raw_rsi


# =============================================================================
# SIGNAL DETECTION
# =============================================================================

def check_signals():
    """Check for RSI entry signals"""
    global prev_rsi
    
    curr_rsi = get_current_rsi()
    
    if curr_rsi is None or prev_rsi is None:
        prev_rsi = curr_rsi
        return None
    
    signal = None
    
    # LONG signal: RSI crosses ABOVE 30 (from oversold)
    if prev_rsi <= RSI_OVERSOLD and curr_rsi > RSI_OVERSOLD:
        signal = {
            'type': 'LONG',
            'option': 'CALL',
            'rsi': curr_rsi,
            'price': candles[-1]['close'],
            'stop_loss': candles[-1]['low'],  # SL = candle low
            'reason': f'RSI crossed above {RSI_OVERSOLD}'
        }
    
    # SHORT signal: RSI crosses BELOW 70 (from overbought)
    elif prev_rsi >= RSI_OVERBOUGHT and curr_rsi < RSI_OVERBOUGHT:
        signal = {
            'type': 'SHORT',
            'option': 'PUT',
            'rsi': curr_rsi,
            'price': candles[-1]['close'],
            'stop_loss': candles[-1]['high'],  # SL = candle high
            'reason': f'RSI crossed below {RSI_OVERBOUGHT}'
        }
    
    prev_rsi = curr_rsi
    return signal


# =============================================================================
# OPTIONS TRADING
# =============================================================================

def get_dynamic_expiry():
    """Get expiry date X days from today"""
    expiry_date = datetime.now() + timedelta(days=EXPIRY_DAYS_AHEAD)
    return expiry_date.strftime("%d%m%y")


def find_atm_option(option_type):
    """Find ATM CALL or PUT option"""
    btc_price = get_btc_price()
    expiry = get_dynamic_expiry()
    
    prefix = "C-BTC-" if option_type == "CALL" else "P-BTC-"
    
    try:
        r = requests.get(f"{BASE_URL}/v2/products", timeout=60)
        if r.status_code != 200:
            return None
        
        products = r.json().get("result", [])
        options = []
        
        for p in products:
            symbol = p.get("symbol", "")
            strike = p.get("strike_price")
            
            if symbol.startswith(prefix) and expiry in symbol and strike:
                options.append({
                    "id": p["id"],
                    "symbol": symbol,
                    "strike": float(strike)
                })
        
        if not options:
            return None
        
        # Find ATM (closest to current price)
        options.sort(key=lambda x: abs(x["strike"] - btc_price))
        return options[0]
        
    except Exception as e:
        print(f"❌ Error finding option: {e}")
        return None


def place_option_order(product_id, symbol, side, size):
    """Place option order"""
    order_data = {
        "product_id": product_id,
        "size": size,
        "side": side,
        "order_type": "market_order"
    }
    
    print(f"📤 Placing {side.upper()} order: {symbol} x {size}...")
    result = api_request("POST", "/v2/orders", order_data)
    
    if result and result.get("success"):
        order = result.get("result", {})
        print(f"✅ Order placed! ID: {order.get('id')}")
        return order
    else:
        error = result.get("error", {}) if result else {}
        print(f"❌ Failed: {error.get('code', 'Unknown')} - {error.get('message', '')}")
        return None


# =============================================================================
# TRADE MANAGEMENT
# =============================================================================

def execute_signal(signal):
    """Execute trade based on signal"""
    global current_position
    
    option_type = signal['option']  # CALL or PUT
    
    print(f"\n{'='*60}")
    color = Fore.GREEN if option_type == "CALL" else Fore.RED
    icon = "🟢" if option_type == "CALL" else "🔴"
    
    print(f"{color}{icon} {signal['type']} SIGNAL - Buy {option_type}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"   RSI: {signal['rsi']:.2f}")
    print(f"   Price: ${signal['price']:,.2f}")
    print(f"   Reason: {signal['reason']}")
    print(f"{'='*60}")
    
    # Find ATM option
    option = find_atm_option(option_type)
    if not option:
        print(f"❌ Could not find ATM {option_type}")
        return False
    
    print(f"📊 Found: {option['symbol']} (Strike: ${option['strike']:,.0f})")
    
    # Place order
    order = place_option_order(option["id"], option["symbol"], "buy", ORDER_SIZE)
    
    if order:
        # Calculate risk and targets
        entry_price = signal['price']
        stop_loss = signal['stop_loss']
        
        if signal['type'] == 'LONG':
            risk = entry_price - stop_loss
        else:
            risk = stop_loss - entry_price
        
        current_position = {
            'type': signal['type'],
            'option': option_type,
            'symbol': option['symbol'],
            'product_id': option['id'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'initial_sl': stop_loss,
            'risk': risk,
            'entry_rsi': signal['rsi'],
            'order_id': order.get('id'),
            'entry_time': datetime.now().isoformat(),
            'target_level': 2,
            'max_target': 0
        }
        
        save_trade(current_position, 'OPEN')
        
        print(f"✅ Position opened!")
        print(f"   Entry: ${entry_price:,.2f}")
        print(f"   Stop Loss: ${stop_loss:,.2f}")
        print(f"   Risk: ${risk:,.2f}")
        print(f"   Target (2x): ${entry_price + (2*risk if signal['type']=='LONG' else -2*risk):,.2f}")
        
        return True
    
    return False


def check_exit():
    """Check if position should exit based on trailing stop logic"""
    global current_position
    
    if current_position is None:
        return
    
    current_price = get_btc_price()
    if current_price <= 0:
        return
    
    entry_price = current_position['entry_price']
    stop_loss = current_position['stop_loss']
    risk = current_position['risk']
    target_level = current_position['target_level']
    
    if current_position['type'] == 'LONG':
        # Check stop loss
        if current_price <= stop_loss:
            close_position(current_price, f'TRAIL_SL_{current_position["max_target"]}X')
            return
        
        # Check target
        target_price = entry_price + (target_level * risk)
        if current_price >= target_price:
            # Update trailing stop
            profit_at_level = target_price - entry_price
            new_sl = entry_price + (TRAIL_LOCK_PCT * profit_at_level)
            
            current_position['stop_loss'] = new_sl
            current_position['max_target'] = target_level
            current_position['target_level'] = target_level + 1
            
            print(f"🎯 {target_level}X HIT! Trail SL → ${new_sl:,.2f}, aiming for {target_level+1}X")
    
    else:  # SHORT
        # Check stop loss
        if current_price >= stop_loss:
            close_position(current_price, f'TRAIL_SL_{current_position["max_target"]}X')
            return
        
        # Check target
        target_price = entry_price - (target_level * risk)
        if current_price <= target_price:
            # Update trailing stop
            profit_at_level = entry_price - target_price
            new_sl = entry_price - (TRAIL_LOCK_PCT * profit_at_level)
            
            current_position['stop_loss'] = new_sl
            current_position['max_target'] = target_level
            current_position['target_level'] = target_level + 1
            
            print(f"🎯 {target_level}X HIT! Trail SL → ${new_sl:,.2f}, aiming for {target_level+1}X")


def close_position(exit_price, reason):
    """Close current position"""
    global current_position
    
    if current_position is None:
        return
    
    entry_price = current_position['entry_price']
    
    if current_position['type'] == 'LONG':
        pnl = exit_price - entry_price
    else:
        pnl = entry_price - exit_price
    
    pnl_pct = (pnl / entry_price) * 100
    r_multiple = pnl / current_position['risk'] if current_position['risk'] > 0 else 0
    is_win = pnl > 0
    
    color = Fore.GREEN if is_win else Fore.RED
    icon = "✅" if is_win else "❌"
    
    print(f"\n{'='*60}")
    print(f"{color}{icon} POSITION CLOSED - {reason}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"   Entry: ${entry_price:,.2f} → Exit: ${exit_price:,.2f}")
    print(f"   P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
    print(f"   R-Multiple: {r_multiple:+.1f}R")
    print(f"   Max Target: {current_position['max_target']}X")
    print(f"{'='*60}")
    
    # Save closed trade
    current_position['exit_price'] = exit_price
    current_position['exit_time'] = datetime.now().isoformat()
    current_position['pnl'] = pnl
    current_position['pnl_pct'] = pnl_pct
    current_position['r_multiple'] = r_multiple
    current_position['exit_reason'] = reason
    current_position['is_win'] = is_win
    
    save_trade(current_position, 'CLOSED')
    
    current_position = None


def save_trade(trade, status):
    """Save trade to JSON and MongoDB using unified storage"""
    trade_copy = trade.copy()
    trade_copy['status'] = status
    trade_copy['updated'] = datetime.now().isoformat()
    trade_copy['strategy'] = 'RSI Options Trader'
    
    # Use unified storage (JSON + MongoDB)
    storage.save_trade(trade_copy)
    print(f"💾 Trade saved to JSON + MongoDB")


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    """Main trading loop"""
    global prev_rsi
    
    print("=" * 60)
    print("📊 RSI LIVE OPTIONS TRADER - Delta Exchange Demo")
    print("=" * 60)
    log_to_ui(f"RSI Period: {RSI_PERIOD}, Oversold: {RSI_OVERSOLD}, Overbought: {RSI_OVERBOUGHT}", "info")
    log_to_ui(f"Timeframe: {TIMEFRAME}, Target: {FIRST_TARGET_MULT}x, Trail Lock: {TRAIL_LOCK_PCT*100:.0f}%", "info")
    print(f"⚙️  RSI Period: {RSI_PERIOD}")
    print(f"🔻 Oversold: {RSI_OVERSOLD} (Buy CALL)")
    print(f"🔺 Overbought: {RSI_OVERBOUGHT} (Buy PUT)")
    print(f"⏱️  Timeframe: {TIMEFRAME}")
    print(f"🎯 First Target: {FIRST_TARGET_MULT}x")
    print(f"🔄 Trail Lock: {TRAIL_LOCK_PCT*100:.0f}%")
    print(f"📅 Expiry: {EXPIRY_DAYS_AHEAD} days ahead")
    print(f"⏳ Scan Interval: {SCAN_INTERVAL_SECONDS}s")
    print("=" * 60)
    
    # Fetch historical candles
    if not fetch_historical_candles():
        log_to_ui("Failed to fetch historical data", "error")
        return
    
    log_to_ui(f"Loaded {len(candles)} candles ({TIMEFRAME})", "success")
    
    # Initial RSI
    prev_rsi = get_current_rsi()
    if prev_rsi:
        log_to_ui(f"Initial RSI: {prev_rsi:.2f}", "info")
    
    log_to_ui("Starting live trading loop...", "success")
    print(f"\n🚀 Starting live trading loop...")
    print(f"⌨️  Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Update price
            price = get_btc_price()
            if price > 0:
                update_candles_with_price(price)
            
            # Check exit if in position
            if current_position is not None:
                check_exit()
            
            # Check for new signals if not in position
            if current_position is None:
                signal = check_signals()
                if signal:
                    execute_signal(signal)
            
            # Display status
            curr_rsi = get_current_rsi()
            if curr_rsi and price > 0:
                pos_status = f"In {current_position['type']} ({current_position['option']})" if current_position else "No position"
                status_msg = f"BTC: ${price:,.2f} | RSI: {curr_rsi:.2f} | {pos_status}"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_msg}")
                # Log to dashboard (less frequently to avoid spam)
                log_to_ui(status_msg, "info")
            
            time.sleep(SCAN_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            log_to_ui("Trading stopped by user", "warning")
            print(f"\n\n{'='*60}")
            print("⏹️  Trading stopped!")
            if current_position:
                print(f"⚠️  Open position: {current_position['type']} ({current_position['option']})")
            print(f"💾 Trades saved to: {TRADES_FILE}")
            print(f"{'='*60}")
            break
        except Exception as e:
            log_to_ui(f"Error: {str(e)[:80]}", "error")
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
