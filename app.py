“””
Fundamentalanalyse-Assistent
Abhaengigkeiten: pip install streamlit yfinance anthropic pandas requests
Start: streamlit run app.py
“””

import streamlit as st
import yfinance as yf
import pandas as pd
import anthropic
import requests
import json
from datetime import datetime, date

# ─────────────────────────────────────────────

# KONFIGURATION

# ─────────────────────────────────────────────

st.set_page_config(
page_title=“Fundamentalanalyse”,
page_icon=“📊”,
layout=“wide”
)

st.title(“📊 Fundamentalanalyse-Assistent”)
st.write(“Analyse nach deinen Praeferenzen: KGV, EV/EBIT, Dividendenrendite, 3-Jahres-Retrospektive, Analystenmeinungen”)

# ─────────────────────────────────────────────

# SIDEBAR: API KEY & EINSTELLUNGEN

# ─────────────────────────────────────────────

with st.sidebar:
st.header(“⚙️ Einstellungen”)
api_key = st.text_input(“Anthropic API Key”, type=“password”, help=“Benoetigt fuer die KI-Analyse”)
st.divider()
st.markdown(”**Datenquellen**”)
st.markdown(”- Yahoo Finance (yfinance)”)
st.markdown(”- Exchangerate-API (Wechselkurse)”)
st.markdown(”- Claude AI (Interpretation)”)
st.divider()
st.caption(“Alle Geldwerte werden in EUR ausgegeben.”)

# ─────────────────────────────────────────────

# EINGABE

# ─────────────────────────────────────────────

col_in1, col_in2, col_in3 = st.columns([2, 1, 1])

with col_in1:
ticker = st.text_input(
“Ticker-Symbol”,
value=“ALV.DE”,
help=“z. B. ALV.DE (Allianz), AAPL (Apple), MC.PA (LVMH), 7203.T (Toyota)”
)
with col_in2:
analyse_btn = st.button(“🔍 Analyse starten”, type=“primary”, use_container_width=True)
with col_in3:
st.caption(“Beispiele:”)
st.caption(“ALV.DE · SAP.DE · AAPL · MC.PA”)

# ─────────────────────────────────────────────

# WECHSELKURS: X → EUR

# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_eur_rate(currency: str) -> float:
“”“Gibt den Umrechnungsfaktor [Waehrung -> EUR] zurueck.”””
if currency == “EUR”:
return 1.0
try:
url = f”https://api.exchangerate-api.com/v4/latest/{currency}”
r = requests.get(url, timeout=5)
data = r.json()
return data[“rates”].get(“EUR”, 1.0)
except Exception:
fallbacks = {“USD”: 0.92, “GBP”: 1.17, “JPY”: 0.0062, “CHF”: 1.04, “SEK”: 0.088}
return fallbacks.get(currency, 1.0)

def to_eur(value, rate):
if value is None:
return None
try:
return float(value) * rate
except Exception:
return None

def fmt_eur(value, decimals=2, unit=””):
if value is None or (isinstance(value, float) and (value != value)):
return “N/V”
try:
v = float(value)
if abs(v) >= 1e9:
return f”EUR {v/1e9:.{decimals}f} Mrd{unit}”
elif abs(v) >= 1e6:
return f”EUR {v/1e6:.{decimals}f} Mio{unit}”
else:
return f”EUR {v:.{decimals}f}{unit}”
except Exception:
return “N/V”

def fmt_pct(value):
if value is None:
return “N/V”
try:
return f”{float(value)*100:.2f} %”
except Exception:
return “N/V”

def safe(info, key, default=None):
v = info.get(key, default)
return v if v not in [None, “N/A”, “”] else default

# ─────────────────────────────────────────────

# DATEN LADEN

# ─────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data(symbol: str):
stock = yf.Ticker(symbol)
info = stock.info

```
currency = info.get("currency", "EUR")
rate = get_eur_rate(currency)

# Kurs-History (fuer Chart)
history_1y = stock.history(period="1y")
history_3y = stock.history(period="3y")

# Finanzdaten (letzte 3 GJ)
try:
    income = stock.financials
except Exception:
    income = pd.DataFrame()

try:
    balance = stock.balance_sheet
except Exception:
    balance = pd.DataFrame()

# Analystendaten
try:
    recommendations = stock.recommendations
except Exception:
    recommendations = pd.DataFrame()

return {
    "info": info,
    "currency": currency,
    "rate": rate,
    "history_1y": history_1y,
    "history_3y": history_3y,
    "income": income,
    "balance": balance,
    "recommendations": recommendations,
}
```

# ─────────────────────────────────────────────

