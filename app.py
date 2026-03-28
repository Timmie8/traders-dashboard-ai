import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests

# --- CONFIGURATIE ---
FINNHUB_API_KEY = "JOUW_API_KEY_HIER"
SYMBOL = "AAPL"

def get_data(symbol):
    # Finnhub API call voor candlestick data (candles)
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&token={FINNHUB_API_KEY}"
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data)
    df['t'] = pd.to_datetime(df['t'], unit='s')
    return df

# --- INDICATOR LOGICA (VERTALING VAN JE PINE CODES) ---
def calculate_scores(df):
    # 1. Trend Score (EMA 50 + RSI)
    ema50 = ta.ema(df['c'], length=50)
    rsi = ta.rsi(df['c'], length=14)
    trend_status = "Bullish" if df['c'].iloc[-1] > ema50.iloc[-1] and rsi.iloc[-1] > 50 else "Bearish"
    
    # 2. SST Neural (Simulatie van je Momentum/Regression logica)
    pct_chg = df['c'].pct_change(5).iloc[-1]
    m_score = min(98, max(5, int(68 + (pct_chg * 160))))
    
    return trend_status, m_score, rsi.iloc[-1]

# --- STREAMLIT DASHBOARD LAYOUT ---
st.set_page_config(layout="wide")
st.title(f"🚀 Multi-Strategy Dashboard: {SYMBOL}")

df = get_data(SYMBOL)
trend, sst, rsi_val = calculate_scores(df)

# OVERALL SCORE VAK
st.header("Overall Method Score")
total_score = (sst + (100 if trend == "Bullish" else 0)) / 2
st.metric(label="Totaal Score", value=f"{total_score}%", delta=f"{sst}% Momentum")

# INDIVIDUELE VAKKEN
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("SST Neural")
    st.write(f"Momentum: {sst}%")

with col2:
    st.subheader("Trend V2")
    st.write(f"Status: {trend}")
    st.write(f"RSI: {round(rsi_val, 2)}")

# ... (Andere kolommen toevoegen)
