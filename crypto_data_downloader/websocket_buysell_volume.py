import websocket
import json
import datetime as dt
import time
import os
from collections import defaultdict
from colorama import init, Fore, Style

# Initialize colorama
try:
    init(autoreset=True)
    HAS_COLOR = True
except:
    HAS_COLOR = False

# -------------------------------------
# CONFIG
# -------------------------------------
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
SYMBOL = "BTCUSD"
CANDLE_INTERVAL = 60  # 1 minute in seconds

# Volume tracking
current_minute = None
buy_volume = 0
sell_volume = 0
total_trades = 0
buy_trades = 0
sell_trades = 0

# Price tracking
current_price = 0
minute_open = 0
minute_high = 0
minute_low = float('inf')


# -------------------------------------
# CLEAR SCREEN
# -------------------------------------
def clear_screen():
    """Clear console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


# -------------------------------------
# RESET MINUTE DATA
# -------------------------------------
def reset_minute():
    """Reset counters for a new minute"""
    global buy_volume, sell_volume, total_trades, buy_trades, sell_trades
    global minute_open, minute_high, minute_low, current_price
    
    buy_volume = 0
    sell_volume = 0
    total_trades = 0
    buy_trades = 0
    sell_trades = 0
    minute_open = current_price
    minute_high = current_price
    minute_low = current_price


# -------------------------------------
# PRINT STATS
# -------------------------------------
def print_live_stats():
    """Print live buy/sell volume statistics"""
    global buy_volume, sell_volume, total_trades, buy_trades, sell_trades
    global current_price, minute_open, minute_high, minute_low
    
    total_volume = buy_volume + sell_volume
    
    # Calculate percentages
    buy_pct = (buy_volume / total_volume * 100) if total_volume > 0 else 0
    sell_pct = (sell_volume / total_volume * 100) if total_volume > 0 else 0
    
    # Determine market pressure
    if buy_volume > sell_volume:
        pressure = "BULLISH"
        pressure_color = Fore.GREEN if HAS_COLOR else ""
        pressure_icon = "📈"
    elif sell_volume > buy_volume:
        pressure = "BEARISH"
        pressure_color = Fore.RED if HAS_COLOR else ""
        pressure_icon = "📉"
    else:
        pressure = "NEUTRAL"
        pressure_color = Fore.YELLOW if HAS_COLOR else ""
        pressure_icon = "➡️"
    
    # Calculate price change
    price_change = current_price - minute_open if minute_open > 0 else 0
    price_change_pct = (price_change / minute_open * 100) if minute_open > 0 else 0
    
    # Get current time
    now = dt.datetime.now()
    current_time = now.strftime("%H:%M:%S")
    minute_label = now.strftime("%H:%M")
    
    if HAS_COLOR:
        print(f"\033[2J\033[H")  # Clear screen and move to top
        
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}🔴 LIVE BUY/SELL VOLUME TRACKER - {SYMBOL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}⏰ Current Time:{Style.RESET_ALL} {current_time}")
        print(f"{Fore.YELLOW}📊 Minute:{Style.RESET_ALL} {minute_label}")
        
        # Price Info
        price_color = Fore.GREEN if price_change >= 0 else Fore.RED
        print(f"\n{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💰 PRICE INFO{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"   Current:  {price_color}${current_price:,.2f}{Style.RESET_ALL}")
        print(f"   Open:     ${minute_open:,.2f}")
        print(f"   High:     ${minute_high:,.2f}")
        print(f"   Low:      ${minute_low:,.2f}")
        print(f"   Change:   {price_color}{price_change:+,.2f} ({price_change_pct:+.2f}%){Style.RESET_ALL}")
        
        # Volume Info
        print(f"\n{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📦 VOLUME BREAKDOWN{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        
        # Buy Volume
        buy_bar = "█" * int(buy_pct / 2)
        print(f"   {Fore.GREEN}🟢 BUY:  {buy_volume:>10,.0f} ({buy_pct:>5.1f}%) {buy_bar}{Style.RESET_ALL}")
        
        # Sell Volume
        sell_bar = "█" * int(sell_pct / 2)
        print(f"   {Fore.RED}🔴 SELL: {sell_volume:>10,.0f} ({sell_pct:>5.1f}%) {sell_bar}{Style.RESET_ALL}")
        
        # Total
        print(f"   {Fore.CYAN}📊 TOTAL:{Style.RESET_ALL} {total_volume:>10,.0f}")
        
        # Delta (Difference)
        delta = buy_volume - sell_volume
        delta_color = Fore.GREEN if delta > 0 else Fore.RED if delta < 0 else Fore.YELLOW
        print(f"   {delta_color}⚖️  DELTA:{Style.RESET_ALL} {delta_color}{delta:>+10,.0f}{Style.RESET_ALL}")
        
        # Trade Count
        print(f"\n{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🔢 TRADE COUNT{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"   {Fore.GREEN}🟢 Buy Trades:  {buy_trades:>6}{Style.RESET_ALL}")
        print(f"   {Fore.RED}🔴 Sell Trades: {sell_trades:>6}{Style.RESET_ALL}")
        print(f"   {Fore.CYAN}📊 Total:       {total_trades:>6}{Style.RESET_ALL}")
        
        # Market Pressure
        print(f"\n{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 MARKET PRESSURE{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
        print(f"   {pressure_color}{pressure_icon} {pressure}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}⌨️  Press Ctrl+C to stop{Style.RESET_ALL}\n")
        
    else:
        # No color fallback
        os.system('cls')
        
        print(f"{'='*80}")
        print(f"LIVE BUY/SELL VOLUME TRACKER - {SYMBOL}")
        print(f"{'='*80}")
        
        print(f"\nCurrent Time: {current_time}")
        print(f"Minute: {minute_label}")
        
        print(f"\n{'-'*80}")
        print(f"PRICE INFO")
        print(f"{'-'*80}")
        print(f"   Current:  ${current_price:,.2f}")
        print(f"   Open:     ${minute_open:,.2f}")
        print(f"   High:     ${minute_high:,.2f}")
        print(f"   Low:      ${minute_low:,.2f}")
        print(f"   Change:   ${price_change:+,.2f} ({price_change_pct:+.2f}%)")
        
        print(f"\n{'-'*80}")
        print(f"VOLUME BREAKDOWN")
        print(f"{'-'*80}")
        print(f"   BUY:   {buy_volume:>10,.0f} ({buy_pct:>5.1f}%)")
        print(f"   SELL:  {sell_volume:>10,.0f} ({sell_pct:>5.1f}%)")
        print(f"   TOTAL: {total_volume:>10,.0f}")
        print(f"   DELTA: {delta:>+10,.0f}")
        
        print(f"\n{'-'*80}")
        print(f"TRADE COUNT")
        print(f"{'-'*80}")
        print(f"   Buy Trades:  {buy_trades:>6}")
        print(f"   Sell Trades: {sell_trades:>6}")
        print(f"   Total:       {total_trades:>6}")
        
        print(f"\n{'-'*80}")
        print(f"MARKET PRESSURE: {pressure}")
        print(f"{'-'*80}")
        
        print(f"\nPress Ctrl+C to stop\n")


# -------------------------------------
# WEBSOCKET HANDLERS
# -------------------------------------
def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global current_minute, buy_volume, sell_volume, total_trades, buy_trades, sell_trades
    global current_price, minute_open, minute_high, minute_low
    
    try:
        data = json.loads(message)
        
        # Handle snapshot (initial 50 trades)
        if isinstance(data, dict) and data.get("type") == "all_trades_snapshot":
            if data.get("symbol") == SYMBOL and "trades" in data:
                # Process recent trades for initial data
                for trade in data["trades"][-10:]:  # Just last 10 to initialize
                    process_trade(trade)
                print_live_stats()
        
        # Handle real-time trades
        elif isinstance(data, dict) and data.get("type") == "all_trades":
            if data.get("symbol") == SYMBOL:
                process_trade(data)
                print_live_stats()
                
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Error: {e}")


def process_trade(trade):
    """Process a single trade"""
    global current_minute, buy_volume, sell_volume, total_trades, buy_trades, sell_trades
    global current_price, minute_open, minute_high, minute_low
    
    # Get trade details
    price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))
    timestamp = trade.get("timestamp", 0)
    buyer_role = trade.get("buyer_role", "")
    seller_role = trade.get("seller_role", "")
    
    # Determine trade direction
    # If buyer is taker = market buy = buy pressure
    # If seller is taker = market sell = sell pressure
    is_buy = (buyer_role == "taker")
    
    # Get minute timestamp
    trade_time = dt.datetime.fromtimestamp(timestamp / 1000000)
    minute_ts = trade_time.replace(second=0, microsecond=0)
    
    # Check if we're in a new minute
    if current_minute is None:
        current_minute = minute_ts
        reset_minute()
    elif minute_ts > current_minute:
        # New minute started
        current_minute = minute_ts
        reset_minute()
    
    # Update volume
    if is_buy:
        buy_volume += size
        buy_trades += 1
    else:
        sell_volume += size
        sell_trades += 1
    
    total_trades += 1
    
    # Update price tracking
    current_price = price
    if minute_open == 0:
        minute_open = price
    minute_high = max(minute_high, price)
    minute_low = min(minute_low, price)


def on_error(ws, error):
    """Handle WebSocket errors"""
    if HAS_COLOR:
        print(f"{Fore.RED}❌ WebSocket Error: {error}{Style.RESET_ALL}")
    else:
        print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    if HAS_COLOR:
        print(f"\n{Fore.YELLOW}🔌 WebSocket closed{Style.RESET_ALL}")
    else:
        print(f"\n🔌 WebSocket closed")


def on_open(ws):
    """Handle WebSocket connection open"""
    clear_screen()
    
    if HAS_COLOR:
        print(f"{Fore.GREEN}{'='*80}")
        print(f"{Fore.GREEN}🔴 Connecting to Live Trade Feed...")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
    else:
        print(f"{'='*80}")
        print(f"Connecting to Live Trade Feed...")
        print(f"{'='*80}")
    
    print(f"🌐 Connected to: {WEBSOCKET_URL}")
    print(f"📡 Symbol: {SYMBOL}\n")
    
    # Subscribe to all_trades channel
    subscribe_message = {
        "type": "subscribe",
        "payload": {
            "channels": [
                {
                    "name": "all_trades",
                    "symbols": [SYMBOL]
                }
            ]
        }
    }
    
    ws.send(json.dumps(subscribe_message))
    
    if HAS_COLOR:
        print(f"{Fore.CYAN}📊 Subscribing to live trades...{Style.RESET_ALL}\n")
    else:
        print(f"📊 Subscribing to live trades...\n")
    
    time.sleep(1)


# -------------------------------------
# MAIN
# -------------------------------------
def main():
    try:
        ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        
        # Run forever
        ws.run_forever()
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*80}")
        if HAS_COLOR:
            print(f"{Fore.YELLOW}⏹️  Tracker stopped by user{Style.RESET_ALL}")
        else:
            print(f"⏹️  Tracker stopped by user")
        print(f"{'='*80}")
        print(f"👋 Goodbye!\n")


# -------------------------------------
# RUN
# -------------------------------------
if __name__ == "__main__":
    main()
