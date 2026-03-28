import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | MTF AI", layout="wide")

# Custom CSS for MTF Badges & High-Visibility Score
st.markdown("""
    <style>
    .score-container {
        background-color: #161a25; border-radius: 15px; padding: 25px; text-align: center; margin-bottom: 15px; transition: all 0.5s ease;
    }
    .mtf-box {
        background-color: #1c222d; border: 1px solid #2d3139; border-radius: 10px; padding: 15px; text-align: center;
    }
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def play_alert():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.components.v1.html(
        f"<audio autoplay><source src='{sound_url}' type='audio/mpeg'></audio>",
        height=0,
    )

@st.cache_data(ttl=60)
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
    ema = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_val = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
    last_p = df['Close'].iloc[-1]
    is_bull = last_p > ema and rsi_val > 50
    ret_5p = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (ret_5p * 160))))
    return round((sst + (100 if is_bull else 0)) / 2, 1), is_bull

# --- SESSION STATE ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "AAPL"

with st.sidebar:
    st.title("🛡️ Terminal")
    new_t = st.text_input("Add Ticker", "").upper()
    if st.button("Add & Analyze") and new_t:
        if new_t not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_t)
        st.session_state.active_ticker = new_t
        st.rerun()
    
    symbol = st.selectbox("Active Asset", st.session_state.watchlist, 
                          index=st.session_state.watchlist.index(st.session_state.active_ticker) if st.session_state.active_ticker in st.session_state.watchlist else 0)
    
    if symbol != st.session_state.active_ticker:
        st.session_state.active_ticker = symbol
        st.rerun()

    st.divider()
    capital = st.number_input("Balance ($)", value=10000)
    risk_pct = st.slider("Risk (%)", 0.5, 5.0, 1.0)

# --- PROCESSING ---
df_15m = get_mtf_data(symbol, "15m", "5d")
df_1h = get_mtf_data(symbol, "1h", "1mo")
df_1d = get_mtf_data(symbol, "1d", "1y")

if df_1d is not None and len(df_1d) > 30:
    score_15m, bull_15m = calc_mtf_score(df_15m)
    score_1h, bull_1h = calc_mtf_score(df_1h)
    score_1d, bull_1d = calc_mtf_score(df_1d)

    # --- TOP DISPLAY ---
    border = "4px solid #00FFCC; box-shadow: 0px 0px 15px #00FFCC;" if score_1d >= 80 else "2px solid #2d3139;"
    color_d = "#00FFCC" if score_1d >= 80 else "#FFA500" if score_1d >= 50 else "#FF4B4B"

    st.markdown(f"""
        <div class="score-container" style="border: {border}">
            <p style="font-size: 14px; color: #808495; text-transform: uppercase; letter-spacing: 3px; margin: 0;">Daily AI Conviction - {symbol}</p>
            <p style="font-size: 60px; font-weight: 900; margin: 0; color: {color_d};">{score_1d}%</p>
        </div>
        """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        c_15 = "#00FFCC" if score_15m >= 70 else "#FF4B4B"
        st.markdown(f'<div class="mtf-box"><small style="color:#808495">15M SCORE</small><h3 style="color:{c_15};margin:0">{score_15m}% {"🟢" if bull_15m else "🔴"}</h3></div>', unsafe_allow_html=True)
    with c2:
        c_1h = "#00FFCC" if score_1h >= 70 else "#FF4B4B"
        st.markdown(f'<div class="mtf-box"><small style="color:#808495">1H SCORE</small><h3 style="color:{c_1h};margin:0">{score_1h}% {"🟢" if bull_1h else "🔴"}</h3></div>', unsafe_allow_html=True)

    # --- DAILY CHART CALCULATIONS ---
    df_1d['EMA_50'] = df_1d['Close'].ewm(span=50, adjust=False).mean()
    df_1d['SMA_20'] = df_1d['Close'].rolling(window=20).mean()
    df_1d['ATR'] = (df_1d['High'] - df_1d['Low']).rolling(10).mean()
    df_1d['Signal'] = np.where(df_1d['Close'] > (df_1d['High'].shift() - df_1d['ATR']), 1, 0)
    df_1d['Entry'] = df_1d['Signal'].diff()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_1d['Date'], open=df_1d['Open'], high=df_1d['High'], low=df_1d['Low'], close=df_1d['Close'], name="Daily"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['EMA_50'], line=dict(color='yellow'), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['SMA_20'], line=dict(color='#00BFFF'), name="SMA 20"), row=1, col=1)
    
    buys = df_1d[df_1d['Entry'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low']*0.98, mode='markers', marker=dict(symbol='triangle-up', size=15, color='lime'), name='BUY'), row=1, col=1)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- PLAN ---
    last_p = float(df_1d['Close'].iloc[-1])
    atr_v = float(df_1d['ATR'].iloc[-1])
    sl = last_p - (atr_v * 2)
    qty = (capital * (risk_pct/100)) / (last_p - sl) if last_p > sl else 0

    st.subheader("📝 Trade Plan")
    p1, p2, p3 = st.columns(3)
    p1.metric("Trend", "BULLISH" if bull_1d else "BEARISH", delta="CONFIRMED" if bull_1d else "WEAK", delta_color="green" if bull_1d else "inverse")
    p2.success(f"Quantity: {int(qty)} units")
    p3.warning(f"Stop Loss: ${round(sl, 2)}")

    if score_1d >= 80:
        play_alert()

else:
    st.error("No data found. Check ticker.")
