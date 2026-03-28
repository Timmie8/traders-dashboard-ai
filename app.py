import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGINA INSTELLINGEN ---
st.set_page_config(page_title="Free AI Trading Dashboard", layout="wide")

# --- DATA FUNCTIE (YAHOO) ---
@st.cache_data(ttl=600) # Ververs data elke 10 minuten
def load_data(ticker):
    try:
        # Haal 1 jaar data op
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if df.empty:
            return None
        
        # FIX VOOR YAHOO MULTI-INDEX: Dit is vaak de reden voor "Geen Data"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        
        # Zorg dat kolomnamen simpel zijn (Open, High, Low, Close, Volume)
        df.columns = [str(col).capitalize() for col in df.columns]
        if 'Date' not in df.columns and 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        return df
    except Exception as e:
        st.error(f"Fout bij ophalen {ticker}: {e}")
        return None

# --- STRATEGIE LOGICA ---
def apply_strategies(df):
    df = df.copy()
    
    # Forceer numerieke types voor pandas-ta
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Indicatoren berekenen
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Kolomnamen van pandas-ta opzoeken (soms verschillen ze per versie)
    ema_col = [c for c in df.columns if 'EMA_50' in c][0]
    rsi_col = [c for c in df.columns if 'RSI_14' in c][0]
    atr_col = [c for c in df.columns if 'ATR' in c][0]
    
    last_row = df.iloc[-1]
    close = float(last_row['Close'])
    ema = float(last_row[ema_col])
    rsi = float(last_row[rsi_col])
    atr = float(last_row[atr_col])
    
    # 1. Trend V2
    trend = "BULLISH" if close > ema and rsi > 50 else "BEARISH"
    
    # 2. SST Neural (Momentum score)
    ret = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (ret * 160))))
    
    # 3. UT Bot MTF
    ut_status = "BUY ACTIVE" if close > (last_row['High'] - (1.0 * atr)) else "SELL / WAIT"
    
    # 4. S/R Levels
    res = float(df['High'].rolling(20).max().iloc[-1])
    sup = float(df['Low'].rolling(20).min().iloc[-1])
    
    return trend, sst, ut_status, res, sup, rsi, ema, ema_col

# --- DASHBOARD UI ---
st.title("📊 Free AI Trading Dashboard")
ticker_input = st.sidebar.text_input("Ticker (bv. AAPL, TSLA, BTC-USD)", "AAPL").upper()

df = load_data(ticker_input)

if df is not None and len(df) > 50:
    try:
        trend, sst, ut, res, sup, rsi, ema_val, ema_name = apply_strategies(df)
        
        # Overall Score
        score = (sst + (100 if trend == "BULLISH" else 0) + (100 if "BUY" in ut else 0)) / 3
        
        col_main, col_info = st.columns([1, 2])
        with col_main:
            st.metric("TOTAAL SCORE", f"{round(score, 1)}%", delta=f"{sst}% Momentum")
        with col_info:
            st.subheader(f"Analyse: {ticker_input}")
            st.write(f"De markt is momenteel **{trend}**.")

        st.divider()

        # Grid
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.subheader("SST Neural")
            st.write(f"Score: {sst}")
            st.progress(sst/100)
        with c2:
            st.subheader("Trend V2")
            st.write(f"Trend: {trend}")
            st.write(f"RSI: {round(rsi, 2)}")
        with c3:
            st.subheader("UT Bot")
            st.write(f"Status: {ut}")
        with c4:
            st.subheader("S/R Levels")
            st.write(f"Target: {round(res, 2)}")
            st.write(f"Floor: {round(sup, 2)}")

        # Grafiek
        fig = go.Figure(data=[go.Candlestick(
            x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs"
        )])
        fig.add_trace(go.Scatter(x=df['Date'], y=df[ema_name], line=dict(color='yellow', width=1.5), name="EMA 50"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=550)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Berekeningsfout: {e}. Probeer een ander symbool.")
else:
    st.warning("Wachten op data... Gebruik 'AAPL' of 'BTC-USD'.")
