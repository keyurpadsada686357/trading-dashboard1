import websocket
import json
import datetime as dt
import time
import os
from collections import deque
from colorama import init, Fore, Style

# Initialize colorama
try:
    init(autoreset=True)
    HAS_COLOR = True
except:
    HAS_COLOR = False

# -------------------------------------
# STRATEGY CONFIGURATION
# -------------------------------------
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
SYMBOL = "BTCUSD"

# Strategy Parameters (MODERATE SETTINGS - 5 MINUTE)
CANDLE_INTERVAL = 5  # 5-minute candles
MIN_DELTA_BUY = 150
MIN_DELTA_SELL = -150
MIN_BUY_PERCENT = 60
MIN_SELL_PERCENT = 60
CONSECUTIVE_CANDLES = 2
TAKE_PROFIT_PCT = 0.6  # 0.6%
STOP_LOSS_PCT = 0.15   # 0.15%
MAX_HOLD_MINUTES = 30

# Trade Tracking
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, "trades_5min.json")

# Import unified storage
import sys
parent_dir = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, parent_dir)
from utils.trade_storage import TradeStorage

# Initialize storage handler (JSON + MongoDB if configured)
storage = TradeStorage(
    json_file=TRADES_FILE,
    collection_name='volume_trades_5min'
)

current_position = None  # None, "LONG", or "SHORT"
entry_price = 0
entry_time = None
trade_id = 1

# Candle history (store last N minutes)
candle_history = deque(maxlen=10)

# Current minute tracking
current_minute = None
buy_volume = 0
sell_volume = 0
total_trades = 0
minute_open = 0
minute_high = 0
minute_low = float('inf')
minute_close = 0
current_price = 0



