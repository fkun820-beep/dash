import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import requests
import json
import plotly.graph_objects as go

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
    .sub-header {
        text-align: center;
        padding: 0.75rem;
        background: linear-gradient(90deg, #059669 0%, #10b981 100%);
        color: white;
        border-radius: 8px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📈 Börsenübersicht</h1><p>Tägliche Aktualisierung aller wichtigen Kennzahlen</p></div>', unsafe_allow_html=True)

# ISIN zu Yahoo Ticker Konvertierung
@st.cache_data(ttl=3600)
def isin_to_ticker(isin):
    """Konvertiert ISIN zu Yahoo Finance Ticker."""
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={isin}&quotesCount=5&newsCount=0"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get('quotes'):
            return data['quotes'][0]['symbol']
    except:
        pass
    return None

# Bekannte ISIN-Zuordnungen
KNOWN_ISINS = {
    "US0378331005": "AAPL",
    "US5949181045": "MSFT",
    "US02079K3059": "GOOGL",
    "US0231351067": "AMZN",
    "US88160R1014": "TSLA",
    "DE0008469008": "SIE.DE",
    "DE0007164600": "SAP.DE",
    "DE0008404005": "ALV.DE",
    "IE00B3RBWM25": "VWRL.AS",
    "IE00B4L5Y983": "IWDA.AS",
    "DE000A1JXU90": "EQQQ.DE",
    "DE000ETFL508": "VUSA.DE",
    "US78462F1030": "SPY",
    "US92826C8394": "VTI",
}

# Ticker zu ISIN Mapping
TICKER_TO_ISIN = {v: k for k, v in KNOWN_ISINS.items()}

# Globale Top-Performer abrufen
@st.cache_data(ttl=3600)
def get_global_top_performers(limit=15):
    """Holt die globalen Top-Performer aus Yahoo Finance."""
    try:
        # Yahoo Finance Screener API für Top-Performer
        url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
        params = {
            "scrIds": "top_mutual_funds",  # Top Fonds
            "count": limit,
            "quoteType": "ETF"
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('finance', {}).get('result'):
            quotes = data['finance']['result'][0].get('quotes', [])
            return quotes
    except:
        pass
    
    # Fallback: Bekannte Top-ETFs und Fonds
    fallback_tickers = [
        "SPY", "IVV", "VTI", "VOO", "QQQ",
        "VUG", "VGT", "XLK", "SMH", "SOXX",
        "ARKK", "ICLN", "TAN", "URA", "XLE",
        "XLF", "XLV", "XLY", "XLP", "XLI"
    ]
    return fallback_tickers

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    input_mode = st.radio(
        "Eingabemodus:",
        ["Ticker-Symbole", "ISIN-Nummern"],
        help="Wähle zwischen Yahoo-Ticker-Symbolen oder ISIN-Nummern"
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
        st.info("💡 Tipp: Für deutsche Aktien .DE anhängen")
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
DE000ETFL508"""
        st.info("💡 ISIN-Nummern werden in Yahoo-Ticker umgewandelt")
    
    user_input = st.text_area(
        "Wertpapiere (eine pro Zeile):",
        value=default_input,
        height=300,
        key="input_field"
    )
    
    input_list = [x.strip() for x in user_input.split("\n") if x.strip()]
    
    if st.button("🔄 Daten aktualisieren", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.subheader("📊 Anzeigeoptionen")
    show_charts = st.checkbox("Charts anzeigen", value=False)
    show_ranking = st.checkbox("Performance-Ranking", value=True)
    show_top15 = st.checkbox("Globale Top 15 anzeigen", value=True)
    show_debug = st.checkbox("Debug-Informationen", value=False)
    
    st.divider()
    st.caption(f"🕐 Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# ISIN und Ticker Mapping
isin_ticker_map = {}
ticker_isin_map = {}

if input_mode == "ISIN-Nummern":
    tickers = []
    conversion_log = []
    
    with st.spinner("Konvertiere ISIN zu Ticker..."):
        for isin in input_list:
            isin = isin.strip().upper()
            
            if isin in KNOWN_ISINS:
                ticker = KNOWN_ISINS[isin]
                tickers.append(ticker)
                isin_ticker_map[ticker] = isin
                ticker_isin_map[ticker] = isin
                conversion_log.append(f"✅ {isin} → {ticker} (bekannt)")
            else:
                ticker = isin_to_ticker(isin)
                if ticker:
                    tickers.append(ticker)
                    isin_ticker_map[ticker] = isin
                    ticker_isin_map[ticker] = isin
                    conversion_log.append(f"✅ {isin} → {ticker}")
                else:
                    tickers.append(isin)
                    isin_ticker_map[isin] = isin
                    ticker_isin_map[isin] = isin
                    conversion_log.append(f"⚠️ {isin} → nicht konvertiert, versuche direkt")
else:
    tickers = input_list
    for ticker in tickers:
        if ticker in TICKER_TO_ISIN:
            ticker_isin_map[ticker] = TICKER_TO_ISIN[ticker]
            isin_ticker_map[ticker] = ticker
        else:
            ticker_isin_map[ticker] = ""
            isin_ticker_map[ticker] = ticker

# Debug-Anzeige
if show_debug:
    st.subheader("🔍 Debug-Informationen")
    if input_mode == "ISIN-Nummern":
        for log in conversion_log:
            st.text(log)
    else:
        for ticker in tickers:
            isin = ticker_isin_map.get(ticker, "Nicht gefunden")
            st.text(f"{ticker} → ISIN: {isin}")

# Daten laden
@st.cache_data(ttl=1800)
def load_stock_data(tickers_list, ticker_isin_dict):
    data = []
    
    for ticker in tickers_list:
        try:
            stock = yf.Ticker(ticker)
            hist_5y = stock.history(period="5y")
            hist_1y = stock.history(period="1y")
            hist_1mo = stock.history(period="1mo")
            hist_1w = stock.history(period="5d")
            
            if len(hist_5y) > 0 and len(hist_1y) > 0:
                current_price = hist_5y['Close'].iloc[-1]
                
                high_5y = hist_5y['High'].max()
                low_5y = hist_5y['Low'].min()
                
                change_1w = (current_price / hist_1w['Close'].iloc[0] - 1) * 100 if len(hist_1w) > 1 else None
                change_1mo = (current_price / hist_1mo['Close'].iloc[0] - 1) * 100 if len(hist_1mo) > 1 else None
                change_1y = (current_price / hist_1y['Close'].iloc[0] - 1) * 100 if len(hist_1y) > 1 else None
                change_5y = (current_price / hist_5y['Close'].iloc[0] - 1) * 100 if len(hist_5y) > 1 else None
                
                high_low_diff = ((high_5y - low_5y) / low_5y) * 100 if low_5y > 0 else None
                
                isin = ticker_isin_dict.get(ticker, "")
                
                # Fallback: Versuche ISIN von Yahoo zu bekommen
                if not isin:
                    try:
                        info = stock.info
                        if info and 'isin' in info:
                            isin = info['isin']
                    except:
                        pass
                
                data.append({
                    "ISIN": isin,
                    "Name": stock.info.get('longName', ticker)[:40] if stock.info else ticker,
                    "Ticker": ticker,
                    "1 Woche %": round(change_1w, 2) if change_1w is not None else None,
                    "1 Monat %": round(change_1mo, 2) if change_1mo is not None else None,
                    "1 Jahr %": round(change_1y, 2) if change_1y is not None else None,
                    "5 Jahre %": round(change_5y, 2) if change_5y is not None else None,
                    "5J Tief": round(low_5y, 2),
                    "5J Hoch": round(high_5y, 2),
                    "5 J. Hoch-Tief %": round(high_low_diff, 2) if high_low_diff is not None else None,
                    "Preis": round(current_price, 2)
                })
            else:
                raise ValueError(f"Keine Daten für {ticker}")
                
        except Exception as e:
            isin = ticker_isin_dict.get(ticker, "")
            data.append({
                "ISIN": isin,
                "Name": f"❌ {str(e)[:30]}",
                "Ticker": ticker,
                "1 Woche %": None,
                "1 Monat %": None,
                "1 Jahr %": None,
                "5 Jahre %": None,
                "5J Tief": None,
                "5J Hoch": None,
                "5 J. Hoch-Tief %": None,
                "Preis": None
            })
    
    return pd.DataFrame(data)

# Globale Top-Performer laden
@st.cache_data(ttl=3600)
def load_global_top_performers():
    """Lädt die globalen Top-Performer mit Performance-Daten."""
    top_tickers = get_global_top_performers(15)
    
    data = []
    for ticker in top_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist_1y = stock.history(period="1y")
            
            if len(hist_1y) > 1:
                current_price = hist_1y['Close'].iloc[-1]
                change_1y = (current_price / hist_1y['Close'].iloc[0] - 1) * 100
                
                # Weitere Perioden
                hist_1w = stock.history(period="5d")
                hist_1mo = stock.history(period="1mo")
                hist_5y = stock.history(period="5y")
                
                change_1w = (current_price / hist_1w['Close'].iloc[0] - 1) * 100 if len(hist_1w) > 1 else None
                change_1mo = (current_price / hist_1mo['Close'].iloc[0] - 1) * 100 if len(hist_1mo) > 1 else None
                change_5y = (current_price / hist_5y['Close'].iloc[0] - 1) * 100 if len(hist_5y) > 1 else None
                
                isin = ""
                try:
                    info = stock.info
                    if info and 'isin' in info:
                        isin = info['isin']
                except:
                    pass
                
                data.append({
                    "ISIN": isin,
                    "Name": stock.info.get('longName', ticker)[:40] if stock.info else ticker,
                    "Ticker": ticker,
                    "1 Woche %": round(change_1w, 2) if change_1w is not None else None,
                    "1 Monat %": round(change_1mo, 2) if change_1mo is not None else None,
                    "1 Jahr %": round(change_1y, 2),
                    "5 Jahre %": round(change_5y, 2) if change_5y is not None else None,
                    "Preis": round(current_price, 2)
                })
        except:
            continue
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.nlargest(15, '1 Jahr %')
    return df

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
        df = load_stock_data(tuple(tickers), ticker_isin_map)
    
    # Spalten neu ordnen - ISIN ganz links
    column_order = ["ISIN", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", 
                   "5 Jahre %", "5J Tief", "5J Hoch", "5 J. Hoch-Tief %", "Preis"]
    
    df_display = df[column_order].copy()
    
    # Formatierung
    def color_negative_red(val):
        if isinstance(val, (int, float)):
            if val < 0:
                return 'color: #dc2626; font-weight: bold;'
            elif val > 0:
                return 'color: #16a34a; font-weight: bold;'
        return ''
    
    pct_columns = ["1 Woche %", "1 Monat %", "1 Jahr %", "5 Jahre %", "5 J. Hoch-Tief %"]
    
    styled_df = df_display.style.map(color_negative_red, subset=pct_columns)
    
    column_config = {
        "ISIN": st.column_config.TextColumn("ISIN", width="medium"),
        "Name": st.column_config.TextColumn("Name", width="large"),
        "1 Woche %": st.column_config.NumberColumn("1 Woche %", format="%.2f%%"),
        "1 Monat %": st.column_config.NumberColumn("1 Monat %", format="%.2f%%"),
        "1 Jahr %": st.column_config.NumberColumn("1 Jahr %", format="%.2f%%"),
        "5 Jahre %": st.column_config.NumberColumn("5 Jahre %", format="%.2f%%"),
        "5J Tief": st.column_config.NumberColumn("5J Tief", format="%.2f"),
        "5J Hoch": st.column_config.NumberColumn("5J Hoch", format="%.2f"),
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
    
    # Globale Top 15 profitabelste Wertpapiere
    if show_top15:
        st.divider()
        st.markdown('<div class="sub-header"><h2>🌍 Globale Top 15 profitabelste Wertpapiere (nach 1 Jahr %)</h2></div>', 
                   unsafe_allow_html=True)
        
        with st.spinner("Lade globale Top-Performer..."):
            top15_df = load_global_top_performers()
        
        if not top15_df.empty:
            # Prüfen welche Ticker in der Haupttabelle sind
            main_tickers = set(df['Ticker'].tolist())
            
            def highlight_if_in_main(val, row):
                if row['Ticker'] in main_tickers:
                    return ['color: #16a34a; font-weight: bold;' if col == 'Name' else '' for col in row.index]
                return ['' for _ in row.index]
            
            top15_styled = top15_df.style.map(color_negative_red, subset=['1 Woche %', '1 Monat %', '1 Jahr %', '5 Jahre %'])
            top15_styled = top15_styled.apply(highlight_if_in_main, axis=1)
            
            st.dataframe(
                top15_styled,
                use_container_width=True,
                column_config={
                    "ISIN": st.column_config.TextColumn("ISIN", width="medium"),
                    "Name": st.column_config.TextColumn("Name", width="large"),
                    "1 Woche %": st.column_config.NumberColumn("1 Woche %", format="%.2f%%"),
                    "1 Monat %": st.column_config.NumberColumn("1 Monat %", format="%.2f%%"),
                    "1 Jahr %": st.column_config.NumberColumn("1 Jahr %", format="%.2f%%"),
                    "5 Jahre %": st.column_config.NumberColumn("5 Jahre %", format="%.2f%%"),
                    "Preis": st.column_config.NumberColumn("Preis", format="%.2f")
                },
                hide_index=True,
                height=500
            )
            
            st.caption("💡 Grün markierte Namen = auch in deiner Haupttabelle vorhanden")
        else:
            st.warning("Keine globalen Top-Performer gefunden")
    
    # Performance-Ranking
    if show_ranking:
        st.divider()
        st.subheader("🏆 Performance-Ranking (1 Woche)")
        
        rank_col1, rank_col2 = st.columns(2)
        
        with rank_col1:
            st.markdown("**Top 5 Performer**")
            top5 = df.nlargest(5, '1 Woche %')[['ISIN', 'Name', '1 Woche %', '1 Jahr %']]
            st.dataframe(
                top5.style.map(color_negative_red, subset=['1 Woche %', '1 Jahr %']),
                hide_index=True,
                use_container_width=True
            )
        
        with rank_col2:
            st.markdown("**Flop 5 Performer**")
            bottom5 = df.nsmallest(5, '1 Woche %')[['ISIN', 'Name', '1 Woche %', '1 Jahr %']]
            st.dataframe(
                bottom5.style.map(color_negative_red, subset=['1 Woche %', '1 Jahr %']),
                hide_index=True,
                use_container_width=True
            )

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
    st.info("Bitte überprüfe deine Eingaben.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>📊 Börsenübersicht | Datenquelle: Yahoo Finance | Erstellt mit Streamlit</p>
        <p>💡 5 J. Hoch-Tief % = ((Hoch - Tief) / Tief) × 100</p>
        <p>🌍 Globale Top 15 = Die profitabelsten Wertpapiere aus dem gesamten Yahoo Finance Universum</p>
    </div>
    """,
    unsafe_allow_html=True
)
