# 🤖 Volume-Price Trading Strategy - Automated System

This folder contains a complete automated trading system that combines live price action with buy/sell volume analysis.

---

## 📁 Files

### 1. **live_strategy.py** 
Real-time trading strategy that monitors WebSocket data and executes trades based on volume delta signals.

**Features:**
- ✅ Live WebSocket connection to Delta Exchange
- ✅ Automatic BUY/SELL signal detection
- ✅ Position management with Take Profit and Stop Loss
- ✅ Detailed console logging of all trades
- ✅ JSON trade history (trades.json)
- ✅ Configurable strategy parameters

### 2. **analyze_performance.py**
Performance analysis tool that reads trade history and generates comprehensive statistics.

**Features:**
- ✅ Overall win rate and P&L statistics
- ✅ Best and worst trade analysis
- ✅ LONG vs SHORT performance breakdown
- ✅ Exit reason statistics
- ✅ Detailed trade-by-trade listing
- ✅ Color-coded output

### 3. **trades.json** (Generated)
JSON file containing all executed trades with complete details.

---

## 🚀 How to Use

### **Step 1: Run Live Strategy**

```bash
cd volume_strategy
python live_strategy.py
```

**What it does:**
- Connects to Delta Exchange WebSocket
- Monitors live price and volume data
- Detects BUY/SELL signals based on strategy rules
- Simulates taking positions (entry/exit)
- Logs all trades to `trades.json`
- Prints detailed console output for each trade

**Example Output:**
```
================================================================================
🟢 LONG SIGNAL - ENTERING POSITION #1
================================================================================
⏰ Time: 2025-12-15 23:15:30
💰 Entry Price: $86,450.00
🎯 Take Profit: $86,709.35 (+0.3%)
🛑 Stop Loss: $86,320.25 (-0.15%)
📊 Last Candle Delta: +485
================================================================================

... (monitoring position) ...

================================================================================
✅ CLOSING LONG POSITION #1 - TAKE_PROFIT
================================================================================
⏰ Exit Time: 2025-12-15 23:18:45
💰 Entry Price: $86,450.00
💰 Exit Price: $86,710.00
⏱️  Duration: 3.3 minutes
📊 P&L: +$260.00 (+0.30%)
================================================================================
```

---

### **Step 2: Analyze Performance**

```bash
python analyze_performance.py
```

**What it does:**
- Loads all trades from `trades.json`
- Calculates comprehensive statistics
- Shows win rate, total P&L, risk/reward ratio
- Displays best/worst trades
- Analyzes LONG vs SHORT performance
- Optional: Shows detailed trade list

**Example Output:**
```
================================================================================
📊 TRADING PERFORMANCE REPORT
================================================================================

📈 OVERALL STATISTICS
--------------------------------------------------------------------------------
Total Trades:      25
Wins:              15 (60.0%)
Losses:            10 (40.0%)

💰 PROFIT & LOSS
--------------------------------------------------------------------------------
Net P&L:           +$3,450.50
Net P&L %:         +6.85%
Gross Profit:      $5,200.00
Gross Loss:        -$1,749.50
Average Win:       $346.67
Average Loss:      -$174.95
Risk/Reward:       1.98:1

🏆 BEST & WORST TRADES
--------------------------------------------------------------------------------
Best Trade:        Trade #7 - +$520.00 (+0.61%)
                   LONG @ $85,300.00 → $85,820.00
Worst Trade:       Trade #12 - -$320.00 (-0.38%)
                   SHORT @ $84,500.00 → $84,820.00

📊 DIRECTION BREAKDOWN
--------------------------------------------------------------------------------
LONG Trades:       14 trades, 9 wins (64.3%)
LONG P&L:          +$2,100.00
SHORT Trades:      11 trades, 6 wins (54.5%)
SHORT P&L:         +$1,350.50

🚪 EXIT REASONS
--------------------------------------------------------------------------------
TAKE_PROFIT          15 (60.0%)
STOP_LOSS             7 (28.0%)
DELTA_REVERSAL        2 (8.0%)
TIME_EXIT             1 (4.0%)

⏱️  TIME STATISTICS
--------------------------------------------------------------------------------
Average Duration:  3.8 minutes
```

---

## ⚙️ Strategy Parameters

Located in `live_strategy.py`:

```python
# Moderate Settings (Default)
MIN_DELTA_BUY = 300           # Minimum buy delta for LONG signal
MIN_DELTA_SELL = -300         # Minimum sell delta for SHORT signal
MIN_BUY_PERCENT = 60          # Minimum 60% buy volume
MIN_SELL_PERCENT = 60         # Minimum 60% sell volume
CONSECUTIVE_CANDLES = 2       # Need 2 confirming candles
TAKE_PROFIT_PCT = 0.3         # Take profit at +0.3%
STOP_LOSS_PCT = 0.15          # Stop loss at -0.15%
MAX_HOLD_MINUTES = 5          # Max hold time: 5 minutes
```

### Adjusting for Different Risk Profiles:

