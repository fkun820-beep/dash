import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Börsenübersicht", layout="wide")

st.title("📈 Tägliche Börsenübersicht")

st.sidebar.header("Einstellungen")

default_tickers = "AAPL\nMSFT\nGOOGL\nAMZN\nTSLA\n^GDAXI\n^GSPC\n^IXIC\nVWRL.AS\nIWDA.AS\nEQQQ.DE\nSIE.DE\nSAP.DE\nALV.DE\nBTC-USD\nETH-USD\nGC=F\nCL=F"

tickers_text = st.sidebar.text_area("Ticker (eine pro Zeile):", value=default_tickers, height=300)
tickers = [t.strip() for t in tickers_text.split("\n") if t.strip()]

st.sidebar.info(f"{len(tickers)} Ticker geladen")

@st.cache_data(ttl=1800)
def load_data(tickers_list):
    data = []
    for ticker in tickers_list:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if len(hist) > 1:
                current = hist['Close'].iloc[-1]
                week_ago = hist['Close'].iloc[-6] if len(hist) > 6 else hist['Close'].iloc[0]
                month_ago = hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0]
                year_ago = hist['Close'].iloc[0]
                
                data.append({
                    "Ticker": ticker,
                    "Preis": round(current, 2),
                    "1 Woche %": round((current/week_ago - 1) * 100, 2),
                    "1 Monat %": round((current/month_ago - 1) * 100, 2),
                    "1 Jahr %": round((current/year_ago - 1) * 100, 2),
                    "52W Hoch": round(hist['High'].max(), 2),
                    "52W Tief": round(hist['Low'].min(), 2)
                })
        except:
            data.append({
                "Ticker": ticker,
                "Preis": None,
                "1 Woche %": None,
                "1 Monat %": None,
                "1 Jahr %": None,
                "52W Hoch": None,
                "52W Tief": None
            })
    return pd.DataFrame(data)

try:
    df = load_data(tuple(tickers))
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False)
    st.download_button("📥 CSV herunterladen", csv, "boersenkurse.csv", "text/csv")
except Exception as e:
    st.error(f"Fehler: {e}")
