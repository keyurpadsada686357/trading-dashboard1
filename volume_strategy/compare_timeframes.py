import json
import os

def compare_strategies():
    """Compare 1-min vs 5-min strategy performance"""
    
    files = {
        "1-MIN": "trades_1min.json",
        "5-MIN": "trades_5min.json"
    }
    
    print("\n" + "="*80)
    print("STRATEGY COMPARISON: 1-MINUTE vs 5-MINUTE")
    print("="*80 + "\n")
    
    results = {}
    
    for timeframe, filename in files.items():
        if not os.path.exists(filename):
            print(f"{timeframe}: No data yet ({filename})")
            results[timeframe] = None
            continue
        
        with open(filename, 'r') as f:
            trades = json.load(f)
        
        if not trades:
            print(f"{timeframe}: No trades yet")
            results[timeframe] = None
            continue
        
        # Calculate stats
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in trades)
        total_pnl_pct = sum(t['pnl_pct'] for t in trades)
        
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = sum(t['pnl'] for t in losses) if losses else 0
        
        avg_win = (gross_profit / win_count) if win_count > 0 else 0
        avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0
        
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
        
        avg_duration = sum(t['duration_minutes'] for t in trades) / total if total > 0 else 0
        
        expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * abs(avg_loss)) if total > 0 else 0
        
        results[timeframe] = {
            'total': total,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_duration': avg_duration,
            'expectancy': expectancy
        }
    
    # Print comparison
    print(f"{'METRIC':<25} {'1-MIN':<20} {'5-MIN':<20} {'WINNER':<15}")
    print("-"*80)
    
    if results["1-MIN"] and results["5-MIN"]:
        metrics = [
            ("Total Trades", 'total', False),
            ("Win Rate %", 'win_rate', True),
            ("Net P&L $", 'total_pnl', True),
            ("Net P&L %", 'total_pnl_pct', True),
            ("Profit Factor", 'profit_factor', True),
            ("Avg Win $", 'avg_win', True),
            ("Avg Loss $", 'avg_loss', False),
            ("Avg Duration (min)", 'avg_duration', False),
            ("Expectancy $", 'expectancy', True)
        ]
        
        for label, key, higher_is_better in metrics:
            val_1min = results["1-MIN"][key]
            val_5min = results["5-MIN"][key]
            
            # Format values
            if key in ['total', 'wins', 'losses']:
                s1 = f"{val_1min:.0f}"
                s5 = f"{val_5min:.0f}"
            elif key in ['win_rate', 'total_pnl_pct']:
                s1 = f"{val_1min:+.2f}%"
                s5 = f"{val_5min:+.2f}%"
            elif key in ['avg_duration']:
                s1 = f"{val_1min:.1f}"
                s5 = f"{val_5min:.1f}"
            else:
                s1 = f"${val_1min:+,.2f}"
                s5 = f"${val_5min:+,.2f}"
            
            # Determine winner
            if higher_is_better:
                winner = "1-MIN" if val_1min > val_5min else "5-MIN" if val_5min > val_1min else "TIE"
            else:
                winner = "1-MIN" if val_1min < val_5min else "5-MIN" if val_5min < val_1min else "TIE"
            
            print(f"{label:<25} {s1:<20} {s5:<20} {winner:<15}")
    
    elif results["1-MIN"]:
        print(f"\nOnly 1-MIN data available:")
        print(f"  Total Trades: {results['1-MIN']['total']}")
        print(f"  Win Rate: {results['1-MIN']['win_rate']:.1f}%")
        print(f"  Net P&L: ${results['1-MIN']['total_pnl']:+,.2f}")
    
    elif results["5-MIN"]:
        print(f"\nOnly 5-MIN data available:")
        print(f"  Total Trades: {results['5-MIN']['total']}")
        print(f"  Win Rate: {results['5-MIN']['win_rate']:.1f}%")
        print(f"  Net P&L: ${results['5-MIN']['total_pnl']:+,.2f}")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    compare_strategies()