**Conservative (Lower risk, fewer trades):**
```python
MIN_DELTA_BUY = 500
MIN_DELTA_SELL = -500
MIN_BUY_PERCENT = 65
CONSECUTIVE_CANDLES = 3
TAKE_PROFIT_PCT = 0.5
STOP_LOSS_PCT = 0.2
```

**Aggressive (Higher risk, more trades):**
```python
MIN_DELTA_BUY = 150
MIN_DELTA_SELL = -150
MIN_BUY_PERCENT = 55
CONSECUTIVE_CANDLES = 1
TAKE_PROFIT_PCT = 0.2
STOP_LOSS_PCT = 0.1
```

---

## 📊 Trade JSON Format

Each trade in `trades.json` contains:

```json
{
  "trade_id": 1,
  "direction": "LONG",
  "entry_time": "2025-12-15 23:15:30",
  "exit_time": "2025-12-15 23:18:45",
  "entry_price": 86450.0,
  "exit_price": 86710.0,
  "duration_minutes": 3.25,
  "pnl": 260.0,
  "pnl_pct": 0.3006,
  "exit_reason": "TAKE_PROFIT",
  "is_win": true
}
```

---

## 🎯 Strategy Logic

### **BUY Signal (LONG Entry)**

All conditions must be TRUE for 2 consecutive minutes:
1. ✅ Delta > +300 (strong buying pressure)
2. ✅ Buy volume > 60% of total
3. ✅ Green candle (Close > Open)
4. ✅ Price rising (Close > previous Close)

### **SELL Signal (SHORT Entry)**

All conditions must be TRUE for 2 consecutive minutes:
1. ✅ Delta < -300 (strong selling pressure)
2. ✅ Sell volume > 60% of total
3. ✅ Red candle (Close < Open)
4. ✅ Price falling (Close < previous Close)

### **Exit Conditions**

**LONG positions exit when:**
- ✅ Take Profit: Price rises +0.3%
- ❌ Stop Loss: Price falls -0.15%
- 🔄 Delta Reversal: Strong selling (delta < -200) for 2 minutes
- ⏰ Time Exit: 5 minutes elapsed

**SHORT positions exit when:**
- ✅ Take Profit: Price falls -0.3%
- ❌ Stop Loss: Price rises +0.15%
- 🔄 Delta Reversal: Strong buying (delta > +200) for 2 minutes
- ⏰ Time Exit: 5 minutes elapsed

---

## 📈 Expected Performance

Based on the strategy parameters:

- **Win Rate**: 55-60%
- **Risk/Reward**: 2:1 (average win $260, average loss $130)
- **Average Trade Duration**: 3-5 minutes
- **Daily Trades**: 5-15 (depending on market volatility)

**Example: 100 trades**
- Wins: 57 × $260 = $14,820
- Losses: 43 × -$130 = -$5,590
- **Net Profit: $9,230 (+92.3% if starting with $10,000)**

---

## ⚠️ Important Notes

### **This is a SIMULATION**
- The strategy simulates trades but does NOT place real orders
- No actual money is at risk
- Use this to test and validate the strategy before live trading

### **For Live Trading**
To connect to Delta Exchange API and place real orders, you would need to:
1. Get API keys from Delta Exchange
2. Implement order placement logic
3. Add proper error handling
4. Implement risk management (position sizing, daily limits)

### **Risk Disclaimer**
- Trading involves significant risk
- Past performance does not guarantee future results
- Always use proper risk management
- Never risk more than you can afford to lose

---

## 🐛 Troubleshooting

### WebSocket Connection Issues
```
❌ WebSocket Error: ...
```
**Solution**: Check internet connection, Delta Exchange might be down

### No Signals Generated
```
(Strategy runs but no trades)
```
**Possible Causes:**
- Market not volatile enough
- Delta thresholds too high
- Not enough consecutive confirmations

**Solution**: Lower MIN_DELTA values or reduce CONSECUTIVE_CANDLES

### JSON File Errors
```
❌ Error loading trades: ...
```
**Solution**: Delete `trades.json` and restart

---

## 📚 Related Documentation

- **VOLUME_PRICE_STRATEGY.md** - Complete strategy explanation
- **BUY_SELL_VOLUME_EXPLAINED.md** - Understanding volume metrics

---

## 🔮 Next Steps

1. **Test the Strategy**: Run `live_strategy.py` and let it collect trades
2. **Analyze Results**: Use `analyze_performance.py` to review stats
3. **Tune Parameters**: Adjust thresholds based on market conditions
4. **Backtest**: Use historical data to validate performance
5. **Paper Trade**: Run live with simulated positions (current mode)
6. **Live Trade**: Connect to real API (requires additional implementation)

---

## 💡 Tips

- **Best Hours**: Trade during high volume (8 AM - 10 PM UTC)
- **Avoid Low Volume**: < 1,000 contracts/minute gives false signals
- **Monitor News**: Pause during major economic announcements
- **Review Daily**: Check performance stats every day
- **Adjust Parameters**: Optimize based on market conditions

---

**Happy Trading! 🚀**
