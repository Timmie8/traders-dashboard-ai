import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Ultimate Trader Dashboard", layout="wide")

# Veilig de key ophalen uit Streamlit Secrets
if "FINNHUB_KEY" in st.secrets:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
else:
    st.error("❌ FOUT: FINNHUB_KEY niet gevonden in Secrets!")
    st.info("Ga naar Streamlit Cloud > Settings > Secrets en voeg toe: FINNHUB_KEY = 'jouw_key'")
    st.stop()

# --- DATA FUNCTIE MET DEBUGGING ---
def get_data(symbol):
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=200)).timestamp())
    
    # We gebruiken de officiële Finnhub URL voor candles
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={start}&to={end}&token={FINNHUB_KEY}"
    
    try:
        res = requests.get(url)
        data = res.json()
        
        # Als Finnhub een fout geeft, tonen we die op het scherm
        if data.get('s') != 'ok':
            st.warning(f"Finnhub melding voor {symbol}: {data.get('s', 'Geen respons')}")
            if 'error' in data:
                st.error(f"Detail: {data['error']}")
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'Date': pd.to_datetime(data['t'], unit='s'),
            'Open': data['o'], 
            'High': data['h'],
            'Low': data['l'], 
            'Close': data['c'], 
            'Volume': data['v']
        })
        return df
    except Exception as e:
        st.error(f"Verbindingsfout: {e}")
        return pd.DataFrame()

# --- STRATEGIE LOGICA (VERTALING PINE SCRIPTS) ---
def calc_all_strategies(df):
    # Kopie maken om waarschuwingen te voorkomen
    df = df.copy()
    
    # 1. Trend & Momentum (Code 2 & 4)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    
    last_close = df['Close'].iloc[-1]
    last_ema = df['EMA_50'].iloc[-1]
    last_rsi = df['RSI_14'].iloc[-1]
    
    trend_status = "BULLISH" if last_close > last_ema and last_rsi > 50 else "BEARISH"
    
    # 2. SST Neural / Momentum Score (Code 1)
    # Berekening gebaseerd op je pct_chg logica
    df['returns'] = df['Close'].pct_change(5)
    last_ret = df['returns'].iloc[-1] if not pd.isna(df['returns'].iloc[-1]) else 0
    sst_score = max(5, min(98, int(68 + (last_ret * 160))))
    
    # 3. UT Bot Signaal (Code 3)
    df.ta.atr(length=10, append=True)
    # Simpele UT Bot logica: Prijs vs Trailing Stop
    ut_signal = "BUY ACTIVE" if last_close > (df['High'].iloc[-1] - (1.0 * df['ATRr_10'].iloc[-1])) else "SELL / WAIT"
    
    # 4. S/R Levels (Code 4)
    res_level = df['High'].rolling(20).max().iloc[-1]
    sup_level = df['Low'].rolling(20).min().iloc[-1]
    
    return trend_status, sst_score, ut_signal, res_level, sup_level, last_rsi

# --- UI DASHBOARD ---
st.title("📊 Multi-Strategy Trader Dashboard")
st.markdown("---")

# Sidebar voor input
ticker = st.sidebar.text_input("Voer Ticker in (bv. AAPL of BTCUSDT)", "AAPL").upper()

# Data ophalen
df_raw = get_data(ticker)

if not df_raw.empty:
    # Berekeningen uitvoeren
    trend, sst, ut, res, sup, rsi = calc_all_strategies(df_raw)
    
    # OVERALL SCORE VAK (HET CENTRALE PANEEL)
    # We wegen de verschillende methodes mee voor de totaalscore
    trend_points = 100 if trend == "BULLISH" else 0
    ut_points = 100 if ut == "BUY ACTIVE" else 0
    total_score = (sst + trend_points + ut_points) / 3
    
    score_col1, score_col2 = st.columns([1, 3])
    with score_col1:
        st.metric("OVERALL METHOD SCORE", f"{round(total_score, 1)}%", delta=f"{sst}% AI")
    with score_col2:
        st.subheader("Systeem Analyse")
        st.write(f"De gecombineerde score van **{round(total_score, 1)}%** is gebaseerd op de SST Neural, Trend V2 en UT Bot algoritmes.")

    st.markdown("---")

    # VIER INDIVIDUELE VAKKEN
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.subheader("SST Neural")
        st.write(f"Momentum Score: **{sst}%**")
        st.progress(sst / 100)
        
    with c2:
        st.subheader("Trend V2")
        color = "green" if trend == "BULLISH" else "red"
        st.markdown(f"Status: **:{color}[{trend}]**")
        st.write(f"RSI (14): {round(rsi, 2)}")

    with c3:
        st.subheader("UT Bot MTF")
        ut_color = "green" if "BUY" in ut else "red"
        st.markdown(f"Signaal: **:{ut_color}[{ut}]**")

    with c4:
        st.subheader("S/R & Targets")
        st.write(f"Resistance: {round(res, 2)}")
        st.write(f"Support: {round(sup, 2)}")

    # CHART
    st.markdown("### Prijsgrafiek")
    fig = go.Figure(data=[go.Candlestick(
        x=df_raw['Date'],
        open=df_raw['Open'],
        high=df_raw['High'],
        low=df_raw['Low'],
        close=df_raw['Close'],
        name="Candlesticks"
    )])
    
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("💡 Tip: Gebruik voor crypto tickers zoals 'BINANCE:BTCUSDT' of 'AAPL' voor aandelen.")
