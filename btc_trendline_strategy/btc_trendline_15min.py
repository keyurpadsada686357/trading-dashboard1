"""
Bitcoin Trendline Breakout Strategy - 1 Minute
Based on MaxCapital stock strategy adapted for crypto
"""
import websocket
import json
import datetime as dt
import time
import os
import pandas as pd
import numpy as np
import requests
from collections import deque
from colorama import init, Fore, Style

# Initialize colorama
try:
    init(autoreset=True)
    HAS_COLOR = True
except:
    HAS_COLOR = False

# Strategy Configuration
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
CANDLE_API = "https://cdn.india.deltaex.org/v2/chart/history"
SYMBOL = "BTCUSD"
CANDLE_INTERVAL = 15  # 15 minutes

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, f"trades_{CANDLE_INTERVAL}min.json")

# MaxCapital Strategy Parameters
LOOKBACK_SWING = 3
VOLUME_MA_DAYS = 20
VOLUME_MA_MULT = 1.2
ATR_LENGTH = 14
ATR_SL_MULT = 1.0
TARGET_ATR_MULT = 3.0
MIN_CANDLES_REQUIRED = 20  # Lower for 15-min

# Trading state
current_position = None
entry_price = 0
entry_time = None
stop_loss = 0
target = 0
trade_id = 1

# Candle storage
candle_data = []
current_candle = {
    'timestamp': None,
    'open': 0,
    'high': 0,
    'low': float('inf'),
    'close': 0,
    'volume': 0
}


def load_historical_candles():
    """Load last 100 candles from API for immediate startup"""
    global candle_data
    
    print("📥 Loading historical candles...")
    
    try:
        # Get last 6 hours of data (enough for all timeframes)
        now = int(time.time())
        from_ts = now - (360 * 60)  # 6 hours (360 minutes)
        
        params = {
            "symbol": SYMBOL,
            "resolution": str(CANDLE_INTERVAL),
            "from": from_ts,
            "to": now
        }
        
        r = requests.get(CANDLE_API, params=params, timeout=10)
        js = r.json()
        
        if "result" in js and js["result"].get("s") == "ok":
            res = js["result"]
            
            for i in range(len(res["t"])):
                candle_time = dt.datetime.fromtimestamp(res["t"][i])
                
                candle_data.append({
                    'timestamp': candle_time,
                    'open': res["o"][i],
                    'high': res["h"][i],
                    'low': res["l"][i],
                    'close': res["c"][i],
                    'volume': res["v"][i]
                })
            
            print(f"✅ Loaded {len(candle_data)} historical candles!")
            if len(candle_data) >= MIN_CANDLES_REQUIRED:
                print(f"🎯 Ready to trade immediately!\n")
            else:
                print(f"⏳ Need {MIN_CANDLES_REQUIRED - len(candle_data)} more candles...\n")
            
            return True
        else:
            print(f"⚠️  Could not load historical data, will build from live stream\n")
            return False
            
    except Exception as e:
        print(f"⚠️  Error loading history: {e}")
        print(f"📊 Will build candles from live stream instead\n")
        return False


def calculate_atr(df, length=14):
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=length).mean()
    
    return atr


def detect_swing_highs(df, lookback=3):
    """Detect swing high points"""
    swing_highs = pd.Series([False] * len(df), index=df.index)
    
    for i in range(lookback, len(df) - lookback):
        is_swing = True
        center_high = df.iloc[i]['high']
        
        # Check left
        for j in range(i - lookback, i):
            if df.iloc[j]['high'] >= center_high:
                is_swing = False
                break
        
        # Check right
        if is_swing:
            for j in range(i + 1, i + lookback + 1):
                if df.iloc[j]['high'] > center_high:
                    is_swing = False
                    break
        
        if is_swing:
            swing_highs.iloc[i] = True
    
    return swing_highs


def detect_swing_lows(df, lookback=3):
    """Detect swing low points"""
    swing_lows = pd.Series([False] * len(df), index=df.index)
    
    for i in range(lookback, len(df) - lookback):
        is_swing = True
        center_low = df.iloc[i]['low']
        
        # Check left
        for j in range(i - lookback, i):
            if df.iloc[j]['low'] <= center_low:
                is_swing = False
                break
        
        # Check right
        if is_swing:
            for j in range(i + 1, i + lookback + 1):
                if df.iloc[j]['low'] < center_low:
                    is_swing = False
                    break
        
        if is_swing:
            swing_lows.iloc[i] = True
    
    return swing_lows


def line_value_at(idx1, price1, idx2, price2, target_idx):
    """Calculate trendline value at target index"""
    if idx2 == idx1:
        return price2
    
    slope = (price2 - price1) / (idx2 - idx1)
    value = price1 + slope * (target_idx - idx1)
    
    return value


