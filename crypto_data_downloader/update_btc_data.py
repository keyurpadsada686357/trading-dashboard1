import requests
import datetime as dt
import csv
import os
from pathlib import Path

# -------------------------------------
# CONFIG
# -------------------------------------
CANDLE_API = "https://cdn.india.deltaex.org/v2/chart/history"
SYMBOL = "BTCUSD"
RESOLUTION = "5"
DATA_FOLDER = "Data"

# -------------------------------------
# GET SERVER TIME (ISO 8601 → datetime)
# -------------------------------------
def get_server_time():
    try:
        url = "https://cdn.india.deltaex.org/v2/tickers?contract_types=perpetual_futures"
        r = requests.get(url, timeout=10)
        js = r.json()

        # Example: "2025-11-24T17:31:11.40932862Z"
        iso = js["result"][0]["time"]
        server_now = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))

        return server_now

    except Exception as e:
        print("❌ Cannot get server time:", e)
        raise


# -------------------------------------
# FIND LATEST CSV FILE
# -------------------------------------
def find_latest_csv():
    """Find the most recent BTCUSD CSV file in Data folder"""
    data_path = Path(DATA_FOLDER)
    
    if not data_path.exists():
        print(f"❌ Data folder '{DATA_FOLDER}' not found!")
        return None
    
    # Find all BTCUSD CSV files
    csv_files = list(data_path.glob("BTCUSD_*.csv"))
    
    if not csv_files:
        print(f"❌ No BTCUSD CSV files found in '{DATA_FOLDER}'!")
        return None
    
    # Get the most recent file by modification time
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    
    print(f"📄 Found latest file: {latest_file.name}")
    return str(latest_file)


# -------------------------------------
# GET LAST TIMESTAMP FROM CSV
# -------------------------------------
def get_last_timestamp(csv_file):
    """Read the last timestamp from existing CSV file"""
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if not rows:
                print("❌ CSV file is empty!")
                return None
            
            last_row = rows[-1]
            last_timestamp = int(last_row['timestamp'])
            last_datetime = last_row['datetime_utc']
            
            print(f"📅 Last candle in CSV: {last_datetime} (timestamp: {last_timestamp})")
            return last_timestamp
            
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return None


# -------------------------------------
# FETCH CANDLES FROM START TO END TIME
# -------------------------------------
def fetch_candles(from_ts, to_ts):
    """Fetch candles between two timestamps"""
    print(f"📥 Fetching data from {dt.datetime.utcfromtimestamp(from_ts)} to {dt.datetime.utcfromtimestamp(to_ts)}")
    
    params = {
        "symbol": SYMBOL,
        "resolution": RESOLUTION,
        "from": from_ts,
        "to": to_ts,
        "cache_ttl": "1m"
    }

    try:
        r = requests.get(CANDLE_API, params=params, timeout=15)
        js = r.json()

        # Validate structure
        if "result" not in js or js["result"].get("s") != "ok":
            print(f"   ❌ No data returned: {js.get('result')}")
            return []

        res = js["result"]

        candles = []
        for i in range(len(res["t"])):

            ts = res["t"][i]
            dt_utc = dt.datetime.utcfromtimestamp(ts)
            dt_ist = dt_utc + dt.timedelta(hours=5, minutes=30)

            candles.append({
                "timestamp": ts,
                "datetime_utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "datetime_ist": dt_ist.strftime("%Y-%m-%d %H:%M:%S"),
                "open":      res["o"][i],
                "high":      res["h"][i],
                "low":       res["l"][i],
                "close":     res["c"][i],
                "volume":    res["v"][i]
            })

        return candles
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []


# -------------------------------------
# APPEND NEW DATA TO CSV
# -------------------------------------
def append_to_csv(csv_file, new_candles):
    """Append new candles to existing CSV file"""
    if not new_candles:
        print("⚠️ No new data to append!")
        return
    
    try:
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            for candle in new_candles:
                writer.writerow([
                    candle["timestamp"],
                    candle["datetime_utc"],
                    candle["datetime_ist"],
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["volume"]
                ])
        
        print(f"✅ Added {len(new_candles)} new candles to CSV!")
        
    except Exception as e:
        print(f"❌ Error appending to CSV: {e}")


# -------------------------------------
# MAIN UPDATE WORKFLOW
# -------------------------------------
def main():
    print("🔄 BTCUSD Data Update Script")
    print("=" * 50)
    
    # Step 1: Find latest CSV file
    csv_file = find_latest_csv()
    if not csv_file:
        print("\n💡 TIP: Run 'download_btc_data.py' first to create initial dataset!")
        return
    
    # Step 2: Get last timestamp from CSV
    last_timestamp = get_last_timestamp(csv_file)
    if last_timestamp is None:
        return
    
    # Step 3: Get current server time
    server_now = get_server_time()
    current_timestamp = int(server_now.timestamp())
    
    print(f"📆 Current server time: {server_now.strftime('%Y-%m-%d %H:%M:%S')} (timestamp: {current_timestamp})")
    
    # Step 4: Calculate time gap
    time_gap = current_timestamp - last_timestamp
    gap_minutes = time_gap // 60
    gap_hours = gap_minutes / 60
    
    print(f"\n⏱️ Time gap: {gap_minutes} minutes ({gap_hours:.1f} hours)")
    
    # If gap is less than 5 minutes (one candle), no update needed
    if time_gap < 300:  # 5 minutes in seconds
        print("✨ Data is already up-to-date! No new candles available.")
        return
    
    # Step 5: Fetch new candles (start from next candle after last timestamp)
    # Add 5 minutes (300 seconds) to avoid duplicate
    from_timestamp = last_timestamp + 300
    
    new_candles = fetch_candles(from_timestamp, current_timestamp)
    
    if not new_candles:
        print("⚠️ No new candles found in the time range.")
        return
    
    print(f"📊 Found {len(new_candles)} new candles")
    
    # Step 6: Append new data to CSV
    append_to_csv(csv_file, new_candles)
    
    # Step 7: Show summary
    print(f"\n{'=' * 50}")
    print(f"🎉 Update Complete!")
    print(f"📄 Updated file: {csv_file}")
    print(f"📊 New candles added: {len(new_candles)}")
    print(f"💾 File size: {os.path.getsize(csv_file):,} bytes")
    
    # Show first and last new candle
    if new_candles:
        print(f"\n📅 New data range:")
        print(f"   First: {new_candles[0]['datetime_utc']} UTC")
        print(f"   Last:  {new_candles[-1]['datetime_utc']} UTC")


# -------------------------------------
# RUN
# -------------------------------------
if __name__ == "__main__":
    main()
