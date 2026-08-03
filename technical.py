import numpy as np
import pandas as pd


def calculate_indicators(candle_values: list) -> pd.DataFrame:
    """Calculates EMAs, RSI, MACD, Bollinger Bands, and ATR for signal confluence."""
    df = pd.DataFrame(candle_values)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    # 1. Exponential Moving Averages (Trend)
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

    # 2. Relative Strength Index (RSI - Momentum)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))

    # 3. MACD (Oscillator)
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 4. Bollinger Bands (Volatility Squeeze / Expansion)
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    bb_std = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
    df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

    # 5. Average True Range (ATR - Volatility & SL/TP Sizing)
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = np.abs(df["high"] - df["close"].shift())
    df["low_close"] = np.abs(df["low"] - df["close"].shift())
    tr = df[["high_low", "high_close", "low_close"]].max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    return df