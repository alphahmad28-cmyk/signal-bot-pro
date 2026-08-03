import pandas as pd
import plotly.graph_objects as go


def create_candlestick(data):
    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["datetime"])

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # 20-period EMA overlay
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()

    fig = go.Figure()

    # Neon Candlestick Trace
    fig.add_trace(
        go.Candlestick(
            x=df["datetime"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing=dict(
                fillcolor="#00F0FF",
                line=dict(color="#00F0FF", width=1.5)
            ),
            decreasing=dict(
                fillcolor="#FF3366",
                line=dict(color="#FF3366", width=1.5)
            )
        )
    )

    # Glowing Vector Trendline
    fig.add_trace(
        go.Scatter(
            x=df["datetime"],
            y=df["ema_20"],
            mode="lines",
            name="EMA 20",
            line=dict(color="#3B82F6", width=2, shape="spline"),
            hoverinfo="skip"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0A0E17",
        plot_bgcolor="#0D1322",
        height=650,
        margin=dict(l=10, r=20, t=20, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94A3B8", size=11)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94A3B8", size=11),
            side="right"
        )
    )

    return fig