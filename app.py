import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# --- CONFIGURATIE ---
st.set_page_config(page_title="AI Trader Dashboard", layout="wide")

def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        # Fix voor Yahoo data-structuur
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except:
        return None

# --- UI ---
st.title("📈 AI Trading Dashboard (Stable Version)")
symbol = st.sidebar.text_input("Ticker (bv. AAPL of BTC-USD)", "AAPL").upper()

df = get_data(symbol)

if df is not None and len(df) > 50:
    # HANDMATIGE BEREKENINGEN (Vervangt pandas-ta)
    # 1. EMA 50
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # 2. RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # LAATSTE DATA OPHALEN
    last_close = float(df['Close'].iloc[-1])
    last_ema = float(df['EMA_50'].iloc[-1])
    last_rsi = float(df['RSI_14'].iloc[-1])
    
    # TREND LOGICA
    trend = "BULLISH 🟢" if last_close > last_ema and last_rsi > 50 else "BEARISH 🔴"
    
    # DASHBOARD
    c1, c2, c3 = st.columns(3)
    c1.metric("Prijs", f"${round(last_close, 2)}")
    c2.metric("EMA 50", round(last_ema, 2))
    c3.metric("Trend", trend)
    
    st.subheader(f"RSI (14): {round(last_rsi, 2)}")

    # GRAFIEK
    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Kaarsen"
    )])
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Voer een geldige ticker in (bv. AAPL, TSLA of BTC-USD).")
