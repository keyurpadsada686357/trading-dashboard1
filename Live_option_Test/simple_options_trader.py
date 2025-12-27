"""
SIMPLE OPTIONS TRADER - Delta Exchange Demo
Places 1 CALL and 1 PUT order at ATM strike
"""
import json
import time
import os
import hashlib
import hmac
import requests
from datetime import datetime, timedelta

# =============================================================================
# API CONFIGURATION - DELTA EXCHANGE TESTNET (DEMO)
# =============================================================================
API_KEY = "hxHrRiP9O6CATdQoYKccuOaJbMz0Yj"
API_SECRET = "GE3If4w5WHrxuSCdMZjurpiMU2xf0ZIsoxa8kcNRoSZCyoDShQeuYLRGe9rk"

# Testnet URLs
BASE_URL = "https://cdn-ind.testnet.deltaex.org"

# =============================================================================
# OPTIONS CONFIGURATION
# =============================================================================
# Dynamic expiry - calculates 2 days from today
EXPIRY_DAYS_AHEAD = 2  # How many days ahead for expiry
expiry_date = datetime.now() + timedelta(days=EXPIRY_DAYS_AHEAD)
OPTIONS_EXPIRY = expiry_date.strftime("%d%m%y")  # Format: DDMMYY

ORDER_SIZE = 1  # Contracts per order
SIDE = "buy"  # "buy" or "sell"

# =============================================================================
# FILE PATHS
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, "simple_options_trades.json")

# Import unified storage (JSON + MongoDB)
import sys
parent_dir = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, parent_dir)
from utils.trade_storage import TradeStorage

# Initialize storage handler
storage = TradeStorage(
    json_file=TRADES_FILE,
    collection_name='simple_options_trades'
)


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
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def get_btc_price():
    """Get current BTC price from API"""
    try:
        r = requests.get(f"{BASE_URL}/v2/tickers/BTCUSD", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return float(data.get("result", {}).get("mark_price", 0))
    except:
        pass
    return 87000  # fallback


def find_atm_options():
    """Find ATM CALL and PUT options for the expiry"""
    print(f"🔍 Finding ATM options for expiry {OPTIONS_EXPIRY}...")
    
    btc_price = get_btc_price()
    print(f"📊 BTC Price: ${btc_price:,.2f}")
    
    try:
        r = requests.get(f"{BASE_URL}/v2/products", timeout=60)
        if r.status_code != 200:
            print("❌ Failed to fetch products")
            return None, None
        
        products = r.json().get("result", [])
        
        call_options = []
        put_options = []
        
        for p in products:
            symbol = p.get("symbol", "")
            strike = p.get("strike_price")
            
            if OPTIONS_EXPIRY in symbol and strike:
                opt = {
                    "id": p["id"],
                    "symbol": symbol,
                    "strike": float(strike)
                }
                
                if symbol.startswith("C-BTC-"):
                    call_options.append(opt)
                elif symbol.startswith("P-BTC-"):
                    put_options.append(opt)
        
        # Sort by distance from current price
        call_options.sort(key=lambda x: abs(x["strike"] - btc_price))
        put_options.sort(key=lambda x: abs(x["strike"] - btc_price))
        
        atm_call = call_options[0] if call_options else None
        atm_put = put_options[0] if put_options else None
        
        if atm_call:
            print(f"✅ ATM CALL: {atm_call['symbol']} (Strike: ${atm_call['strike']:,.0f})")
        if atm_put:
            print(f"✅ ATM PUT: {atm_put['symbol']} (Strike: ${atm_put['strike']:,.0f})")
        
        return atm_call, atm_put
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


def place_order(product_id, symbol, side, size):
    """Place a market order"""
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


def save_trade(trade):
    """Save trade to JSON and MongoDB using unified storage"""
    trade['strategy'] = 'Simple Options Trader'
    storage.save_trade(trade)
    print(f"💾 Trade saved to JSON + MongoDB")


def main():
    """Main function - Place 1 CALL and 1 PUT order"""
    print("=" * 60)
    print("📊 SIMPLE OPTIONS TRADER - Delta Exchange Demo")
    print("=" * 60)
    print(f"🎯 Action: {SIDE.upper()} 1 CALL + 1 PUT at ATM")
    print(f"📅 Expiry: {OPTIONS_EXPIRY}")
    print(f"📦 Size: {ORDER_SIZE} contract(s) each")
    print("=" * 60)
    
    # Find ATM options
    atm_call, atm_put = find_atm_options()
    
    if not atm_call or not atm_put:
        print("❌ Could not find ATM options")
        return
    
    print("\n" + "=" * 60)
    print("📤 PLACING ORDERS...")
    print("=" * 60)
    
    # Place CALL order
    print(f"\n🟢 CALL ORDER:")
    call_order = place_order(atm_call["id"], atm_call["symbol"], SIDE, ORDER_SIZE)
    
    # Place PUT order
    print(f"\n🔴 PUT ORDER:")
    put_order = place_order(atm_put["id"], atm_put["symbol"], SIDE, ORDER_SIZE)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if call_order:
        print(f"✅ CALL: {atm_call['symbol']} - Order ID: {call_order.get('id')}")
        save_trade({
            "type": "CALL",
            "symbol": atm_call["symbol"],
            "strike": atm_call["strike"],
            "side": SIDE,
            "size": ORDER_SIZE,
            "order_id": call_order.get("id"),
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        print(f"❌ CALL: Failed")
    
    if put_order:
        print(f"✅ PUT: {atm_put['symbol']} - Order ID: {put_order.get('id')}")
        save_trade({
            "type": "PUT",
            "symbol": atm_put["symbol"],
            "strike": atm_put["strike"],
            "side": SIDE,
            "size": ORDER_SIZE,
            "order_id": put_order.get("id"),
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        print(f"❌ PUT: Failed")
    
    print(f"\n💾 Trades saved to: {TRADES_FILE}")
    print("=" * 60)
    print("✅ DONE!")


if __name__ == "__main__":
    main()
