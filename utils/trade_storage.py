"""
Unified storage handler for trade data
Supports both local JSON files and MongoDB (free MongoDB Atlas)
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# MongoDB support (optional)
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    HAS_MONGODB = True
except ImportError:
    HAS_MONGODB = False


class TradeStorage:
    """Handles trade data storage - JSON files + optional MongoDB backup"""
    
    def __init__(self, json_file: str, collection_name: str = None):
        """
        Initialize storage handler
        
        Args:
            json_file: Path to JSON file for local storage
            collection_name: MongoDB collection name (e.g., 'trades_1min')
        """
        self.json_file = json_file
        self.collection_name = collection_name or os.path.basename(json_file).replace('.json', '')
        
        # MongoDB setup (if enabled via environment variable)
        self.mongo_enabled = False
        self.mongo_client = None
        self.mongo_collection = None
        
        mongo_uri = os.environ.get('MONGODB_URI')
        if mongo_uri and HAS_MONGODB:
            try:
                self.mongo_client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                # Test connection
                self.mongo_client.admin.command('ping')
                
                # Get database and collection
                db = self.mongo_client['trading_strategies']
                self.mongo_collection = db[self.collection_name]
                
                self.mongo_enabled = True
                print(f"✅ MongoDB connected: {self.collection_name}")
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                print(f"⚠️  MongoDB connection failed: {e}")
                print(f"📝 Falling back to JSON-only storage")
                self.mongo_enabled = False
            except Exception as e:
                print(f"⚠️  MongoDB error: {e}")
                self.mongo_enabled = False
    
    
    def load_trades(self) -> List[Dict]:
        """
        Load all trades from storage
        Priority: MongoDB (if available) -> JSON file
        """
        # Try MongoDB first
        if self.mongo_enabled and self.mongo_collection is not None:
            try:
                trades = list(self.mongo_collection.find({}, {'_id': 0}).sort('trade_id', 1))
                if trades:
                    print(f"📥 Loaded {len(trades)} trades from MongoDB")
                    return trades
            except Exception as e:
                print(f"⚠️  Error reading from MongoDB: {e}")
        
        # Fallback to JSON
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r') as f:
                    trades = json.load(f)
                    print(f"📥 Loaded {len(trades)} trades from JSON")
                    return trades
            except Exception as e:
                print(f"⚠️  Error reading JSON: {e}")
                return []
        
        return []
    
    
    def save_trade(self, trade_data: Dict) -> bool:
        """
        Save a single trade to storage
        Saves to BOTH JSON and MongoDB (if enabled)
        
        Returns:
            True if saved successfully to at least one storage
        """
        success = False
        
        # Save to JSON file
        try:
            trades = self.load_trades()
            trades.append(trade_data)
            
            with open(self.json_file, 'w') as f:
                json.dump(trades, f, indent=2)
            
            print(f"💾 Trade #{trade_data.get('trade_id')} saved to JSON")
            success = True
            
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
        
        # Save to MongoDB (if enabled)
        if self.mongo_enabled and self.mongo_collection is not None:
            try:
                # Add timestamp for MongoDB
                trade_data_copy = trade_data.copy()
                trade_data_copy['saved_at'] = datetime.utcnow()
                
                # Insert or update
                self.mongo_collection.update_one(
                    {'trade_id': trade_data['trade_id']},
                    {'$set': trade_data_copy},
                    upsert=True
                )
                
                print(f"☁️  Trade #{trade_data.get('trade_id')} synced to MongoDB")
                success = True
                
            except Exception as e:
                print(f"⚠️  Error saving to MongoDB: {e}")
        
        return success
    
    
    def get_next_trade_id(self) -> int:
        """Get the next trade ID"""
        trades = self.load_trades()
        if trades:
            return trades[-1]['trade_id'] + 1
        return 1
    
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        trades = self.load_trades()
        
        if not trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0
            }
        
        wins = [t for t in trades if t.get('is_win', False)]
        losses = [t for t in trades if not t.get('is_win', False)]
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / len(trades) * 100) if trades else 0,
            'total_pnl': sum(t.get('pnl', 0) for t in trades)
        }
    
    
    def close(self):
        """Close MongoDB connection"""
        if self.mongo_client:
            self.mongo_client.close()


# Example usage:
if __name__ == '__main__':
    # Create storage handler
    storage = TradeStorage('test_trades.json', 'test_collection')
    
    # Save a test trade
    test_trade = {
        'trade_id': 1,
        'direction': 'LONG',
        'entry_time': '2024-12-16 18:00:00',
        'exit_time': '2024-12-16 18:05:00',
        'entry_price': 42500.50,
        'exit_price': 42650.25,
        'duration_minutes': 5.0,
        'pnl': 149.75,
        'pnl_pct': 0.35,
        'exit_reason': 'TAKE_PROFIT',
        'is_win': True
    }
    
    storage.save_trade(test_trade)
    
    # Load and display
    trades = storage.load_trades()
    print(f"\nTotal trades: {len(trades)}")
    
    # Show stats
    stats = storage.get_stats()
    print(f"\nStats: {stats}")
    
    storage.close()
