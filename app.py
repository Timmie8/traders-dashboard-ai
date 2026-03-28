import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="AI Trader Dashboard", layout="wide")

@st.cache_data(ttl=600)
def load_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df is None or df.empty:
            return None
            
        # Fix voor Yahoo Multi-index (cruciaal voor nieuwe yfinance versies)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        # Maak kolomnamen netjes: Date, Open, High, Low, Close
        df.columns = [str(col).strip().capitalize() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Data Fout: {e}")
        return None

def apply_strategies(df):
    df = df.copy()
    
    # Voeg indicatoren toe
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Zoek kolomnamen (flexibel)
    ema_col = [c for c in df.columns if 'EMA_50' in c.upper()][0]
    rsi_col = [c for c in df.columns if 'RSI_14' in c.upper()][0]
    atr_col = [c for c in df.columns if 'ATR' in c.upper()][0]
    
    last = df.iloc[-1]
    close = float(last['Close'])
    ema = float(last[ema_col])
    rsi = float(last[rsi_col])
    atr = float(last[atr_col])
    
    # Berekeningen
    trend = "BULLISH" if close > ema and rsi > 50 else "BEARISH"
    # Momentum score (SST)
    ret = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (float(ret) * 160))))
    # UT Bot signaal
    ut_status = "BUY" if close > (last['High'] - atr) else "SELL / WAIT"
    
    return trend, sst, ut_status, rsi, ema, ema_col

# --- UI ---
st.title("📈 AI Trader Dashboard (v3.0)")

ticker = st.sidebar.text_input("Ticker (bv. AAPL of BTC-USD)", "AAPL").upper()
df = load_data(ticker)

if df is not None and len(df) > 50:
    try:
        trend, sst, ut, rsi, ema_val, ema_name = apply_strategies(df)
        
        # Dashboard Statistieken
        c1, c2, c3 = st.columns(3)
        c1.metric("Trend V2", trend)
        c2.metric("SST Neural Score", f"{sst}%")
        c3.metric("UT Bot Signal", ut)
        
        # Grafiek
        fig = go.Figure(data=[go.Candlestick(
            x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs"
        )])
        fig.add_trace(go.Scatter(x=df['Date'], y=df[ema_name], line=dict(color='yellow'), name="EMA 50"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Berekeningsfout: {e}")
else:
    st.info("Voer een geldige ticker in in de zijbalk (bijv. AAPL of BTC-USD).")
