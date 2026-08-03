import pandas as pd


def generate_signal(m15_df: pd.DataFrame, h1_df: pd.DataFrame) -> dict:
    """Balanced 4-Factor Engine with bidirectional scoring."""
    if len(m15_df) < 50 or len(h1_df) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0}

    current_m15 = m15_df.iloc[-1]
    current_h1 = h1_df.iloc[-1]

    close_price = float(current_m15["close"])
    atr = (
        float(current_m15["atr"])
        if ("atr" in current_m15 and not pd.isna(current_m15["atr"]) and current_m15["atr"] > 0)
        else 0.0012
    )

    bullish_score = 0
    bearish_score = 0

    # 1. H1 Trend (25 Pts)
    h1_close = float(current_h1["close"])
    h1_ema50 = float(current_h1.get("ema50", 0))
    if h1_close > h1_ema50:
        bullish_score += 25
    elif h1_close < h1_ema50:
        bearish_score += 25

    # 2. M15 EMA Trend (25 Pts)
    m15_ema20 = float(current_m15.get("ema20", 0))
    m15_ema50 = float(current_m15.get("ema50", 0))
    if m15_ema20 > m15_ema50:
        bullish_score += 25
    elif m15_ema20 < m15_ema50:
        bearish_score += 25

    # 3. M15 MACD Histogram (25 Pts)
    macd_hist = float(current_m15.get("macd_hist", 0))
    if macd_hist > 0:
        bullish_score += 25
    elif macd_hist < 0:
        bearish_score += 25

    # 4. M15 RSI Position (25 Pts)
    rsi = float(current_m15.get("rsi", 50))
    if rsi > 52:
        bullish_score += 25
    elif rsi < 48:
        bearish_score += 25

    # Signal Output (Minimum 75% agreement)
    if bullish_score >= 75 and bullish_score > bearish_score:
        sl = close_price - (atr * 1.5)
        tp = close_price + (atr * 3.0)
        return {
            "signal": "BUY",
            "confidence": bullish_score,
            "sl": round(sl, 5),
            "tp": round(tp, 5),
        }

    elif bearish_score >= 75 and bearish_score > bullish_score:
        sl = close_price + (atr * 1.5)
        tp = close_price - (atr * 3.0)
        return {
            "signal": "SELL",
            "confidence": bearish_score,
            "sl": round(sl, 5),
            "tp": round(tp, 5),
        }

    return {
        "signal": "NEUTRAL",
        "confidence": max(bullish_score, bearish_score),
        "sl": 0.0,
        "tp": 0.0,
    }