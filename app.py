import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGINA INSTELLINGEN ---
st.set_page_config(page_title="Free AI Trading Dashboard", layout="wide")

# --- DATA FUNCTIE (YAHOO) ---
@st.cache_data(ttl=3600) # Slaat data 1 uur op voor snelheid
def load_data(ticker):
    try:
        # Haal 1 jaar data op voor de EMA berekeningen
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty:
            return None
        # Fix voor Yahoo's nieuwe dataformaat
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        data.reset_index(inplace=True)
        return data
    except Exception as e:
        st.error(f"Fout bij ophalen {ticker}: {e}")
        return None

# --- STRATEGIE LOGICA ---
def apply_strategies(df):
    df = df.copy()
    
    # Indicatoren via Pandas-TA
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Laatste waarden voor het dashboard
    last_row = df.iloc[-1]
    close = float(last_row['Close'])
    ema = float(last_row['EMA_50'])
    rsi = float(last_row['RSI_14'])
    atr = float(last_row['ATRr_10'])
    
    # 1. Trend V2 Status
    trend = "BULLISH" if close > ema and rsi > 50 else "BEARISH"
    
    # 2. SST Neural (Momentum score)
    ret = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (ret * 160))))
    
    # 3. UT Bot MTF
    ut_status = "BUY ACTIVE" if close > (last_row['High'] - atr) else "SELL / WAIT"
    
    # 4. S/R Levels
    res = float(df['High'].rolling(20).max().iloc[-1])
    sup = float(df['Low'].rolling(20).min().iloc[-1])
    
    return trend, sst, ut_status, res, sup, rsi, ema

# --- DASHBOARD UI ---
st.title("📊 AI Trading Dashboard (Free Data)")
ticker_input = st.sidebar.text_input("Ticker (bv. AAPL, TSLA, BTC-USD)", "AAPL").upper()

df = load_data(ticker_input)

if df is not None:
    trend, sst, ut, res, sup, rsi, ema = apply_strategies(df)
    
    # Overall Score Berekening
    score = (sst + (100 if trend == "BULLISH" else 0) + (100 if "BUY" in ut else 0)) / 3
    
    col_main, col_info = st.columns([1, 2])
    with col_main:
        st.metric("TOTAAL SCORE", f"{round(score, 1)}%", delta=f"{sst}% AI Momentum")
    with col_info:
        st.subheader(f"Markt Analyse: {ticker_input}")
        st.write(f"De algemene trend is momenteel **{trend}**.")

    st.divider()

    # De 4 Vakken uit je Pine Script
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("SST Neural")
        st.write(f"Score: {sst}")
        st.progress(sst/100)
    with c2:
        st.subheader("Trend V2")
        st.write(f"Status: {trend}")
        st.write(f"RSI: {round(rsi, 2)}")
    with c3:
        st.subheader("UT Bot")
        st.write(f"Signaal: {ut}")
    with c4:
        st.subheader("S/R Levels")
        st.write(f"Target: {round(res, 2)}")
        st.write(f"Floor: {round(sup, 2)}")

    # GRAFIEK
    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs"
    )])
    # Voeg EMA 50 toe aan de grafiek
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"))
    
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Kon geen data vinden. Check of de ticker klopt (bv. BTC-USD voor Bitcoin).")