def check_entry_signal(df):
    """
    Check for trendline breakout entry signal
    Returns: dict with entry info or None
    """
    if len(df) < MIN_CANDLES_REQUIRED:
        return None
    
    # Calculate indicators
    df['atr'] = calculate_atr(df, ATR_LENGTH)
    df['vol_ma'] = df['volume'].rolling(VOLUME_MA_DAYS).mean()
    df['swing_high'] = detect_swing_highs(df, LOOKBACK_SWING)
    df['swing_low'] = detect_swing_lows(df, LOOKBACK_SWING)
    
    i = len(df) - 1
    
    # Need at least 2 swing highs
    swing_high_indices = df.index[df['swing_high'] & (df.index < i)].tolist()
    if len(swing_high_indices) < 2:
        return None
    
    idx2 = swing_high_indices[-1]
    idx1 = swing_high_indices[-2]
    price1 = df.loc[idx1, 'high']
    price2 = df.loc[idx2, 'high']
    
    # Require descending highs (downtrend)
    if price2 >= price1:
        return None
    
    # Check breakout
    if i < 1:
        return None
    
    line_prev = line_value_at(idx1, price1, idx2, price2, i-1)
    line_curr = line_value_at(idx1, price1, idx2, price2, i)
    
    prev_close = df.loc[i-1, 'close']
    curr_close = df.loc[i, 'close']
    
    # Breakout condition: previous close below line, current close above
    if not (prev_close <= line_prev and curr_close > line_curr):
        return None
    
    # Volume confirmation
    if pd.notna(df.loc[i, 'vol_ma']):
        if df.loc[i, 'volume'] <= VOLUME_MA_MULT * df.loc[i, 'vol_ma']:
            return None
    
    # ATR check
    entry_atr = df.loc[i, 'atr']
    if pd.isna(entry_atr) or entry_atr <= 0:
        return None
    
    # Find reference swing low for stop loss
    swing_low_indices = df.index[df['swing_low'] & (df.index < i)].tolist()
    if len(swing_low_indices) > 0:
        ref_low_idx = swing_low_indices[-1]
        ref_low_price = df.loc[ref_low_idx, 'low']
    else:
        ref_low_price = df.loc[i, 'low']
    
    sl = ref_low_price - ATR_SL_MULT * entry_atr
    tgt = curr_close + TARGET_ATR_MULT * entry_atr
    
    return {
        'entry_price': float(curr_close),
        'atr': float(entry_atr),
        'stop_loss': float(sl),
        'target': float(tgt),
        'timestamp': df.loc[i, 'timestamp']
    }


def finalize_candle():
    """Finalize current candle and add to history"""
    global current_candle, candle_data
    
    if current_candle['timestamp'] is None:
        return
    
    candle_data.append({
        'timestamp': current_candle['timestamp'],
        'open': current_candle['open'],
        'high': current_candle['high'],
        'low': current_candle['low'],
        'close': current_candle['close'],
        'volume': current_candle['volume']
    })
    
    # Show progress
    candle_count = len(candle_data)
    if candle_count % 10 == 0:
        print(f"📊 Collected {candle_count} candles... (need {MIN_CANDLES_REQUIRED} minimum)")
    
    # Keep only last 200 candles in memory
    if len(candle_data) > 200:
        candle_data.pop(0)
    
    # Check for entry signal if not in position
    if current_position is None and len(candle_data) >= MIN_CANDLES_REQUIRED:
        if candle_count == MIN_CANDLES_REQUIRED:
            print(f"\n✅ Ready! Now scanning for trendline breakouts...\n")
        
        df = pd.DataFrame(candle_data)
        df.reset_index(drop=True, inplace=True)
        
        signal = check_entry_signal(df)
        if signal:
            open_position(signal)
    
    # Check exit if in position
    if current_position:
        check_exit()


def open_position(signal):
    """Open new position"""
    global current_position, entry_price, entry_time, stop_loss, target
    
    current_position = "LONG"
    entry_price = signal['entry_price']
    entry_time = dt.datetime.now()
    stop_loss = signal['stop_loss']
    target = signal['target']
    
    print(f"\n{'='*80}")
    print(f"{Fore.GREEN if HAS_COLOR else ''}🟢 LONG BREAKOUT - POSITION #{trade_id}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}")
    print(f"⏰ Time: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 Entry: ${entry_price:,.2f}")
    print(f"🎯 Target: ${target:,.2f} (ATR: {signal['atr']:.2f})")
    print(f"🛑 Stop: ${stop_loss:,.2f}")
    print(f"{'='*80}\n")


