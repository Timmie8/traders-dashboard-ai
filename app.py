import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="AlphaScanner Ultra | High Win-Rate", layout="wide")

st.markdown("""
    <style>
    .score-container {
        background-color: #0e1117; border-radius: 15px; padding: 30px; text-align: center; 
        margin-bottom: 15px; border: 2px solid #2d3139;
    }
    .mtf-box {
        background-color: #161a25; border: 1px solid #2d3139; border-radius: 10px; padding: 15px; text-align: center;
    }
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_advanced_data(ticker, interval, period):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except: return None

def calculate_ultra_score(df):
    if df is None or len(df) < 50: return 0, False, 0
    
    # 1. Trend & RSI
    ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    last_p = df['Close'].iloc[-1]
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
    
    # 2. Volume Check (Nieuw!)
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
    current_vol = df['Volume'].iloc[-1]
    vol_confirm = current_vol > avg_vol
    
    # 3. Momentum
    ret_5p = df['Close'].pct_change(5).iloc[-1]
    sst = 68 + (ret_5p * 160)
    
    # Bonus/Straf Punten
    score = sst
    if last_p > ema_50: score += 15
    if rsi > 50 and rsi < 70: score += 10 # Sweet spot
    if vol_confirm: score += 10
    if rsi > 75: score -= 15 # Overbought risk
    
    final_score = max(5, min(99, int(score)))
    is_bullish = last_p > ema_50
    return final_score, is_bullish, rsi

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Ultra Terminal")
    if 'watchlist' not in st.session_state: st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
    if 'active_ticker' not in st.session_state: st.session_state.active_ticker = "AAPL"
    
    new_t = st.text_input("Add Ticker", "").upper()
    if st.button("Add & Analyze") and new_t:
        if new_t not in st.session_state.watchlist: st.session_state.watchlist.append(new_t)
        st.session_state.active_ticker = new_t
        st.rerun()
    
    symbol = st.selectbox("Asset", st.session_state.watchlist, index=st.session_state.watchlist.index(st.session_state.active_ticker))
    st.session_state.active_ticker = symbol
    
    capital = st.number_input("Balance ($)", value=10000)
    risk_pct = st.slider("Risk (%)", 0.5, 5.0, 1.0)

# --- DATA ---
df_1d = get_advanced_data(symbol, "1d", "1y")
df_1h = get_advanced_data(symbol, "1h", "1mo")
df_15m = get_advanced_data(symbol, "15m", "5d")

if df_1d is not None:
    score_d, bull_d, rsi_d = calculate_ultra_score(df_1d)
    score_1h, bull_1h, _ = calculate_ultra_score(df_1h)
    score_15m, bull_15m, _ = calculate_ultra_score(df_15m)

    # --- UI: HET COMMAND CENTER ---
    glow = "5px solid #00FFCC; box-shadow: 0px 0px 25px #00FFCC;" if score_d >= 80 else "2px solid #2d3139;"
    s_color = "#00FFCC" if score_d >= 80 else "#FFA500" if score_d >= 50 else "#FF4B4B"
    
    st.markdown(f"""
        <div class="score-container" style="border: {glow}">
            <p style="color: #808495; letter-spacing: 2px; margin:0;">ULTRA CONVICTION SCORE</p>
            <h1 style="font-size: 80px; color: {s_color}; margin: 0;">{score_d}%</h1>
            <p style="font-size: 20px; color: {'#00FFCC' if bull_d else '#FF4B4B'}; font-weight: bold;">
                {'🚀 BULLISH TREND' if bull_d else '⚠️ BEARISH TREND'} | RSI: {round(rsi_d, 1)}
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="mtf-box">15M Score: <b style="color:#00FFCC">{score_15m}%</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="mtf-box">1H Score: <b style="color:#00FFCC">{score_1h}%</b></div>', unsafe_allow_html=True)

    # --- ADVANCED CHART ---
    df_1d['SMA_20'] = df_1d['Close'].rolling(20).mean()
    df_1d['EMA_50'] = df_1d['Close'].ewm(span=50, adjust=False).mean()
    df_1d['ATR'] = (df_1d['High'] - df_1d['Low']).rolling(10).mean()
    
    # Bollinger Bands voor Volatility
    std = df_1d['Close'].rolling(20).std()
    df_1d['BB_upper'] = df_1d['SMA_20'] + (std * 2)
    df_1d['BB_lower'] = df_1d['SMA_20'] - (std * 2)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_1d['Date'], open=df_1d['Open'], high=df_1d['High'], low=df_1d['Low'], close=df_1d['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['BB_upper'], line=dict(color='rgba(173, 216, 230, 0.2)'), name="BB Upper"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['BB_lower'], line=dict(color='rgba(173, 216, 230, 0.2)'), fill='tonexty', name="BB Range"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['EMA_50'], line=dict(color='yellow'), name="EMA 50"), row=1, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- WIN-OPTIMIZED EXECUTION PLAN ---
    last_p = float(df_1d['Close'].iloc[-1])
    atr = float(df_1d['ATR'].iloc[-1])
    
    stop_loss = last_p - (atr * 2)
    take_profit = last_p + (atr * 3) # 1.5 Reward/Risk ratio
    qty = (capital * (risk_pct/100)) / (last_p - stop_loss) if last_p > stop_loss else 0

    st.subheader("🎯 High-Probability Execution")
    e1, e2, e3 = st.columns(3)
    e1.metric("Entry Price", f"${round(last_p, 2)}")
    e2.success(f"Target (TP): ${round(take_profit, 2)}")
    e3.warning(f"Stop Loss (SL): ${round(stop_loss, 2)}")
    
    st.info(f"💡 **Trading Advies:** Positie grootte: **{int(qty)} units**. Alleen instappen als Score > 80% EN de 15M/1H scores ook groen zijn.")
