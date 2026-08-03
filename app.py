from datetime import datetime, timezone
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from market_data import fetch_candles
from technical import calculate_indicators

# Page Configuration
st.set_page_config(
    page_title="Vital Forex",
    page_icon="⚡",
    layout="wide",
)

# Display Logo and Title
st.image("logo.png", width=250)
st.title("Vital Forex Dashboard")
st.markdown("---")

# --- FORCED CYBERPUNK STYLING & CSS ---
st.markdown(
    """
    <style>
    /* Main Theme Overrides */
    .stApp {
        background-color: #0b0f19;
        color: #00f3ff;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #131825;
        border-right: 1px solid #00f3ff33;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #131825;
        border: 1px solid #00f3ff55;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.1);
    }
    [data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00f3ff !important;
    }

    /* Headers */
    h1, h2, h3 {
        color: #00f3ff !important;
        font-family: 'Courier New', Courier, monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar Inputs & Controls
st.sidebar.header("Vital Forex Settings")
symbol = st.sidebar.selectbox("Trading Pair", ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"], index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["M1", "M5", "M15", "H1"], index=2)
refresh_rate = st.sidebar.slider("Auto-Refresh Rate (seconds)", 5, 60, 15)

st.sidebar.markdown("---")
st.sidebar.info("System status: Connected to live feed.")

# Main Application Layout Tabs
tab1, tab2 = st.tabs(["Live Market Dashboard", "Technical Analytics"])

with tab1:
    st.subheader(f"Live Feed: {symbol} ({timeframe})")
    
    # Fetch candle data and calculate indicators
    try:
        df = fetch_candles(symbol, timeframe)
        df = calculate_indicators(df)
        
        # Display latest key metrics
        if not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Latest Close", f"{latest['close']:.5f}", f"{latest['close'] - prev['close']:.5f}")
            col2.metric("RSI (14)", f"{latest.get('rsi', 50):.2f}")
            col3.metric("MACD", f"{latest.get('macd', 0):.4f}")
            col4.metric("Signal Status", "ACTIVE WATCH", "M15 Engine")
            
            # Interactive Candlestick Chart with Plotly
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Candles"
            )])
            
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0b0f19",
                plot_bgcolor="#0b0f19",
                title=f"{symbol} Price Action & Indicators",
                xaxis_title="Time",
                yaxis_title="Price",
                height=550
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No candle data returned for the selected configuration.")
            
    except Exception as e:
        st.error(f"Error loading market data: {e}")

with tab2:
    st.subheader("Advanced Technical Parameters")
    st.write("Reviewing indicator calculations and historical triggers across the M15 baseline setup.")
    try:
        if 'df' in locals() and not df.empty:
            st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.info("Awaiting active data pipeline...")
    except Exception as e:
        st.info("Load the main feed tab to initialize technical tables.")
