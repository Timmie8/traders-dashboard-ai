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

# --- SIDEBAR: WATCHLIST ---
with st.sidebar:
    st.title("🛡️ AlphaScanner Pro")
    st.subheader("📋 Watchlist Manager")
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
    
    new_ticker = st.text_input("Add Ticker", "").upper()
    if st.button("Add to List") and new_ticker:
        if new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.rerun()

    symbol = st.selectbox("Select Active Asset", st.session_state.watchlist)
    if st.button("Clear Watchlist"):
        st.session_state.watchlist = []
        st.rerun()

    st.divider()
    st.subheader("🧮 Position Sizing")
    capital = st.number_input("Account Balance ($)", value=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)

# --- MAIN ANALYSIS ---
df = get_data(symbol)

if df is not None and len(df) > 50:
    df = df.copy()

    # Indicators
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
    
    # Strategy Logic
    last = df.iloc[-1]
    prev = df.iloc[-2]
    last_price = float(last['Close'])
    
    trend_bullish = last_price > last['EMA_50'] and last['RSI'] > 50
    ret_5d = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (ret_5d * 160))))
    total_score = (sst_score + (100 if trend_bullish else 0)) / 2
    
    # UT Bot Signal Logic (Fixed Version)
    df['UT_Stop'] = df['High'].rolling(1).max().shift() - (1.0 * df['ATR'])
    # Convert Signal to numbers: 1 for BUY, 0 for SELL
    df['Signal_Num'] = np.where(df['Close'] > df['UT_Stop'], 1, 0)
    # diff() now works on numbers: 1 (New Buy), -1 (New Sell), 0 (No change)
    df['Entry_Exit'] = df['Signal_Num'].diff()

    # --- DASHBOARD ---
    st.header(f"📊 Analysis: {symbol}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Conviction Score", f"{round(total_score, 1)}%", delta=f"{sst_score}% AI")
    m2.metric("Market Price", f"${round(last_price, 2)}")
    m3.metric("Trend Phase", "BULLISH" if trend_bullish else "BEARISH")
    m4.metric("UT Bot Signal", "BUY" if df['Signal_Num'].iloc[-1] == 1 else "SELL")

    if total_score >= 80:
        st.toast(f"🚀 HIGH CONVICTION: {symbol}", icon="🔥")
        play_alert()

    # --- CHART WITH ARROWS ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"), row=1, col=1)
    
    # Buy Arrows (Entry_Exit == 1)
    buys = df[df['Entry_Exit'] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low'] * 0.98, mode='markers', 
                                 marker=dict(symbol='triangle-up', size=15, color='lime'), name='Buy'), row=1, col=1)
        
    # Sell Arrows (Entry_Exit == -1)
    sells = df[df['Entry_Exit'] == -1]
    if not sells.empty:
        fig.add_trace(go.Scatter(x=sells['Date'], y=sells['High'] * 1.02, mode='markers', 
                                 marker=dict(symbol='triangle-down', size=15, color='red'), name='Sell'), row=1, col=1)

    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00FFCC'), name="RSI"), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- TRADE PLAN ---
    st.subheader("📝 Trade Plan")
    stop_loss = last_price - (last['ATR'] * 2)
    risk_amt = capital * (risk_pct / 100)
    qty = risk_amt / (last_price - stop_loss) if last_price > stop_loss else 0
    
    c1, c2 = st.columns(2)
    c1.success(f"Optimal Quantity: **{int(qty)} units**")
    c2.warning(f"Stop Loss: **${round(stop_loss, 2)}**")

else:
    st.warning("Please select a valid ticker.")
