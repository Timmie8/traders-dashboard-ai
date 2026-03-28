import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | AI Quant", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def play_alert():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.components.v1.html(
        f"<audio autoplay><source src='{sound_url}' type='audio/mpeg'></audio>",
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

# --- SIDEBAR: WATCHLIST & AUTO-FOCUS ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "AAPL"

with st.sidebar:
    st.title("🛡️ AlphaScanner Pro")
    st.subheader("📋 Watchlist Manager")
    
    new_ticker = st.text_input("Add Ticker", "").upper()
    if st.button("Add & Analyze") and new_ticker:
        if new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
        st.session_state.active_ticker = new_ticker
        st.rerun()

    symbol = st.selectbox("Select Asset", st.session_state.watchlist, 
                          index=st.session_state.watchlist.index(st.session_state.active_ticker) 
                          if st.session_state.active_ticker in st.session_state.watchlist else 0)
    
    if symbol != st.session_state.active_ticker:
        st.session_state.active_ticker = symbol
        st.rerun()

    if st.button("Clear Watchlist"):
        st.session_state.watchlist = ["AAPL"]
        st.session_state.active_ticker = "AAPL"
        st.rerun()

    st.divider()
    st.subheader("🧮 Settings")
    capital = st.number_input("Balance ($)", value=10000)
    risk_pct = st.slider("Risk (%)", 0.5, 5.0, 1.0)

# --- DATA PROCESSING ---
df = get_data(st.session_state.active_ticker)

if df is not None and len(df) > 50:
    df = df.copy()

    # Indicators
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # RSI & ATR
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
    
    # Signals
    last_price = float(df['Close'].iloc[-1])
    trend_bullish = last_price > df['EMA_50'].iloc[-1] and df['RSI'].iloc[-1] > 50
    ret_5d = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (ret_5d * 160))))
    total_score = (sst_score + (100 if trend_bullish else 0)) / 2
    
    # UT Bot Signal
    df['UT_Stop'] = df['High'].rolling(1).max().shift() - (1.0 * df['ATR'])
    df['Signal_Num'] = np.where(df['Close'] > df['UT_Stop'], 1, 0)
    df['Entry'] = df['Signal_Num'].diff()

    # --- DASHBOARD ---
    st.header(f"📊 Analysis: {st.session_state.active_ticker}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Conviction", f"{round(total_score, 1)}%", delta=f"{sst_score}% AI")
    m2.metric("Price", f"${round(last_price, 2)}")
    m3.metric("Trend", "BULLISH" if trend_bullish else "BEARISH")
    m4.metric("UT Signal", "BUY" if df['Signal_Num'].iloc[-1] == 1 else "SELL")

    if total_score >= 80:
        st.toast(f"🚀 HIGH CONVICTION: {st.session_state.active_ticker}", icon="🔥")
        play_alert()

    # --- CHART ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Price
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    
    # Moving Averages
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1.5), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], line=dict(color='#00BFFF', width=1.5), name="SMA 20"), row=1, col=1)
    
    # ONLY BUY ARROWS
    buys = df[df['Entry'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low'] * 0.98, mode='markers', 
                                 marker=dict(symbol='triangle-up', size=18, color='lime'), name='BUY SIGNAL'), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00FFCC'), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- POSITION SIZING ---
    st.subheader("📝 Position Plan")
    stop_loss = last_price - (df['ATR'].iloc[-1] * 2)
    risk_amt = capital * (risk_pct / 100)
    diff_val = last_price - stop_loss
    qty = risk_amt / diff_val if diff_val > 0 else 0
    
    c1, c2 = st.columns(2)
    c1.success(f"Recommended Quantity: **{int(qty)} units**")
    c2.warning(f"Stop Loss Level: **${round(stop_loss, 2)}**")

else:
    st.warning("Data loading... please check ticker symbol.")
