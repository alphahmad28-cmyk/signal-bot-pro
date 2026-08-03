import requests
from config import BASE_URL, OANDA_ACCOUNT_ID, OANDA_API_KEY
import pandas as pd


def fetch_candles(symbol: str, granularity: str, count: int = 100) -> pd.DataFrame:
    """Fetches historical candlestick data from OANDA v20 API and returns a DataFrame."""
    url = f"{BASE_URL}/v3/instruments/{symbol}/candles"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        res_json = response.json()

        if "candles" in res_json:
            formatted_values = []
            for c in res_json["candles"]:
                if c.get("complete") or c == res_json["candles"][-1]:
                    formatted_values.append({
                        "time": c["time"],
                        "open": float(c["mid"]["o"]),
                        "high": float(c["mid"]["h"]),
                        "low": float(c["mid"]["l"]),
                        "close": float(c["mid"]["c"]),
                        "volume": int(c["volume"])
                    })
            df = pd.DataFrame(formatted_values)
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"[API Error] {e}")
        return pd.DataFrame()


def fetch_live_price(symbol: str) -> dict | None:
    """Fetches real-time bid/ask/mid prices from OANDA pricing endpoint."""
    url = f"{BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"instruments": symbol}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        res_json = response.json()

        if "prices" in res_json and len(res_json["prices"]) > 0:
            price_data = res_json["prices"][0]
            bid = float(price_data["bids"][0]["price"])
            ask = float(price_data["asks"][0]["price"])
            return {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}
    except Exception as e:
        print(f"[API Warning] Could not fetch live pricing for {symbol}: {e}")

    return None


def fetch_market_data(symbol: str, granularity: str):
    """Unified function fetching primary candles, H1 macro trend candles, and live pricing."""
    candles_res = fetch_candles(symbol, granularity)
    h1_candles_res = fetch_candles(symbol, "H1", count=100)
    live_res = fetch_live_price(symbol)
    
    return {
        "candles": candles_res,
        "h1_candles": h1_candles_res,
        "live": live_res
    }
