import requests
import json
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import os

API_KEY = os.getenv('TIINGO_API_KEY')
BASE_URL = 'https://api.tiingo
