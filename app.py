import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="AlphaScanner Pro | AI Quant", layout="wide")

# Custom CSS for Professional Dark Theme
st.markdown("""
    <style>
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Function for Sound Alert
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

# --- SIDEBAR: WATCHLIST MANAGER ---
with st.sidebar:
    st.title("🛡️ AlphaScanner Pro")
    
    # 1. Add Ticker to Watchlist
    st.subheader("📋 Watchlist Manager")
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ["AAPL", "NVDA", "BTC-USD", "TSLA"]
    
    new_ticker = st.text_input("Add Ticker (e.g. MSFT)", "").upper()
    if st.button("Add to List") and new_ticker:
        if new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.rerun()

    # 2. Select Active Ticker from Watchlist
    symbol = st.selectbox("Select Active Asset", st.session_state.watchlist)
    
    if st.button("Clear Watchlist"):
        st.session_state.watchlist = []
        st.rerun()

    st.divider()
    
    # 3. Risk Management
    st.subheader("🧮 Position Sizing")
    capital = st.number_input("Account Balance ($)", value=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)

# --- MAIN ANALYSIS ---
df = get_data(symbol)

if df is not None and len(df) > 50:
    # --- CALCULATIONS ---
    # Create copy to avoid SettingWithCopy warnings
    df = df.copy()

    # EMAs
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # ATR for Trailing Stop logic
    df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
    
    # metrics for Logic
    last = df.iloc[-1]
    prev = df.iloc[-2]
    last_price = float(last['Close'])
    rsi_val = float(last['RSI'])
    
    # --- STRATEGY LOGIC ---
    trend_bullish = last_price > last['EMA_50'] and rsi_val > 50
    ret_5d = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (ret_5d * 160))))
    total_score = (sst_score + (100 if trend_bullish else 0)) / 2
    
    # UT Bot Signal (Trailing Stop)
    df['UT_Stop'] = df['High'].rolling(1).max().shift() - (1.0 * df['ATR'])
    # Vectorized check for Buy/Sell condition
    df['Signal'] = np.where(df['Close'] > df['UT_Stop'], 'BUY', 'SELL')
    
    # Current Signal for Metric display
    current_signal = df['Signal'].iloc[-1]

    # --- DASHBOARD DISPLAY ---
    st.header(f"📊 Analysis: {symbol}")
    
    # Top Row Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Conviction Score", f"{round(total_score, 1)}%", delta=f"{sst_score}% AI")
    m2.metric("Market Price", f"${round(last_price, 2)}")
    m3.metric("Trend Phase", "BULLISH" if trend_bullish else "BEARISH")
    m4.metric("UT Bot Signal", current_signal)

    # Alerts
    if total_score >= 80:
        st.toast(f"🚀 HIGH CONVICTION DETECTED: {symbol}", icon="🔥")
        play_alert()

    # --- PROFESSIONAL CHART with Arrows ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # 1. Price Candlesticks
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    
    # 2. Add EMA lines
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
    
    # 3. Add Buy/Sell Arrows (Overlays)
    # We find where the signal CHANGES from previous day
    df['Entry_Exit'] = df['Signal'].diff()
    
    # Filter for Buy Signals
    buys = df[df['Entry_Exit'] == 'BUY']
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys['Date'], y=buys['Low'] * 0.99, # Slightly below low
                                 mode='markers', marker=dict(symbol='triangle-up', size=15, color='lime'),
                                 name='Buy Entry'), row=1, col=1)
        
    # Filter for Sell Signals
    sells = df[df['Entry_Exit'] == 'SELL']
    if not sells.empty:
        fig.add_trace(go.Scatter(x=sells['Date'], y=sells['High'] * 1.01, # Slightly above high
                                 mode='markers', marker=dict(symbol='triangle-down', size=15, color='red'),
                                 name='Sell Exit'), row=1, col=1)

    # 4. RSI subplot
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00FFCC', width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- TRADE PLAN ---
    st.subheader("📝 Trade Plan")
    tp_col1, tp_col2 = st.columns(2)
    
    stop_loss = last_price - (last['ATR'] * 2)
    risk_amt = capital * (risk_pct / 100)
    # Fix for division by zero
    diff = last_price - stop_loss
    qty = risk_amt / diff if diff > 0 else 0
    
    with tp_col1:
        st.write(f"**Position Sizing:**")
        st.write(f"• Recommended Stop Loss: `${round(stop_loss, 2)}`")
        st.write(f"• Risk Amount: `${round(risk_amt, 2)}`")
        st.success(f"• Optimal Quantity: **{int(qty)} units**")
        
    with tp_col2:
        st.write(f"**Current Indicators:**")
        st.write(f"• RSI Level: {round(rsi_val, 2)}")
        st.write(f"• EMA 50: ${round(last['EMA_50'], 2)}")

else:
    st.warning("Please add or select a valid ticker from your watchlist in the sidebar to begin analysis.")
