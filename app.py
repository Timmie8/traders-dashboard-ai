import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="AI Trader Dashboard v4", layout="wide")

def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        return df
    except:
        return None

# --- UI ---
st.title("🚀 Multi-Strategy AI Dashboard")
symbol = st.sidebar.text_input("Ticker (bv. AAPL of BTC-USD)", "AAPL").upper()

df = get_data(symbol)

if df is not None and len(df) > 50:
    # 1. EMA 50 (Trend V2)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # 2. RSI 14 (Trend V2 Filter)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # 3. ATR 10 (Voor UT Bot)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(10).mean()
    
    # LAATSTE WAARDEN
    last = df.iloc[-1]
    close = float(last['Close'])
    ema = float(last['EMA_50'])
    rsi = float(last['RSI_14'])
    atr = float(last['ATR'])
    
    # --- STRATEGIE BEREKENINGEN ---
    
    # A. Trend V2
    trend_status = "BULLISH 🟢" if close > ema and rsi > 50 else "BEARISH 🔴"
    
    # B. SST Neural Score (Momentum)
    ret_5d = df['Close'].pct_change(5).iloc[-1]
    sst_score = max(5, min(98, int(68 + (ret_5d * 160))))
    
    # C. UT Bot (Trailing Stop simulatie)
    # We kijken of de prijs boven de High minus ATR van gisteren zit
    ut_signal = "BUY ACTIVE" if close > (df['High'].iloc[-2] - (1.0 * atr)) else "SELL / WAIT"
    
    # D. S/R Targets (20-daagse High/Low)
    res_target = df['High'].rolling(20).max().iloc[-1]
    sup_floor = df['Low'].rolling(20).min().iloc[-1]

    # --- DASHBOARD LAYOUT ---
    
    # Overall Score berekening
    total_score = (sst_score + (100 if "BULLISH" in trend_status else 0) + (100 if "BUY" in ut_signal else 0)) / 3
    
    col_score, col_text = st.columns([1, 2])
    with col_score:
        st.metric("OVERALL METHOD SCORE", f"{round(total_score, 1)}%", delta=f"{sst_score}% Momentum")
    with col_text:
        st.subheader(f"Analyse resultaat voor {symbol}")
        st.write(f"Het systeem geeft een score van **{round(total_score, 1)}%**. De UT Bot staat op **{ut_signal}**.")

    st.divider()

    # De 4 Vakken
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("SST Neural")
        st.write(f"AI Score: {sst_score}%")
        st.progress(sst_score / 100)
    with c2:
        st.subheader("Trend V2")
        st.write(f"Status: {trend_status}")
        st.write(f"RSI: {round(rsi, 2)}")
    with c3:
        st.subheader("UT Bot")
        st.write(f"Signaal: {ut_signal}")
    with c4:
        st.subheader("S/R Levels")
        st.write(f"Target: {round(res_target, 2)}")
        st.write(f"Floor: {round(sup_floor, 2)}")

    # GRAFIEK
    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prijs"
    )])
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_50'], line=dict(color='yellow', width=1), name="EMA 50"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=550)
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.info("Voer een ticker in om de analyse te starten.")