# KENNZAHLEN AUFBEREITEN

# ─────────────────────────────────────────────

def build_metrics(d: dict) -> dict:
info = d[“info”]
rate = d[“rate”]

```
def s(key):
    return safe(info, key)

current_price_eur = to_eur(s("currentPrice") or s("regularMarketPrice"), rate)
market_cap_eur    = to_eur(s("marketCap"), rate)
ev_eur            = to_eur(s("enterpriseValue"), rate)
ebit_eur          = to_eur(s("ebit"), rate)
ev_ebit           = (ev_eur / ebit_eur) if ev_eur and ebit_eur and ebit_eur != 0 else None

div_yield = s("dividendYield")
div_rate_eur = to_eur(s("dividendRate"), rate)

return {
    "name":             s("longName") or s("shortName") or ticker,
    "sector":           s("sector"),
    "industry":         s("industry"),
    "country":          s("country"),
    "currency":         d["currency"],
    "rate":             rate,
    "current_price":    current_price_eur,
    "market_cap":       market_cap_eur,
    "ev":               ev_eur,
    "ebit":             ebit_eur,
    "ev_ebit":          ev_ebit,
    "pe_trailing":      s("trailingPE"),
    "pe_forward":       s("forwardPE"),
    "peg":              s("pegRatio"),
    "eps_trailing":     to_eur(s("trailingEps"), rate),
    "eps_forward":      to_eur(s("forwardEps"), rate),
    "revenue":          to_eur(s("totalRevenue"), rate),
    "gross_margin":     s("grossMargins"),
    "operating_margin": s("operatingMargins"),
    "net_margin":       s("netMargins"),
    "roe":              s("returnOnEquity"),
    "roa":              s("returnOnAssets"),
    "debt_equity":      s("debtToEquity"),
    "current_ratio":    s("currentRatio"),
    "quick_ratio":      s("quickRatio"),
    "div_yield":        div_yield,
    "div_rate":         div_rate_eur,
    "payout_ratio":     s("payoutRatio"),
    "div_growth_5y":    s("fiveYearAvgDividendYield"),
    "beta":             s("beta"),
    "52w_high":         to_eur(s("fiftyTwoWeekHigh"), rate),
    "52w_low":          to_eur(s("fiftyTwoWeekLow"), rate),
    "analyst_count":    s("numberOfAnalystOpinions"),
    "target_mean":      to_eur(s("targetMeanPrice"), rate),
    "target_high":      to_eur(s("targetHighPrice"), rate),
    "target_low":       to_eur(s("targetLowPrice"), rate),
    "recommendation":   s("recommendationKey"),
    "employees":        s("fullTimeEmployees"),
    "description":      s("longBusinessSummary"),
}
```

# ─────────────────────────────────────────────

# 3-JAHRES-RETROSPEKTIVE

# ─────────────────────────────────────────────

def build_retrospective(d: dict) -> pd.DataFrame:
income = d[“income”]
rate   = d[“rate”]

```
if income.empty:
    return pd.DataFrame()

rows = []
for col in income.columns[:3]:
    jahr = col.year if hasattr(col, "year") else str(col)[:4]

    def g(key):
        try:
            v = income.loc[key, col]
            return to_eur(v, rate) if v == v else None
        except Exception:
            return None

    umsatz = g("Total Revenue")
    ebit   = g("EBIT") or g("Operating Income")
    gewinn = g("Net Income")
    marge  = (ebit / umsatz * 100) if ebit and umsatz else None
    rows.append({
        "Geschaeftsjahr": str(jahr),
        "Umsatz":         fmt_eur(umsatz, 1),
        "EBIT":           fmt_eur(ebit, 1),
        "EBIT-Marge":     f"{marge:.1f} %" if marge else "N/V",
        "Nettogewinn":    fmt_eur(gewinn, 1),
    })

return pd.DataFrame(rows)
```

# ─────────────────────────────────────────────

# ANALYSTENKONSENS

# ─────────────────────────────────────────────

def build_analyst_summary(d: dict) -> pd.DataFrame:
rec = d[“recommendations”]
if rec is None or rec.empty:
return pd.DataFrame()

```
try:
    recent = rec.tail(20)
    if "period" in recent.columns:
        period_map = {"0m": "Aktuell", "-1m": "Vor 1 Monat", "-2m": "Vor 2 Monaten", "-3m": "Vor 3 Monaten"}
        recent = recent[recent["period"].isin(period_map.keys())].copy()
        recent["period"] = recent["period"].map(period_map)
        cols = [c for c in ["period", "strongBuy", "buy", "hold", "sell", "strongSell"] if c in recent.columns]
        return recent[cols].rename(columns={
            "period": "Zeitraum", "strongBuy": "Stark Kaufen", "buy": "Kaufen",
            "hold": "Halten", "sell": "Verkaufen", "strongSell": "Stark Verkaufen"
        })
except Exception:
    pass
return pd.DataFrame()
```

