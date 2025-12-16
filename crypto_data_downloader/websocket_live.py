import websocket
import json
import datetime as dt
import time
import os
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
RESOLUTION = "1m"  # 1-minute candles

# Current candle being built
current_candle = None
candle_count = 0


# -------------------------------------
# CLEAR SCREEN
# -------------------------------------
def clear_screen():
    """Clear console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


# -------------------------------------
# PRINT CANDLE (REAL-TIME)
# -------------------------------------
def print_candle(candle, is_completed=False):
    """Print candle data in real-time"""
    global candle_count
    
    # Convert timestamp
    candle_start = dt.datetime.fromtimestamp(candle["candle_start_time"] / 1000000, tz=dt.timezone.utc)
    candle_start_ist = candle_start + dt.timedelta(hours=5, minutes=30)
    
    # Calculate change
    change = candle["close"] - candle["open"]
    change_pct = (change / candle["open"]) * 100 if candle["open"] != 0 else 0
    
    # Determine color
    if HAS_COLOR:
        if change >= 0:
            price_color = Fore.GREEN
            arrow = "📈"
            status_icon = "✅" if is_completed else "🔄"
        else:
            price_color = Fore.RED
            arrow = "📉"
            status_icon = "✅" if is_completed else "🔄"
        
        # Clear and redraw (for live updates)
        if not is_completed:
            # Move cursor up and clear for live update
            # print("\033[F" * 12, end='')  # Move up 12 lines
            pass
        
        print(f"\n{'='*70}")
        if is_completed:
            candle_count += 1
            print(f"{Fore.YELLOW}{status_icon} CANDLE #{candle_count} COMPLETED!{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}{status_icon} FORMING CANDLE (Live Update){Style.RESET_ALL}")
        print(f"{'='*70}")
        
        print(f"{Fore.CYAN}📅 Time (IST):{Style.RESET_ALL}  {candle_start_ist.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}📅 Time (UTC):{Style.RESET_ALL}  {candle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}⏱️  Resolution:{Style.RESET_ALL}  {candle['resolution']}")
        
        print(f"\n{price_color}{arrow} OHLC:{Style.RESET_ALL}")
        print(f"   Open:   ${candle['open']:>12,.2f}")
        print(f"   High:   ${candle['high']:>12,.2f}")
        print(f"   Low:    ${candle['low']:>12,.2f}")
        print(f"   Close:  ${candle['close']:>12,.2f}")
        
        print(f"\n{price_color}📊 Change:{Style.RESET_ALL}  ${change:+,.2f} ({change_pct:+.2f}%)")
        
        if "volume" in candle and candle["volume"]:
            print(f"{Fore.CYAN}📦 Volume:{Style.RESET_ALL}  {candle['volume']:,.2f}")
        
        # Show current time for live updates
        now = dt.datetime.now().strftime("%H:%M:%S")
        print(f"\n{Fore.YELLOW}🕐 Last Update:{Style.RESET_ALL} {now}")
        
    else:
        # No color fallback
        arrow = "↑" if change >= 0 else "↓"
        status = "COMPLETED" if is_completed else "FORMING (Live)"
        
        print(f"\n{'='*70}")
        print(f"{status} - Candle #{candle_count if is_completed else 'Current'}")
        print(f"{'='*70}")
        
        print(f"Time (IST):  {candle_start_ist.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Time (UTC):  {candle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Resolution:  {candle['resolution']}")
        
        print(f"\n{arrow} OHLC:")
        print(f"   Open:   ${candle['open']:>12,.2f}")
        print(f"   High:   ${candle['high']:>12,.2f}")
        print(f"   Low:    ${candle['low']:>12,.2f}")
        print(f"   Close:  ${candle['close']:>12,.2f}")
        
        print(f"\nChange:  ${change:+,.2f} ({change_pct:+.2f}%)")
        
        if "volume" in candle and candle["volume"]:
            print(f"Volume:  {candle['volume']:,.2f}")


# -------------------------------------
# WEBSOCKET HANDLERS
# -------------------------------------
def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global current_candle
    
    try:
        data = json.loads(message)
        
        # Check if it's a candlestick message
        if isinstance(data, dict) and data.get("type") == f"candlestick_{RESOLUTION}":
            symbol = data.get("symbol")
            
            if symbol == SYMBOL:
                # Check if this is a new candle
                if current_candle is None:
                    # First candle
                    current_candle = data.copy()
                    print_candle(current_candle, is_completed=False)
                    
                elif data["candle_start_time"] != current_candle["candle_start_time"]:
                    # New candle started! Previous one is complete
                    print_candle(current_candle, is_completed=True)
                    
                    # Beep for completed candle
                    try:
                        print('\a')
                    except:
                        pass
                    
                    # Start tracking new candle
                    current_candle = data.copy()
                    print_candle(current_candle, is_completed=False)
                    
                else:
                    # Same candle, update values
                    current_candle = data.copy()
                    print_candle(current_candle, is_completed=False)
        
        # Handle subscription confirmation
        elif isinstance(data, dict) and data.get("type") == "subscribed":
            if HAS_COLOR:
                print(f"{Fore.GREEN}✅ Successfully subscribed to: {data.get('symbol', 'channel')}{Style.RESET_ALL}")
            else:
                print(f"✅ Successfully subscribed to: {data.get('symbol', 'channel')}")
                
    except json.JSONDecodeError:
        pass  # Ignore non-JSON messages
    except Exception as e:
        print(f"Error processing message: {e}")


def on_error(ws, error):
    """Handle WebSocket errors"""
    if HAS_COLOR:
        print(f"{Fore.RED}❌ WebSocket Error: {error}{Style.RESET_ALL}")
    else:
        print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    if HAS_COLOR:
        print(f"\n{Fore.YELLOW}🔌 WebSocket closed")
        print(f"   Status: {close_status_code}")
        print(f"   Message: {close_msg}{Style.RESET_ALL}")
    else:
        print(f"\n🔌 WebSocket closed")
        print(f"   Status: {close_status_code}")
        print(f"   Message: {close_msg}")


def on_open(ws):
    """Handle WebSocket connection open"""
    if HAS_COLOR:
        print(f"{Fore.GREEN}{'='*70}")
        print(f"{Fore.GREEN}🔴 LIVE WebSocket Monitor - {SYMBOL} {RESOLUTION} Candles")
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
    else:
        print(f"{'='*70}")
        print(f"🔴 LIVE WebSocket Monitor - {SYMBOL} {RESOLUTION} Candles")
        print(f"{'='*70}")
    
    print(f"🌐 Connected to: {WEBSOCKET_URL}")
    print(f"⌨️  Press Ctrl+C to stop\n")
    
    # Subscribe to 1-minute candlestick channel
    subscribe_message = {
        "type": "subscribe",
        "payload": {
            "channels": [
                {
                    "name": f"candlestick_{RESOLUTION}",
                    "symbols": [SYMBOL]
                }
            ]
        }
    }
    
    ws.send(json.dumps(subscribe_message))
    
    if HAS_COLOR:
        print(f"{Fore.CYAN}📡 Subscribing to {SYMBOL} {RESOLUTION} candles...{Style.RESET_ALL}\n")
    else:
        print(f"📡 Subscribing to {SYMBOL} {RESOLUTION} candles...\n")


# -------------------------------------
# MAIN
# -------------------------------------
def main():
    clear_screen()
    
    print("Initializing WebSocket connection...\n")
    
    try:
        ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        
        # Run forever (blocks)
        ws.run_forever()
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        if HAS_COLOR:
            print(f"{Fore.YELLOW}⏹️  WebSocket monitor stopped by user{Style.RESET_ALL}")
        else:
            print(f"⏹️  WebSocket monitor stopped by user")
        print(f"{'='*70}")
        print(f"📊 Total completed candles: {candle_count}")
        print(f"👋 Goodbye!\n")


# -------------------------------------
# RUN
# -------------------------------------
if __name__ == "__main__":
    main()
