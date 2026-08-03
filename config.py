import os
from dotenv import load_dotenv

load_dotenv()

# OANDA Base URL (Use practice URL for demo accounts)
BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# API Credentials
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Supported Symbols
SYMBOLS = [
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "XAU_USD"
]

# Timeframe Mappings (Streamlit Label -> OANDA Granularity)
TIMEFRAMES = {
    "5min": "M5",
    "15min": "M15",
    "30min": "M30",
    "1h": "H1",
    "4h": "H4",
    "1day": "D"
}