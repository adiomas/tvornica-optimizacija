import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.excel_parser import parse_excel
from src.pdf_parser import parse_pdf
from src.matcher import (
    validate_periods,
    match_summary,
    match_details,
    get_unmatched_bank,
    get_unmatched_by_date,
)
from src.report import generate_excel_report, generate_pdf_report

# Version — works in both dev mode and PyInstaller frozen bundle
import os, sys
_base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(__file__)
__version__ = "0.0.0"
with open(os.path.join(_base, "version.py"), encoding="utf-8") as _f:
    for _line in _f:
        if _line.startswith("__version__"):
            __version__ = _line.split('"')[1]
            break

# --- Page Config (no sidebar) ---
st.set_page_config(
    page_title="TZH | Promet vs Banka",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Brand Colors ---
BRAND_GREEN = "#4a7c28"
BRAND_GREEN_DARK = "#1b5e20"
BRAND_GREEN_LIGHT = "#e8f5e9"
BRAND_ORANGE = "#e65100"
BRAND_ORANGE_LIGHT = "#fff3e0"

# --- Custom CSS ---
st.markdown(f"""
<style>
    /* Hide sidebar toggle & default header/footer */
    [data-testid="collapsedControl"] {{ display: none; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* Global background */
    .stApp {{ background-color: #fafbf8; }}

    /* Brand header */
    .brand-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 0 16px 0;
        border-bottom: 2px solid #eee;
        margin-bottom: 20px;
    }}
    .brand-header .mark {{
        width: 5px; height: 32px;
        background: {BRAND_GREEN};
        border-radius: 3px;
    }}
    .brand-header h1 {{
        font-size: 20px !important; font-weight: 700 !important;
        color: #333 !important; margin: 0 !important; padding: 0 !important;
    }}
    .brand-header .sub {{ font-size: 12px; color: #999; margin: 0; }}

    /* Period badge */
    .badge {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 5px 14px; border-radius: 20px;
        font-size: 12px; font-weight: 500; margin-bottom: 14px;
    }}
    .badge.ok {{ background: {BRAND_GREEN_LIGHT}; color: {BRAND_GREEN_DARK}; }}
    .badge.warn {{ background: {BRAND_ORANGE_LIGHT}; color: {BRAND_ORANGE}; }}

    /* KPI row */
    .kpi-row {{ display: flex; gap: 12px; margin-bottom: 20px; }}
    .kpi {{
        flex: 1; border-radius: 12px; padding: 14px 18px;
        position: relative;
    }}
    .kpi.green {{ background: linear-gradient(135deg, {BRAND_GREEN_LIGHT}, #f1f8e9); }}
    .kpi.orange {{ background: linear-gradient(135deg, {BRAND_ORANGE_LIGHT}, #ffe0b2); }}
    .kpi.neutral {{ background: linear-gradient(135deg, #f5f5f5, #eee); }}
    .kpi .lbl {{
        font-size: 10px; text-transform: uppercase;
        letter-spacing: 0.5px; color: #666; margin-bottom: 2px;
    }}
    .kpi .val {{ font-size: 20px; font-weight: 800; }}
    .kpi.green .val {{ color: {BRAND_GREEN_DARK}; }}
    .kpi.orange .val {{ color: {BRAND_ORANGE}; }}
    .kpi.neutral .val {{ color: #333; }}
    .kpi .det {{ font-size: 11px; color: #999; margin-top: 1px; }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 2px solid #eee; }}
    .stTabs [data-baseweb="tab"] {{ padding: 8px 20px; font-size: 13px; font-weight: 500; color: #999; }}
    .stTabs [aria-selected="true"] {{ color: {BRAND_GREEN} !important; border-bottom-color: {BRAND_GREEN} !important; }}

    /* Section dot-header */
    .sec {{ display:flex; align-items:center; gap:8px; margin:18px 0 10px 0; }}
    .sec .dot {{ width:8px; height:8px; background:{BRAND_GREEN}; border-radius:50%; }}
    .sec h3 {{ font-size:15px; font-weight:600; color:#333; margin:0; }}

    /* Download buttons */
    div[data-testid="stDownloadButton"] > button {{
        background: #fff !important; border: 1px solid #ddd !important;
        color: #333 !important; border-radius: 8px !important;
    }}
    div[data-testid="stDownloadButton"] > button:hover {{
        border-color: {BRAND_GREEN} !important; color: {BRAND_GREEN} !important;
    }}

    /* Primary button */
    .stButton > button[kind="primary"] {{
        background: {BRAND_GREEN} !important; border: none !important; border-radius: 8px !important;
    }}
    .stButton > button[kind="primary"]:hover {{ background: {BRAND_GREEN_DARK} !important; }}

    /* Expander styling */
    .stExpander {{
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
        background-color: #fff !important;
    }}
    .stExpander details {{
        background-color: #fff !important;
    }}
    .stExpander summary {{
        background-color: #f8f9f5 !important;
        color: #333 !important;
    }}
    .stExpander [data-testid="stExpanderToggleIcon"] {{ color: {BRAND_GREEN}; }}

    /* File uploader — styled drop zone */
    [data-testid="stFileUploader"] {{
        background-color: #fff !important;
    }}
    [data-testid="stFileUploader"] label p {{
        color: #555 !important;
        font-weight: 500 !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background-color: #f8fbf5 !important;
        border: 2px dashed #b5cda0 !important;
        border-radius: 10px !important;
        padding: 28px 16px !important;
        transition: all 0.2s ease;
    }}
    [data-testid="stFileUploaderDropzone"]:hover {{
        border-color: {BRAND_GREEN} !important;
        background-color: #eef5e6 !important;
    }}
    [data-testid="stFileUploaderDropzone"] > div > span {{
        color: #888 !important;
        font-size: 13px !important;
    }}
    [data-testid="stFileUploaderDropzone"] > button {{
        background-color: #fff !important;
        color: {BRAND_GREEN} !important;
        border: 1px solid {BRAND_GREEN} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }}
    [data-testid="stFileUploaderDropzone"] > button:hover {{
        background-color: {BRAND_GREEN_LIGHT} !important;
    }}
    [data-testid="stFileUploader"] small {{
        color: #aaa !important;
    }}
    /* Uploaded file chip */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
        background-color: {BRAND_GREEN_LIGHT} !important;
        border-radius: 8px !important;
    }}
</style>
""", unsafe_allow_html=True)


# --- Header ---
st.markdown("""
<div class="brand-header">
    <div class="mark"></div>
    <div>
        <h1>Promet vs Banka</h1>
        <p class="sub">Tvornica Zdrave Hrane — Usporedba gotovinskog prometa i bankovnih izvoda</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- File Upload (Expander) ---
has_results = "results" in st.session_state
expander_label = "📂 Datoteke  ✅ Učitane" if has_results else "📂 Učitaj datoteke"

with st.expander(expander_label, expanded=not has_results):
    uc1, uc2 = st.columns(2)
    with uc1:
        excel_file = st.file_uploader(
            "📄 Promet — Excel OLAP",
            type=["xlsx", "xls"],
            help="Povuci Excel datoteku ovdje ili klikni za odabir",
        )
    with uc2:
        pdf_file = st.file_uploader(
            "📑 Bankovni izvod — PDF",
            type=["pdf"],
            help="Povuci PDF datoteku ovdje ili klikni za odabir",
        )
    compare_btn = st.button(
        "Usporedi", type="primary", use_container_width=True,
        disabled=not (excel_file and pdf_file),
    )

# --- Guard: no files ---
if not (excel_file and pdf_file) and not has_results:
    st.markdown("""
    <div style="text-align:center; padding:80px 20px; color:#bbb;">
        <div style="font-size:44px; margin-bottom:12px;">📂</div>
        <div style="font-size:15px; color:#888;">Učitaj Excel i PDF datoteke za početak</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not has_results and not compare_btn:
    st.markdown("""
    <div style="text-align:center; padding:80px 20px; color:#bbb;">
        <div style="font-size:44px; margin-bottom:12px;">🔍</div>
        <div style="font-size:15px; color:#888;">Klikni <b>Usporedi</b> za analizu</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# --- Processing ---
@st.cache_data
def process_files(excel_bytes, pdf_bytes):
    import io
    excel_df, ex_meta = parse_excel(io.BytesIO(excel_bytes))
    pdf_df, pdf_meta = parse_pdf(io.BytesIO(pdf_bytes))
    valid, period_msg = validate_periods(ex_meta, pdf_meta)
    summary = match_summary(excel_df, pdf_df)
    unmatched_bank = get_unmatched_bank(pdf_df)
    unmatched_dates = get_unmatched_by_date(excel_df, pdf_df)
    xlsx_report = generate_excel_report(
        summary, excel_df, pdf_df, unmatched_bank, ex_meta, pdf_meta, match_details
    )
    pdf_report = generate_pdf_report(summary, excel_df, pdf_df, ex_meta, pdf_meta, match_details)
    return {
        "excel_df": excel_df, "pdf_df": pdf_df,
        "ex_meta": ex_meta, "pdf_meta": pdf_meta,
        "valid": valid, "period_msg": period_msg,
        "summary": summary, "unmatched_bank": unmatched_bank,
        "unmatched_dates": unmatched_dates,
        "xlsx_report": xlsx_report, "pdf_report": pdf_report,
    }


if compare_btn:
    with st.spinner("Analiziram podatke..."):
        st.session_state["results"] = process_files(excel_file.getvalue(), pdf_file.getvalue())
        st.rerun()

if not has_results:
    st.stop()

r = st.session_state["results"]
summary = r["summary"]

# --- Period Badge ---
ex = r["ex_meta"]
if r["valid"]:
    st.markdown(
        f'<div class="badge ok">✅ {ex["period_start"].strftime("%d.%m.%Y")} — '
        f'{ex["period_end"].strftime("%d.%m.%Y")} · {ex["branch_count"]} poslovnica · '
        f'{r["pdf_meta"]["transaction_count"]} transakcija</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(f'<div class="badge warn">⚠️ {r["period_msg"]}</div>', unsafe_allow_html=True)

# --- KPI Cards ---
promet_total = summary["promet_total"].sum()
banka_total = summary["banka_total"].sum()
razlika_total = summary["razlika"].sum()
ok_count = len(summary[summary["status"] == "OK"])
err_count = len(summary[summary["status"] != "OK"])

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi green">
        <div class="lbl">Ukupno Promet</div>
        <div class="val">{promet_total:,.2f} €</div>
        <div class="det">{len(r["excel_df"])} zapisa</div>
    </div>
    <div class="kpi green">
        <div class="lbl">Ukupno Banka</div>
        <div class="val">{banka_total:,.2f} €</div>
        <div class="det">{r["pdf_meta"]["transaction_count"]} transakcija</div>
    </div>
    <div class="kpi orange">
        <div class="lbl">Razlika</div>
        <div class="val">{razlika_total:+,.2f} €</div>
        <div class="det">{razlika_total / promet_total * 100:+.2f}%</div>
    </div>
    <div class="kpi neutral">
        <div class="lbl">Podudaranje</div>
        <div class="val">{ok_count} / {ok_count + err_count}</div>
        <div class="det">{err_count} s razlikom</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- Shared styling function ---
def color_status(val):
    if val == "OK":
        return f"background-color:{BRAND_GREEN_LIGHT};color:{BRAND_GREEN_DARK};font-weight:600"
    if val == "UPOZORENJE":
        return "background-color:#fff8e1;color:#f57f17;font-weight:600"
    return f"background-color:{BRAND_ORANGE_LIGHT};color:{BRAND_ORANGE};font-weight:600"


# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Sumarni pregled", "Detalji po poslovnici", "Neuparene stavke", "Preuzmi"])

with tab1:
    # Chart
    colors = [BRAND_GREEN if x >= 0 else BRAND_ORANGE for x in summary["razlika"]]
    fig = go.Figure(go.Bar(
        y=summary["pj_code"] + " " + summary["pj_name"],
        x=summary["razlika"], orientation="h", marker_color=colors,
        text=[f"{x:+,.0f} €" for x in summary["razlika"]],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.update_layout(
        title=dict(text="Razlike po poslovnici (Banka − Promet)", font=dict(size=14)),
        height=max(380, len(summary) * 26),
        yaxis=dict(autorange="reversed"),
        xaxis_title="EUR",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=60, t=36, b=36),
        font=dict(family="system-ui, -apple-system, sans-serif"),
    )
    fig.update_xaxes(gridcolor="#f0f0f0", zerolinecolor="#ddd")
    fig.update_yaxes(gridcolor="#f0f0f0")
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown('<div class="sec"><div class="dot"></div><h3>Tablica usporedbe</h3></div>', unsafe_allow_html=True)
    display_df = summary[
        ["pj_code", "pj_name", "promet_total", "banka_total", "razlika", "razlika_pct", "status"]
    ].copy()
    display_df.columns = ["PJ", "Poslovnica", "Promet (€)", "Banka (€)", "Razlika (€)", "%", "Status"]
    styled = display_df.style.map(color_status, subset=["Status"]).format(
        {"Promet (€)": "{:,.2f}", "Banka (€)": "{:,.2f}", "Razlika (€)": "{:+,.2f}", "%": "{:+.1f}%"}
    )
    st.dataframe(styled, use_container_width=True, hide_index=True, height=min(600, 36 + len(display_df) * 35))


with tab2:
    pj_options = {f"{row['pj_code']} — {row['pj_name']}": row["pj_code"] for _, row in summary.iterrows()}
    selected = st.selectbox("Poslovnica", list(pj_options.keys()), label_visibility="collapsed")
    selected_pj = pj_options[selected]
    details = match_details(r["excel_df"], r["pdf_df"], selected_pj)

    if details.empty:
        st.info("Nema podataka.")
    else:
        branch_row = summary[summary["pj_code"] == selected_pj].iloc[0]
        st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi green"><div class="lbl">Promet</div><div class="val">{branch_row['promet_total']:,.2f} €</div></div>
            <div class="kpi green"><div class="lbl">Banka</div><div class="val">{branch_row['banka_total']:,.2f} €</div></div>
            <div class="kpi {'orange' if abs(branch_row['razlika']) > 5 else 'green'}">
                <div class="lbl">Razlika</div><div class="val">{branch_row['razlika']:+,.2f} €</div>
                <div class="det">{branch_row['razlika_pct']:+.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=details["date"], y=details["promet"], name="Promet",
            mode="lines+markers", line=dict(color=BRAND_GREEN, width=2), marker=dict(size=5),
        ))
        fig3.add_trace(go.Scatter(
            x=details["date"], y=details["banka"], name="Banka",
            mode="lines+markers", line=dict(color="#1976d2", width=2), marker=dict(size=5),
        ))
        fig3.update_layout(
            height=320, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=16, b=36),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            font=dict(family="system-ui"), xaxis_title="", yaxis_title="EUR",
        )
        fig3.update_xaxes(gridcolor="#f0f0f0")
        fig3.update_yaxes(gridcolor="#f0f0f0")
        st.plotly_chart(fig3, use_container_width=True)

        dd = details.copy()
        dd["date"] = dd["date"].dt.strftime("%d.%m.%Y")
        dd.columns = ["Datum", "Promet (€)", "Banka (€)", "Razlika (€)", "Status", "Napomena"]

        def color_status_star(val):
            if val == "OK":
                return f"background-color:{BRAND_GREEN_LIGHT};color:{BRAND_GREEN_DARK};font-weight:600"
            if val == "OK*":
                return "background-color:#e0f2f1;color:#00695c;font-weight:600"
            if val == "UPOZORENJE":
                return "background-color:#fff8e1;color:#f57f17;font-weight:600"
            return f"background-color:{BRAND_ORANGE_LIGHT};color:{BRAND_ORANGE};font-weight:600"

        st.dataframe(
            dd.style.map(color_status_star, subset=["Status"]).format(
                {"Promet (€)": "{:,.2f}", "Banka (€)": "{:,.2f}", "Razlika (€)": "{:+,.2f}"}
            ),
            use_container_width=True, hide_index=True,
        )


with tab3:
    unmatched_bank = r["unmatched_bank"]
    unmatched_dates = r["unmatched_dates"]

    ca, cb = st.columns(2)
    with ca:
        st.markdown('<div class="sec"><div class="dot"></div><h3>Neidentificirane uplate</h3></div>', unsafe_allow_html=True)
        if unmatched_bank.empty:
            st.success("Sve transakcije prepoznate.")
        else:
            ub = unmatched_bank.copy()
            ub["booking_date"] = ub["booking_date"].dt.strftime("%d.%m.%Y")
            ub.columns = ["Rb", "Datum", "Iznos (€)", "PNB", "Opis"]
            st.dataframe(ub, use_container_width=True, hide_index=True)
            st.markdown(f'<div class="badge warn">Neupareno: {unmatched_bank["amount"].sum():,.2f} €</div>', unsafe_allow_html=True)

    with cb:
        st.markdown('<div class="sec"><div class="dot"></div><h3>Promet bez uplate</h3></div>', unsafe_allow_html=True)
        if unmatched_dates.empty:
            st.success("Sve stavke imaju uplatu.")
        else:
            ud = unmatched_dates[["pj_code", "pj_name", "date", "amount"]].copy()
            ud["date"] = ud["date"].dt.strftime("%d.%m.%Y")
            ud.columns = ["PJ", "Poslovnica", "Datum", "Iznos (€)"]
            st.dataframe(ud, use_container_width=True, hide_index=True, height=400)
            st.markdown(f'<div class="badge warn">Bez uplate: {unmatched_dates["amount"].sum():,.2f} €</div>', unsafe_allow_html=True)


with tab4:
    st.markdown('<div class="sec"><div class="dot"></div><h3>Preuzmi izvještaj</h3></div>', unsafe_allow_html=True)
    st.caption("Generirani izvještaji sa svim detaljima usporedbe")
    d1, d2, d3 = st.columns([1, 1, 2])
    with d1:
        st.download_button(
            "📥 Excel izvještaj", data=r["xlsx_report"],
            file_name="usporedba_promet_banka.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "📥 PDF izvještaj", data=r["pdf_report"],
            file_name="usporedba_promet_banka.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# --- Footer with version ---
st.markdown(
    f'<div style="text-align:center;padding:20px 0 10px;color:#ccc;font-size:11px;">'
    f'TZH Promet vs Banka v{__version__}</div>',
    unsafe_allow_html=True,
)
