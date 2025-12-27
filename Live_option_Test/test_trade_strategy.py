"""
LIVE DEMO TRADING - Delta Exchange Testnet
Takes real trades on demo account every 30 seconds
"""
import websocket
import json
import datetime as dt
import time
import os
import threading
import hashlib
import hmac
import requests
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

# Testnet URLs (Demo account)
BASE_URL = "https://cdn-ind.testnet.deltaex.org"
WEBSOCKET_URL = "wss://socket.india.delta.exchange"

# =============================================================================
# TRADING MODE CONFIGURATION
# =============================================================================
# Set to "FUTURES" or "OPTIONS"
TRADING_MODE = "OPTIONS"  # <-- CHANGE THIS: "FUTURES" or "OPTIONS"

# Common Configuration
SYMBOL = "BTCUSD"
ORDER_SIZE = 1  # Number of contracts per trade
TRADE_INTERVAL_SECONDS = 30

# Futures Configuration (used when TRADING_MODE = "FUTURES")
FUTURES_PRODUCT_ID = None  # Auto-detected

# Options Configuration (used when TRADING_MODE = "OPTIONS")
OPTIONS_TYPE = "STRADDLE"  # "CALL", "PUT", or "STRADDLE" (both CALL + PUT)
OPTIONS_EXPIRY = "271225"  # Expiry date in DDMMYY format (e.g., 27-Dec-2025)

# Auto-detected product IDs
OPTIONS_CALL_PRODUCT_ID = None
OPTIONS_PUT_PRODUCT_ID = None
OPTIONS_CALL_SYMBOL = None
OPTIONS_PUT_SYMBOL = None

# =============================================================================
# FILE PATHS
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, "demo_trades.json")

# Import unified storage (JSON + MongoDB)
import sys
parent_dir = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, parent_dir)
from utils.trade_storage import TradeStorage

# Initialize storage handler
storage = TradeStorage(
    json_file=TRADES_FILE,
    collection_name='demo_trades'
)

# =============================================================================
# TRADING STATE
# =============================================================================
current_price = 0.0
trade_count = 0
current_position = None  # None, "LONG", or "SHORT"
entry_price = 0
entry_time = None

# Lock for thread safety
price_lock = threading.Lock()


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


