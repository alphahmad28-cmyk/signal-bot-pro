from datetime import datetime, timezone
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from market_data import fetch_candles
from technical import calculate_indicators

# Page Configuration
st.set_page_config(
    page_title="Signal Bot Pro",
    page_icon="⚡",
    layout="wide",
)

# --- FORCED CYBERPUNK STYLING & CSS ---
st.markdown(
    """
    <style>
    /* Force Dark Cyberpunk App Background */
    .stApp {
        background-color: #07090e !important;
        color: #e2e8f0 !important;
    }
    
    /* Neon Custom Metric Containers */
    div[data-testid="stMetric"] {
        background: #0f141d !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 0 12px rgba(0, 242, 254, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-family: 'Courier New', Courier, monospace !important;
        text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
    }
    
    /* Glowing Neon Action Button */
    .stButton > button {
        background: linear-gradient(135deg, #00f2fe 0%, #0072ff 100%) !important;
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 17px !important;
        letter-spacing: 1px;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 28px !important;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.5) !important;
        transition: all 0.3s ease-in-out;
        width: 100%;
    }
    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(0, 242, 254, 0.9) !important;
        transform: translateY(-2px);
    }
    </style>
""",
    unsafe_allow_html=True,
)

SYMBOL = "XAU_USD"
GRANULARITY = "M15"
LOOKBACK_CANDLES = 250


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


def get_val(row, *keys, default=0.0):
    for k in keys:
        if k in row and not pd.isna(row[k]):
            return float(row[k])
    return float(default)


def fetch_live_data():
    candles_res = fetch_candles(SYMBOL, GRANULARITY, count=LOOKBACK_CANDLES)
    if "values" not in candles_res or len(candles_res["values"]) < 200:
        return None, None

    m15_df = calculate_indicators(candles_res["values"])
    if not isinstance(m15_df, pd.DataFrame):
        m15_df = pd.DataFrame(m15_df)

    h1_df = create_h1_df(m15_df)
    if not isinstance(h1_df, pd.DataFrame):
        h1_df = pd.DataFrame(h1_df)

    return m15_df, h1_df


def evaluate_signal(m15_df: pd.DataFrame, h1_df: pd.DataFrame) -> dict:
    current_m15 = m15_df.iloc[-1]
    current_h1 = h1_df.iloc[-1]

    current_time = pd.to_datetime(current_m15["datetime"])
    hour, minute = current_time.hour, current_time.minute

    atr = get_val(current_m15, "atr", "ATR", default=4.0)
    close_price = float(current_m15["close"])

    m15_ema20 = get_val(current_m15, "ema20", "ema_20", "EMA20")
    m15_ema50 = get_val(current_m15, "ema50", "ema_50", "EMA50")
    m15_ema200 = get_val(current_m15, "ema200", "ema_200", "EMA200")
    h1_ema50 = get_val(current_h1, "ema50", "ema_50", "EMA50")

    rsi = get_val(current_m15, "rsi", "RSI", default=50.0)
    macd_hist = get_val(
        current_m15, "macd_hist", "macd_histogram", "MACDh_12_26_9"
    )

    vol_ma20 = m15_df["volume"].rolling(20).mean().iloc[-1]
    current_vol = float(current_m15.get("volume", 0))

    session_ok = 8 <= hour <= 20
    news_ok = not ((hour == 12 and minute >= 30) or hour in [13, 14])
    volume_ok = current_vol >= vol_ma20

    is_buy = (
        session_ok
        and news_ok
        and volume_ok
        and close_price > m15_ema200
        and m15_ema20 > m15_ema50
        and float(current_h1["close"]) > h1_ema50
        and macd_hist > 0
        and rsi > 58.0
    )

    is_sell = (
        session_ok
        and news_ok
        and volume_ok
        and close_price < m15_ema200
        and m15_ema20 < m15_ema50
        and float(current_h1["close"]) < h1_ema50
        and macd_hist < 0
        and rsi < 42.0
    )

    if is_buy:
        return {
            "signal": "BUY",
            "entry_price": close_price,
            "sl": round(close_price - (atr * 3.0), 2),
            "tp1": round(close_price + (atr * 2.5), 2),
            "tp2": round(close_price + (atr * 6.0), 2),
            "reason": "All strategy conditions met: Strong bullish momentum across M15 & H1 timeframes.",
        }
    elif is_sell:
        return {
            "signal": "SELL",
            "entry_price": close_price,
            "sl": round(close_price + (atr * 3.0), 2),
            "tp1": round(close_price - (atr * 2.5), 2),
            "tp2": round(close_price - (atr * 6.0), 2),
            "reason": "All strategy conditions met: Strong bearish momentum across M15 & H1 timeframes.",
        }
    else:
        if not session_ok:
            reason = f"Market is outside active session trading hours ({hour:02d}:{minute:02d} UTC)."
        elif not news_ok:
            reason = (
                "Volatility blackout window active (News / NY Open churn)."
            )
        elif not volume_ok:
            reason = "Current volume is below 20-period moving average."
        elif close_price <= m15_ema200 and macd_hist > 0:
            reason = "Price is below 200 EMA while MACD is positive (Trend mismatch)."
        else:
            reason = "Market indicators are neutral. No high-probability setup present."

        return {"signal": "HOLD", "reason": reason}


