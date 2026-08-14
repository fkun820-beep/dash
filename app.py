import yfinance as yf
import pandas as pd
import streamlit as st
from datetime 
import datetime, timedelta 
import plotly.graph_objects as go 
from plotly.subplots 
import make_subplots 
import io

# Seitenkonfiguration
st.set_page_config(
    page_title="📈 Börsenübersicht",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für bessere Optik
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stock-up {
        color: #22c55e;
        font-weight: bold;
    }
    .stock-down {
        color: #ef4444;
        font-weight: bold;
    }
    .ticker-symbol {
        font-weight: bold;
        color: #1e40af;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Cache für 30 Minuten
@st.cache_data(ttl=1800)
def fetch_stock_data(tickers_tuple, start_date, end_date):
    """Holt die Börsendaten für alle Ticker."""
    tickers = list(tickers_tuple)
    data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        try:
            status_text.text(f"Lade Daten für {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Aktueller Preis
            price = stock.fast_info.last_price
            
            # Historische Daten
            hist = stock.history(start=start_date, end=end_date)
            
            if len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
                
                # Veränderungen berechnen
                changes = {}
                periods = {
                    "1 Tag": 2,
                    "1 Woche": 8,
                    "1 Monat": 32,
                    "3 Monate": 95,
                    "1 Jahr": 370,
                    "5 Jahre": 1830
                }
                
                for period_name, days in periods.items():
                    hist_period = stock.history(
                        start=datetime.now() - timedelta(days=days),
                        end=datetime.now()
                    )
                    if len(hist_period) > 1:
                        changes[period_name] = (
                            (hist_period['Close'].iloc[-1] / hist_period['Close'].iloc[0] - 1) * 100
                        )
                    else:
                        changes[period_name] = None
                
                data.append({
                    "Ticker": ticker,
                    "Name": stock.info.get('longName', ticker),
                    "Aktueller Preis": current_price,
                    "Währung": stock.info.get('currency', 'USD'),
                    **changes,
                    "52W Hoch": hist['High'].tail(365).max(),
                    "52W Tief": hist['Low'].tail(365).min(),
                    "Durchschn. Volumen": hist['Volume'].tail(30).mean()
                })
            else:
                st.warning(f"Keine Daten für {ticker} gefunden")
                
        except Exception as e:
            st.error(f"Fehler bei {ticker}: {str(e)}")
            data.append({
                "Ticker": ticker,
                "Name": ticker,
                "Aktueller Preis": None,
                "Währung": None,
                "1 Tag": None, "1 Woche": None, "1 Monat": None,
                "3 Monate": None, "1 Jahr": None, "5 Jahre": None,
                "52W Hoch": None, "52W Tief": None,
                "Durchschn. Volumen": None
            })
        
        progress_bar.progress((i + 1) / len(tickers))
    
    status_text.empty()
    progress_bar.empty()
    
    return pd.DataFrame(data)

def create_stock_chart(ticker, period="1y"):
    """Erstellt einen interaktiven Chart für einen Ticker."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    
    fig = go.Figure()
    
    # Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name='OHLC'
    ))
    
    # Gleitender Durchschnitt
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()
    
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=hist['MA20'],
        name='MA20',
        line=dict(color='orange', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=hist['MA50'],
        name='MA50',
        line=dict(color='blue', width=1)
    ))
    
    fig.update_layout(
        title=f"{ticker} - {period.upper()}",
        xaxis_title="Datum",
        yaxis_title="Preis",
        height=400,
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

# Header
st.markdown('<div class="main-header"><h1>📈 Tägliche Börsenübersicht</h1><p>Automatische Aktualisierung alle 30 Minuten</p></div>', 
            unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    # Ticker-Eingabe
    default_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",  # US-Aktien
        "^GDAXI", "^GSPC", "^IXIC",  # Indizes
        "VWRL.AS", "IWDA.AS", "EQQQ.DE", "VUSA.AS",  # ETFs
        "SIE.DE", "SAP.DE", "ALV.DE",  # Deutsche Aktien
        "BTC-USD", "ETH-USD",  # Krypto
        "GC=F", "CL=F"  # Rohstoffe
    ]
    
    tickers_text = st.text_area(
        "Ticker-Symbole (eine pro Zeile):",
        value="\n".join(default_tickers),
        height=300
    )
    
    tickers = [t.strip() for t in tickers_text.split("\n") if t.strip()]
    
    # Zeitraum für Datenabruf
    data_range = st.selectbox(
        "Datenzeitraum:",
        ["1 Monat", "3 Monate", "6 Monate", "1 Jahr", "5 Jahre"],
        index=3
    )
    
    range_days = {
        "1 Monat": 30,
        "3 Monate": 90,
        "6 Monate": 180,
        "1 Jahr": 365,
        "5 Jahre": 1825
    }
    
    st.divider()
    
    # Auto-Refresh
    auto_refresh = st.checkbox("Automatische Aktualisierung", value=True)
    if auto_refresh:
        st.info("Daten werden alle 30 Minuten aktualisiert")
    
    st.divider()
    
    # Export-Optionen
    st.download_button(
        label="📥 CSV exportieren",
        data="",  # Wird später gefüllt
        file_name="boersenkurse.csv",
        mime="text/csv",
        disabled=True  # Aktivieren nach Datengenerierung
    )
    
    st.markdown("---")
    st.caption(f"Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# Hauptbereich
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Anzahl der Ticker", len(tickers)) with col2:
    st.metric("Datenzeitraum", data_range) with col3:
    st.metric("Letzte Aktualisierung", datetime.now().strftime("%H:%M"))

st.divider()

# Daten laden
start_date = datetime.now() - timedelta(days=range_days[data_range])
end_date = datetime.now()

try:
    df = fetch_stock_data(tuple(tickers), start_date, end_date)
    
    # Tabelle anzeigen
    st.subheader("📊 Kursübersicht")
    
    # Formatierung
    def style_negative_positive(v, props=''):
        if isinstance(v, (int, float)):
            if v > 0:
                return 'color: #22c55e; font-weight: bold;'
            elif v < 0:
                return 'color: #ef4444; font-weight: bold;'
        return ''
    
    # Spalten formatieren
    formatted_df = df.copy()
    
    # Prozent-Spalten identifizieren
    pct_columns = ["1 Tag", "1 Woche", "1 Monat", "3 Monate", "1 Jahr", "5 Jahre"]
    price_columns = ["Aktueller Preis", "52W Hoch", "52W Tief"]
    
    # Styling anwenden
    styled_df = formatted_df.style
    styled_df = styled_df.applymap(style_negative_positive, subset=pct_columns)
    
    # Spaltenüberschriften
    column_config = {
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Name": st.column_config.TextColumn("Name", width="medium"),
        "Aktueller Preis": st.column_config.NumberColumn("Aktueller Preis", format="%.2f"),
        "1 Tag": st.column_config.NumberColumn("1 Tag %", format="%.2f%%"),
        "1 Woche": st.column_config.NumberColumn("1 Woche %", format="%.2f%%"),
        "1 Monat": st.column_config.NumberColumn("1 Monat %", format="%.2f%%"),
        "3 Monate": st.column_config.NumberColumn("3 Monate %", format="%.2f%%"),
        "1 Jahr": st.column_config.NumberColumn("1 Jahr %", format="%.2f%%"),
        "5 Jahre": st.column_config.NumberColumn("5 Jahre %", format="%.2f%%"),
        "52W Hoch": st.column_config.NumberColumn("52W Hoch", format="%.2f"),
        "52W Tief": st.column_config.NumberColumn("52W Tief", format="%.2f"),
        "Durchschn. Volumen": st.column_config.NumberColumn("Ø Volumen", format="%.0f")
    }
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config=column_config,
        hide_index=True,
        height=500
    )
    
    # CSV-Export aktivieren
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="📥 Aktuelle Daten als CSV herunterladen",
        data=csv_data,
        file_name=f"boersenkurse_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Charts
    st.divider()
    st.subheader("📈 Kurscharts")
    
    # Ticker für Chart auswählen
    chart_col1, chart_col2 = st.columns([1, 2])
    with chart_col1:
        selected_ticker = st.selectbox(
            "Ticker für Chart auswählen:",
            options=tickers,
            key="chart_ticker"
        )
    
    with chart_col2:
        chart_period = st.radio(
            "Zeitraum:",
            ["1mo", "3mo", "6mo", "1y", "5y"],
            horizontal=True,
            key="chart_period"
        )
    
    try:
        fig = create_stock_chart(selected_ticker, chart_period)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart kann nicht erstellt werden: {e}")
    
    # Performance-Übersicht
    st.divider()
    st.subheader("🏆 Performance-Ranking")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Performer (1 Woche)**")
        if '1 Woche' in df.columns:
            top_performers = df.nlargest(5, '1 Woche')[['Ticker', '1 Woche']]
            st.dataframe(
                top_performers.style.applymap(style_negative_positive, subset=['1 Woche']),
                hide_index=True,
                use_container_width=True
            )
    
    with col2:
        st.markdown("**Schlechteste Performer (1 Woche)**")
        if '1 Woche' in df.columns:
            worst_performers = df.nsmallest(5, '1 Woche')[['Ticker', '1 Woche']]
            st.dataframe(
                worst_performers.style.applymap(style_negative_positive, subset=['1 Woche']),
                hide_index=True,
                use_container_width=True
            )
    
    # Statistiken
    st.divider()
    st.subheader("📊 Portfolio-Statistiken")
    
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        avg_day = df['1 Tag'].mean(skipna=True)
        st.metric("Ø Tagesperformance", f"{avg_day:.2f}%" if not pd.isna(avg_day) else "N/A")
    
    with stat_col2:
        avg_week = df['1 Woche'].mean(skipna=True)
        st.metric("Ø Wochenperformance", f"{avg_week:.2f}%" if not pd.isna(avg_week) else "N/A")
    
    with stat_col3:
        avg_year = df['1 Jahr'].mean(skipna=True)
        st.metric("Ø Jahresperformance", f"{avg_year:.2f}%" if not pd.isna(avg_year) else "N/A")
    
    with stat_col4:
        winners = (df['1 Tag'] > 0).sum()
        losers = (df['1 Tag'] < 0).sum()
        st.metric("Gewinner/Verlierer", f"{winners}/{losers}")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
    st.info("Bitte überprüfe deine Ticker-Symbole und Internetverbindung.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>📊 Tägliche Börsenübersicht | Aktualisiert alle 30 Minuten</p>
        <p>Datenquelle: Yahoo Finance | Erstellt mit Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
