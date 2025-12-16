"""
ALL-IN-ONE: Trading Strategies + Web Dashboard
Runs all strategies in parallel with web monitoring interface
"""
import threading
import time
import sys
import os
import json
from datetime import datetime
from collections import deque

# Flask for web dashboard
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import strategies
from btc_trendline_strategy import btc_trendline_1min, btc_trendline_5min, btc_trendline_15min
from volume_strategy import live_strategy, live_strategy_5min
from utils.trade_storage import TradeStorage

# ============================================================================
# WEB DASHBOARD (Flask App)
# ============================================================================

app = Flask(__name__)
CORS(app)

# Global state for monitoring
strategy_status = {
    "BTC Trendline 1-min": {"status": "running", "position": None, "last_update": None},
    "BTC Trendline 5-min": {"status": "running", "position": None, "last_update": None},
    "BTC Trendline 15-min": {"status": "running", "position": None, "last_update": None},
    "Volume Strategy 1-min": {"status": "running", "position": None, "last_update": None},
    "Volume Strategy 5-min": {"status": "running", "position": None, "last_update": None},
}

# Live logs storage (last 100 log entries)
live_logs = deque(maxlen=100)

def log_to_dashboard(strategy_name, message, level="info"):
    """Add log message to dashboard"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    live_logs.append({
        "timestamp": timestamp,
        "strategy": strategy_name,
        "message": message,
        "level": level  # info, success, warning, error
    })
    
    # Update strategy last update time
    if strategy_name in strategy_status:
        strategy_status[strategy_name]["last_update"] = timestamp

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get current status of all strategies"""
    return jsonify({
        "strategies": strategy_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/trades')
def get_trades():
    """Get all trades from all strategies"""
    trades = {
        "trendline_1min": [],
        "trendline_5min": [],
        "trendline_15min": [],
        "volume_1min": []
    }
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Trendline trades
        for timeframe in ['1', '5', '15']:
            storage = TradeStorage(
                json_file=os.path.join(script_dir, f'btc_trendline_strategy/trades_{timeframe}min.json'),
                collection_name=f'trendline_trades_{timeframe}min'
            )
            trades[f'trendline_{timeframe}min'] = storage.load_trades()
        
        # Volume trades
        storage = TradeStorage(
            json_file=os.path.join(script_dir, 'volume_strategy/trades_1min.json'),
            collection_name='volume_trades_1min'
        )
        trades['volume_1min'] = storage.load_trades()
        
    except Exception as e:
        print(f"Error loading trades: {e}")
    
    return jsonify(trades)

@app.route('/api/stats')
def get_stats():
    """Get trading statistics"""
    stats = {}
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        strategies = [
            ('trendline_1min', 'btc_trendline_strategy/trades_1min.json', 'trendline_trades_1min'),
            ('trendline_5min', 'btc_trendline_strategy/trades_5min.json', 'trendline_trades_5min'),
            ('trendline_15min', 'btc_trendline_strategy/trades_15min.json', 'trendline_trades_15min'),
            ('volume_1min', 'volume_strategy/trades_1min.json', 'volume_trades_1min'),
        ]
        
        for name, json_file, collection in strategies:
            storage = TradeStorage(
                json_file=os.path.join(script_dir, json_file),
                collection_name=collection
            )
            stats[name] = storage.get_stats()
    
    except Exception as e:
        print(f"Error loading stats: {e}")
    
    return jsonify(stats)

@app.route('/api/logs')
def get_logs():
    """Get recent logs"""
    return jsonify({
        "logs": list(live_logs),
        "count": len(live_logs)
    })

def run_dashboard(host='0.0.0.0', port=5000):
    """Run the Flask dashboard"""
    print(f"\n{'='*80}")
    print(f"🌐 WEB DASHBOARD STARTING")
    print(f"{'='*80}")
    print(f"📊 Dashboard URL: http://localhost:{port}")
    print(f"🔗 Access from network: http://<your-ip>:{port}")
    print(f"{'='*80}\n")
    
    app.run(host=host, port=port, debug=False, use_reloader=False)

# ============================================================================
# TRADING STRATEGIES MANAGER
# ============================================================================

# Strategy configuration - set to True to enable
STRATEGIES = {
    "BTC Trendline 1-min": {
        "enabled": True,
        "module": btc_trendline_1min
    },
    "BTC Trendline 5-min": {
        "enabled": True,
        "module": btc_trendline_5min
    },
    "BTC Trendline 15-min": {
        "enabled": True,
        "module": btc_trendline_15min
    },
    "Volume Strategy 1-min": {
        "enabled": True,
        "module": live_strategy
    },
    "Volume Strategy 5-min": {
        "enabled": True,
        "module": live_strategy_5min
    }
}


def run_strategy(name, module):
    """Run a single strategy with automatic restart on failure"""
    retry_count = 0
    max_retries = 100
    
    while retry_count < max_retries:
        try:
            msg = f"Starting {name}..."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 {msg}")
            log_to_dashboard(name, msg, "info")
            
            module.main()
            
        except KeyboardInterrupt:
            msg = f"Stopped by user"
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏹️  {name} {msg}")
            log_to_dashboard(name, msg, "warning")
            break
            
        except Exception as e:
            retry_count += 1
            error_msg = f"Error: {str(e)[:100]}"
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ {name} {error_msg}")
            log_to_dashboard(name, error_msg, "error")
            
            if retry_count < max_retries:
                wait_time = min(retry_count * 5, 60)
                restart_msg = f"Restarting in {wait_time}s (attempt {retry_count})"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 {restart_msg}")
                log_to_dashboard(name, restart_msg, "warning")
                time.sleep(wait_time)


def main():
    """Main entry point - start all enabled strategies and web dashboard"""
    print("=" * 80)
    print("🤖 TRADING STRATEGIES + WEB DASHBOARD")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start web dashboard in background thread
    dashboard_thread = threading.Thread(
        target=run_dashboard,
        args=('0.0.0.0', int(os.environ.get('PORT', 5000))),
        daemon=True,
        name="Web Dashboard"
    )
    dashboard_thread.start()
    
    print(f"\n📊 Enabled Strategies:")
    
    threads = []
    enabled_count = 0
    
    for name, config in STRATEGIES.items():
        if config["enabled"]:
            enabled_count += 1
            print(f"   ✅ {name}")
            
            # Start each strategy in its own thread
            thread = threading.Thread(
                target=run_strategy,
                args=(name, config["module"]),
                daemon=True,
                name=name
            )
            thread.start()
            threads.append(thread)
        else:
            print(f"   ⏸️  {name} (disabled)")
    
    print(f"\n🎯 Running {enabled_count} strategies in parallel")
    print("🌐 Web Dashboard: http://localhost:5000")
    print("⌨️  Press Ctrl+C to stop all")
    print("=" * 80 + "\n")
    
    if not threads:
        print("⚠️  No strategies enabled!")
        return
    
    # Keep main thread alive
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(10)
            
            # Health check - restart dead threads
            for i, thread in enumerate(threads):
                if not thread.is_alive():
                    name = thread.name
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️  {name} died, restarting...")
                    
                    strategy_config = STRATEGIES.get(name)
                    if strategy_config:
                        new_thread = threading.Thread(
                            target=run_strategy,
                            args=(name, strategy_config["module"]),
                            daemon=True,
                            name=name
                        )
                        new_thread.start()
                        threads[i] = new_thread
                        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("⏹️  STOPPING ALL STRATEGIES")
        print("=" * 80)
        print(f"⏰ Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("👋 Goodbye!\n")


if __name__ == "__main__":
    main()
