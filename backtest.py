import pandas as pd
from api.market_data import fetch_candles
from indicators.technical import calculate_indicators


# ==========================================
# 1. OPTIMIZED XAU_USD SIGNAL ENGINE
# ==========================================
def generate_signal(m15_df: pd.DataFrame, h1_df: pd.DataFrame) -> dict:
    """Gold (XAU_USD) high-probability signal engine.

    Filters:
    - Session Window: London & New York (08:00 - 20:00 UTC)
    - News Blackout: Excludes US market open chaos (12:30 - 15:00 UTC)
    - Volume Filter: Volume must exceed 20-period SMA to confirm move
    - Trend Filters: M15 EMA 200 + H1 EMA 50 alignment
    - R:R Ratio: 1:2.0 (3.0x ATR Stop Loss / 6.0x ATR Take Profit)
    """
    if len(m15_df) < 200 or len(h1_df) < 50:
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0, "atr": 4.0}

    current_m15 = m15_df.iloc[-1]
    current_h1 = h1_df.iloc[-1]

    current_time = pd.to_datetime(current_m15["datetime"])
    hour = current_time.hour
    minute = current_time.minute

    # Safe ATR extraction
    atr = current_m15.get("atr", current_m15.get("ATR", 4.0))
    atr = float(atr) if not pd.isna(atr) and float(atr) > 0 else 4.0

    # 1. Active Session Filter (08:00 - 20:00 UTC)
    if not (8 <= hour <= 20):
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0, "atr": atr}

    # 2. News/Open Churn Filter: Skip 12:30 - 15:00 UTC
    if hour == 12 and minute >= 30:
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0, "atr": atr}
    if hour in [13, 14]:
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0, "atr": atr}

    # 3. Volumetric Filter: Volume must be above 20-period average
    vol_ma20 = m15_df["volume"].rolling(20).mean().iloc[-1]
    current_vol = float(current_m15.get("volume", 0))
    if current_vol < vol_ma20:
        return {"signal": "NEUTRAL", "confidence": 0, "sl": 0.0, "tp": 0.0, "atr": atr}

    close_price = float(current_m15["close"])

    def get_val(row, *keys, default=0.0):
        for k in keys:
            if k in row and not pd.isna(row[k]):
                return float(row[k])
        return float(default)

    m15_ema20 = get_val(current_m15, "ema20", "ema_20", "EMA20")
    m15_ema50 = get_val(current_m15, "ema50", "ema_50", "EMA50")
    m15_ema200 = get_val(current_m15, "ema200", "ema_200", "EMA200")
    h1_ema50 = get_val(current_h1, "ema50", "ema_50", "EMA50")

    rsi = get_val(current_m15, "rsi", "RSI", default=50.0)
    macd_hist = get_val(current_m15, "macd_hist", "macd_histogram", "MACDh_12_26_9")

    # 4. Entry Conditions
    is_buy = (
        close_price > m15_ema200
        and m15_ema20 > m15_ema50
        and float(current_h1["close"]) > h1_ema50
        and macd_hist > 0
        and rsi > 58.0
    )

    is_sell = (
        close_price < m15_ema200
        and m15_ema20 < m15_ema50
        and float(current_h1["close"]) < h1_ema50
        and macd_hist < 0
        and rsi < 42.0
    )

    if is_buy:
        sl = close_price - (atr * 3.0)
        tp = close_price + (atr * 6.0)
        return {
            "signal": "BUY",
            "confidence": 85.0,
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "atr": atr,
        }

    elif is_sell:
        sl = close_price + (atr * 3.0)
        tp = close_price - (atr * 6.0)
        return {
            "signal": "SELL",
            "confidence": 85.0,
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "atr": atr,
        }

    return {"signal": "NEUTRAL", "confidence": 50.0, "sl": 0.0, "tp": 0.0, "atr": atr}