# Sidebar controls for live loop configuration
st.sidebar.header("⚡ Live Terminal Settings")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_rate = st.sidebar.slider(
    "Refresh Interval (seconds)", min_value=2, max_value=30, value=5
)

# Fetch live data
m15_df, h1_df = fetch_live_data()

# Display Logo and Title
st.image("logo.png", width=220)
st.title("⚡ SIGNAL BOT PRO")
st.caption("GOLD (XAU_USD) • M15 LIVE ACTIVE TERMINAL")

if m15_df is not None:
    current_candle = m15_df.iloc[-1]
    prev_candle = m15_df.iloc[-2]

    live_price = float(current_candle["close"])
    price_change = live_price - float(prev_candle["close"])

    # 1. TOP METRICS BLOCK
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "LIVE PRICE", f"${live_price:,.2f}", f"{price_change:+.2f}"
    )
    c2.metric("ATR (14)", get_val(current_candle, "atr", "ATR", default=4.0))
    c3.metric("RSI (14)", get_val(current_candle, "rsi", "RSI", default=50.0))
    c4.metric(
        "MACD HIST",
        get_val(
            current_candle, "macd_hist", "macd_histogram", "MACDh_12_26_9"
        ),
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. HD PROFESSIONAL CANDLESTICK CHART
    chart_df = m15_df.tail(60).copy()

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_df["datetime"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="XAU_USD",
            increasing_line=dict(color="#00ffcc", width=1.5),
            increasing_fillcolor="#00ffcc",
            decreasing_line=dict(color="#e60039", width=1.5),
            decreasing_fillcolor="#e60039",
        )
    )

    ema_mappings = [
        ("ema20", ["ema20", "ema_20", "EMA20", "EMA_20"], "#ffaa00", "EMA 20"),
        ("ema50", ["ema50", "ema_50", "EMA50", "EMA_50"], "#00f2fe", "EMA 50"),
        (
            "ema200",
            ["ema200", "ema_200", "EMA200", "EMA_200"],
            "#b026ff",
            "EMA 200",
        ),
    ]

    for default_key, possible_keys, color, name in ema_mappings:
        target_col = next(
            (k for k in possible_keys if k in chart_df.columns), None
        )
        if target_col and not chart_df[target_col].dropna().empty:
            fig.add_trace(
                go.Scatter(
                    x=chart_df["datetime"],
                    y=chart_df[target_col],
                    mode="lines",
                    line=dict(color=color, width=2.0, shape="spline"),
                    name=name,
                )
            )

    fig.update_layout(
        paper_bgcolor="#07090e",
        plot_bgcolor="#07090e",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#1e293b")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#1e293b")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. GLOWING SIGNAL ACTION BUTTON & RESULTS
    if st.button("⚡ GENERATE SIGNAL", use_container_width=True):
        with st.spinner("Executing rule engine evaluation..."):
            res = evaluate_signal(m15_df, h1_df)

        sig = res["signal"]

        if sig == "BUY":
            st.success("🚨 **SIGNAL: BUY**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Entry", f"${res['entry_price']}")
            m2.metric("Stop Loss", f"${res['sl']}")
            m3.metric("Partial TP (2.5x)", f"${res['tp1']}")
            m4.metric("Final TP (6.0x)", f"${res['tp2']}")
            st.info(f"**Reason:** {res['reason']}")

        elif sig == "SELL":
            st.error("🚨 **SIGNAL: SELL**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Entry", f"${res['entry_price']}")
            m2.metric("Stop Loss", f"${res['sl']}")
            m3.metric("Partial TP (2.5x)", f"${res['tp1']}")
            m4.metric("Final TP (6.0x)", f"${res['tp2']}")
            st.info(f"**Reason:** {res['reason']}")

        else:
            st.warning("✋ **SIGNAL: HOLD**")
            st.write(f"**Reason:** {res['reason']}")

    # --- LIVE AUTO-REFRESH LOOP ---
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

else:
    st.error("Unable to connect to market data feed. Check your API settings.")
