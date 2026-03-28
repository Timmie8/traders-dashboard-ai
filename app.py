import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go

# --- CONFIGURATIE ---
st.set_page_config(page_title="AI Trader Dashboard", layout="wide")

@st.cache_data(ttl=600)
def get_stock_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        # Fix voor Yahoo's nieuwe data-indeling
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        df.columns = [str(c).capitalize() for c in df.columns]
        return df
    except:
        return None

# --- UI ---
st.title("📈 Mijn AI Trading Dashboard")
symbol = st.sidebar.text_input("Vul Ticker in (bv. AAPL of BTC-USD)", "AAPL").upper()

df = get_stock_data(symbol)

if df is not None and len(df) > 50:
    # Indicatoren berekenen
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Namen van kolommen opzoeken
    ema_col = [c for c in df.columns if 'EMA_50' in c][0]
    rsi_col = [c for c in df.columns if 'RSI_14' in c][0]
    
    last_close = float(df['Close'].iloc[-1])
    last_ema = float(df[ema_col].iloc[-1])
    last_rsi = float(df[rsi_col].iloc[-1])
    
    # Logica
    trend = "BULLISH 🟢" if last_close > last_ema and last_rsi > 50 else "BEARISH 🔴"
    
    # Dashboard Layout
    c1, c2 = st.columns(2)
    c1.metric("Huidige Prijs", f"${round(last_close, 2)}")
    c2.metric("Trend Status", trend)
    
    # Grafiek
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=df['Date'], y=df[ema_col], line=dict(color='yellow'), name="EMA 50"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Voer een geldige ticker in (bijv. AAPL of TSLA).")
