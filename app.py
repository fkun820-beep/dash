import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import requests
import json

st.set_page_config(page_title="Börsenübersicht", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stock-up {
        color: #16a34a;
        font-weight: bold;
    }
    .stock-down {
        color: #dc2626;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📈 Börsenübersicht</h1><p>Tägliche Aktualisierung aller wichtigen Kennzahlen</p></div>', unsafe_allow_html=True)

# ISIN zu Yahoo Ticker Konvertierung
@st.cache_data(ttl=3600)
def isin_to_ticker(isin):
    """Konvertiert ISIN zu Yahoo Finance Ticker."""
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={isin}&quotesCount=1&newsCount=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data.get('quotes'):
            return data['quotes'][0]['symbol']
    except:
        pass
    return None

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    # Eingabemodus wählen
    input_mode = st.radio(
        "Eingabemodus:",
        ["Ticker-Symbole", "ISIN-Nummern"],
        help="Wähle zwischen Yahoo-Ticker-Symbolen (z.B. AAPL) oder ISIN-Nummern (z.B. US0378331005)"
    )
    
    if input_mode == "Ticker-Symbole":
        default_input = """AAPL
MSFT
GOOGL
AMZN
TSLA
^GDAXI
^GSPC
^IXIC
VWRL.AS
IWDA.AS
EQQQ.DE
VUSA.AS
SIE.DE
SAP.DE
ALV.DE
BTC-USD
ETH-USD
GC=F
CL=F"""
        st.info("💡 Tipp: Für deutsche Aktien .DE anhängen (z.B. SIE.DE)")
    else:
        default_input = """US0378331005
US5949181045
US02079K3059
US0231351067
US88160R1014
DE0008469008
DE0007164600
DE0008404005
IE00B3RBWM25
IE00B4L5Y983
DE000A1JXU90
DE000ETFL508
US78462F1030
US92826C8394
US0231351067"""
        st.info("💡 ISIN-Nummern werden automatisch in Yahoo-Ticker umgewandelt")
    
    user_input = st.text_area(
        "Wertpapiere (eine pro Zeile):",
        value=default_input,
        height=300
    )
    
    input_list = [x.strip() for x in user_input.split("\n") if x.strip()]
    
    st.divider()
    st.subheader("📊 Anzeigeoptionen")
    show_charts = st.checkbox("Charts anzeigen", value=False)
    show_ranking = st.checkbox("Performance-Ranking", value=True)
    
    st.divider()
    st.caption(f"🕐 Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# ISIN-Konvertierung
if input_mode == "ISIN-Nummern":
    with st.spinner("Konvertiere ISIN zu Ticker..."):
        tickers = []
        isin_mapping = {}
        progress_bar = st.progress(0)
        
        for i, isin in enumerate(input_list):
            ticker = isin_to_ticker(isin)
            if ticker:
                tickers.append(ticker)
                isin_mapping[ticker] = isin
            else:
                tickers.append(isin)  # Falls Konvertierung fehlschlägt, ISIN direkt versuchen
            progress_bar.progress((i + 1) / len(input_list))
        
        progress_bar.empty()
        
    if len(isin_mapping) > 0:
        st.success(f"✅ {len(isin_mapping)} ISIN-Nummern erfolgreich konvertiert")
        if len(isin_mapping) < len(input_list):
            st.warning(f"⚠️ {len(input_list) - len(isin_mapping)} ISINs konnten nicht konvertiert werden")
else:
    tickers = input_list

# Daten laden
@st.cache_data(ttl=1800)
def load_stock_data(tickers_list):
    data = []
    
    for ticker in tickers_list:
        try:
            stock = yf.Ticker(ticker)
            hist_5y = stock.history(period="5y")
            hist_1y = stock.history(period="1y")
            hist_1mo = stock.history(period="1mo")
            hist_1w = stock.history(period="5d")
            
            if len(hist_5y) > 0:
                current_price = hist_5y['Close'].iloc[-1]
                
                # 5 Jahre Hoch und Tief
                high_5y = hist_5y['High'].max()
                low_5y = hist_5y['Low'].min()
                
                # Prozentuale Veränderungen
                change_1w = (current_price / hist_1w['Close'].iloc[0] - 1) * 100 if len(hist_1w) > 1 else None
                change_1mo = (current_price / hist_1mo['Close'].iloc[0] - 1) * 100 if len(hist_1mo) > 1 else None
                change_1y = (current_price / hist_1y['Close'].iloc[0] - 1) * 100 if len(hist_1y) > 1 else None
                change_5y = (current_price / hist_5y['Close'].iloc[0] - 1) * 100 if len(hist_5y) > 1 else None
                
                # 5J Hoch-Tief Differenz
                high_low_diff = ((high_5y - low_5y) / high_5y) * 100 if high_5y > 0 else None
                
                data.append({
                    "Ticker": ticker,
                    "Name": stock.info.get('longName', ticker)[:30],
                    "1 Woche %": round(change_1w, 2) if change_1w is not None else None,
                    "1 Monat %": round(change_1mo, 2) if change_1mo is not None else None,
                    "1 Jahr %": round(change_1y, 2) if change_1y is not None else None,
                    "5 Jahre %": round(change_5y, 2) if change_5y is not None else None,
                    "5J Hoch": round(high_5y, 2),
                    "5J Tief": round(low_5y, 2),
                    "5 J. Hoch-Tief %": round(high_low_diff, 2) if high_low_diff is not None else None,
                    "Preis": round(current_price, 2)
                })
            else:
                data.append({
                    "Ticker": ticker,
                    "Name": ticker,
                    "1 Woche %": None,
                    "1 Monat %": None,
                    "1 Jahr %": None,
                    "5 Jahre %": None,
                    "5J Hoch": None,
                    "5J Tief": None,
                    "5 J. Hoch-Tief %": None,
                    "Preis": None
                })
        except Exception as e:
            data.append({
                "Ticker": ticker,
                "Name": f"Fehler: {str(e)[:20]}",
                "1 Woche %": None,
                "1 Monat %": None,
                "1 Jahr %": None,
                "5 Jahre %": None,
                "5J Hoch": None,
                "5J Tief": None,
                "5 J. Hoch-Tief %": None,
                "Preis": None
            })
    
    return pd.DataFrame(data)

# Hauptbereich
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Anzahl Wertpapiere", len(tickers))
with col2:
    st.metric("Datenquelle", "Yahoo Finance")
with col3:
    st.metric("Aktualisierung", "Alle 30 Min")

st.divider()

try:
    with st.spinner("Lade Börsendaten..."):
        df = load_stock_data(tuple(tickers))
    
    # Spalten neu ordnen - Preis nach ganz rechts
    column_order = ["Ticker", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", 
                   "5 Jahre %", "5J Hoch", "5J Tief", "5 J. Hoch-Tief %", "Preis"]
    df = df[column_order]
    
    # Formatierung
    def color_negative_red(val):
        if isinstance(val, (int, float)):
            if val < 0:
                return 'color: #dc2626; font-weight: bold;'
            elif val > 0:
                return 'color: #16a34a; font-weight: bold;'
        return ''
    
    # Prozent-Spalten
    pct_columns = ["1 Woche %", "1 Monat %", "1 Jahr %", "5 Jahre %", "5 J. Hoch-Tief %"]
    
    # Styling anwenden
    styled_df = df.style.applymap(color_negative_red, subset=pct_columns)
    
    # Spaltenkonfiguration
    column_config = {
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Name": st.column_config.TextColumn("Name", width="medium"),
        "1 Woche %": st.column_config.NumberColumn("1 Woche %", format="%.2f%%"),
        "1 Monat %": st.column_config.NumberColumn("1 Monat %", format="%.2f%%"),
        "1 Jahr %": st.column_config.NumberColumn("1 Jahr %", format="%.2f%%"),
        "5 Jahre %": st.column_config.NumberColumn("5 Jahre %", format="%.2f%%"),
        "5J Hoch": st.column_config.NumberColumn("5J Hoch", format="%.2f"),
        "5J Tief": st.column_config.NumberColumn("5J Tief", format="%.2f"),
        "5 J. Hoch-Tief %": st.column_config.NumberColumn("5 J. Hoch-Tief %", format="%.2f%%"),
        "Preis": st.column_config.NumberColumn("Preis", format="%.2f")
    }
    
    st.subheader("📊 Kursübersicht")
    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config=column_config,
        hide_index=True,
        height=600
    )
    
    # CSV Download
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
    st.download_button(
        label="📥 CSV herunterladen",
        data=csv_buffer.getvalue(),
        file_name=f"boersenkurse_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Performance-Ranking
    if show_ranking:
        st.divider()
        st.subheader("🏆 Performance-Ranking (1 Woche)")
        
        rank_col1, rank_col2 = st.columns(2)
        
        with rank_col1:
            st.markdown("**Top 5 Performer**")
            top5 = df.nlargest(5, '1 Woche %')[['Ticker', '1 Woche %', '1 Jahr %']]
            st.dataframe(
                top5.style.applymap(color_negative_red, subset=['1 Woche %', '1 Jahr %']),
                hide_index=True,
                use_container_width=True
            )
        
        with rank_col2:
            st.markdown("**Flop 5 Performer**")
            bottom5 = df.nsmallest(5, '1 Woche %')[['Ticker', '1 Woche %', '1 Jahr %']]
            st.dataframe(
                bottom5.style.applymap(color_negative_red, subset=['1 Woche %', '1 Jahr %']),
                hide_index=True,
                use_container_width=True
            )
    
    # Charts
    if show_charts:
        st.divider()
        st.subheader("📈 Kurschart")
        
        chart_col1, chart_col2 = st.columns([1, 3])
        with chart_col1:
            selected_ticker = st.selectbox("Ticker:", options=df['Ticker'].tolist())
        with chart_col2:
            chart_period = st.radio("Zeitraum:", ["1mo", "3mo", "6mo", "1y", "5y"], horizontal=True)
        
        try:
            stock = yf.Ticker(selected_ticker)
            hist = stock.history(period=chart_period)
            
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close'))
            fig.update_layout(
                title=f"{selected_ticker} - {chart_period.upper()}",
                xaxis_title="Datum",
                yaxis_title="Preis",
                height=400,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Chart konnte nicht erstellt werden: {e}")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
    st.info("Bitte überprüfe deine Eingaben. Ticker-Symbole müssen im Yahoo-Format sein.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>📊 Börsenübersicht | Datenquelle: Yahoo Finance | Erstellt mit Streamlit</p>
        <p>💡 Tipp: Du kannst sowohl Ticker-Symbole als auch ISIN-Nummern verwenden</p>
    </div>
    """,
    unsafe_allow_html=True
)
