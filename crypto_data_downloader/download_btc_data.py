import requests
import datetime as dt
import csv
import os

# -------------------------------------
# CONFIG
# -------------------------------------
CANDLE_API = "https://cdn.india.deltaex.org/v2/chart/history"
SYMBOL = "BTCUSD"
RESOLUTION = "1"
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
# FETCH CANDLES FOR A SINGLE DAY
# -------------------------------------
def fetch_day(y, m, d):
    day_start = int(dt.datetime(y, m, d, 0, 0, tzinfo=dt.UTC).timestamp())
    day_end   = int(dt.datetime(y, m, d, 23, 59, tzinfo=dt.UTC).timestamp())

    params = {
        "symbol": SYMBOL,
        "resolution": RESOLUTION,
        "from": day_start,
        "to": day_end,
        "cache_ttl": "1m"
    }

    r = requests.get(CANDLE_API, params=params, timeout=15)
    js = r.json()

    # Validate structure
    if "result" not in js or js["result"].get("s") != "ok":
        print(f"   ❌ No data for {y}-{m}-{d}: {js.get('result')}")
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


# -------------------------------------
# MAIN WORKFLOW
# -------------------------------------
def main():
    # Create Data folder if it doesn't exist
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"📁 Created folder: {DATA_FOLDER}\n")
    
    server_now = get_server_time()
    server_date = server_now.date()

    print(f"📆 Today (server): {server_date}")
    
    # Generate proper filename with date
    output_filename = f"BTCUSD_5min_6months_{server_date.strftime('%Y-%m-%d')}.csv"
    output_path = os.path.join(DATA_FOLDER, output_filename)

    # ⭐⭐⭐ 6 MONTHS = last 180 days ⭐⭐⭐
    days = [
        server_date - dt.timedelta(days=i)
        for i in range(1, 181)  # 1 to 180 days back
    ]

    print("\n📥 Downloading last 6 months of data...\n")

    all_rows = []

    for day in days:
        print(f"➡️  {day} ...")
        rows = fetch_day(day.year, day.month, day.day)

        if len(rows) == 0:
            print("   ❌ No candles\n")
        else:
            print(f"   ✅ {len(rows)} candles\n")
            all_rows.extend(rows)

    if len(all_rows) == 0:
        print("\n❌ No data collected. Exiting.")
        return

    # Sort final dataset
    all_rows.sort(key=lambda x: x["timestamp"])

    # Write CSV
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "datetime_utc",
            "datetime_ist",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ])

        for row in all_rows:
            writer.writerow([
                row["timestamp"],
                row["datetime_utc"],
                row["datetime_ist"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"]
            ])

    print(f"\n🎉 DONE! 6-month CSV saved → {output_path}")
    print(f"📊 Total candles: {len(all_rows)}")
    print(f"💾 File size: {os.path.getsize(output_path):,} bytes")


# -------------------------------------
# RUN
# -------------------------------------
if __name__ == "__main__":
    main()
