# 🕐 Dual Timeframe Trading Strategy

Run **1-minute** and **5-minute** strategies simultaneously to compare performance!

---

## 📁 Files

### **1-Minute Strategy**
- **Script**: `live_strategy.py`
- **Trades**: `trades_1min.json`
- **Candle**: 1 minute

### **5-Minute Strategy**  
- **Script**: `live_strategy_5min.py`
- **Trades**: `trades_5min.json`
- **Candle**: 5 minutes (aggregates tick data into 5-min intervals)

### **Comparison**
- **Script**: `compare_timeframes.py`
- Analyzes both and shows which performs better

---

## 🚀 How to Run

### **Option 1: Run Both in Separate Terminals**

**Terminal 1 - 1-Minute:**
```bash
cd volume_strategy
python live_strategy.py
```

**Terminal 2 - 5-Minute:**
```bash
cd volume_strategy
python live_strategy_5min.py
```

### **Option 2: Run Both in Background (PowerShell)**

```powershell
cd volume_strategy

# Start 1-min strategy
Start-Process python -ArgumentList "live_strategy.py" -WindowStyle Normal

# Start 5-min strategy  
Start-Process python -ArgumentList "live_strategy_5min.py" -WindowStyle Normal
```

---

## 📊 Compare Performance

Anytime you want to see which is winning:

```bash
python compare_timeframes.py
```

**Example Output:**
```
METRIC                    1-MIN                5-MIN                WINNER         
--------------------------------------------------------------------------------
Total Trades              64                   15                   1-MIN          
Win Rate %                +42.20%              +60.00%              5-MIN          
Net P&L $                 $-806.00             $+245.00             5-MIN          
Profit Factor             $0.65                $1.35                5-MIN          
Expectancy $              $-12.59              $+16.33              5-MIN          
```

---

## 🔍 Strategy Differences

| Setting | 1-MIN | 5-MIN |
|---------|-------|-------|
| **Candle Size** | 1 minute | 5 minutes (aggregated) |
| **Signal Frequency** | More trades | Fewer, higher quality trades |
| **Confirmations** | 2 consecutive 1-min candles | 2 consecutive 5-min candles |
| **Typical Hold Time** | 1-5 minutes | 5-30 minutes |
| **Noise Level** | Higher (more false signals) | Lower (smoother trends) |

---

## 💡 Expected Results

**1-Minute:**
- ✅ More trading opportunities
- ✅ Faster entries/exits
- ❌ More whipsaws and false signals
- ❌ Lower win rate (~40-50%)

**5-Minute:**
- ✅ Better signal quality
- ✅ Higher win rate (~55-65%)
- ✅ Clearer trends
- ❌ Fewer trade opportunities
- ❌ Slower to react

---

## 🎯 Which Is Better?

**Use 1-MIN if:**
- You want high-frequency scalping
- You can monitor trades actively
- You're comfortable with more volatility

**Use 5-MIN if:**
- You want quality over quantity
- You prefer fewer but better trades
- You want smoother P&L curves

**Or run BOTH and compare after 24-48 hours!** 📈

---

## 📈 Monitoring

Both strategies will display their timeframe in the header:

**1-Minute:**
```
📊 LIVE MARKET MONITOR - BTCUSD
```

**5-Minute:**
```
📊 LIVE MARKET MONITOR - BTCUSD [5-MIN]
```

---

## 🛑 Stopping

Press `Ctrl+C` in each terminal to stop them independently.

---

**Happy Testing!** 🚀
