import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import requests
import json
import plotly.graph_objects as go

st.set_page_config(page_title="Börsenübersicht", page_icon="📈", layout="wide")

# Session State für Markierungen initialisieren
if 'marked_securities' not in st.session_state:
    st.session_state.marked_securities = set()

if 'show_marked_only' not in st.session_state:
    st.session_state.show_marked_only = False

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
    .green-name {
        color: #16a34a;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📈 Börsenübersicht</h1><p>Tägliche Aktualisierung aller wichtigen Kennzahlen</p></div>', unsafe_allow_html=True)

# ISIN zu Yahoo Ticker Konvertierung
@st.cache_data(ttl=3600)
def isin_to_ticker(isin):
    """Konvertiert ISIN zu Yahoo Finance Ticker."""
    # Bekannte ISIN-Zuordnungen
    KNOWN_ISINS = {
        "LU0203975197": "0P0000WLAC.F",  # Fidelity Funds - Global Dividend Fund
        "LU0757431068": "0P0000Y4BX.F",  # Fidelity Funds - Global Technology Fund
        "FR0010315770": "0P0000X5Z3.F",  # Fidelity Funds - France Fund
        "LU0274211480": "0P0000QA1J.F",  # Fidelity Funds - Global Focus Fund
        "IE00B1D7YP71": "0P0000WLUY.F",  # Fidelity Funds - Global Dividend Fund
        "IE00B8GKDB10": "0P0000WLUZ.F",  # Fidelity Funds - Global Technology Fund
        "LU0411078552": "0P0000QA1K.F",  # Fidelity Funds - Global Focus Fund
        "LU1900066033": "0P0000WLVA.F",  # Fidelity Funds - Global Dividend Fund
        "FR0010930644": "0P0000X5Z4.F",  # Fidelity Funds - France Fund
        "DE000A0F5UJ7": "0P0000WLVD.F",  # Fidelity Funds - Global Dividend Fund
        "US5324571083": "LLY",  # Eli Lilly
        "US0404132054": "ARWR",  # Arrowhead Pharmaceuticals
        "US67066G1040": "NVDA",  # NVIDIA
    }
    
    if isin in KNOWN_ISINS:
        return KNOWN_ISINS[isin]
    
    # Versuche Yahoo Finance Suche
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

# Feste Wertpapierliste (ISIN-Nummern)
DEFAULT_ISINS = [
    "LU0203975197",  # Fidelity Funds - Global Dividend Fund
    "LU0757431068",  # Fidelity Funds - Global Technology Fund
    "FR0010315770",  # Fidelity Funds - France Fund
    "LU0274211480",  # Fidelity Funds - Global Focus Fund
    "IE00B1D7YP71",  # Fidelity Funds - Global Dividend Fund
    "IE00B8GKDB10",  # Fidelity Funds - Global Technology Fund
    "LU0411078552",  # Fidelity Funds - Global Focus Fund
    "LU1900066033",  # Fidelity Funds - Global Dividend Fund
    "FR0010930644",  # Fidelity Funds - France Fund
    "DE000A0F5UJ7",  # Fidelity Funds - Global Dividend Fund
    "US5324571083",  # Eli Lilly
    "US0404132054",  # Arrowhead Pharmaceuticals
    "US67066G1040",  # NVIDIA
    "^GDAXI",  # DAX
]

# Feste Top-Performer-Liste
TOP_PERFORMERS = [
    "NVDA", "MSTR", "PLTR", "COIN", "SMCI",
    "AMD", "AVGO", "TSLA", "META", "CRWD",
    "HOOD", "APP", "VRT", "ARM", "LLY",
    "DDOG", "NET", "SHOP", "UBER", "ANET"
]

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    # Seiten-Navigation
    st.subheader("📑 Navigation")
    if st.button("📊 Hauptansicht", use_container_width=True):
        st.session_state.show_marked_only = False
        st.rerun()
    
    if st.button("⭐ Markierte Wertpapiere", use_container_width=True):
        st.session_state.show_marked_only = True
        st.rerun()
    
    st.divider()
    
    st.info("💡 Die feste Wertpapierliste ist im Programm integriert")
    
    # Optionale zusätzliche Ticker
    additional_input = st.text_area(
        "Zusätzliche Wertpapiere (optional, eine pro Zeile):",
        value="",
        height=150,
        key="additional_input",
        help="Hier kannst du zusätzliche Ticker oder ISIN-Nummern eingeben"
    )
    
    # Kombiniere feste Liste mit zusätzlichen Eingaben
    all_inputs = DEFAULT_ISINS.copy()
    if additional_input.strip():
        additional_list = [x.strip() for x in additional_input.split("\n") if x.strip()]
        all_inputs.extend(additional_list)
    
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
    st.caption(f"⭐ Markierte Wertpapiere: {len(st.session_state.marked_securities)}")

# ISIN zu Ticker Konvertierung für die Hauptliste
tickers = []
conversion_log = []

with st.spinner("Konvertiere ISIN zu Ticker..."):
    for item in all_inputs:
        item = item.strip()
        if not item:
            continue
            
        # Prüfe ob es ein direkter Ticker ist (nicht ISIN)
        if item.startswith("^") or "." in item or not item[:2].isalpha() or not item[2:].isdigit():
            # Ist bereits ein Ticker
            tickers.append(item)
            conversion_log.append(f"✅ {item} → {item} (direkter Ticker)")
        else:
            # Ist eine ISIN
            ticker = isin_to_ticker(item)
            if ticker:
                tickers.append(ticker)
                conversion_log.append(f"✅ {item} → {ticker}")
            else:
                # Fallback: Versuche ISIN direkt
                tickers.append(item)
                conversion_log.append(f"⚠️ {item} → nicht konvertiert, versuche direkt")

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
                
                yahoo_link = f"https://finance.yahoo.com/quote/{ticker}"
                
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
                    "Preis": round(current_price, 2),
                    "Link": yahoo_link
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
                "Preis": None,
                "Link": f"https://finance.yahoo.com/quote/{ticker}"
            })
    
    return pd.DataFrame(data)

