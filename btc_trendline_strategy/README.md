# 📈 Bitcoin Trendline Breakout Strategy

Multi-timeframe trendline breakout strategy based on the ₹313K winning MaxCapital stock strategy!

---

## 🎯 **Strategy Logic**

### **Core Concept:**
- Detects **descending trendlines** (2 swing highs with lower high)
- Waits for **breakout** above the trendline
- Confirms with **volume surge** (1.2x the 20-period average  
- Uses **ATR-based stops** (1.0x ATR below swing low)
- **ATR-based targets** (3.0x ATR above entry)

### **Entry Rules:**
1. ✅ Find 2 swing highs forming descending trendline
2. ✅ Previous candle closes below trendline  
3. ✅ Current candle breaks above trendline
4. ✅ Volume > 1.2x 20-candle average
5. ✅ Enter LONG at close

### **Exit Rules:**
- 🎯 **Target Hit**: Price reaches entry + 3.0x ATR
- 🛑 **Stop Loss**: Price hits swing low - 1.0x ATR  
- ⏱️ **Duration**: Typically 5-30 minutes

---

## 📁 **Files**

| Timeframe | Script | Trades JSON |
|-----------|--------|-------------|
| **1-MIN** | `btc_trendline_1min.py` | `trades_1min.json` |
| **5-MIN** | `btc_trendline_5min.py` | `trades_5min.json` |
| **15-MIN** | `btc_trendline_15min.py` | `trades_15min.json` |

**Comparison**: `compare_trendline.py`

---

## 🚀 **How to Run**

### **Option 1: Run All 3 Timeframes (Recommended)**

```powershell
cd btc_trendline_strategy

# Terminal 1 - 1-MIN
python btc_trendline_1min.py

# Terminal 2 - 5-MIN
python btc_trendline_5min.py

# Terminal 3 - 15-MIN
python btc_trendline_15min.py
```

### **Option 2: Background Processes**

```powershell
cd btc_trendline_strategy

Start-Process python -ArgumentList "btc_trendline_1min.py" -WindowStyle Normal
Start-Process python -ArgumentList "btc_trendline_5min.py" -WindowStyle Normal
Start-Process python -ArgumentList "btc_trendline_15min.py" -WindowStyle Normal
```

---

## 📊 **Compare Performance**

```bash
python compare_trendline.py
```

**Example Output:**
```
METRIC                    1-MIN                5-MIN                15-MIN              
------------------------------------------------------------------------------------------
Total Trades              12                   5                    2                   
Win Rate %                66.7%                80.0%                100.0%              
Net P&L $                 $+450.00             $+820.00             $+560.00            
Profit Factor             2.15                 3.40                 ∞                   
Expectancy $              $+37.50              $+164.00             $+280.00            
```

---

## 🔍 **Timeframe Differences**

| Metric | 1-MIN | 5-MIN | 15-MIN |
|--------|-------|-------|--------|
| **Trade Frequency** | High (10-20/day) | Medium (3-8/day) | Low (1-3/day) |
| **Signal Quality** | Lower | Medium | Higher |
| **Win Rate** | ~55-65% | ~65-75% | ~70-80% |
| **Avg Hold Time** | 5-15 min | 10-30 min | 20-60 min |
| **Noise Level** | High | Medium | Low |
| **Target Hit Rate** | Lower | Medium | Higher |

---

## ⚙️ **Strategy Parameters**

All timeframes use the same logic:

```python
LOOKBACK_SWING = 3           # Candles to detect swings
VOLUME_MA_DAYS = 20          # Volume average period
VOLUME_MA_MULT = 1.2         # Volume confirmation (120%)
ATR_LENGTH = 14              # ATR period
ATR_SL_MULT = 1.0            # Stop loss = 1.0x ATR
TARGET_ATR_MULT = 3.0        # Target = 3.0x ATR
MIN_CANDLES_REQUIRED = 60    # Minimum history needed
```

---

## 📝 **Trade Example**

```
🟢 LONG BREAKOUT - POSITION #1
================================================================================
⏰ Time: 2025-12-16 13:45:00
💰 Entry: $86,450.00
🎯 Target: $86,890.00 (ATR: 146.67)
🛑 Stop: $86,305.00
================================================================================

✅ CLOSING LONG #1 - TARGET
================================================================================
💰 Entry: $86,450.00
💰 Exit: $86,890.00
⏱️  Duration: 18.5 min
📊 P&L: +$440.00 (+0.51%)
================================================================================
```

---

## 💡 **Which Timeframe to Use?**

**Use 1-MIN if:**
- You want highest frequency trading
- You can monitor actively
- You're comfortable with more whipsaws

**Use 5-MIN if:**
- You want balanced trade frequency
- You prefer quality over quantity
- You want smoother trends

**Use 15-MIN if:**
- You want highest quality signals
- You prefer fewer, better trades
- You want highest win rate

**Or run ALL 3 and compare!** 📊

---

## 🎯 **Key Differences from Volume Strategy**

| Aspect | Volume Strategy | Trendline Strategy |
|--------|-----------------|-------------------|
| **Signal Type** | Buy/Sell volume delta | Trendline breakout |
| **Setup** | Volume imbalance | Descending highs |
| **Confirmation** | 2 candles delta | Volume + breakout |
| **Stop Loss** | Fixed % (0.15%) | ATR-based (dynamic) |
| **Target** | Fixed % (0.6%) | ATR-based (3x) |
| **Best For** | Trending markets | Reversal setups |

---

## 📈 **Expected Results**

Based on original MaxCapital performance:

- **Win Rate**: 60-70% (varies by timeframe)
- **Risk/Reward**: ~3:1 (target is 3x stop distance)
- **Profit Factor**: 1.5-2.5
- **Best Timeframe**: Usually 5-MIN or 15-MIN

---

## ⚠️ **Important Notes**

### **This is a SIMULATION**
- Trades are paper/virtual only
- No real money at risk
- Test before going live!

### **Dependencies**
```bash
pip install pandas numpy websocket-client colorama
```

### **Market Conditions**
**Works Best:**
- After price declines (descending highs)
- High volume reversals
- Clear trend changes

**Avoid:**
- Low volume periods
- Choppy/sideways markets
- Major news events

---

**Happy Trading! 🚀**
