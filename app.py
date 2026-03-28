import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Yahoo AI Trader Dashboard", layout="wide")

# --- DATA FUNCTIE (YAHOO FINANCE) ---
def get_data(symbol):
    try:
        # We halen 1 jaar aan data op om genoeg historie te hebben voor de EMA 50
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return pd.DataFrame()
        
        # Yahoo data opschonen (Multi-index fix)
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        st.error(f"Yahoo Finance Fout: {e}")
        return pd.DataFrame()

# --- STRATEGIE LOGICA ---
def calc_all_strategies(df):
    df = df.copy()
    
    # Indicatoren berekenen
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Laatste waarden ophalen
    last_close = float(df['Close'].iloc[-1])
    last_ema = float(df['EMA_50'].iloc[-1])
    last_rsi = float(df['RSI_14'].iloc[-1])
    
    # 1. Trend V2
    trend_status = "BULLISH" if last_close > last_ema and last_rsi > 50 else "BEARISH"
    
    # 2. SST Neural (Momentum simulatie)
    returns = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (returns * 160))))
    
    # 3. UT Bot
    last_atr = float(df['ATRr_10'].iloc[-1])
    ut_signal = "BUY ACTIVE" if last_close > (df['High'].iloc[-1] - last_atr) else "SELL / WAIT"
    
    # 4. S/R Levels
    res_level = float(df['High'].rolling(20).max().iloc[-1])
    sup_level = float(df['Low'].rolling(20).min().iloc[-1])
    
    return trend_status, sst_score, ut_signal, res_level, sup_level, last_rsi

# --- UI DASHBOARD ---
st.title("📈 Free Yahoo AI Dashboard")
st.caption("Geen API Key nodig - Live data van Yahoo Finance")

# Sidebar input
ticker = st.sidebar.text_input("Ticker (bv. AAPL, TSLA, BTC-USD)", "AAPL").upper()

df_raw = get_data(ticker)

if not df_raw.empty:
    trend, sst, ut, res, sup, rsi = calc_all_strategies(df_raw)
    
    # Overall Score
    total_score = (sst + (100 if trend == "BULLISH" else 0) + (100 if "BUY" in ut else 0)) / 3
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.metric("OVERALL SCORE", f"{round(total_score, 1)}%", delta=f"{sst}% AI")
    with col_m2:
        st.subheader(f"Analyse voor {ticker}")
        st.write(f"Systeem status is momenteel: **{trend}**")

    st.markdown("---")
    
    # Grid Layout
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("SST Neural")
        st.write(f"Score: {sst}%")
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

    # Grafiek
    fig = go.Figure(data=[go.Candlestick(
        x=df_raw['Date'], open=df_raw['Open'], high=df_raw['High'], low=df_raw['Low'], close=df_raw['Close']
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Kon geen data vinden voor dit symbool. Gebruik 'BTC-USD' voor Bitcoin of 'AAPL' voor Apple.")
