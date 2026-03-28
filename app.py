import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Crypto/Stock AI Dashboard", layout="wide")
# Haal de key op uit de Streamlit Secrets
FINNHUB_KEY = st.secrets["FINNHUB_KEY"]

# --- FUNCTIES VOOR DATA ---
def get_finnhub_data(symbol, resolution='D', days=100):
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&from={start}&to={end}&token={FINNHUB_KEY}"
    
    response = requests.get(url)
    data = response.json()
    
    if data.get('s') != 'ok':
        return pd.DataFrame()
    
    df = pd.DataFrame({
        'time': pd.to_datetime(data['t'], unit='s'),
        'open': data['o'],
        'high': data['h'],
        'low': data['l'],
        'close': data['c'],
        'volume': data['v']
    })
    return df

# --- LOGICA VERTALINGEN ---
def calculate_metrics(df):
    # 1. SST Neural Logica
    pct_chg = df['close'].pct_change(5)
    m_score = (68 + (pct_chg * 160)).iloc[-1]
    m_score = max(5, min(98, m_score))
    
    # 2. Trend V2 Logica (EMA 50 + RSI)
    ema50 = ta.ema(df['close'], length=50)
    rsi = ta.rsi(df['close'], length=14)
    is_bullish = df['close'].iloc[-1] > ema50.iloc[-1] and rsi.iloc[-1] > 50
    
    # 3. UT Bot Logica (Simulatie)
    atr = ta.atr(df['high'], df['low'], df['close'], length=10)
    # Eenvoudige check: prijs boven trailing stop simulatie
    ut_buy = df['close'].iloc[-1] > (df['close'].iloc[-1] - (1.0 * atr.iloc[-1]))
    
    # 4. S/R Logica
    resistance = df['high'].rolling(window=20).max().iloc[-1]
    support = df['low'].rolling(window=20).min().iloc[-1]
    
    return {
        "m_score": round(m_score, 2),
        "rsi": round(rsi.iloc[-1], 2),
        "trend": "BULLISH" if is_bullish else "BEARISH",
        "ut_bot": "BUY ACTIVE" if ut_buy else "SELL/WAIT",
        "support": round(support, 2),
        "resistance": round(resistance, 2)
    }

# --- DASHBOARD UI ---
st.title("📊 Multi-Strategy Trader Dashboard")
symbol = st.sidebar.text_input("Ticker Symbol (bijv. AAPL of BINANCE:BTCUSDT)", "AAPL")

df = get_finnhub_data(symbol)

if not df.empty:
    metrics = calculate_metrics(df)
    
    # --- OVERALL SCORE VAK ---
    st.markdown("---")
    total_score = (metrics['m_score'] + (100 if metrics['trend'] == "BULLISH" else 0) + (100 if metrics['ut_bot'] == "BUY ACTIVE" else 0)) / 3
    
    col_score, col_status = st.columns([1, 2])
    with col_score:
        st.metric("OVERALL SCORE", f"{round(total_score, 1)}%", delta=f"{metrics['m_score']}% AI")
    with col_status:
        st.subheader("Systeem Status")
        st.info(f"De huidige marktconditie voor {symbol} is overwegend **{metrics['trend']}**.")

    # --- DE VIER INDIVIDUELE VAKKEN ---
    st.markdown("### Strategie Details")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.write("**SST NEURAL**")
        st.write(f"Momentum Score: {metrics['m_score']}")
        st.progress(metrics['m_score'] / 100)
        
    with c2:
        st.write("**TREND V2**")
        color = "green" if metrics['trend'] == "BULLISH" else "red"
        st.markdown(f":{color}[{metrics['trend']}]")
        st.write(f"RSI: {metrics['rsi']}")

    with c3:
        st.write("**UT BOT MTF**")
        st.write(f"Status: {metrics['ut_bot']}")
        
    with c4:
        st.write("**S/R & TARGETS**")
        st.write(f"Resistance: {metrics['resistance']}")
        st.write(f"Support: {metrics['support']}")

    # --- CHART ---
    fig = go.Figure(data=[go.Candlestick(x=df['time'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'])])
    fig.update_layout(title=f"Prijsgrafiek {symbol}", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Kon geen data ophalen. Controleer je API Key en het Symbool.")

# --- FOOTER ---
st.markdown("---")
st.caption("Data via Finnhub.io | Gebouwd met Python & Streamlit")
