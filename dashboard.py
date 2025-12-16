"""
Web Dashboard for Trading Strategies Monitoring
Shows real-time status, logs, and trade history
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import sys
import json
import threading
from datetime import datetime
from collections import deque

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.trade_storage import TradeStorage

app = Flask(__name__)
CORS(app)

# Global state for monitoring
strategy_status = {
    "BTC Trendline 1-min": {"status": "running", "position": None, "last_update": None},
    "BTC Trendline 5-min": {"status": "running", "position": None, "last_update": None},
    "BTC Trendline 15-min": {"status": "running", "position": None, "last_update": None},
    "Volume Strategy 1-min": {"status": "running", "position": None, "last_update": None},
}

# Recent logs (last 100 entries)
recent_logs = deque(maxlen=100)

def log_message(message):
    """Add message to recent logs"""
    recent_logs.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "message": message
    })


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
        # Load trades from each strategy
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
        
        # Stats for each strategy
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
        "logs": list(recent_logs),
        "count": len(recent_logs)
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


if __name__ == '__main__':
    run_dashboard()
