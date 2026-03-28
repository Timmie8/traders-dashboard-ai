import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | AI Quant", layout="wide")

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

# --- SESSION STATE ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "AAPL"

with st.sidebar:
    st.title("🛡️ Terminal")
    new_ticker = st.text_input("Add Ticker", "").upper()
    if st.button("Add & Analyze") and new_ticker:
        if new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
        st.session_state.active_ticker = new_ticker
        st.rerun()

    symbol = st.selectbox("Active Asset", st.session_state.watchlist, 
                          index=st.session_state.watchlist.index(st.session_state.active_ticker) 
                          if st.session_state.active_ticker in st.session_state.watchlist else 0)
    
    if symbol != st.session_state.active_ticker:
        st.session_state.active_ticker = symbol
        st.rerun()

    st.divider()
    capital = st.number_input("Balance ($)", value=10000)
    risk_pct = st.slider("Risk (%)", 0.5, 5.0, 1.0)

# --- DATA PROCESSING ---
df = get_data(st.session_state.active_ticker)

if df is not None and len(df) > 50:
    df = df.copy()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    df['Ret_5d'] = df['Close'].pct_change(5)
    df['SST_Raw'] = (68 + (df['Ret_5d'] * 160)).clip(5, 98)
    df['Trend_Bonus'] = np.where((df['Close'] > df['EMA_50']) & (df['RSI'] > 50), 100, 0)
    df['Conviction_Score'] = (df['SST_Raw'] + df['Trend_Bonus']) / 2

    df['UT_Stop'] = df['High'].rolling(1).max().shift() - (1.0 * df['ATR'])
    df['Signal_Num'] = np.where(df['Close'] > df['UT_Stop'], 1, 0)
    df['Entry'] = df['Signal_Num'].diff()

    # --- SETTINGS & COLORS ---
    last = df.iloc[-1]
    score = round(last['Conviction_Score'], 1)
    is_bullish = last['Trend_Bonus'] == 100
    is_buy = last['Signal_Num'] == 1
    
    # Border & Score Color
    border_style = "4px solid #00FFCC; box-shadow: 0px 0px 15px #00FFCC;" if score >= 80 else "2px solid #2d3139;"
    score_color = "#00FFCC" if score >= 80 else "#FFA500" if score >= 50 else "#FF4B4B"
    
    # Text Colors for Metrics
    trend_color = "green" if is_bullish else "normal"
    signal_color = "green" if is_buy else "normal"

    # --- TOP ROW: HIGH VISIBILITY SCORE ---
    st.markdown(f"""
        <style>
        .score-container {{
            background-color: #161a25;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: {border_style}
            margin-bottom: 25px;
            transition: all 0.5s ease;
        }}
        .score-value {{ font-size: 60px; font-weight: 900; margin: 0; line-height: 1; }}
        .score-label {{ font-size: 16px; color: #808495; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 10px; }}
        </style>
        <div class="score-container">
            <p class="score-label">AI Conviction - {st.session_state.active_ticker}</p>
            <p class="score-value" style="color: {score_color};">{score}%</p>
        </div>
        """, unsafe_allow_html=True)

    # Secondary Metrics with Colored Labels
    m1, m2, m3 = st.columns(3)
    m1.metric("Market Price", f"${round(last['Close'], 2)}")
    m2.metric("Trend Phase", "BULLISH" if is_bullish else "BEARISH", delta="CONFIRMED" if is_bullish else "WEAK", delta_color=trend_color)
    m3.metric("UT Bot Signal", "BUY" if is_buy else "SELL", delta="ACTIVE" if is_buy else "WAIT", delta_color=signal_color)

    if score >= 80:
        st.toast(f"🚀 CONVICTION THRESHOLD REACHED: {st.session_state.active_ticker}", icon="🔥")
        play_alert()

    # --- CHART ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], line=dict(color='#00BFFF', width=1), name="SMA 20"), row=1, col=1)
    
    buys = df[df['Entry'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', size=15, color='lime'), name='BUY'), row=1, col=1)

    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00FFCC'), name="RSI"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Conviction_Score'], fill='tozeroy', line=dict(color=score_color, width=2), name="AI Score"), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- TRADE PLAN ---
    st.subheader("📝 Trade Plan")
    stop_loss = float(last['Close'] - (last['ATR'] * 2))
    risk_amt = capital * (risk_pct / 100)
    qty = risk_amt / (float(last['Close']) - stop_loss) if float(last['Close']) > stop_loss else 0
    
    c1, c2 = st.columns(2)
    c1.success(f"Position: **{int(qty)} units**")
    c2.warning(f"Stop Loss: **${round(stop_loss, 2)}**")
else:
    st.warning("Awaiting Data Selection...")