# -------------------------------------
# CANDLE MANAGEMENT
# -------------------------------------
def print_current_market_state():
    """Print current candle state to console"""
    total_volume = buy_volume + sell_volume
    if total_volume == 0:
        return
    
    delta = buy_volume - sell_volume
    buy_pct = (buy_volume / total_volume * 100) if total_volume > 0 else 0
    sell_pct = (sell_volume / total_volume * 100) if total_volume > 0 else 0
    
    # Determine candle color
    is_green = minute_close >= minute_open
    price_change = minute_close - minute_open
    price_change_pct = (price_change / minute_open * 100) if minute_open > 0 else 0
    
    # Determine market pressure
    if delta > MIN_DELTA_BUY:
        pressure = "🟢 BULLISH"
        pressure_color = Fore.GREEN if HAS_COLOR else ""
    elif delta < MIN_DELTA_SELL:
        pressure = "🔴 BEARISH"
        pressure_color = Fore.RED if HAS_COLOR else ""
    else:
        pressure = "⚪ NEUTRAL"
        pressure_color = Fore.YELLOW if HAS_COLOR else ""
    
    # Check signal readiness
    buy_ready = delta > MIN_DELTA_BUY and buy_pct > MIN_BUY_PERCENT and is_green
    sell_ready = delta < MIN_DELTA_SELL and sell_pct > MIN_SELL_PERCENT and not is_green
    
    # Clear screen and print
    if HAS_COLOR:
        print("\033[2J\033[H", end='')  # Clear screen
    
    now = dt.datetime.now().strftime("%H:%M:%S")
    candle_time = current_minute.strftime("%H:%M") if current_minute else "--:--"
    
    print(f"\n{'='*80}")
    if HAS_COLOR:
        print(f"{Fore.CYAN}📊 LIVE MARKET MONITOR - {SYMBOL} [5-MIN]{Style.RESET_ALL}")
    else:
        print(f"📊 LIVE MARKET MONITOR - {SYMBOL} [5-MIN]")
    print(f"{'='*80}")
    print(f"🕐 Current Time: {now} | Candle: {candle_time}")
    
    # Position status
    if current_position:
        pnl = (current_price - entry_price) if current_position == "LONG" else (entry_price - current_price)
        pnl_pct = (pnl / entry_price * 100) if entry_price > 0 else 0
        duration = (dt.datetime.now() - entry_time).total_seconds() / 60 if entry_time else 0
        
        pos_color = Fore.GREEN if pnl >= 0 else Fore.RED if HAS_COLOR else ""
        if HAS_COLOR:
            print(f"\n{pos_color}💼 POSITION: {current_position} | P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | {duration:.1f}min{Style.RESET_ALL}")
        else:
            print(f"\n💼 POSITION: {current_position} | P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | {duration:.1f}min")
    else:
        print(f"\n💼 POSITION: None (Waiting for signal...)")
    
    # Price info
    price_color = Fore.GREEN if is_green else Fore.RED if HAS_COLOR else ""
    print(f"\n{'-'*80}")
    if HAS_COLOR:
        print(f"{Fore.YELLOW}💰 PRICE{Style.RESET_ALL}")
    else:
        print(f"💰 PRICE")
    print(f"{'-'*80}")
    print(f"Open:    ${minute_open:>10,.2f}")
    print(f"High:    ${minute_high:>10,.2f}")
    print(f"Low:     ${minute_low:>10,.2f}")
    if HAS_COLOR:
        print(f"Close:   {price_color}${minute_close:>10,.2f}{Style.RESET_ALL}")
        print(f"Change:  {price_color}{price_change:>+10,.2f} ({price_change_pct:+.2f}%){Style.RESET_ALL}")
    else:
        print(f"Close:   ${minute_close:>10,.2f}")
        print(f"Change:  {price_change:>+10,.2f} ({price_change_pct:+.2f}%)")
    
    # Volume info
    print(f"\n{'-'*80}")
    if HAS_COLOR:
        print(f"{Fore.YELLOW}📦 VOLUME{Style.RESET_ALL}")
    else:
        print(f"📦 VOLUME")
    print(f"{'-'*80}")
    
    buy_bar = "█" * min(int(buy_pct / 2), 50)
    sell_bar = "█" * min(int(sell_pct / 2), 50)
    
    if HAS_COLOR:
        print(f"{Fore.GREEN}BUY:   {buy_volume:>8,.0f} ({buy_pct:>5.1f}%) {buy_bar}{Style.RESET_ALL}")
        print(f"{Fore.RED}SELL:  {sell_volume:>8,.0f} ({sell_pct:>5.1f}%) {sell_bar}{Style.RESET_ALL}")
        print(f"TOTAL: {total_volume:>8,.0f}")
        
        delta_color = Fore.GREEN if delta > 0 else Fore.RED if delta < 0 else Fore.YELLOW
        print(f"\n{delta_color}DELTA: {delta:>+8,.0f}{Style.RESET_ALL}")
    else:
        print(f"BUY:   {buy_volume:>8,.0f} ({buy_pct:>5.1f}%) {buy_bar}")
        print(f"SELL:  {sell_volume:>8,.0f} ({sell_pct:>5.1f}%) {sell_bar}")
        print(f"TOTAL: {total_volume:>8,.0f}")
        print(f"\nDELTA: {delta:>+8,.0f}")
    
    # Market pressure
    if HAS_COLOR:
        print(f"\n{pressure_color}{pressure}{Style.RESET_ALL}")
    else:
        print(f"\n{pressure}")
    
    # Signal readiness
    print(f"\n{'-'*80}")
    if HAS_COLOR:
        print(f"{Fore.YELLOW}🎯 SIGNAL STATUS{Style.RESET_ALL}")
    else:
        print(f"🎯 SIGNAL STATUS")
    print(f"{'-'*80}")
    
    if buy_ready:
        remaining = max(0, CONSECUTIVE_CANDLES - len([c for c in list(candle_history) if c.get('delta', 0) > MIN_DELTA_BUY and c.get('buy_pct', 0) > MIN_BUY_PERCENT and c.get('is_green', False)]))
        if CONSECUTIVE_CANDLES == 1:
            msg = "✅ BUY signal! Will trigger when current candle closes"
        else:
            msg = f"✅ BUY conditions met! Need {remaining} more confirming candle(s)"
        
        if HAS_COLOR:
            print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
        else:
            print(msg)
    elif sell_ready:
        remaining = max(0, CONSECUTIVE_CANDLES - len([c for c in list(candle_history) if c.get('delta', 0) < MIN_DELTA_SELL and c.get('sell_pct', 0) > MIN_SELL_PERCENT and not c.get('is_green', True)]))
        if CONSECUTIVE_CANDLES == 1:
            msg = "✅ SELL signal! Will trigger when current candle closes"
        else:
            msg = f"✅ SELL conditions met! Need {remaining} more confirming candle(s)"
        
        if HAS_COLOR:
            print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
        else:
            print(msg)
    else:
        print(f"⏳ Monitoring... (Delta: {abs(MIN_DELTA_BUY - delta) if delta > 0 else abs(MIN_DELTA_SELL - delta):.0f} away from threshold)")
    
    print(f"\n{'='*80}\n")