def fetch_product_id():
    """Fetch product ID based on TRADING_MODE (FUTURES or OPTIONS)"""
    global FUTURES_PRODUCT_ID, OPTIONS_CALL_PRODUCT_ID, OPTIONS_PUT_PRODUCT_ID
    global OPTIONS_CALL_SYMBOL, OPTIONS_PUT_SYMBOL, current_price
    
    print(f"🔍 Looking up product for {TRADING_MODE} mode...")
    
    try:
        r = requests.get(f"{BASE_URL}/v2/products", timeout=60)
        if r.status_code == 200:
            data = r.json()
            products = data.get("result", [])
            
            if TRADING_MODE == "FUTURES":
                # Look for BTCUSD perpetual
                for p in products:
                    symbol = p.get("symbol", "")
                    contract_type = p.get("contract_type", "")
                    
                    if symbol == "BTCUSD" and contract_type == "perpetual_futures":
                        FUTURES_PRODUCT_ID = p["id"]
                        print(f"✅ Found BTCUSD perpetual: ID = {FUTURES_PRODUCT_ID}")
                        return FUTURES_PRODUCT_ID
                
                print(f"⚠️ BTCUSD futures not found")
                return None
                
            elif TRADING_MODE == "OPTIONS":
                # Find ATM option based on current price
                btc_price = current_price if current_price > 0 else 87000  # fallback
                
                # Collect CALL and PUT options
                call_options = []
                put_options = []
                
                for p in products:
                    symbol = p.get("symbol", "")
                    contract_type = p.get("contract_type", "")
                    strike = p.get("strike_price")
                    
                    if OPTIONS_EXPIRY in symbol and strike:
                        opt_data = {
                            "id": p["id"],
                            "symbol": symbol,
                            "strike": float(strike)
                        }
                        
                        if symbol.startswith("C-BTC-") and contract_type == "call_options":
                            call_options.append(opt_data)
                        elif symbol.startswith("P-BTC-") and contract_type == "put_options":
                            put_options.append(opt_data)
                
                # Sort by distance from current price (ATM)
                call_options.sort(key=lambda x: abs(x["strike"] - btc_price))
                put_options.sort(key=lambda x: abs(x["strike"] - btc_price))
                
                if OPTIONS_TYPE in ["CALL", "STRADDLE"] and call_options:
                    atm_call = call_options[0]
                    OPTIONS_CALL_PRODUCT_ID = atm_call["id"]
                    OPTIONS_CALL_SYMBOL = atm_call["symbol"]
                    print(f"✅ Found ATM CALL: {atm_call['symbol']}")
                    print(f"   Strike: ${atm_call['strike']:,.0f} | ID: {OPTIONS_CALL_PRODUCT_ID}")
                
                if OPTIONS_TYPE in ["PUT", "STRADDLE"] and put_options:
                    atm_put = put_options[0]
                    OPTIONS_PUT_PRODUCT_ID = atm_put["id"]
                    OPTIONS_PUT_SYMBOL = atm_put["symbol"]
                    print(f"✅ Found ATM PUT: {atm_put['symbol']}")
                    print(f"   Strike: ${atm_put['strike']:,.0f} | ID: {OPTIONS_PUT_PRODUCT_ID}")
                
                if OPTIONS_TYPE == "STRADDLE":
                    print(f"\n📊 STRADDLE: Will buy both CALL + PUT at ATM")
                    return (OPTIONS_CALL_PRODUCT_ID, OPTIONS_PUT_PRODUCT_ID)
                elif OPTIONS_TYPE == "CALL":
                    return OPTIONS_CALL_PRODUCT_ID
                else:
                    return OPTIONS_PUT_PRODUCT_ID
            
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def get_active_product_ids():
    """Get product IDs based on trading mode"""
    if TRADING_MODE == "FUTURES":
        return [FUTURES_PRODUCT_ID]
    elif OPTIONS_TYPE == "STRADDLE":
        return [OPTIONS_CALL_PRODUCT_ID, OPTIONS_PUT_PRODUCT_ID]
    elif OPTIONS_TYPE == "CALL":
        return [OPTIONS_CALL_PRODUCT_ID]
    else:
        return [OPTIONS_PUT_PRODUCT_ID]


def get_active_product_id():
    """Get single active product ID (for non-straddle)"""
    ids = get_active_product_ids()
    return ids[0] if ids else None



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
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=payload, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        return response.json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def get_wallet_balance():
    """Get wallet balance"""
    result = api_request("GET", "/v2/wallet/balances")
    if result and result.get("success"):
        balances = result.get("result", [])
        for bal in balances:
            if bal.get("asset_symbol") == "USDT":
                print(f"💰 USDT Balance: ${float(bal.get('available_balance', 0)):,.2f}")
                return float(bal.get('available_balance', 0))
    return 0


def get_positions():
    """Get open positions"""
    result = api_request("GET", "/v2/positions")
    if result and result.get("success"):
        return result.get("result", [])
    return []


def place_order(side, size):
    """Place market order (for non-straddle modes)"""
    product_id = get_active_product_id()
    if not product_id:
        print("❌ No product ID available")
        return None
    
    return place_order_by_product_id(product_id, side, size)


def place_order_by_product_id(product_id, side, size, symbol=None):
    """Place market order for a specific product"""
    order_data = {
        "product_id": product_id,
        "size": size,
        "side": side,
        "order_type": "market_order"
    }
    
    label = symbol if symbol else f"ID:{product_id}"
    print(f"📤 Placing {side.upper()} order for {size} contracts ({label})...")
    result = api_request("POST", "/v2/orders", order_data)
    
    if result:
        if result.get("success"):
            order = result.get("result", {})
            print(f"✅ Order placed! ID: {order.get('id')}")
            return order
        else:
            error = result.get("error", {})
            print(f"❌ Order failed: {error.get('code')} - {error.get('message', 'Unknown error')}")
    return None


