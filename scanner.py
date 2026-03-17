import os
print("Scanner starting...")
print("TIINGO_API_KEY:", "YES" if os.getenv('TIINGO_API_KEY') else "NO")
print("Test success!")