# Formatierung
def color_negative_red(val):
    if isinstance(val, (int, float)):
        if val < 0:
            return 'color: #dc2626; font-weight: bold;'
        elif val > 0:
            return 'color: #16a34a; font-weight: bold;'
    return ''

# Hauptbereich
if st.session_state.show_marked_only:
    # Seite für markierte Wertpapiere
    st.markdown('<div class="sub-header"><h2>⭐ Markierte Wertpapiere</h2></div>', unsafe_allow_html=True)
    
    if len(st.session_state.marked_securities) > 0:
        with st.spinner("Lade markierte Wertpapiere..."):
            marked_df = load_stock_data(tuple(st.session_state.marked_securities))
        
        column_order = ["Ticker", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", 
                       "5 Jahre %", "5J Tief", "5J Hoch", "5 J. Hoch-Tief %", "Preis"]
        
        marked_display = marked_df[column_order].copy()
        
        pct_columns = ["1 Woche %", "1 Monat %", "1 Jahr %", "5 Jahre %", "5 J. Hoch-Tief %"]
        marked_styled = marked_display.style.map(color_negative_red, subset=pct_columns)
        
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
        
        st.dataframe(
            marked_styled,
            use_container_width=True,
            column_config=column_config,
            hide_index=True,
            height=600
        )
        
        st.subheader("🔗 Yahoo Finance Links")
        for _, row in marked_df.iterrows():
            st.markdown(f"[{row['Ticker']} - {row['Name']}]({row['Link']})")
        
        csv_buffer = io.StringIO()
        marked_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Markierte als CSV herunterladen",
            data=csv_buffer.getvalue(),
            file_name=f"markierte_wertpapiere_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        if st.button("🗑️ Alle Markierungen löschen", use_container_width=True):
            st.session_state.marked_securities.clear()
            st.rerun()
    else:
        st.info("Keine markierten Wertpapiere vorhanden.")
        st.write("Gehe zur Hauptansicht und setze Häkchen bei Wertpapieren, die du markieren möchtest.")

else:
    # Hauptansicht
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anzahl Wertpapiere", len(tickers))
    with col2:
        st.metric("Datenquelle", "Yahoo Finance")
    with col3:
        st.metric("Markiert", len(st.session_state.marked_securities))

    st.divider()

    try:
        with st.spinner("Lade Börsendaten..."):
            df = load_stock_data(tuple(tickers))
        
        column_order = ["Ticker", "Name", "1 Woche %", "1 Monat %", "1 Jahr %", 
                       "5 Jahre %", "5J Tief", "5J Hoch", "5 J. Hoch-Tief %", "Preis"]
        
        df_display = df[column_order].copy()
        
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
        
        # Checkboxen für Markierung
        st.subheader("⭐ Wertpapiere markieren")
        for _, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([0.1, 0.15, 0.45, 0.3])
            with col1:
                is_marked = row['Ticker'] in st.session_state.marked_securities
                if st.checkbox("", key=f"mark_{row['Ticker']}", value=is_marked):
                    st.session_state.marked_securities.add(row['Ticker'])
                else:
                    st.session_state.marked_securities.discard(row['Ticker'])
            with col2:
                st.text(row['Ticker'])
            with col3:
                st.text(row['Name'])
            with col4:
                st.markdown(f"[Yahoo Finance 🔗]({row['Link']})")
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 CSV herunterladen",
            data=csv_buffer.getvalue(),
            file_name=f"boersenkurse_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # Top Performer
        if show_top_performers:
            st.divider()
            st.markdown('<div class="sub-header"><h2>🚀 Top Performer (Wertzuwachs >40% in 1 Jahr)</h2></div>', 
                       unsafe_allow_html=True)
            
            with st.spinner("Lade Top-Performer..."):
                top_df = load_stock_data(tuple(TOP_PERFORMERS))
            
            if not top_df.empty:
                top_df_sorted = top_df.nlargest(20, '1 Jahr %')
                
                main_tickers = set(df['Ticker'].tolist())
                
                def highlight_if_in_main(row):
                    if row['Ticker'] in main_tickers:
                        return ['color: #16a34a; font-weight: bold;' if col == 'Name' else '' for col in row.index]
                    return ['' for _ in row.index]
                
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
                
                st.subheader("⭐ Top Performer markieren")
                for _, row in top_df_sorted.iterrows():
                    col1, col2, col3, col4 = st.columns([0.1, 0.15, 0.45, 0.3])
                    with col1:
                        is_marked = row['Ticker'] in st.session_state.marked_securities
                        if st.checkbox("", key=f"mark_top_{row['Ticker']}", value=is_marked):
                            st.session_state.marked_securities.add(row['Ticker'])
                        else:
                            st.session_state.marked_securities.discard(row['Ticker'])
                    with col2:
                        st.text(row['Ticker'])
                    with col3:
                        name_color = "green" if row['Ticker'] in main_tickers else "black"
                        st.markdown(f"<span style='color: {name_color}; font-weight: bold;'>{row['Name']}</span>", 
                                   unsafe_allow_html=True)
                    with col4:
                        st.markdown(f"[Yahoo Finance 🔗]({row['Link']})")
        
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
        <p>⭐ Markierte Wertpapiere werden dauerhaft gespeichert</p>
    </div>
    """,
    unsafe_allow_html=True
)