def check_exit():
    """Check if position should exit"""
    global current_position, entry_price, entry_time, trade_id
    
    if not current_position:
        return
    
    current = candle_data[-1]
    
    # Check stop loss
    if current['low'] <= stop_loss:
        close_position(stop_loss, "STOP_LOSS")
        return
    
    # Check target
    if current['high'] >= target:
        close_position(target, "TARGET")
        return


def close_position(exit_price, reason):
    """Close position and log trade"""
    global current_position, entry_price, entry_time, trade_id
    
    exit_time = dt.datetime.now()
    duration = (exit_time - entry_time).total_seconds() / 60
    
    pnl = exit_price - entry_price
    pnl_pct = (pnl / entry_price) * 100
    is_win = pnl > 0
    
    # Print
    color = Fore.GREEN if is_win else Fore.RED if HAS_COLOR else ""
    icon = "✅" if is_win else "❌"
    
    print(f"\n{'='*80}")
    print(f"{color}{icon} CLOSING LONG #{trade_id} - {reason}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}")
    print(f"💰 Entry: ${entry_price:,.2f}")
    print(f"💰 Exit: ${exit_price:,.2f}")
    print(f"⏱️  Duration: {duration:.1f} min")
    print(f"📊 P&L: {color}${pnl:+,.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}\n")
    
    # Save to JSON
    trade = {
        'trade_id': trade_id,
        'direction': 'LONG',
        'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
        'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
        'entry_price': entry_price,
        'exit_price': exit_price,
        'stop_loss': stop_loss,
        'target': target,
        'duration_minutes': round(duration, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 4),
        'exit_reason': reason,
        'is_win': is_win
    }
    
    # Load and save
    trades = []
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            trades = json.load(f)
    
    trades.append(trade)
    
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2)
    
    # Reset
    current_position = None
    entry_price = 0
    entry_time = None
    trade_id += 1


def on_message(ws, message):
    """Handle WebSocket messages"""
    global current_candle
    
    try:
        data = json.loads(message)
        
        if isinstance(data, dict) and data.get("type") in ["all_trades", "all_trades_snapshot"]:
            if data.get("symbol") == SYMBOL:
                if data.get("type") == "all_trades_snapshot":
                    for trade in data.get("trades", [])[-5:]:
                        process_trade(trade)
                else:
                    process_trade(data)
    except:
        pass


def process_trade(trade):
    """Process individual trade"""
    global current_candle
    
    price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))
    timestamp = trade.get("timestamp", 0)
    
    trade_time = dt.datetime.fromtimestamp(timestamp / 1000000)
    # Round to 15-minute intervals
    candle_time = trade_time.replace(second=0, microsecond=0)
    candle_time = candle_time.replace(minute=(candle_time.minute // CANDLE_INTERVAL) * CANDLE_INTERVAL)
    
    # New candle
    if current_candle['timestamp'] is None:
        current_candle['timestamp'] = candle_time
        current_candle['open'] = price
        current_candle['high'] = price
        current_candle['low'] = price
        current_candle['close'] = price
        current_candle['volume'] = 0
    elif candle_time > current_candle['timestamp']:
        finalize_candle()
        current_candle = {
            'timestamp': candle_time,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0
        }
    
    # Update current candle
    current_candle['high'] = max(current_candle['high'], price)
    current_candle['low'] = min(current_candle['low'], price)
    current_candle['close'] = price
    current_candle['volume'] += size


def on_open(ws):
    """Handle connection open"""
    print(f"\n{'='*80}")
    print(f"{Fore.CYAN if HAS_COLOR else ''}🚀 BITCOIN TRENDLINE BREAKOUT [{CANDLE_INTERVAL}-MIN]{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}")
    print(f"📊 Symbol: {SYMBOL}")
    print(f"⏱️  Timeframe: {CANDLE_INTERVAL} minute")
    print(f"💾 Trades: {TRADES_FILE}")
    print(f"\n📋 Strategy:")
    print(f"   - Descending trendline breakout")
    print(f"   - ATR-based stops ({ATR_SL_MULT}x)")
    print(f"   - ATR-based targets ({TARGET_ATR_MULT}x)")
    print(f"   - Volume confirmation ({VOLUME_MA_MULT}x)")
    print(f"\n⌨️  Press Ctrl+C to stop\n{'='*80}\n")
    
    # Load historical candles first
    load_historical_candles()
    
    # Subscribe
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
    print(f"❌ Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"\n🔌 Connection closed")


def main():
    """Main entry point"""
    global trade_id
    
    # Load previous trades
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            trades = json.load(f)
            if trades:
                trade_id = trades[-1]['trade_id'] + 1
    
    print(f"🚀 Starting {CANDLE_INTERVAL}-min Bitcoin Trendline Strategy...")
    
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
        print(f"\n\n{'='*80}")
        print(f"⏹️  Strategy stopped")
        print(f"📊 Trades: {trade_id - 1}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