# ==========================================
# 2. TIMEFRAME RESAMPLING HELPER
# ==========================================
def create_h1_df(m15_df: pd.DataFrame) -> pd.DataFrame:
    df = m15_df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    h1 = (
        df.resample("1h")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
        .reset_index()
    )

    h1_list = h1.to_dict("records")
    return calculate_indicators(h1_list)


# ==========================================
# 3. BACKTEST RUNNER ENGINE
# ==========================================
def run_backtest(
    symbol: str = "XAU_USD",
    granularity: str = "M15",
    count: int = 1000,
    initial_balance: float = 10000.0,
    risk_pct: float = 1.0,
    min_confidence: float = 70.0,
):
    print(f"\n==================================================")
    print(f"🚀 STARTING BACKTEST: {symbol} ({granularity})")
    print(
        f"Candles: {count} | Balance: ${initial_balance:,.2f} | Risk: {risk_pct}%"
    )
    print(f"==================================================\n")

    candles_res = fetch_candles(symbol, granularity, count=count)
    if "values" not in candles_res or len(candles_res["values"]) < 200:
        print(
            f"❌ Error fetching market data: {candles_res.get('error', 'Insufficient candles')}"
        )
        return

    full_m15_df = calculate_indicators(candles_res["values"])
    full_h1_df = create_h1_df(full_m15_df)

    balance = initial_balance
    trades = []
    active_position = None
    cooldown_counter = 0

    for i in range(200, len(full_m15_df)):
        window_m15 = full_m15_df.iloc[: i + 1]
        current_candle = window_m15.iloc[-1]
        current_time = pd.to_datetime(current_candle["datetime"])

        high_price = float(current_candle["high"])
        low_price = float(current_candle["low"])

        window_h1 = full_h1_df[
            pd.to_datetime(full_h1_df["datetime"]) <= current_time
        ]

        if cooldown_counter > 0:
            cooldown_counter -= 1

        # --- STEP A: CHECK ACTIVE TRADE SL/TP & PARTIAL BE LOGIC ---
        if active_position is not None:
            pos_type = active_position["type"]
            sl = active_position["sl"]
            tp = active_position["tp"]
            entry_p = active_position["entry_price"]
            risk_amount = active_position["risk_amount"]
            atr_val = active_position["atr"]
            partial_taken = active_position.get("partial_taken", False)
            accumulated_pnl = active_position.get("accumulated_pnl", 0.0)

            trade_closed = False
            pnl = 0.0
            outcome = ""

            if pos_type == "BUY":
                # Partial TP & Move SL to Break-Even at +2.5x ATR
                if not partial_taken and high_price >= entry_p + (atr_val * 2.5):
                    # Lock in 50% position profit at 2.5x ATR gain ratio
                    secured_profit = (risk_amount * 0.5) * (2.5 / 3.0)
                    accumulated_pnl += secured_profit
                    active_position["accumulated_pnl"] = accumulated_pnl
                    active_position["partial_taken"] = True
                    active_position["sl"] = entry_p
                    sl = entry_p

                if low_price <= sl:
                    if partial_taken:
                        pnl = accumulated_pnl  # Locked in 50% profit, remaining 50% stopped at BE
                        outcome = "PARTIAL WIN (BE Hit)"
                    else:
                        pnl = -risk_amount
                        outcome = "LOSS (SL Hit)"
                    trade_closed = True

                elif high_price >= tp:
                    if partial_taken:
                        # 50% secured earlier + remaining 50% hitting full 1:2 TP
                        pnl = accumulated_pnl + (risk_amount * 0.5 * 2.0)
                    else:
                        pnl = risk_amount * 2.0
                    outcome = "WIN (TP Hit)"
                    trade_closed = True

            elif pos_type == "SELL":
                # Partial TP & Move SL to Break-Even at +2.5x ATR
                if not partial_taken and low_price <= entry_p - (atr_val * 2.5):
                    secured_profit = (risk_amount * 0.5) * (2.5 / 3.0)
                    accumulated_pnl += secured_profit
                    active_position["accumulated_pnl"] = accumulated_pnl
                    active_position["partial_taken"] = True
                    active_position["sl"] = entry_p
                    sl = entry_p

                if high_price >= sl:
                    if partial_taken:
                        pnl = accumulated_pnl
                        outcome = "PARTIAL WIN (BE Hit)"
                    else:
                        pnl = -risk_amount
                        outcome = "LOSS (SL Hit)"
                    trade_closed = True

                elif low_price <= tp:
                    if partial_taken:
                        pnl = accumulated_pnl + (risk_amount * 0.5 * 2.0)
                    else:
                        pnl = risk_amount * 2.0
                    outcome = "WIN (TP Hit)"
                    trade_closed = True

            if trade_closed:
                balance += pnl
                trades.append(
                    {
                        "entry_time": active_position["entry_time"],
                        "exit_time": current_candle["datetime"],
                        "type": pos_type,
                        "entry_price": active_position["entry_price"],
                        "pnl": round(pnl, 2),
                        "outcome": outcome,
                        "balance": round(balance, 2),
                    }
                )
                active_position = None
                cooldown_counter = 4

        # --- STEP B: CHECK FOR NEW SIGNAL ---
        if (
            active_position is None
            and cooldown_counter == 0
            and len(window_h1) >= 20
        ):
            signal_res = generate_signal(window_m15, window_h1)
            signal_type = signal_res.get("signal", "NEUTRAL")
            confidence = signal_res.get("confidence", 0.0)

            if signal_type in ["BUY", "SELL"] and confidence >= min_confidence:
                risk_amount = balance * (risk_pct / 100.0)
                sl_price = signal_res["sl"]
                tp_price = signal_res["tp"]
                atr_val = signal_res.get("atr", 4.0)

                if sl_price > 0 and tp_price > 0:
                    active_position = {
                        "type": signal_type,
                        "entry_price": float(current_candle["close"]),
                        "sl": sl_price,
                        "tp": tp_price,
                        "risk_amount": risk_amount,
                        "entry_time": current_candle["datetime"],
                        "atr": atr_val,
                        "partial_taken": False,
                        "accumulated_pnl": 0.0,
                    }

    # --- STEP C: OUTPUT STATS & LOG ---
    total_trades = len(trades)
    if total_trades == 0:
        print(f"⚠️ No trades executed. Filter conditions were too strict.")
        return

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    break_evens = [t for t in trades if t["pnl"] == 0]

    win_rate = (len(wins) / total_trades) * 100
    total_pnl = balance - initial_balance
    total_return_pct = (total_pnl / initial_balance) * 100

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = (
        (gross_profit / gross_loss) if gross_loss > 0 else gross_profit
    )

    print("\n---------------- BACKTEST RESULTS ----------------")
    print(f"Symbol                : {symbol}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {len(wins)}")
    print(f"Losing Trades         : {len(losses)}")
    print(f"Break-Even Trades     : {len(break_evens)}")
    print(f"Win Rate              : {win_rate:.2f}%")
    print(f"Profit Factor         : {profit_factor:.2f}")
    print(f"Initial Balance       : ${initial_balance:,.2f}")
    print(f"Final Balance         : ${balance:,.2f}")
    print(
        f"Net Profit/Loss       : ${total_pnl:,.2f} ({total_return_pct:+.2f}%)"
    )
    print("--------------------------------------------------\n")

    trades_df = pd.DataFrame(trades)
    print(
        trades_df[
            [
                "entry_time",
                "type",
                "entry_price",
                "pnl",
                "outcome",
                "balance",
            ]
        ].to_string()
    )


if __name__ == "__main__":
    run_backtest(
        symbol="XAU_USD",
        granularity="M15",
        count=1000,
        initial_balance=10000.0,
        risk_pct=1.0,
        min_confidence=70.0,
    )