def place_straddle_orders(side, size):
    """Place both CALL and PUT orders for straddle"""
    print(f"\n{'='*60}")
    print(f"📊 STRADDLE: Placing {side.upper()} for both CALL + PUT")
    print(f"{'='*60}")
    
    orders = []
    
    # Place CALL order
    if OPTIONS_CALL_PRODUCT_ID:
        print(f"\n🟢 CALL: {OPTIONS_CALL_SYMBOL}")
        call_order = place_order_by_product_id(
            OPTIONS_CALL_PRODUCT_ID, side, size, OPTIONS_CALL_SYMBOL
        )
        if call_order:
            orders.append({"type": "CALL", "order": call_order})
    
    # Place PUT order
    if OPTIONS_PUT_PRODUCT_ID:
        print(f"\n🔴 PUT: {OPTIONS_PUT_SYMBOL}")
        put_order = place_order_by_product_id(
            OPTIONS_PUT_PRODUCT_ID, side, size, OPTIONS_PUT_SYMBOL
        )
        if put_order:
            orders.append({"type": "PUT", "order": put_order})
    
    return orders


def close_position():
    """Close current position"""
    positions = get_positions()
    
    product_id = get_active_product_id()
    for pos in positions:
        if pos.get("product_id") == product_id:
            size = abs(int(pos.get("size", 0)))
            if size > 0:
                # Opposite side to close
                side = "sell" if pos.get("size", 0) > 0 else "buy"
                return place_order(side, size)
    return None


def load_trades():
    """Load existing trades from JSON"""
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_trade(trade):
    """Save trade to JSON and MongoDB using unified storage"""
    trade['strategy'] = 'Test Trade Strategy'
    storage.save_trade(trade)
    print(f"💾 Trade saved to JSON + MongoDB")


def get_next_trade_id():
    """Get next trade ID"""
    trades = load_trades()
    if trades:
        return max(t.get('trade_id', 0) for t in trades) + 1
    return 1


def take_trade():
    """Execute a real trade on Delta Exchange Demo"""
    global trade_count, current_position, entry_price, entry_time
    
    with price_lock:
        price = current_price
    
    if price <= 0:
        print("⏳ Waiting for live price...")
        return
    
    trade_count += 1
    trade_id = get_next_trade_id()
    current_time = dt.datetime.now()
    
    # Alternate between LONG and SHORT
    new_direction = "LONG" if trade_count % 2 == 1 else "SHORT"
    
    # =================================================================
    # CLOSE EXISTING POSITION (if any)
    # =================================================================
    if current_position is not None:
        print(f"\n{'='*60}")
        print(f"🔄 Closing {current_position} position...")
        
        close_result = close_position()
        
        if close_result:
            exit_price = price
            duration = (current_time - entry_time).total_seconds() / 60
            
            if current_position == "LONG":
                pnl = exit_price - entry_price
            else:
                pnl = entry_price - exit_price
            
            pnl_pct = (pnl / entry_price) * 100
            is_win = pnl > 0
            
            color = Fore.GREEN if is_win else Fore.RED if HAS_COLOR else ""
            icon = "✅" if is_win else "❌"
            
            print(f"{color}{icon} CLOSED {current_position}{Style.RESET_ALL if HAS_COLOR else ''}")
            print(f"💰 Entry: ${entry_price:,.2f} → Exit: ${exit_price:,.2f}")
            print(f"📊 P&L: {color}${pnl:+,.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL if HAS_COLOR else ''}")
            
            # Save closed trade
            trade = {
                'trade_id': trade_id - 1,
                'direction': current_position,
                'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'exit_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'duration_minutes': round(duration, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 4),
                'exit_reason': 'TIME_EXIT',
                'is_win': is_win,
                'executed_on': 'DELTA_DEMO'
            }
            save_trade(trade)
    
    # =================================================================
    # OPEN NEW POSITION
    # =================================================================
    side = "buy" if new_direction == "LONG" else "sell"
    
    # Check if we're in straddle mode
    if TRADING_MODE == "OPTIONS" and OPTIONS_TYPE == "STRADDLE":
        orders = place_straddle_orders(side, ORDER_SIZE)
        if orders:
            current_position = new_direction
            entry_price = price
            entry_time = current_time
            
            print(f"\n{'='*60}")
            print(f"📊 STRADDLE {new_direction} OPENED on DELTA DEMO")
            print(f"{'='*60}")
            print(f"⏰ Time: {current_time.strftime('%H:%M:%S')}")
            print(f"💰 BTC Price: ${price:,.2f}")
            print(f"📦 Size: {ORDER_SIZE} contracts each")
            print(f"✅ CALL: {OPTIONS_CALL_SYMBOL}")
            print(f"✅ PUT: {OPTIONS_PUT_SYMBOL}")
            print(f"🔢 Trade #{trade_count}")
            print(f"⏳ Next trade in {TRADE_INTERVAL_SECONDS}s...")
            print(f"{'='*60}")
        else:
            print(f"⚠️ Failed to open straddle position")
            current_position = None
    else:
        # Regular single order
        order = place_order(side, ORDER_SIZE)
        
        if order:
            current_position = new_direction
            entry_price = price
            entry_time = current_time
            
            color = Fore.GREEN if new_direction == "LONG" else Fore.RED if HAS_COLOR else ""
            icon = "🟢" if new_direction == "LONG" else "🔴"
            
            print(f"\n{'='*60}")
            print(f"{color}{icon} OPENED {new_direction} on DELTA DEMO{Style.RESET_ALL if HAS_COLOR else ''}")
            print(f"{'='*60}")
            print(f"⏰ Time: {current_time.strftime('%H:%M:%S')}")
            print(f"💰 Entry: ${price:,.2f}")
            print(f"📦 Size: {ORDER_SIZE} contracts")
            print(f"🔢 Trade #{trade_count}")
            print(f"⏳ Next trade in {TRADE_INTERVAL_SECONDS}s...")
            print(f"{'='*60}")
        else:
            print(f"⚠️ Failed to open {new_direction} position")
            current_position = None