# ─────────────────────────────────────────────

# CLAUDE KI-ANALYSE

# ─────────────────────────────────────────────

def claude_analyse(metrics: dict, retro_df: pd.DataFrame, api_key: str) -> str:
client = anthropic.Anthropic(api_key=api_key)

```
retro_txt = retro_df.to_string(index=False) if not retro_df.empty else "Keine historischen Daten verfuegbar"

prompt = (
    "Du bist ein professioneller Finanzanalyst. Erstelle auf Basis der folgenden Daten eine strukturierte Analyse auf Deutsch.\n\n"
    f"UNTERNEHMEN: {metrics['name']} ({ticker.upper()})\n"
    f"Sektor: {metrics['sector']} | Branche: {metrics['industry']} | Land: {metrics['country']}\n"
    f"Originalwaehrung: {metrics['currency']} (Kurs zu EUR: {metrics['rate']:.4f})\n\n"
    "FUNDAMENTALKENNZAHLEN (alle in EUR):\n"
    f"- Aktueller Kurs: {fmt_eur(metrics['current_price'])}\n"
    f"- Marktkapitalisierung: {fmt_eur(metrics['market_cap'], 1)}\n"
    f"- EV: {fmt_eur(metrics['ev'], 1)}\n"
    f"- EV/EBIT: {f\"{metrics['ev_ebit']:.1f}x\" if metrics['ev_ebit'] else 'N/V'}\n"
    f"- KGV (trailing): {f\"{metrics['pe_trailing']:.1f}\" if metrics['pe_trailing'] else 'N/V'}\n"
    f"- KGV (forward): {f\"{metrics['pe_forward']:.1f}\" if metrics['pe_forward'] else 'N/V'}\n"
    f"- EPS (trailing): {fmt_eur(metrics['eps_trailing'])}\n"
    f"- Umsatz: {fmt_eur(metrics['revenue'], 1)}\n"
    f"- Operative Marge: {fmt_pct(metrics['operating_margin'])}\n"
    f"- Nettomarge: {fmt_pct(metrics['net_margin'])}\n"
    f"- ROE: {fmt_pct(metrics['roe'])}\n"
    f"- Debt/Equity: {f\"{metrics['debt_equity']:.2f}\" if metrics['debt_equity'] else 'N/V'}\n"
    f"- Current Ratio: {f\"{metrics['current_ratio']:.2f}\" if metrics['current_ratio'] else 'N/V'}\n"
    f"- Dividendenrendite: {fmt_pct(metrics['div_yield'])}\n"
    f"- Ausschuettungsquote: {fmt_pct(metrics['payout_ratio'])}\n"
    f"- Beta: {f\"{metrics['beta']:.2f}\" if metrics['beta'] else 'N/V'}\n"
    f"- 52W-Hoch: {fmt_eur(metrics['52w_high'])} | 52W-Tief: {fmt_eur(metrics['52w_low'])}\n\n"
    f"3-JAHRES-RETROSPEKTIVE:\n{retro_txt}\n\n"
    "ANALYSTENKONSENS:\n"
    f"- Empfehlung: {metrics['recommendation'] or 'N/V'}\n"
    f"- Kursziel Mittel: {fmt_eur(metrics['target_mean'])}\n"
    f"- Kursziel Range: {fmt_eur(metrics['target_low'])} - {fmt_eur(metrics['target_high'])}\n"
    f"- Anzahl Analysten: {metrics['analyst_count'] or 'N/V'}\n"
    f"- Impliziertes Upside: {f\"{(metrics['target_mean']/metrics['current_price']-1)*100:.1f} %\" if metrics['target_mean'] and metrics['current_price'] else 'N/V'}\n\n"
    "Erstelle folgende Abschnitte:\n\n"
    "## Bewertungseinschaetzung\n"
    "Bewerte EV/EBIT und KGV im historischen und Branchenkontext. Ist die Aktie fair bewertet, guenstig oder teuer?\n\n"
    "## Qualitaet des Geschaeftsmodells\n"
    "Analysiere Margen, ROE, Verschuldung und Dividendenhistorie.\n\n"
    "## Analysteneinschaetzung & Kursziel\n"
    "Interpretiere den Analystenkonsens. Ist das Kursziel realistisch?\n\n"
    "## Wahrscheinlichkeitsgewichtete Szenarien\n\n"
    "|Szenario |Wahrscheinlichkeit|Kursziel EUR|Treiber|\n"
    "|---------|------------------|------------|-------|\n"
    "|Bull-Case|XX%               |EUR XX      |...    |\n"
    "|Base-Case|XX%               |EUR XX      |...    |\n"
    "|Bear-Case|XX%               |EUR XX      |...    |\n\n"
    "## Chancen & Risiken\n\n"
    "**Chancen (max. 4):**\n- ...\n\n"
    "**Risiken (max. 4):**\n- ...\n\n"
    "## Fazit\n"
    "2-3 Saetze Gesamteinschaetzung fuer einen langfristigen Investor.\n\n"
    "Wichtig: EV/EBIT verwenden (kein EV/EBITDA). Alle Werte in EUR. Professionell und praezise."
)

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)
return message.content[0].text
```

