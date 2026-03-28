import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | MTF AI", layout="wide")

# Custom CSS for MTF Badges
st.markdown("""
    <style>
    .score-container {
        background-color: #161a25; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 10px; transition: all 0.5s ease;
    }
    .mtf-box {
        background-color: #1c222d; border: 1px solid #2d3139; border-radius: 10px; padding: 15px; text-align: center;
    }
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60) # Lower TTL for faster intra-day updates
def get_mtf_data(ticker, interval, period):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except: return None

def calc_mtf_score(df):
    if df is None or len(df) < 20: return 0, False
    # Quick calc for MTF
    ema = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
    
    last_price = df['Close'].iloc[-1]
    bullish = last_price > ema and rsi > 50
    ret_5p = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (ret_5p * 160))))
    score = (sst + (100 if bullish else 0)) / 2
    return round(score, 1), bullish

# --- SESSION STATE ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "AAPL"

with st.sidebar:
    st.title("🛡️ MTF Terminal")
    new_ticker = st.text_input("Add Ticker", "").upper()
    if st.button("Add & Analyze") and new_ticker:
        if new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
        st.session_state.active_ticker = new_ticker
        st.rerun()
    
    symbol = st.selectbox("Active Asset", st.session_state.watchlist, 
                          index=st.session_state.watchlist.index(st.session_state.active_ticker) if st.session_state.active_ticker in st.session_state.watchlist else 0)
    
    st.divider()
    capital = st.number_input("Balance ($)", value=10000)
    risk_pct = st.slider("Risk (%)", 0.5, 5.0, 1.0)

# --- MTF DATA FETCHING ---
df_15m = get_mtf_data(symbol, "15m", "5d")
df_1h = get_mtf_data(symbol, "1h", "2y") # Extended for stability
df_1d = get_mtf_data(symbol, "1d", "1y")

if df_1d is not None:
    # Calculate Scores
    score_15m, bull_15m = calc_mtf_score(df_15m)
    score_1h, bull_1h = calc_mtf_score(df_1h)
    score_1d, bull_1d = calc_mtf_score(df_1d)

    # --- TOP ROW: MAIN DAILY SCORE ---
    border_style = "4px solid #00FFCC; box-shadow: 0px 0px 15px #00FFCC;" if score_1d >= 80 else "2px solid #2d3139;"
    score_color = "#00FFCC" if score_1d >= 80 else "#FFA500" if score_1d >= 50 else "#FF4B4B"

    st.markdown(f"""
        <div class="score-container" style="border: {border_style}">
            <p style="font-size: 14px; color: #808495; text-transform: uppercase; letter-spacing: 3px; margin: 0;">Daily AI Conviction - {symbol}</p>
            <p style="font-size: 55px; font-weight: 900; margin: 0; color: {score_color};">{score_1d}%</p>
        </div>
        """, unsafe_allow_html=True)

    # --- MTF STATUS BAR ---
    c1, c2 = st.columns(2)
    with c1:
        color_15 = "#00FFCC" if score_15m >= 70 else "#FF4B4B"
        st.markdown(f"""<div class="mtf-box">
            <small style="color: #808495;">15 MIN SCORE</small>
            <h3 style="color: {color_15}; margin: 0;">{score_15m}% {'🟢' if bull_15m else '🔴'}</h3>
        </div>""", unsafe_allow_html=True)
    with c2:
        color_1h = "#00FFCC" if score_1h >= 70 else "#FF4B4B"
        st.markdown(f"""<div class="mtf-box">
            <small style="color: #808495;">1 HOUR SCORE</small>
            <h3 style="color: {color_1h}; margin: 0;">{score_1h}% {'🟢' if bull_1h else '🔴'}</h3>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # --- MAIN CHART (Daily) ---
    # (Calculations for Daily chart logic remain here...)
    df_1d['EMA_50'] = df_1d['Close'].ewm(span=50, adjust=False).mean()
    df_1d['SMA_20'] = df_1d['Close'].rolling(window=20).mean()
    df_1d['ATR'] = (df_1d['High'] - df_1d['Low']).rolling(10).mean()
    df_1d['Signal_Num'] = np.where(df_1d['Close'] > (df_1d['High'].shift() - df_1d['ATR']), 1, 0)
    df_1d['Entry'] = df_1d['Signal_Num'].diff()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_1d['Date'], open=df_1d['Open'], high=df_1d['High'], low=df_1d['Low'], close=df_1d['Close'], name="Daily"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['EMA_50'], line=dict(color='yellow'), name="EMA 50"), row=1, col=1)
    
    buys = df_1d[df_1d['Entry'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low']*0.98, mode='markers', marker=dict(symbol='triangle-up', size=15, color='lime'), name='BUY'), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_1d['Date'], y=score_1d * (df_1d['Close']/df_1d['Close']), line=dict(color=score_color), name="Conviction"), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- POSITION SIZING ---
    last_price = float(df_1d['Close'].iloc[-1])
    atr = float(df_1d['ATR'].iloc[-1])
    stop_loss = last_price - (atr * 2)
    qty = (capital * (risk_pct/100)) / (last_price - stop_loss)
    
    st.subheader("📝 Daily Trade Plan")
    p1, p2, p3 = st.columns(3)
    p1.metric("Status", "B