def trade_timer():
    """Timer thread that takes trades every 30 seconds"""
    # Wait for price
    while current_price <= 0:
        time.sleep(1)
    
    print(f"\n✅ Got live price! Checking account...")
    
    # Fetch correct product ID
    fetch_product_id()
    
    # Check balance
    balance = get_wallet_balance()
    
    print(f"🚀 Starting trade timer - every {TRADE_INTERVAL_SECONDS} seconds\n")
    
    while True:
        try:
            take_trade()
            time.sleep(TRADE_INTERVAL_SECONDS)
        except Exception as e:
            print(f"❌ Trade error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)


def on_message(ws, message):
    """Handle WebSocket messages"""
    global current_price
    
    try:
        data = json.loads(message)
        
        if isinstance(data, dict) and data.get("type") in ["all_trades", "all_trades_snapshot"]:
            if data.get("symbol") == SYMBOL:
                if data.get("type") == "all_trades_snapshot":
                    trades = data.get("trades", [])
                    if trades:
                        with price_lock:
                            current_price = float(trades[-1].get("price", 0))
                else:
                    with price_lock:
                        current_price = float(data.get("price", 0))
    except:
        pass


def on_open(ws):
    """Handle connection open"""
    print(f"\n{'='*60}")
    print(f"{Fore.CYAN if HAS_COLOR else ''}🔥 DELTA EXCHANGE DEMO TRADING{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*60}")
    print(f"📊 Mode: {TRADING_MODE}")
    if TRADING_MODE == "OPTIONS":
        print(f"   Type: {OPTIONS_TYPE} | Expiry: {OPTIONS_EXPIRY}")
    print(f"📊 Symbol: {SYMBOL}")
    print(f"⏱️  Trade Interval: {TRADE_INTERVAL_SECONDS} seconds")
    print(f"📦 Order Size: {ORDER_SIZE} contracts")
    print(f"🌐 API: {BASE_URL}")
    print(f"💾 Trades: {TRADES_FILE}")
    print(f"\n⚠️  THIS TRADES ON YOUR DEMO ACCOUNT!")
    print(f"\n⌨️  Press Ctrl+C to stop")
    print(f"{'='*60}")
    print(f"\n🔌 Connected! Waiting for live price...")
    
    # Start trade timer
    timer_thread = threading.Thread(target=trade_timer, daemon=True)
    timer_thread.start()
    
    # Subscribe to trades
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": {
            "channels": [{
                "name": "all_trades",
                "symbols": [SYMBOL]
            }]
        }
    }))


def on_error(ws, error):
    print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"\n🔌 Connection closed")


def main():
    """Main entry point"""
    print(f"🚀 Starting Delta Exchange Demo Trading...")
    print(f"📡 Connecting to {WEBSOCKET_URL}...")
    
    try:
        ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        ws.run_forever(ping_interval=20, ping_timeout=10)
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print(f"⏹️  Trading stopped!")
        print(f"📊 Total trades: {trade_count}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
