import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

API_KEY = os.getenv('TIINGO_API_KEY')
if not API_KEY:
    print("ERROR: TIINGO_API_KEY not found")
    exit(1)

GROUP12_TICKERS = [
    'NVDA', 'ORCL', 'TER