def finalize_candle():
    """Finalize current minute candle and add to history"""
    global candle_history, buy_volume, sell_volume, minute_open, minute_high, minute_low, minute_close
    
    if current_minute is None:
        return
    
    total_volume = buy_volume + sell_volume
    if total_volume == 0:
        return
    
    delta = buy_volume - sell_volume
    buy_pct = (buy_volume / total_volume * 100) if total_volume > 0 else 0
    sell_pct = (sell_volume / total_volume * 100) if total_volume > 0 else 0
    
    candle = {
        'timestamp': current_minute,
        'open': minute_open,
        'high': minute_high,
        'low': minute_low,
        'close': minute_close,
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'total_volume': total_volume,
        'delta': delta,
        'buy_pct': buy_pct,
        'sell_pct': sell_pct,
        'is_green': minute_close >= minute_open
    }
    
    candle_history.append(candle)
    
    # Check for signals after adding new candle
    check_signals()
    
    # Check position management
    if current_position:
        manage_position()


def reset_minute():
    """Reset counters for new minute"""
    global buy_volume, sell_volume, total_trades, minute_open, minute_high, minute_low, minute_close
    
    buy_volume = 0
    sell_volume = 0
    total_trades = 0
    minute_open = current_price
    minute_high = current_price
    minute_low = current_price
    minute_close = current_price


# -------------------------------------
# SIGNAL DETECTION
# -------------------------------------
def check_signals():
    """Check for BUY or SELL signals"""
    global current_position
    
    # Don't generate new signals if already in position
    if current_position:
        return
    
    # Need at least CONSECUTIVE_CANDLES
    if len(candle_history) < CONSECUTIVE_CANDLES:
        return
    
    # Get last N candles
    recent_candles = list(candle_history)[-CONSECUTIVE_CANDLES:]
    
    # Check BUY signal
    buy_signal = check_buy_signal(recent_candles)
    if buy_signal:
        open_position("LONG")
        return
    
    # Check SELL signal
    sell_signal = check_sell_signal(recent_candles)
    if sell_signal:
        open_position("SHORT")


def check_buy_signal(candles):
    """Check if BUY conditions met"""
    for candle in candles:
        # All conditions must be true
        if candle['delta'] < MIN_DELTA_BUY:
            return False
        if candle['buy_pct'] < MIN_BUY_PERCENT:
            return False
        if not candle['is_green']:
            return False
    
    # Check price rising (only if we have multiple candles to compare)
    if len(candles) > 1:
        if candles[-1]['close'] <= candles[0]['close']:
            return False
    
    return True


def check_sell_signal(candles):
    """Check if SELL conditions met"""
    for candle in candles:
        # All conditions must be true
        if candle['delta'] > MIN_DELTA_SELL:
            return False
        if candle['sell_pct'] < MIN_SELL_PERCENT:
            return False
        if candle['is_green']:
            return False
    
    # Check price falling (only if we have multiple candles to compare)
    if len(candles) > 1:
        if candles[-1]['close'] >= candles[0]['close']:
            return False
    
    return True


# -------------------------------------
# POSITION MANAGEMENT
# -------------------------------------
def open_position(direction):
    """Open a new position"""
    global current_position, entry_price, entry_time, trade_id
    
    current_position = direction
    entry_price = current_price
    entry_time = dt.datetime.now()
    
    # Calculate targets
    if direction == "LONG":
        take_profit = entry_price * (1 + TAKE_PROFIT_PCT / 100)
        stop_loss = entry_price * (1 - STOP_LOSS_PCT / 100)
        signal_icon = "🟢"
        color = Fore.GREEN if HAS_COLOR else ""
    else:
        take_profit = entry_price * (1 - TAKE_PROFIT_PCT / 100)
        stop_loss = entry_price * (1 + STOP_LOSS_PCT / 100)
        signal_icon = "🔴"
        color = Fore.RED if HAS_COLOR else ""
    
    # Print entry
    print(f"\n{'='*80}")
    if HAS_COLOR:
        print(f"{color}{signal_icon} {direction} SIGNAL - ENTERING POSITION #{trade_id}{Style.RESET_ALL}")
    else:
        print(f"{signal_icon} {direction} SIGNAL - ENTERING POSITION #{trade_id}")
    print(f"{'='*80}")
    print(f"⏰ Time: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 Entry Price: ${entry_price:,.2f}")
    print(f"🎯 Take Profit: ${take_profit:,.2f} (+{TAKE_PROFIT_PCT}%)")
    print(f"🛑 Stop Loss: ${stop_loss:,.2f} (-{STOP_LOSS_PCT}%)")
    print(f"📊 Last Candle Delta: {candle_history[-1]['delta']:+,.0f}")
    print(f"{'='*80}\n")