# ─────────────────────────────────────────────

# HAUPTLOGIK

# ─────────────────────────────────────────────

if analyse_btn and ticker:
with st.spinner(f”Lade Daten fuer {ticker.upper()}…”):
try:
d = load_stock_data(ticker.strip())
m = build_metrics(d)
retro = build_retrospective(d)
analyst_tbl = build_analyst_summary(d)
except Exception as e:
st.error(f”Fehler beim Laden: {e}”)
st.stop()

```
# HEADER
st.divider()
h1, h2, h3 = st.columns([3, 1, 1])
with h1:
    st.subheader(m["name"])
    st.caption(f"{m['sector']} · {m['industry']} · {m['country']} | Originalwaehrung: {m['currency']} (1 {m['currency']} = {m['rate']:.4f} EUR)")
with h2:
    if m["current_price"]:
        st.metric("Aktueller Kurs", fmt_eur(m["current_price"]))
with h3:
    if m["52w_high"] and m["52w_low"]:
        st.metric("52W-Range", f"{fmt_eur(m['52w_low'])} - {fmt_eur(m['52w_high'])}")

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Kennzahlen", "📈 Chart", "📋 3-Jahres-Retrospektive", "🎯 Analysten", "🤖 KI-Analyse"
])

# TAB 1: KENNZAHLEN
with tab1:
    st.subheader("Bewertungskennzahlen")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EV/EBIT", f"{m['ev_ebit']:.1f}x" if m['ev_ebit'] else "N/V")
    c2.metric("KGV (trailing)", f"{m['pe_trailing']:.1f}" if m['pe_trailing'] else "N/V")
    c3.metric("KGV (forward)", f"{m['pe_forward']:.1f}" if m['pe_forward'] else "N/V")
    c4.metric("EV", fmt_eur(m['ev'], 1))

    st.subheader("Profitabilitaet")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Operative Marge", fmt_pct(m['operating_margin']))
    c2.metric("Nettomarge", fmt_pct(m['net_margin']))
    c3.metric("ROE", fmt_pct(m['roe']))
    c4.metric("ROA", fmt_pct(m['roa']))

    st.subheader("Bilanz & Verschuldung")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Debt/Equity", f"{m['debt_equity']:.2f}" if m['debt_equity'] else "N/V")
    c2.metric("Current Ratio", f"{m['current_ratio']:.2f}" if m['current_ratio'] else "N/V")
    c3.metric("Quick Ratio", f"{m['quick_ratio']:.2f}" if m['quick_ratio'] else "N/V")
    c4.metric("Marktkapitalisierung", fmt_eur(m['market_cap'], 1))

    st.subheader("Dividende")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dividendenrendite", fmt_pct(m['div_yield']))
    c2.metric("Dividende/Aktie", fmt_eur(m['div_rate']))
    c3.metric("Ausschuettungsquote", fmt_pct(m['payout_ratio']))
    c4.metric("Beta", f"{m['beta']:.2f}" if m['beta'] else "N/V")

    if m["description"]:
        st.subheader("Unternehmensbeschreibung")
        st.write(m["description"])

# TAB 2: CHART
with tab2:
    if not d["history_1y"].empty:
        st.subheader("Kursverlauf 1 Jahr (in EUR)")
        chart_data = d["history_1y"][["Close"]].copy()
        chart_data["Close (EUR)"] = chart_data["Close"] * m["rate"]
        st.line_chart(chart_data[["Close (EUR)"]])
    if not d["history_3y"].empty:
        st.subheader("Kursverlauf 3 Jahre (in EUR)")
        chart_data3 = d["history_3y"][["Close"]].copy()
        chart_data3["Close (EUR)"] = chart_data3["Close"] * m["rate"]
        st.line_chart(chart_data3[["Close (EUR)"]])

# TAB 3: RETROSPEKTIVE
with tab3:
    st.subheader("3-Jahres-Retrospektive (alle Werte in EUR)")
    if not retro.empty:
        st.dataframe(retro, use_container_width=True, hide_index=True)
    else:
        st.info("Keine historischen Finanzdaten verfuegbar.")

    income = d["income"]
    rate   = m["rate"]
    if not income.empty:
        rev_data, ebit_data, ni_data = {}, {}, {}
        for col in income.columns[:4]:
            jahr = str(col.year) if hasattr(col, "year") else str(col)[:4]
            try:
                rev = income.loc["Total Revenue", col]
                rev_data[jahr] = to_eur(rev, rate) / 1e6 if rev == rev else None
            except Exception:
                pass
            try:
                ebit = income.loc["EBIT", col] if "EBIT" in income.index else income.loc["Operating Income", col]
                ebit_data[jahr] = to_eur(ebit, rate) / 1e6 if ebit == ebit else None
            except Exception:
                pass
            try:
                ni = income.loc["Net Income", col]
                ni_data[jahr] = to_eur(ni, rate) / 1e6 if ni == ni else None
            except Exception:
                pass

        if rev_data:
            st.subheader("Umsatzentwicklung (EUR Mio.)")
            st.bar_chart(pd.DataFrame({"Umsatz": rev_data}))
        if ebit_data:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("EBIT (EUR Mio.)")
                st.bar_chart(pd.DataFrame({"EBIT": ebit_data}))
            with c2:
                st.subheader("Nettogewinn (EUR Mio.)")
                st.bar_chart(pd.DataFrame({"Nettogewinn": ni_data}))

# TAB 4: ANALYSTEN
with tab4:
    st.subheader("Analystenkonsens")
    c1, c2, c3 = st.columns(3)
    c1.metric("Empfehlung", (m['recommendation'] or 'N/V').upper())
    c2.metric("Kursziel Konsens", fmt_eur(m['target_mean']))
    c3.metric(
        "Impliziertes Upside",
        f"{(m['target_mean']/m['current_price']-1)*100:.1f} %"
        if m['target_mean'] and m['current_price'] else "N/V"
    )
    c1.metric("Kursziel Hoch", fmt_eur(m['target_high']))
    c2.metric("Kursziel Tief", fmt_eur(m['target_low']))
    c3.metric("Anzahl Analysten", m['analyst_count'] or "N/V")

    if not analyst_tbl.empty:
        st.subheader("Empfehlungsverteilung")
        st.dataframe(analyst_tbl, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Detaildaten zur Empfehlungsverteilung verfuegbar.")

# TAB 5: KI-ANALYSE
with tab5:
    st.subheader("KI-gestuetzte Interpretation (Claude)")
    if not api_key:
        st.warning("Bitte einen Anthropic API Key in der Sidebar eingeben.")
    else:
        if st.button("🤖 KI-Analyse generieren", type="primary"):
            with st.spinner("Claude analysiert die Daten..."):
                try:
                    analyse_text = claude_analyse(m, retro, api_key)
                    st.markdown(analyse_text)

                    export_df = pd.DataFrame({
                        "Kennzahl": [
                            "EV/EBIT", "KGV (trailing)", "KGV (forward)",
                            "Dividendenrendite", "Debt/Equity", "ROE",
                            "Operative Marge", "Kursziel Konsens", "Empfehlung"
                        ],
                        "Wert": [
                            f"{m['ev_ebit']:.1f}x" if m['ev_ebit'] else "N/V",
                            f"{m['pe_trailing']:.1f}" if m['pe_trailing'] else "N/V",
                            f"{m['pe_forward']:.1f}" if m['pe_forward'] else "N/V",
                            fmt_pct(m['div_yield']),
                            f"{m['debt_equity']:.2f}" if m['debt_equity'] else "N/V",
                            fmt_pct(m['roe']),
                            fmt_pct(m['operating_margin']),
                            fmt_eur(m['target_mean']),
                            m['recommendation'] or "N/V",
                        ]
                    })
                    st.divider()
                    st.download_button(
                        label="📥 Kennzahlen als CSV exportieren",
                        data=export_df.to_csv(index=False),
                        file_name=f"analyse_{ticker.upper()}_{date.today()}.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"KI-Analyse fehlgeschlagen: {e}")
```

elif not ticker:
st.info(“👆 Bitte ein Ticker-Symbol eingeben und auf ‘Analyse starten’ klicken.”)
