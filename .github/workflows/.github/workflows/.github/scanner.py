import requests
import json
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import os

# Your Tiingo API key (stored in GitHub secrets)
API_KEY = os.getenv('TIINGO_API_KEY')
BASE_URL = 'https://api.tiingo.com/tiingo/daily'

# Group 1 & 2 tickers
GROUP12_TICKERS = [
    'NVDA', 'ORCL', 'TER', 'MU', 'MPWR', 'BE', 'META', 'HIMS', 'TYL', 'STRI', 
    'MSFT', 'TSM', 'AVGO', 'PLTR', 'GOOGL', 'JPM', 'MA', 'BRK-B', 'COF', 'C', 
    'AMZN', 'TSLA', 'TJX', 'WMT', 'COST', 'PG', 'KO', 'PM', 'LLY', 'UNH', 
    'ISRG', 'NFLX', 'GE', 'CAT', 'RTX', 'HON', 'ETN', 'XOM', 'CVX', 'NEE', 
    'SO', 'LIN', 'SCCO', 'SHW', 'BA', 'LMT', 'ASML'
]

# Group 3 universe: we'll filter large caps later
GROUP3_TICKERS = []  # We'll fetch S&P 500 + Nasdaq large caps

def fetch_data(ticker, days=250):
    """Fetch adjusted EOD data from Tiingo"""
    end = datetime.now().date()
    start = end - timedelta(days=days)
    url = f'{BASE_URL}/{ticker}/prices?startDate={start}&resampleFreq=daily&token={API_KEY}'
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['volume_avg20'] = df['volume'].rolling(20).mean()
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()

def check_group1(df):
    """Group 1: Large body, relative size, volume"""
    if len(df) < 21:
        return False
    latest = df.iloc[-1]
    prev = df.iloc[-21:-1]  # Last 20 bars
    
    # Candle body > 70% range
    range_ = latest['high'] - latest['low']
    body = abs(latest['close'] - latest['open'])
    body_pct = body / range_ if range_ > 0 else 0
    
    # Bar larger than 70% of prev 20
    prev_ranges = prev['high'] - prev['low']
    bar_larger = range_ > prev_ranges.quantile(0.7)
    
    # Volume > 20d avg
    vol_high = latest['volume'] > latest['volume_avg20']
    
    return body_pct > 0.7 and bar_larger and vol_high

def check_group2(df):
    """Group 2: SMAs close, flat, range smaller"""
    if len(df) < 200:
        return False
    sma20 = df['close'].rolling(20).mean().iloc[-1]
    sma200 = df['close'].rolling(200).mean().iloc[-1]
    close_pct = abs(sma20 - sma200) / sma20 < 0.01  # <1%
    
    # Flat: slope of last 5 days < threshold
    slope20 = (sma20 - df['close'].rolling(20).mean().iloc[-5]) / 5
    slope200 = (sma200 - df['close'].rolling(200).mean().iloc[-5]) / 5
    flat = abs(slope20) < 0.005 and abs(slope200) < 0.005  # Adjust if needed
    
    # Range smaller than last 3-5
    latest_range = df.iloc[-1]['high'] - df.iloc[-1]['low']
    recent_ranges = df.iloc[-6:-1]['high'] - df.iloc[-6:-1]['low']
    range_small = latest_range < recent_ranges.min()
    
    return close_pct and flat and range_small

def check_group3(df):
    """Group 3: Complex rules"""
    if len(df) < 50:
        return False
    
    # MAs
    ma8 = df['close'].rolling(8).mean().iloc[-1]
    ma21 = df['close'].rolling(21).mean().iloc[-1]
    ma50 = df['close'].rolling(50).mean().iloc[-1]
    ma8_prev = df['close'].rolling(8).mean().iloc[-2]
    ma21_prev = df['close'].rolling(21).mean().iloc[-2]
    ma50_prev = df['close'].rolling(50).mean().iloc[-2]
    mas_up = ma8 > ma50 and ma21 > ma50 and ma8 > ma8_prev and ma21 > ma21_prev and ma50 > ma50_prev
    
    # DMI 10
    dmi = ta.dmi(df['high'], df['low'], df['close'], length=10)
    plus_di = dmi['DMP_10'].iloc[-1]
    minus_di = dmi['DMN_10'].iloc[-1]
    adx = dmi['ADX_10'].iloc[-1]
    dmi_ok = plus_di > minus_di and adx > 18
    
    # Stoch 5
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=5, d=3)
    k = stoch['STOCHk_5_3'].iloc[-1]
    k_prev = stoch['STOCHk_5_3'].iloc[-2]
    stoch_ok = k_prev < 30 and k > k_prev and k < 60
    
    # MACD 3,10,16
    macd = ta.macd(df['close'], fast=3, slow=10, signal=16)
    macd_line = macd['MACD_3_10_16'].iloc[-1]
    macd_prev = macd['MACD_3_10_16'].iloc[-2]
    macd_ok = macd_line >= 0 or macd_line > macd_prev
    
    # RSI 10
    rsi = ta.rsi(df['close'], length=10).iloc[-1]
    rsi_prev = ta.rsi(df['close'], length=10).iloc[-2]
    rsi_ok = rsi_prev < 35 and rsi > rsi_prev and rsi < 60
    
    # ROC up
    roc = ta.roc(df['close'], length=10).iloc[-1]
    roc_prev = ta.roc(df['close'], length=10).iloc[-2]
    roc_up = roc > roc_prev
    
    # Pullback 3-6% to 18-22 EMA on low volume
    ema18 = df['close'].ewm(span=18).mean().iloc[-1]
    ema22 = df['close'].ewm(span=22).mean().iloc[-1]
    high_52 = df['high'].rolling(52).max().iloc[-1]
    pullback_pct = (high_52 - df['close'].iloc[-1]) / high_52
    vol_low = df['volume'].iloc[-1] < df['volume'].tail(10).mean()
    pullback_ok = 0.03 <= pullback_pct <= 0.06 and ema18 <= df['close'].iloc[-1] <= ema22 and vol_low
    
    return (mas_up and dmi_ok and stoch_ok and macd_ok and rsi_ok and roc_up and pullback_ok)

def get_group3_universe():
    """For Group 3, we'll use a subset for now; expand later with fundamentals"""
    return GROUP12_TICKERS  # Start with your list, add S&P/Nasdaq later

def save_group(filename, items, updated):
    """Save group results to JSON"""
    data = {
        "updated": updated,
        "items": items
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Running scanner for {today}")
    
    # Group 1 & 2
    group1 = []
    group2 = []
    for ticker in GROUP12_TICKERS:
        print(f"Scanning {ticker}...")
        df = fetch_data(ticker)
        if not df.empty:
            if check_group1(df):
                group1.append({
                    "symbol": ticker,
                    "name": ticker,  # Add lookup later
                    "close": df['close'].iloc[-1],
                    "changePct": (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] if len(df) > 1 else 0
                })
            if check_group2(df):
                group2.append({
                    "symbol": ticker,
                    "name": ticker,
                    "close": df['close'].iloc[-1],
                    "changePct": (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] if len(df) > 1 else 0
                })
    
    # Group 3
    group3 = []
    group3_tickers = get_group3_universe()
    for ticker in group3_tickers:
        print(f"Scanning Group 3 {ticker}...")
        df = fetch_data(ticker)
        if not df.empty and check_group3(df):
            group3.append({
                "symbol": ticker,
                "name": ticker,
                "close": df['close'].
