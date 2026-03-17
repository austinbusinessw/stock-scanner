import os
import json
from datetime import datetime, timedelta

import pandas as pd
import pandas_ta as ta
import requests

API_KEY = os.getenv("TIINGO_API_KEY")
BASE_URL = "https://api.tiingo.com/tiingo/daily"

TICKERS = [
    "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA",
    "AAPL", "AVGO", "PLTR", "JPM", "WMT", "COST"
]

def fetch_data(ticker, days=120):
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    url = f"{BASE_URL}/{ticker}/prices?startDate={start}&resampleFreq=daily&token={API_KEY}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df

def build_row(ticker, df):
    if len(df) < 25:
        return None

    df["sma20"] = ta.sma(df["close"], length=20)
    df["rsi14"] = ta.rsi(df["close"], length=14)
    df["vol_avg20"] = df["volume"].rolling(20).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    change_pct = ((latest["close"] - prev["close"]) / prev["close"]) * 100

    signal = "WATCH"
    if pd.notna(latest["rsi14"]) and pd.notna(latest["sma20"]):
        if latest["rsi14"] < 35 and latest["close"] > latest["sma20"]:
            signal = "BUY"
        elif latest["rsi14"] > 70:
            signal = "HOT"

    return {
        "symbol": ticker,
        "name": ticker,
        "close": round(float(latest["close"]), 2),
        "changePct": round(float(change_pct), 2),
        "rsi14": round(float(latest["rsi14"]), 2) if pd.notna(latest["rsi14"]) else None,
        "sma20": round(float(latest["sma20"]), 2) if pd.notna(latest["sma20"]) else None,
        "volume": int(latest["volume"]),
        "avgVolume20": round(float(latest["vol_avg20"]), 2) if pd.notna(latest["vol_avg20"]) else None,
        "signal": signal,
        "date": latest["date"].strftime("%Y-%m-%d")
    }

def save_json(filename, items):
    payload = {
        "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "count": len(items),
        "items": items
    }
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)

def main():
    if not API_KEY:
        raise ValueError("TIINGO_API_KEY is missing")

    all_rows = []
    buy_rows = []
    hot_rows = []

    print("Scanner starting...")

    for ticker in TICKERS:
        try:
            print(f"Scanning {ticker}...")
            df = fetch_data(ticker)
            if df.empty:
                continue

            row = build_row(ticker, df)
            if not row:
                continue

            all_rows.append(row)

            if row["signal"] == "BUY":
                buy_rows.append(row)
            if row["signal"] == "HOT":
                hot_rows.append(row)

        except Exception as e:
            print(f"Error on {ticker}: {e}")

    all_rows = sorted(all_rows, key=lambda x: x["changePct"], reverse=True)
    buy_rows = sorted(buy_rows, key=lambda x: x["rsi14"] if x["rsi14"] is not None else 999)
    hot_rows = sorted(hot_rows, key=lambda x: x["changePct"], reverse=True)

    save_json("group1.json", buy_rows)
    save_json("group2.json", hot_rows)
    save_json("group3.json", all_rows)

    with open("signals.json", "w") as f:
        json.dump({
            "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "buyCount": len(buy_rows),
            "hotCount": len(hot_rows),
            "totalCount": len(all_rows)
        }, f, indent=2)

    print(f"Done. group1={len(buy_rows)} group2={len(hot_rows)} group3={len(all_rows)}")

if __name__ == "__main__":
    main()
