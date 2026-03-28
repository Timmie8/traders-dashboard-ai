import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Ultra | institutional Grade", layout="wide")

# Custom CSS for Global UI
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
    
    # 2. Volume Logic
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
    current_vol = df['Volume'].iloc[-1]
    vol_confirm = current_vol > avg_vol
    
    # 3. Momentum Scaler
    ret_5p = df['Close'].pct_change(5).iloc[-1]
    sst = 68 + (ret_5p * 160)
    
    # Final Scoring Calculation
    score = sst
    if last_p > ema_50: score += 15
    if 50 < rsi < 68: score += 12 # Optimal buying momentum zone
    if vol_confirm: score += 10
    if rsi > 75: score -= 25 # Heavy overbought penalty
    
    final_score = max(5, min(99, int(score)))
    is_bullish = last_p > ema_50
    return final_score, is_bullish, rsi

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🛡️ Alpha Terminal")
    if 'watchlist' not in st.session_state: st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
    if 'active_ticker' not in st.session_state: st.session_state.active_ticker = "AAPL"
    
    add_input = st.text_input("Add Ticker Symbol", "").upper()
    if st.button("Add & Analyze") and add_input:
        if add_input not in st.session_state.watchlist: st.session_state.watchlist.append(add_input)
        st.session_state.active_ticker = add_input
        st.rerun()
    
    symbol = st.selectbox("Current Asset", st.session_state.watchlist, index=st.session_state.watchlist.index(st.session_state.active_ticker))
    st.session_state.active_ticker = symbol
    
    capital = st.number_input("Account Balance ($)", value=10000)
    risk_pct = st.slider("Risk per Position (%)", 0.5, 5.0, 1.0)

# --- MTF DATA PROCESSING ---
df_1d = get_advanced_data(symbol, "1d", "1y")
df_1h = get_advanced_data(symbol, "1h", "1mo")
df_15m = get_advanced_data(symbol, "15m", "5d")

if df_1d is not None:
    score_d, bull_d, rsi_d = calculate_ultra_score(df_1d)
    score_1h, bull_1h, _ = calculate_ultra_score(df_1h)
    score_15m, bull_15m, _ = calculate_ultra_score(df_15m)

    # --- TOP PANEL: CONVICTION HUB ---
    glow = "4px solid #00FFCC; box-shadow: 0px 0px 20px #00FFCC;" if score_d >= 80 else "2px solid #2d3139;"
    s_color = "#00FFCC" if score_d >= 80 else "#FFA500" if score_d >= 50 else "#FF4B4B"
    
    st.markdown(f"""
        <div class="score-container" style="border: {glow}">
            <p style="color: #808495; letter-spacing: 2.5px; margin:0;">INSTITUTIONAL CONVICTION SCORE</p>
            <h1 style="font-size: 85px; color: {s_color}; margin: 0;">{score_d}%</h1>
            <p style="font-size: 22px; color: {'#00FFCC' if bull_d else '#FF4B4B'}; font-weight: 800; margin-top: 5px;">
                {'🚀 BULLISH TREND CONFIRMED' if bull_d else '⚠️ BEARISH TREND DETECTED'} | RSI: {round(rsi_d, 1)}
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="mtf-box">15 Min Score: <b style="color:#00FFCC">{score_15m}%</b> {"🟢" if bull_15m else "🔴"}</div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="mtf-box">1 Hour Score: <b style="color:#00FFCC">{score_1h}%</b> {"🟢" if bull_1h else "🔴"}</div>', unsafe_allow_html=True)

    # --- CHARTING ENGINE ---
    df_1d['SMA_20'] = df_1d['Close'].rolling(20).mean()
    df_1d['EMA_50'] = df_1d['Close'].ewm(span=50, adjust=False).mean()
    df_1d['ATR'] = (df_1d['High'] - df_1d['Low']).rolling(10).mean()
    
    # Bollinger Bands
    std_dev = df_1d['Close'].rolling(20).std()
    df_1d['BB_up'] = df_1d['SMA_20'] + (std_dev * 2)
    df_1d['BB_low'] = df_1d['SMA_20'] - (std_dev * 2)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
    
    # Main Candlestick Trace
    fig.add_trace(go.Candlestick(x=df_1d['Date'], open=df_1d['Open'], high=df_1d['High'], low=df_1d['Low'], close=df_1d['Close'], name="Price"), row=1, col=1)
    
    # ULTRA-LIGHT Bollinger Bands Range
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['BB_up'], line=dict(color='rgba(173, 216, 230, 0.2)', width=0.8), name="BB Upper", hoverinfo='skip'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['BB_low'], line=dict(color='rgba(173, 216, 230, 0.2)', width=0.8), fill='tonexty', fillcolor='rgba(173, 216, 230, 0.05)', name="Volatility Range"), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df_1d['Date'], y=df_1d['EMA_50'], line=dict(color='yellow', width=1.2), name="EMA 50 (Trend)"), row=1, col=1)
    
    # Dynamic Signal Markers
    df_1d['Buy_Logic'] = np.where((df_1d['Close'] > df_1d['SMA_20']) & (df_1d['Close'] > df_1d['EMA_50']) & (score_d > 75), 1, 0)
    df_1d['Marker'] = df_1d['Buy_Logic'].diff()
    buys = df_1d[df_1d['Marker'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low']*0.985, mode='markers', marker=dict(symbol='triangle-up', size=16, color='#00FFCC'), name='BUY SIGNAL'), row=1, col=1)

    fig.update_layout(template="plotly_dark", height=750, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- RISK MANAGEMENT & TARGETS ---
    last_close = float(df_1d['Close'].iloc[-1])
    atr_val = float(df_1d['ATR'].iloc[-1])
    
    sl_price = last_close - (atr_val * 2)
    tp_price = last_close + (atr_val * 3.5) # Optimizing for higher Reward:Risk
    shares = (capital * (risk_pct/100)) / (last_close - sl_price) if last_close > sl_price else 0

    st.subheader("⚡ Strategic Trade Execution")
    e1, e2, e3 = st.columns(3)
    e1.metric("Market Entry", f"${round(last_close, 2)}")
    e2.success(f"Profit Target (TP): ${round(tp_price, 2)}")
    e3.warning(f"Stop Loss (SL): ${round(sl_price, 2)}")
    
    st.info(f"💡 **Execution Intel:** Recommend taking **{int(shares)} units**. High-probability entry confirmed when Daily Score is >80% and 15M momentum is 🟢.")
else:
    st.warning("Data loading... please ensure the ticker is valid.")
