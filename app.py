import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Ultimate Trader Dashboard", layout="wide")

# Veilig de key ophalen uit Streamlit Secrets
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
except:
    st.error("FOUT: FINNHUB_KEY niet gevonden in Secrets. Voeg deze toe in de Streamlit Cloud instellingen.")
    st.stop()

# --- DATA FUNCTIE ---
def get_data(symbol):
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=150)).timestamp())
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={start}&to={end}&token={FINNHUB_KEY}"
    
    res = requests.get(url)
    data = res.json()
    
    if data.get('s') != 'ok':
        return pd.DataFrame()
    
    df = pd.DataFrame({
        'Date': pd.to_datetime(data['t'], unit='s'),
        'Open': data['o'], 'High': data['h'],
        'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
    })
    return df

# --- STRATEGIE LOGICA ---
def calc_all_strategies(df):
    # 1. Trend Score (EMA + RSI)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    
    last_close = df['Close'].iloc[-1]
    last_ema = df['EMA_50'].iloc[-1]
    last_rsi = df['RSI_14'].iloc[-1]
    
    trend = "BULLISH" if last_close > last_ema and last_rsi > 50 else "BEARISH"
    
    # 2. SST Neural (Momentum)
    pct_chg = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (pct_chg * 160))))
    
    # 3. UT Bot (Trailing Stop simulatie)
    df.ta.atr(length=10, append=True)
    ut_status = "BUY" if last_close > (df['High'].iloc[-1] - df['ATRr_10'].iloc[-1]) else "SELL"
    
    # 4. S/R Targets
    res = df['High'].rolling(20).max().iloc[-1]
    sup = df['Low'].rolling(20).min().iloc[-1]
    
    return trend, sst_score, ut_status, res, sup

# --- UI DASHBOARD ---
st.title("🚀 Multi-Strategy AI Trader Dashboard")
ticker = st.sidebar.text_input("Symbool (bv. AAPL of BTCUSDT)", "AAPL").upper()

df = get_data(ticker)

if not df.empty:
    trend, sst, ut, res, sup = calc_all_strategies(df)
    
    # OVERALL SCORE BEREKENING
    final_score = (sst + (100 if trend == "BULLISH" else 0) + (100 if ut == "BUY" else 0)) / 3
    
    st.metric("OVERALL SCORE", f"{round(final_score, 1)}%", delta=f"{sst}% Momentum")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("**SST Neural**")
        st.write(f"Score: {sst}%")
    with col2:
        st.success("**Trend V2**") if trend == "BULLISH" else st.error("**Trend V2**")
        st.write(f"Status: {trend}")
    with col3:
        st.warning("**UT Bot**")
        st.write(f"Signaal: {ut}")
    with col4:
        st.help("**S/R Levels**")
        st.write(f"Target: {res}")

    # CHART
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Geen data gevonden. Check je API Key in Secrets en het Ticker symbool.")
