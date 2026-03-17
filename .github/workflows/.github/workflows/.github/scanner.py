import requests
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# Your symbols
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']

api_key = 'your-tiingo-key-here'  # We'll add secret later

results = []

for symbol in symbols:
    url = f'https://api.tiingo.com/tiingo/daily/{symbol}/prices?token={api_key}&startDate=2026-01-01'
    
    resp = requests.get(url)
    data = resp.json()
    
    if data:
        df = pd.DataFrame(data)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['sma20'] = ta.sma(df['close'], length=20)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        if latest['rsi'] < 30 and latest['close'] > latest['sma20']:
            results.append({
                'symbol': symbol,
                'price': latest['close'],
                'rsi': latest['rsi'],
                'signal': 'BUY'
            })

# Save results
with open('signals.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Found {len(results)} signals")
