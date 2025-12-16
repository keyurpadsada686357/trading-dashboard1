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
CANDLE_INTERVAL = 1  # 1 minute

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(SCRIPT_DIR, f"trades_{CANDLE_INTERVAL}min.json")

# Import unified storage
import sys
parent_dir = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, parent_dir)
from utils.trade_storage import TradeStorage

# Initialize storage handler (JSON + MongoDB if configured)
storage = TradeStorage(
    json_file=TRADES_FILE,
    collection_name=f'trendline_trades_{CANDLE_INTERVAL}min'
)


# MaxCapital Strategy Parameters
LOOKBACK_SWING = 3
VOLUME_MA_DAYS = 20
VOLUME_MA_MULT = 1.2
ATR_LENGTH = 14
ATR_SL_MULT = 1.0
TARGET_ATR_MULT = 3.0
MIN_CANDLES_REQUIRED = 60

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
    Check for trendline breakout/breakdown entry signals
    Returns: dict with entry info (including direction) or None
    """
    if len(df) < MIN_CANDLES_REQUIRED:
        return None
    
    # Calculate indicators
    df['atr'] = calculate_atr(df, ATR_LENGTH)
    df['vol_ma'] = df['volume'].rolling(VOLUME_MA_DAYS).mean()
    df['swing_high'] = detect_swing_highs(df, LOOKBACK_SWING)
    df['swing_low'] = detect_swing_lows(df, LOOKBACK_SWING)
    
    i = len(df) - 1
    
    # Check for LONG setup (descending trendline breakout - upward)
    swing_high_indices = df.index[df['swing_high'] & (df.index < i)].tolist()
    if len(swing_high_indices) >= 2:
        idx2 = swing_high_indices[-1]
        idx1 = swing_high_indices[-2]
        price1 = df.loc[idx1, 'high']
        price2 = df.loc[idx2, 'high']
        
        # Descending highs (downtrend)
        if price2 < price1 and i >= 1:
            line_prev = line_value_at(idx1, price1, idx2, price2, i-1)
            line_curr = line_value_at(idx1, price1, idx2, price2, i)
            
            prev_close = df.loc[i-1, 'close']
            curr_close = df.loc[i, 'close']
            
            # Breakout above
            if prev_close <= line_prev and curr_close > line_curr:
                # Volume confirmation
                if pd.notna(df.loc[i, 'vol_ma']):
                    if df.loc[i, 'volume'] <= VOLUME_MA_MULT * df.loc[i, 'vol_ma']:
                        return None
                
                entry_atr = df.loc[i, 'atr']
                if pd.isna(entry_atr) or entry_atr <= 0:
                    return None
                
                # Find swing low for stop
                swing_low_indices = df.index[df['swing_low'] & (df.index < i)].tolist()
                ref_low_price = df.loc[swing_low_indices[-1], 'low'] if swing_low_indices else df.loc[i, 'low']
                
                sl = ref_low_price - ATR_SL_MULT * entry_atr
                tgt = curr_close + TARGET_ATR_MULT * entry_atr
                
                return {
                    'direction': 'LONG',
                    'entry_price': float(curr_close),
                    'atr': float(entry_atr),
                    'stop_loss': float(sl),
                    'target': float(tgt),
                    'timestamp': df.loc[i, 'timestamp']
                }
    
    # Check for SHORT setup (ascending trendline breakdown - downward)
    swing_low_indices = df.index[df['swing_low'] & (df.index < i)].tolist()
    if len(swing_low_indices) >= 2:
        idx2 = swing_low_indices[-1]
        idx1 = swing_low_indices[-2]
        price1 = df.loc[idx1, 'low']
        price2 = df.loc[idx2, 'low']
        
        # Ascending lows (uptrend)
        if price2 > price1 and i >= 1:
            line_prev = line_value_at(idx1, price1, idx2, price2, i-1)
            line_curr = line_value_at(idx1, price1, idx2, price2, i)
            
            prev_close = df.loc[i-1, 'close']
            curr_close = df.loc[i, 'close']
            
            # Breakdown below
            if prev_close >= line_prev and curr_close < line_curr:
                # Volume confirmation
                if pd.notna(df.loc[i, 'vol_ma']):
                    if df.loc[i, 'volume'] <= VOLUME_MA_MULT * df.loc[i, 'vol_ma']:
                        return None
                
                entry_atr = df.loc[i, 'atr']
                if pd.isna(entry_atr) or entry_atr <= 0:
                    return None
                
                # Find swing high for stop
                swing_high_indices_for_stop = df.index[df['swing_high'] & (df.index < i)].tolist()
                ref_high_price = df.loc[swing_high_indices_for_stop[-1], 'high'] if swing_high_indices_for_stop else df.loc[i, 'high']
                
                sl = ref_high_price + ATR_SL_MULT * entry_atr
                tgt = curr_close - TARGET_ATR_MULT * entry_atr
                
                return {
                    'direction': 'SHORT',
                    'entry_price': float(curr_close),
                    'atr': float(entry_atr),
                    'stop_loss': float(sl),
                    'target': float(tgt),
                    'timestamp': df.loc[i, 'timestamp']
                }
    
    return None


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
    
    current_position = signal['direction']
    entry_price = signal['entry_price']
    entry_time = dt.datetime.now()
    stop_loss = signal['stop_loss']
    target = signal['target']
    
    color = Fore.GREEN if signal['direction'] == 'LONG' else Fore.RED if HAS_COLOR else ""
    icon = "🟢" if signal['direction'] == 'LONG' else "🔴"
    
    print(f"\n{'='*80}")
    print(f"{color}{icon} {signal['direction']} - POSITION #{trade_id}{Style.RESET_ALL if HAS_COLOR else ''}")
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
    
    if current_position == "LONG":
        # LONG: stop below entry, target above
        if current['low'] <= stop_loss:
            close_position(stop_loss, "STOP_LOSS")
            return
        if current['high'] >= target:
            close_position(target, "TARGET")
            return
    
    elif current_position == "SHORT":
        # SHORT: stop above entry, target below
        if current['high'] >= stop_loss:
            close_position(stop_loss, "STOP_LOSS")
            return
        if current['low'] <= target:
            close_position(target, "TARGET")
            return


def close_position(exit_price, reason):
    """Close position and log trade"""
    global current_position, entry_price, entry_time, trade_id
    
    exit_time = dt.datetime.now()
    duration = (exit_time - entry_time).total_seconds() / 60
    
    # Calculate P&L based on direction
    if current_position == "LONG":
        pnl = exit_price - entry_price  # Buy low, sell high
    else:  # SHORT
        pnl = entry_price - exit_price  # Sell high, buy low
    
    pnl_pct = (pnl / entry_price) * 100
    is_win = pnl > 0
    
    # Print
    color = Fore.GREEN if is_win else Fore.RED if HAS_COLOR else ""
    icon = "✅" if is_win else "❌"
    
    print(f"\n{'='*80}")
    print(f"{color}{icon} CLOSING {current_position} #{trade_id} - {reason}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}")
    print(f"💰 Entry: ${entry_price:,.2f}")
    print(f"💰 Exit: ${exit_price:,.2f}")
    print(f"⏱️  Duration: {duration:.1f} min")
    print(f"📊 P&L: {color}${pnl:+,.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{'='*80}\n")
    
    # Save to JSON
    trade = {
        'trade_id': trade_id,
        'direction': current_position,
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
    
    # Save using unified storage (JSON + MongoDB if configured)
    storage.save_trade(trade)
    
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
    candle_time = trade_time.replace(second=0, microsecond=0)
    
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
    
    # Load previous trades to get next ID
    trade_id = storage.get_next_trade_id()
    
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
