import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGINA INSTELLINGEN ---
st.set_page_config(page_title="Free AI Trading Dashboard", layout="wide")

@st.cache_data(ttl=600)
def load_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty:
            return None
        # Fix voor Yahoo Multi-index
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        # Forceer hoofdletters voor kolommen
        df.columns = [str(col).strip().capitalize() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Yahoo Fout: {e}")
        return None

def apply_strategies(df):
    df = df.copy()
    # Bereken indicatoren
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=10, append=True)
    
    # Zoek de juiste kolommen (pandas-ta namen kunnen variëren)
    ema_col = [c for c in df.columns if 'EMA_50' in c.upper()][0]
    rsi_col = [c for c in df.columns if 'RSI_14' in c.upper()][0]
    atr_col = [c for c in df.columns if 'ATR' in c.upper()][0]
    
    last = df.iloc[-1]
    close = float(last['Close'])
    ema = float(last[ema_col])
    rsi = float(last[rsi_col])
    atr = float(last[atr_col])
    
    trend = "BULLISH" if close > ema and rsi > 50 else "BEARISH"
    ret = df['Close'].pct_change(5).iloc[-1]
    sst = max(5, min(98, int(68 + (float(ret) * 160))))
    ut_status = "BUY ACTIVE" if close > (last['High'] - atr) else "SELL / WAIT"
    res = float(df['High'].rolling(20).max().iloc[-1])
    sup = float(df['Low'].rolling(20).min().iloc[-1])
    
    return trend, sst, ut_status, res, sup, rsi, ema, ema_col

st.title("📊 AI Trading Dashboard")
ticker_input = st.sidebar.text_input("Ticker (bv. AAPL, BTC-USD)", "AAPL").upper()

df = load_data(ticker_input)

if df is not None and len(df) > 50:
    try:
        trend, sst, ut, res, sup, rsi, ema_val, ema_name = apply_strategies(df)
        score = (sst + (100 if trend == "BULLISH" else 0) + (100 if "BUY" in ut else 0)) / 3
        
        m1, m2 = st.columns([1, 2])
        m1.metric("TOTAAL SCORE", f"{round(score, 1)}%", delta=f"{sst}% Momentum")
        m2.subheader(f"Markt: {ticker_input} is {trend}")

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SST Neural", f"{sst}%")
        c2.metric("Trend V2", trend, f"RSI: {round(rsi,1)}")
        c3.metric("UT Bot", ut)
        c4.metric("S/R Levels", f"H: {round(res,2)}", f"L: {round(sup,2)}")

        fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs")])
        fig.add_trace(go.Scatter(x=df['Date'], y=df[ema_name], line=dict(color='yellow', width=1), name="EMA 50"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Berekeningsfout: {e}")
else:
    st.info("Voer een geldige ticker in.")
