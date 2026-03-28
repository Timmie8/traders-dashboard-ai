import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="PRO AI Quant Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS voor een 'Bloomberg' look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-metric-label-weight="700"] > label { color: #808495; }
    .stMetric { background-color: #161a25; border: 1px solid #2d3139; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except: return None

# --- SIDEBAR & INPUT ---
with st.sidebar:
    st.header("🎯 Asset Selectie")
    symbol = st.text_input("Ticker Symbool", "AAPL").upper()
    st.divider()
    st.info("Dit dashboard combineert SST Neural Momentum, Trend V2 (EMA/RSI) en UT Bot Trailing Signals.")

df = get_data(symbol)

if df is not None and len(df) > 50:
    # --- CALCULATIONS ---
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # ATR & UT Bot Logica
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(10).mean()
    
    # Signalen
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    trend_bullish = last['Close'] > last['EMA_50'] and last['RSI'] > 50
    ut_buy = last['Close'] > (prev['High'] - (1.0 * last['ATR']))
    sst_val = max(5, min(98, int(68 + (df['Close'].pct_change(5).iloc[-1] * 160))))
    
    total_score = (sst_val + (100 if trend_bullish else 0) + (100 if ut_buy else 0)) / 3

    # --- HEADER METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Score", f"{round(total_score, 1)}%", delta=f"{sst_val}% AI", delta_color="normal")
    c2.metric("Laatste Prijs", f"${round(last['Close'], 2)}", f"{round(((last['Close']/prev['Close'])-1)*100, 2)}%")
    c3.metric("Trend Status", "BULLISH" if trend_bullish else "BEARISH", delta="EMA50 Cross" if trend_bullish else "-")
    c4.metric("UT Bot", "BUY" if ut_buy else "SELL", delta="Active" if ut_buy else "Wait")

    st.divider()

    # --- MAIN CHART (Candles + Indicators) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # Candlestick
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='#FFD700', width=1.5), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_20'], line=dict(color='#00BFFF', width=1), name="EMA 20"), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#9467bd', width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, 
                      margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True)

    # --- RISK MANAGEMENT CALCULATOR ---
    st.sidebar.divider()
    st.sidebar.subheader("🧮 Position Sizer")
    capital = st.sidebar.number_input("Account Grootte ($)", value=10000)
    risk_pct = st.sidebar.slider("Risk per trade (%)", 0.5, 5.0, 1.0)
    stop_loss = st.sidebar.number_input("Stop Loss Prijs ($)", value=float(last['Close'] * 0.95))
    
    risk_amount = capital * (risk_pct / 100)
    diff = float(last['Close']) - stop_loss
    if diff > 0:
        shares = risk_amount / diff
        st.sidebar.success(f"Koop: **{int(shares)}** aandelen")
        st.sidebar.caption(f"Totaal risico: ${round(risk_amount, 2)}")
    else:
        st.sidebar.error("Stop loss moet lager zijn dan de prijs.")

else:
    st.warning("⚠️ Geen data gevonden. Controleer de ticker (bijv. AAPL of BTC-USD).")
