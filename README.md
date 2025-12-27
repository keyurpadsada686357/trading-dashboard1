# Cryptocurrency Trading Strategies - Render Deployment

Deploy and run multiple cryptocurrency trading strategies 24/7 on Render cloud platform.

## 📋 What This Does

Runs all your trading strategies automatically on the cloud:
- **BTC Trendline Strategy** (1-min, 5-min, 15-min) - Detects trendline breakouts
- **Volume Strategy** (1-min) - Trades based on buy/sell volume delta
- All trades are automatically logged to JSON files
- Strategies run in parallel with auto-restart on errors

## 🚀 Quick Deploy to Render

### Option 1: Deploy via GitHub (Recommended)

1. **Push to GitHub**
   ```bash
   cd "c:\Stock Market\9_21_ema_CrossOver_2"
   git init
   git add .
   git commit -m "Initial commit - trading strategies"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **"New +"** → **"Background Worker"**
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` and configure everything
   - Click **"Create Background Worker"**

3. **Monitor**
   - View logs in Render dashboard to see strategies running
   - Trades will be logged to JSON files

### Option 2: Deploy via Render CLI

1. **Install Render CLI**
   ```bash
   npm install -g @render/cli
   ```

2. **Login to Render**
   ```bash
   render login
   ```

3. **Deploy**
   ```bash
   cd "c:\Stock Market\9_21_ema_CrossOver_2"
   render up
   ```

## 💻 Test Locally First

Before deploying, test that everything works:

```bash
cd "c:\Stock Market\9_21_ema_CrossOver_2"

# Install dependencies
pip install -r requirements.txt

# Run all strategies
python main.py
```

You should see all enabled strategies start and connect to Delta Exchange WebSocket.

## ⚙️ Configuration

### Enable/Disable Strategies

Edit `main.py` and change `"enabled": True/False`:

```python
STRATEGIES = {
    "BTC Trendline 5-min": {
        "enabled": True,
        "module": btc_trendline_5min
    },
    # ... other strategies
}
```

### Strategy Parameters

Each strategy has its own parameters in its respective file:

- **Volume Strategy**: `volume_strategy/live_strategy.py`
  - `MIN_DELTA_BUY` - Minimum buy volume delta
  - `TAKE_PROFIT_PCT` - Take profit percentage
  - `STOP_LOSS_PCT` - Stop loss percentage

- **Trendline Strategy**: `btc_trendline_strategy/btc_trendline_5min.py`
  - `ATR_SL_MULT` - Stop loss ATR multiplier
  - `TARGET_ATR_MULT` - Target ATR multiplier
  - `LOOKBACK_SWING` - Swing point detection period

## 📊 Trade Data

All trades are saved to JSON files:
- `btc_trendline_strategy/trades_1min.json`
- `btc_trendline_strategy/trades_5min.json`
- `btc_trendline_strategy/trades_15min.json`
- `volume_strategy/trades_1min.json`

Each trade record includes:
```json
{
  "trade_id": 1,
  "direction": "LONG",
  "entry_time": "2024-12-16 18:00:00",
  "exit_time": "2024-12-16 18:05:00",
  "entry_price": 42500.50,
  "exit_price": 42650.25,
  "duration_minutes": 5.2,
  "pnl": 149.75,
  "pnl_pct": 0.35,
  "exit_reason": "TAKE_PROFIT",
  "is_win": true
}
```

### ⚠️ Important: Data Persistence

**Render Free Tier**: JSON files are stored in ephemeral storage and **will be lost** when the service restarts.

**Solutions**:
1. **Upgrade to paid plan** ($7/month) - Add persistent disk in `render.yaml`
2. **Download trades periodically** - Use Render shell to download JSON files
3. **Use external storage** - Modify code to save to MongoDB/PostgreSQL/S3

## 🔍 Monitor Your Strategies

### View Logs
1. Go to Render Dashboard
2. Click on your service
3. Click **"Logs"** tab
4. See real-time output from all strategies

### Download Trade Data
```bash
# Using Render CLI
render shell
cat btc_trendline_strategy/trades_1min.json
```

Or use the Render dashboard's shell feature.

## 🛑 Stop Strategies

- **On Render**: Suspend or delete the service from dashboard
- **Locally**: Press `Ctrl+C`

## 📝 Project Structure

```
9_21_ema_CrossOver_2/
├── main.py                          # Main entry point (NEW)
├── requirements.txt                 # Dependencies (NEW)
├── render.yaml                      # Render config (NEW)
├── .gitignore                       # Git ignore (NEW)
├── btc_trendline_strategy/
│   ├── btc_trendline_5min.py       # 5-min trendline strategy
│   ├── btc_trendline_15min.py      # 15-min trendline strategy
│   ├── compare_trendline.py        # Compare performance
│   └── trades_*.json               # Trade logs
└── volume_strategy/
    ├── live_strategy.py            # 1-min volume strategy
    ├── live_strategy_5min.py       # 5-min volume strategy
    └── trades_1min.json            # Trade logs
```

## 🐛 Troubleshooting

**Strategies not connecting?**
- Check Render logs for WebSocket errors
- Verify Delta Exchange API is accessible

**Import errors?**
- Verify all dependencies in `requirements.txt`
- Check Python version (should be 3.11+)

**Strategies stopping?**
- Auto-restart is enabled, check logs for errors
- Verify WebSocket connection is stable

## 📈 Next Steps

1. Deploy to Render
2. Monitor logs to verify strategies are running
3. Check JSON files for trade entries
4. Consider upgrading to paid plan for persistent storage
5. Optionally integrate with external database

## 💡 Tips

- Start with 1-2 strategies enabled, then add more
- Monitor performance for a few days before full deployment
- Download trade data regularly if on free tier
- Set up alerts/notifications for important trades (future enhancement)