def manage_position():
    """Check if position should be closed"""
    global current_position, entry_price, entry_time, trade_id
    
    if not current_position:
        return
    
    # Calculate P&L
    if current_position == "LONG":
        pnl = current_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        take_profit = entry_price * (1 + TAKE_PROFIT_PCT / 100)
        stop_loss = entry_price * (1 - STOP_LOSS_PCT / 100)
        
        # Check exit conditions
        if current_price >= take_profit:
            close_position("TAKE_PROFIT", pnl, pnl_pct)
        elif current_price <= stop_loss:
            close_position("STOP_LOSS", pnl, pnl_pct)
        elif check_delta_reversal("LONG"):
            close_position("DELTA_REVERSAL", pnl, pnl_pct)
        elif check_time_exit():
            close_position("TIME_EXIT", pnl, pnl_pct)
    
    else:  # SHORT
        pnl = entry_price - current_price
        pnl_pct = (pnl / entry_price) * 100
        take_profit = entry_price * (1 - TAKE_PROFIT_PCT / 100)
        stop_loss = entry_price * (1 + STOP_LOSS_PCT / 100)
        
        # Check exit conditions
        if current_price <= take_profit:
            close_position("TAKE_PROFIT", pnl, pnl_pct)
        elif current_price >= stop_loss:
            close_position("STOP_LOSS", pnl, pnl_pct)
        elif check_delta_reversal("SHORT"):
            close_position("DELTA_REVERSAL", pnl, pnl_pct)
        elif check_time_exit():
            close_position("TIME_EXIT", pnl, pnl_pct)


def check_delta_reversal(position_type):
    """Check if volume delta has reversed"""
    if len(candle_history) < 2:
        return False
    
    recent = list(candle_history)[-2:]
    
    if position_type == "LONG":
        # Exit LONG if strong selling appears
        for candle in recent:
            if candle['delta'] < -200:
                return True
    else:
        # Exit SHORT if strong buying appears
        for candle in recent:
            if candle['delta'] > 200:
                return True
    
    return False


def check_time_exit():
    """Check if max hold time exceeded"""
    if entry_time is None:
        return False
    
    time_elapsed = (dt.datetime.now() - entry_time).total_seconds() / 60
    return time_elapsed >= MAX_HOLD_MINUTES


