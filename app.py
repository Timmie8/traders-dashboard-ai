import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import base64

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | AI Quant", layout="wide")

# Function to play alert sound
def play_alert():
    # A short, professional 'ping' sound
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.components.v1.html(
        f"""
        <audio autoplay>
            <source src="{sound_url}" type="audio/mpeg">
        </audio>
        """,
        height=0,
    )

@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except: return None

def calculate_metrics(df):
    if df is None or len(df) < 50: return 0, "N/A", 0
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
    
    last_close = float(df['Close'].iloc[-1])
    ema_50 = float(df['EMA_50'].iloc[-1])
    
    trend = "BULLISH" if last_close > ema_50 and rsi > 50 else "BEARISH"
    ret_5d = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (ret_5d * 160))))
    
    score = (sst + (100 if trend == "BULLISH" else 0)) / 2
    return round(score, 1), trend, round(rsi, 1)

# --- UI HEADER ---
st.title("🛡️ AlphaScanner Pro")
st.caption("AI-Powered Multi-Strategy Trading Terminal")

# --- MARKET SCANNER ---
st.subheader("🔍 Market Sentinel Scanner")
watch_list = ["AAPL", "NVDA", "TSLA", "BTC-USD", "ETH-USD", "MSFT", "AMD"]
scan_cols = st.columns(len(watch_list))

high_score_detected = False

for i, t in enumerate(watch_list):
    data = get_data(t)
    score, trend, rsi_val = calculate_metrics(data)
    
    with scan_cols[i]:
        st.metric(t, f"{score}%", delta=trend, delta_color="normal")
        if score >= 80:
            st.toast(f"🔥 HIGH CONVICTION: {t}", icon="🚀")
            high_score_detected = True

# Trigger audio if any watched asset is booming
if high_score_detected:
    play_alert()

st.divider()

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Terminal Settings")
    symbol = st.text_input("Active Ticker", "AAPL").upper()
    st.divider()
    st.subheader("🧮 Position Sizing")
    capital = st.number_input("Account Balance ($)", value=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
    
df = get_data(symbol)

if df is not None and len(df) > 50:
    # Technicals
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
    
    # Main Analysis
    score, trend, rsi_now = calculate_metrics(df)
    last_price = float(df['Close'].iloc[-1])
    
    # Dashboard Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Conviction Score", f"{score}%")
    m2.metric("Market Price", f"${round(last_price, 2)}")
    m3.metric("Trend Phase", trend)
    m4.metric("RSI (14)", rsi_now)

    # Professional Charting
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=symbol), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00FFCC'), name="RSI"), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
    
    # Position Calculation
    stop_loss = last_price - (df['ATR'].iloc[-1] * 2)
    risk_amount = capital * (risk_pct / 100)
    position_size = risk_amount / (last_price - stop_loss)
    
    with st.sidebar:
        st.write(f"---")
        st.write(f"**Trade Plan:**")
        st.write(f"Suggested SL: ${round(stop_loss, 2)}")
        st.success(f"Quantity: {int(position_size)} units")

else:
    st.error("Invalid Ticker or Data missing.")
