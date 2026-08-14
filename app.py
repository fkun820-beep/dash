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

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
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
    show_top_performers = st.checkbox("Top Performer anzeigen", value=True)
    
    st.divider()
    st.caption(f"🕐 Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# Feste Top-Performer-Liste (Wertzuwachs >40% in 1 Jahr)
TOP_PERFORMERS = [
    "NVDA",   # NVIDIA
    "MSTR",   # MicroStrategy
    "PLTR",   # Palantir
    "COIN",   # Coinbase
    "SMCI",   # Super Micro Computer
    "AMD",    # Advanced Micro Devices
    "AVGO",   # Broadcom
    "TSLA",   # Tesla
    "META",   # Meta Platforms
    "CRWD",   # CrowdStrike
    "HOOD",   # Robinhood
    "APP",    # AppLovin
    "VRT",    # Vertiv
    "ARM",    # Arm Holdings
    "LLY",    # Eli Lilly
    "DDOG",   # Datadog
    "NET",    # Cloudflare
    "SHOP",   # Shopify
    "UBER",   # Uber
    "ANET",   # Arista Networks
]

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
            
            if len(hist_5y) > 0 and len(hist_1y) > 0:
                current_price = hist_5y['Close'].iloc[-1]
                
                high_5y = hist_5y['High'].max()
                low_5y = hist_5y['Low'].min()
                
                change_1w = (current_price / hist_1w['Close'].iloc[0] - 1) * 100 if len(hist_1w) > 1 else None
                change_1mo = (current_price / hist_1mo['Close'].iloc[0] - 1) * 100 if len(hist_1mo) > 1 else None
                change_1y = (current_price / hist_1y['Close'].iloc[0] - 1) * 100 if len(hist_1y) > 1 else None
                change_5y = (current_price / hist_5y['Close'].iloc[0] - 1) * 100 if len(hist_5y) > 1 else None
                
                high_low_diff = ((high_5y - low_5y) / low_5y) * 100 if low_5y > 0 else None
                
                data.append({
                    "Ticker": ticker,
                    "Name": stock.info.get('longName', ticker)[:40] if stock.info else ticker,
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
            data.append({
                "Ticker": ticker,
                "Name": f"❌ {str(e)[:30]}",
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

# Hauptbereich
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Anzahl Wertpapiere", len(input_list))
with col2:
    st.metric("Datenquelle", "Yahoo Finance")
with col3:
    st.metric("Aktualisierung", "Alle 30 Min")

st.divider()

try:
    with st.spinner("Lade Börsendaten..."):
        df = load_stock_data(tuple(input_list))
    
    # Spalten neu ordnen - Ticker als erste Spalte
    column_order = ["Ticker", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", 
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
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
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
    
    # Top Performer (feste Liste)
    if show_top_performers:
        st.divider()
        st.markdown('<div class="sub-header"><h2>🚀 Top Performer (Wertzuwachs >40% in 1 Jahr)</h2></div>', 
                   unsafe_allow_html=True)
        
        with st.spinner("Lade Top-Performer..."):
            top_df = load_stock_data(tuple(TOP_PERFORMERS))
        
        if not top_df.empty:
            # Sortieren nach 1 Jahr %
            top_df_sorted = top_df.nlargest(20, '1 Jahr %')
            
            # Prüfen welche Ticker in der Haupttabelle sind
            main_tickers = set(df['Ticker'].tolist())
            
            def highlight_if_in_main(row):
                if row['Ticker'] in main_tickers:
                    return ['color: #16a34a; font-weight: bold;' if col == 'Name' else '' for col in row.index]
                return ['' for _ in row.index]
            
            # Spalten für Top-Performer
            top_columns = ["Ticker", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", "5 Jahre %", "Preis"]
            top_df_display = top_df_sorted[top_columns].copy()
            
            top_styled = top_df_display.style.map(color_negative_red, subset=['1 Woche %', '1 Monat %', '1 Jahr %', '5 Jahre %'])
            top_styled = top_styled.apply(highlight_if_in_main, axis=1)
            
            st.dataframe(
                top_styled,
                use_container_width=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
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
            st.warning("Keine Top-Performer gefunden")
    
    # Performance-Ranking
    if show_ranking:
        st.divider()
        st.subheader("🏆 Performance-Ranking (1 Woche)")
        
        rank_col1, rank_col2 = st.columns(2)
        
        with rank_col1:
            st.markdown("**Top 5 Performer**")
            top5 = df.nlargest(5, '1 Woche %')[['Ticker', 'Name', '1 Woche %', '1 Jahr %']]
            st.dataframe(
                top5.style.map(color_negative_red, subset=['1 Woche %', '1 Jahr %']),
                hide_index=True,
                use_container_width=True
            )
        
        with rank_col2:
            st.markdown("**Flop 5 Performer**")
            bottom5 = df.nsmallest(5, '1 Woche %')[['Ticker', 'Name', '1 Woche %', '1 Jahr %']]
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
        <p>🚀 Top Performer = Wertpapiere mit >40% Wertzuwachs in den letzten 12 Monaten</p>
    </div>
    """,
    unsafe_allow_html=True
)