def close_position(reason, pnl, pnl_pct):
    """Close current position and log trade"""
    global current_position, entry_price, entry_time, trade_id
    
    exit_time = dt.datetime.now()
    duration = (exit_time - entry_time).total_seconds() / 60
    
    # Determine if win or loss
    is_win = pnl > 0
    
    # Color coding
    if HAS_COLOR:
        if is_win:
            result_color = Fore.GREEN
            result_icon = "✅"
        else:
            result_color = Fore.RED
            result_icon = "❌"
    else:
        result_color = ""
        result_icon = "✅" if is_win else "❌"
    
    # Print exit
    print(f"\n{'='*80}")
    if HAS_COLOR:
        print(f"{result_color}{result_icon} CLOSING {current_position} POSITION #{trade_id} - {reason}{Style.RESET_ALL}")
    else:
        print(f"{result_icon} CLOSING {current_position} POSITION #{trade_id} - {reason}")
    print(f"{'='*80}")
    print(f"⏰ Exit Time: {exit_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 Entry Price: ${entry_price:,.2f}")
    print(f"💰 Exit Price: ${current_price:,.2f}")
    print(f"⏱️  Duration: {duration:.1f} minutes")
    if HAS_COLOR:
        print(f"📊 P&L: {result_color}${pnl:+,.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL}")
    else:
        print(f"📊 P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
    print(f"{'='*80}\n")
    
    # Save trade to JSON
    trade_data = {
        'trade_id': trade_id,
        'direction': current_position,
        'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
        'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
        'entry_price': entry_price,
        'exit_price': current_price,
        'duration_minutes': round(duration, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 4),
        'exit_reason': reason,
        'is_win': is_win
    }
    
    # Save using unified storage (JSON + MongoDB if configured)
    storage.save_trade(trade_data)
    
    # Reset position
    current_position = None
    entry_price = 0
    entry_time = None
    trade_id += 1


# -------------------------------------
# WEBSOCKET HANDLERS
# -------------------------------------
def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global current_minute, buy_volume, sell_volume, total_trades
    global current_price, minute_open, minute_high, minute_low, minute_close
    
    try:
        data = json.loads(message)
        
        # Handle trades
        if isinstance(data, dict) and data.get("type") in ["all_trades", "all_trades_snapshot"]:
            if data.get("symbol") == SYMBOL:
                if data.get("type") == "all_trades_snapshot" and "trades" in data:
                    for trade in data["trades"][-5:]:
                        process_trade(trade)
                else:
                    process_trade(data)
                    
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Error: {e}")


def process_trade(trade):
    """Process individual trade"""
    global current_minute, buy_volume, sell_volume, total_trades
    global current_price, minute_open, minute_high, minute_low, minute_close
    
    price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))
    timestamp = trade.get("timestamp", 0)
    buyer_role = trade.get("buyer_role", "")
    
    is_buy = (buyer_role == "taker")
    
    trade_time = dt.datetime.fromtimestamp(timestamp / 1000000)
    # Round to CANDLE_INTERVAL (5 minutes)
    minute_ts = trade_time.replace(second=0, microsecond=0)
    minute_ts = minute_ts.replace(minute=(minute_ts.minute // CANDLE_INTERVAL) * CANDLE_INTERVAL)
    
    # Check if new minute
    if current_minute is None:
        current_minute = minute_ts
        reset_minute()
    elif minute_ts > current_minute:
        # Finalize previous candle
        finalize_candle()
        current_minute = minute_ts
        reset_minute()
    
    # Update volume
    if is_buy:
        buy_volume += size
    else:
        sell_volume += size
    
    total_trades += 1
    
    # Update price
    current_price = price
    minute_close = price
    if minute_open == 0:
        minute_open = price
    minute_high = max(minute_high, price)
    minute_low = min(minute_low, price)
    
    # Update display every 20 trades (approximately every few seconds)
    if total_trades % 20 == 0:
        print_current_market_state()


def on_error(ws, error):
    """Handle WebSocket errors"""
    print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    print(f"\n🔌 WebSocket closed")


def on_open(ws):
    """Handle WebSocket connection open"""
    print(f"\n{'='*80}")
    if HAS_COLOR:
        print(f"{Fore.CYAN}🤖 VOLUME-PRICE STRATEGY [5-MIN] - LIVE TRADING{Style.RESET_ALL}")
    else:
        print(f"🤖 VOLUME-PRICE STRATEGY [5-MIN] - LIVE TRADING")
    print(f"{'='*80}")
    print(f"🌐 Connected to: {WEBSOCKET_URL}")
    print(f"📊 Symbol: {SYMBOL}")
    print(f"\n📋 Strategy Parameters:")
    print(f"   Min Buy Delta: +{MIN_DELTA_BUY}")
    print(f"   Min Sell Delta: {MIN_DELTA_SELL}")
    print(f"   Confirmations: {CONSECUTIVE_CANDLES} candles")
    print(f"   Take Profit: {TAKE_PROFIT_PCT}%")
    print(f"   Stop Loss: {STOP_LOSS_PCT}%")
    print(f"   Max Hold: {MAX_HOLD_MINUTES} minutes")
    print(f"\n💾 Trades saved to: {TRADES_FILE}")
    print(f"⌨️  Press Ctrl+C to stop\n")
    print(f"{'='*80}\n")
    
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


# -------------------------------------
# MAIN
# -------------------------------------
def main():
    """Main entry point"""
    global trade_id
    
    # Load previous trades to get next ID
    trade_id = storage.get_next_trade_id()
    
    print("🚀 Starting Volume-Price Strategy...")
    print(f"📂 Trades file: {TRADES_FILE}\n")
    
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            # Use ping/pong for keep-alive
            ws = websocket.WebSocketApp(
                WEBSOCKET_URL,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open
            
            # Run with ping/pong to keep connection alive
            ws.run_forever(ping_interval=20, ping_timeout=10)
            
            # If we reach here, connection closed
            retry_count += 1
            if retry_count < max_retries:
                wait_time = min(retry_count * 2, 10)  # Exponential backoff, max 10s
                print(f"\n⏳ Reconnecting in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print(f"\n\n{'='*80}")
            if HAS_COLOR:
                print(f"{Fore.YELLOW}⏹️  Strategy stopped by user{Style.RESET_ALL}")
            else:
                print(f"⏹️  Strategy stopped by user")
            print(f"{'='*80}")
            print(f"📊 Total trades logged: {trade_id - 1}")
            print(f"👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5)
    
    if retry_count >= max_retries:
        print(f"\n❌ Max reconnection attempts reached. Exiting.")


if __name__ == "__main__":
    main()
