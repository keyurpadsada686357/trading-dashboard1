import json
import os

def compare_all():
    """Compare all 3 timeframes"""
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    timeframes = {
        "1-MIN": os.path.join(script_dir, "trades_1min.json"),
        "5-MIN": os.path.join(script_dir, "trades_5min.json"),
        "15-MIN": os.path.join(script_dir, "trades_15min.json")
    }
    
    print("\n" + "="*90)
    print("BITCOIN TRENDLINE BREAKOUT - MULTI-TIMEFRAME COMPARISON")
    print("="*90 + "\n")
    
    results = {}
    
    for tf, filename in timeframes.items():
        if not os.path.exists(filename):
            results[tf] = None
            continue
        
        with open(filename, 'r') as f:
            trades = json.load(f)
        
        if not trades:
            results[tf] = None
            continue
        
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        
        win_rate = (len(wins) / total * 100) if total > 0 else 0
        total_pnl = sum(t['pnl'] for t in trades)
        
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = sum(t['pnl'] for t in trades if not t['is_win'])
        
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
        
        avg_win = (gross_profit / len(wins)) if wins else 0
        avg_loss = (gross_loss / (total - len(wins))) if (total - len(wins)) > 0 else 0
        
        expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * abs(avg_loss))
        
        results[tf] = {
            'total': total,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'expectancy': expectancy
        }
    
    # Print comparison
    print(f"{'METRIC':<25} {'1-MIN':<20} {'5-MIN':<20} {'15-MIN':<20}")
    print("-"*90)
    
    active_results = {k: v for k, v in results.items() if v is not None}
    
    if active_results:
        metrics = [
            ("Total Trades", 'total'),
            ("Win Rate %", 'win_rate'),
            ("Net P&L $", 'total_pnl'),
            ("Profit Factor", 'profit_factor'),
            ("Expectancy $", 'expectancy')
        ]
        
        for label, key in metrics:
            vals = {}
            for tf in ["1-MIN", "5-MIN", "15-MIN"]:
                if results[tf]:
                    val = results[tf][key]
                    if key in ['total']:
                        vals[tf] = f"{val:.0f}"
                    elif key in ['win_rate']:
                        vals[tf] = f"{val:.1f}%"
                    elif key == 'profit_factor':
                        vals[tf] = f"{val:.2f}"
                    else:
                        vals[tf] = f"${val:+,.2f}"
                else:
                    vals[tf] = "N/A"
            
            print(f"{label:<25} {vals.get('1-MIN', 'N/A'):<20} {vals.get('5-MIN', 'N/A'):<20} {vals.get('15-MIN', 'N/A'):<20}")
    else:
        print("No data available yet. Run the strategies first!")
    
    print("\n" + "="*90 + "\n")

if __name__ == "__main__":
    compare_all()
