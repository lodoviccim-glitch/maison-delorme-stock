from simulation import simuler_rop, simuler_periodic_review, preparer_demande

import math
from statistics import NormalDist
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ABC_COLORS = {
    "A": ("#E3F3E9", "#176B43", "#B9DFC7"),
    "B": ("#FFF5CE", "#886200", "#EBD88C"),
    "C": ("#FFE9D5", "#A84B0B", "#F2C49C"),
}


def badge_abc(classe):
    fond, texte, bord = ABC_COLORS.get(str(classe), ("#EEF0F3", "#374151", "#D1D5DB"))
    return (f'<span style="display:inline-block;padding:5px 13px;'
            f'border-radius:20px;background:{fond};color:{texte};'
            f'border:1px solid {bord};font-weight:700;font-size:0.85rem">'
            f'Classe {classe}</span>')


def couleur_cellule_abc(valeur):
    fond, texte, _ = ABC_COLORS.get(str(valeur), ("#FFFFFF", "#142338", "#FFFFFF"))
    return f"background-color: {fond}; color: {texte}; font-weight: bold; text-align: center"


st.set_page_config(page_title="Maison Delorme | Stock Intelligence", page_icon="🥃", layout="wide")
NAVY, GOLD = "#142338", "#BE9252"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {--ink:#15243A;--muted:#748398;--line:#E7ECF3;--gold:#B58B51;--navy:#111F32;--bg:#F5F7FB}
html, body, [class*="css"], .stApp {font-family:'DM Sans',sans-serif!important}
.stApp, [data-testid="stAppViewContainer"] {background:#F5F7FB!important}
.block-container {max-width:1440px!important;padding:2rem 3.2rem 5rem!important}
h1,h2,h3,h4 {font-family:'Manrope',sans-serif!important;color:#142338!important;letter-spacing:-.035em!important}
h1 {font-size:2.05rem!important;font-weight:800!important;margin-bottom:.25rem!important}
h2 {font-size:1.45rem!important;font-weight:800!important}
h3 {font-size:1.14rem!important;font-weight:800!important}
p {line-height:1.6}
[data-testid="stSidebar"] {background:#111F32!important;border-right:1px solid #283A50!important}
[data-testid="stSidebar"] > div {background:#111F32!important}
[data-testid="stSidebar"] .block-container {padding:1.8rem 1.05rem!important}
[data-testid="stSidebar"] h2 {color:#FFF!important;font-size:1.35rem!important;letter-spacing:-.03em!important}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span {color:#CBD5E3}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#899AB0!important;font-size:.72rem!important;letter-spacing:.075em}
[data-testid="stSidebar"] hr {border-color:#314257!important;margin:1.1rem 0!important}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.3rem!important}
[data-testid="stSidebar"] [role="radiogroup"] label {border:1px solid transparent!important;border-radius:11px!important;padding:11px 12px!important;transition:background .18s ease,border-color .18s ease!important;cursor:pointer!important}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#21344A!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#B58B51!important;border-color:#C6A36F!important;box-shadow:0 6px 18px #00000022!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {color:#101E30!important;font-weight:800!important}
[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] {width:0!important;min-width:0!important;overflow:hidden!important;opacity:0!important;margin:0!important;padding:0!important}
[data-testid="stSidebar"] [role="radiogroup"] label p {font-weight:600!important;font-size:.87rem!important}
[data-testid="stSidebar"] [data-baseweb="select"] > div {background:#FFFFFF!important;border:1px solid #D7DFE8!important;border-radius:10px!important;min-height:44px}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#17283E!important;-webkit-text-fill-color:#17283E!important}
[role="option"] *,[role="listbox"] * {color:#17283E!important}
[data-testid="stSidebar"] button {background:#22364D!important;border:1px solid #3B526D!important;color:#E8EDF5!important;border-radius:10px!important;min-height:42px;font-weight:700!important}
[data-testid="stSidebar"] button:hover {border-color:#B58B51!important;background:#2D435B!important}
[data-testid="stSidebar"] button * {color:#E8EDF5!important}
[data-testid="stMetric"] {background:white!important;border:1px solid #E6ECF3!important;border-radius:16px!important;padding:18px 20px!important;box-shadow:0 3px 14px #1B314509!important}
[data-testid="stMetricLabel"] p {color:#718197!important;font-size:.78rem!important;font-weight:700!important}
[data-testid="stMetricValue"] {color:#17263C!important;font-family:'Manrope',sans-serif!important;font-weight:800!important;letter-spacing:-.035em!important}
[data-testid="stPlotlyChart"] {background:white!important;border:1px solid #E7ECF3!important;border-radius:17px!important;padding:12px!important;box-shadow:0 4px 18px #1B314507!important}
[data-testid="stDataFrame"] {border:1px solid #E4EAF2;border-radius:14px!important;overflow:hidden}
[data-testid="stExpander"] {background:#FFF!important;border:1px solid #E5EBF2!important;border-radius:14px!important;overflow:hidden!important}
[data-testid="stExpander"] summary {font-weight:700!important;color:#21334A!important}
[data-testid="stAlert"] {border-radius:13px!important}
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] {background:#B58B51!important;color:#111F32!important;border:1px solid #B58B51!important;font-weight:800!important;border-radius:11px!important;min-height:46px!important}
.stButton>button[kind="primary"]:hover {background:#CAA56D!important;border-color:#CAA56D!important}
.stButton>button, .stDownloadButton>button {border-radius:11px!important;font-weight:700!important}
[data-baseweb="tab-list"] {background:#EBEFF5!important;padding:5px!important;border-radius:12px!important;gap:4px!important}
[data-baseweb="tab"] {border-radius:9px!important;font-weight:700!important}
[data-baseweb="tab"][aria-selected="true"] {background:white!important;box-shadow:0 2px 7px #17263C15!important}
[data-baseweb="input"] > div,[data-baseweb="select"] > div {border-radius:10px!important}
.md-hero {background:linear-gradient(115deg,#15253B 0%,#1F3750 65%,#29405A 100%);border-radius:21px;padding:30px 34px;margin:0 0 22px;position:relative;overflow:hidden;box-shadow:0 12px 32px #14233815}
.md-hero:after {content:"";position:absolute;width:230px;height:230px;border:1px solid #FFFFFF18;border-radius:50%;right:-70px;top:-110px;box-shadow:0 0 0 45px #FFFFFF06,0 0 0 95px #FFFFFF04;pointer-events:none}
.md-hero .eyebrow {color:#E4BD7D!important;letter-spacing:.18em;font-size:.69rem;font-weight:800;text-transform:uppercase;margin:0 0 9px}
.md-hero h1 {color:#FFF!important;font-size:2.0rem!important;margin:0 0 8px!important}
.md-hero .sub {color:#CBD7E5!important;font-size:.91rem;max-width:900px;margin:0}
.md-section {display:flex;align-items:center;gap:10px;margin:26px 0 12px;color:#142338;font-size:1.06rem;font-weight:800}
.md-section:before {content:"";height:19px;width:4px;background:#B58B51;border-radius:8px}
.md-note {border:1px solid #E3EAF2;background:#FFFFFF;border-radius:14px;padding:14px 18px;color:#64748B;font-size:.85rem;margin:10px 0 20px}
.md-step {display:inline-block;background:#F2E7D7;color:#79562D;border-radius:999px;font-size:.7rem;padding:5px 10px;font-weight:800;letter-spacing:.04em}
@media(max-width:900px){.block-container{padding:1.2rem .85rem 3rem!important}.md-hero{padding:23px 21px}.md-hero h1{font-size:1.5rem!important}}

/* APP SHELL 2.0 — top navigation, no sidebar, product-led interface */
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {display:none!important}
[data-testid="stAppViewContainer"] > .main {margin-left:0!important}
[data-testid="stHeader"] {background:transparent!important}
.block-container {max-width:1580px!important;padding:1.05rem 3.4rem 5rem!important}
.md-topbrand {display:flex;align-items:center;gap:13px;min-height:68px;padding:4px 0 13px;border-bottom:1px solid #E6EBF2;margin-bottom:13px}
.md-brandmark {width:48px;height:48px;border-radius:15px;background:#162940;color:#fff;display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:800;letter-spacing:-.08em;box-shadow:0 8px 18px #16294023}
.md-brandmark span {color:#D8B479;font-size:11px;margin:0 3px}
.md-brandtext {display:flex;flex-direction:column;gap:3px}
.md-brandtext strong {font-family:Manrope,sans-serif;font-size:14px;color:#162940;letter-spacing:.085em;font-weight:800}
.md-brandtext small {font-size:10px;color:#8794A6;letter-spacing:.14em;font-weight:800}
.md-brandtext small b {color:#C8A46E}
.md-live {margin-left:auto;font-size:10px;font-weight:800;letter-spacing:.11em;color:#5D6D82;display:flex;align-items:center;gap:8px}
.md-live i,.md-context-dot {display:inline-block;width:8px;height:8px;background:#29A47A;border-radius:50%;box-shadow:0 0 0 4px #29A47A15}
.md-live span {background:#EEE7DD;color:#87683D;padding:7px 10px;border-radius:7px;margin-left:10px}
div[class*="st-key-nav_"] button {background:transparent!important;color:#6D7A8B!important;border:1px solid transparent!important;border-radius:10px!important;min-height:44px!important;padding:8px 4px!important;box-shadow:none!important;font-size:12px!important;font-weight:750!important;white-space:nowrap!important}
div[class*="st-key-nav_"] button:hover {background:#E9EDF3!important;color:#162940!important}
div[class*="st-key-nav_"] button p {font-size:12px!important;white-space:nowrap!important}
.md-context {height:38px;display:flex;align-items:center;gap:11px;font-size:11px;font-weight:750;letter-spacing:.08em;color:#8391A3}
.md-context strong {font-size:13px;letter-spacing:0;color:#1B3049;font-weight:800}
.md-context-chevron {font-size:18px;color:#C4CFDB;font-weight:400}
.md-shell-divider {height:1px;background:#E4EAF2;margin:8px 0 27px}
.st-key-replay_tour button {min-height:39px!important;border-radius:10px!important;background:#fff!important;border:1px solid #DFE6EE!important;color:#34465C!important;font-size:12px!important;font-weight:750!important}
.st-key-active_sku [data-baseweb="select"] > div {background:#fff!important;border:1px solid #DDE5EF!important;min-height:39px!important}
.st-key-active_sku [data-baseweb="select"] {box-shadow:0 2px 8px #12233807}
.md-hero {background:linear-gradient(112deg,#13263C 0%,#203A54 78%,#31465C 100%);border-radius:19px;padding:31px 38px;margin:0 0 25px}
[data-testid="stMetric"] {border-radius:14px!important;box-shadow:0 8px 26px #182D4408!important}
[data-testid="stPlotlyChart"] {border-radius:14px!important;box-shadow:0 8px 26px #182D4408!important}
[data-testid="stVerticalBlock"] > div {min-width:0}
@media(max-width:1100px){.block-container{padding:1rem 1.1rem 3rem!important}.md-live{display:none}div[class*="st-key-nav_"] button p{font-size:10px!important;white-space:normal!important}div[class*="st-key-nav_"] button{min-height:50px!important}}
</style>
""", unsafe_allow_html=True)


st.markdown("""<style>
/* V3: clean SaaS workspace — reduce decoration and preserve hierarchy */
.stApp,[data-testid="stAppViewContainer"]{background:#F8FAFC!important}
.block-container{max-width:1350px!important;padding:1.25rem 2.5rem 5rem!important}
.md-hero{background:#fff!important;border:1px solid #E2E8F0!important;box-shadow:none!important;padding:24px 28px!important}
.md-hero:after{display:none!important}
.md-hero h1{color:#0F172A!important}
.md-hero .sub{color:#64748B!important}
.md-hero .eyebrow{color:#64748B!important}
.md-section:before{background:#2563EB!important}
.app-brand{display:flex;align-items:center;gap:12px;padding:8px 0 18px}
.app-symbol{width:39px;height:39px;background:#0F172A;color:white;border-radius:11px;display:grid;place-items:center;font-size:12px;font-weight:800;letter-spacing:.04em}
.app-brand strong{font-size:15px;color:#0F172A;display:block;font-weight:800;line-height:1.2}
.app-brand small{display:block;font-size:11px;color:#64748B;margin-top:2px}
.app-tag{margin-left:auto;font-size:10px;color:#64748B;letter-spacing:.08em;font-weight:700}
.app-rule{height:1px;background:#E2E8F0;margin:13px 0 26px}
.app-eyebrow{font-size:11px;letter-spacing:.11em;color:#64748B;font-weight:800;margin-bottom:6px}
.app-gap{height:12px}
[data-testid="stMetric"]{box-shadow:none!important;border-radius:12px!important;padding:15px 17px!important}
[data-testid="stPlotlyChart"]{box-shadow:none!important;border-radius:12px!important}
.stButton>button[kind="primary"]{background:#0F172A!important;color:#fff!important;border-color:#0F172A!important}
.stButton>button[kind="primary"] p{color:#fff!important}
.stButton>button[kind="primary"]:hover{background:#243B59!important;border-color:#243B59!important}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #E2E8F0!important;border-radius:0!important}
[data-baseweb="tab"][aria-selected="true"]{box-shadow:none!important;border-bottom:2px solid #2563EB!important;border-radius:0!important}
@media(max-width:900px){.block-container{padding:1rem!important}.app-tag{display:none}}
</style>""",unsafe_allow_html=True)

def hero(title, subtitle, eyebrow="MAISON DELORME / STOCK INTELLIGENCE"):
    import html
    st.markdown(
        f'<div class="md-hero"><div class="eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1><p class="sub">{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def section(title):
    import html
    st.markdown(f'<div class="md-section">{html.escape(title)}</div>', unsafe_allow_html=True)


def fmt(value):
    return f"{value:,.0f}".replace(",", " ")


def euro(value):
    return fmt(value) + " USD"


@st.cache_data
def charger_donnees(path, mtime):
    p = pd.read_excel(path, sheet_name="Resume ")
    d = pd.read_excel(path, sheet_name="Demande_Mensuelle", header=None)
    p.columns = p.columns.astype(str).str.strip()
    p["SKU"] = p["SKU"].astype(str).str.strip()
    # Ignorer la ligne de totalisation, qui n'est pas une reference.
    p = p.loc[~p["SKU"].str.casefold().isin(["total", "nan", ""])].copy()
    # Le classeur comporte deux blocs de demande : seul le premier
    # contient les 24 mois complets. Ignorer le second bloc incomplet.
    d = d.loc[d.iloc[:, 0].astype(str).str.strip().isin(p["SKU"])].copy()
    d = d.drop_duplicates(subset=d.columns[0], keep="first")
    return p, d


@st.cache_data(show_spinner=False)
def optimiser_rop(demandes, stock, q_ref, delai, cout, cible):
    """Meilleur stock moyen parmi les politiques testées qui respectent la cible."""
    moyenne = float(np.mean(demandes))
    hebdo = moyenne * 12 / 52
    q_min = max(1, math.ceil(hebdo * 0.5))
    q_max = max(q_min + 1, math.ceil(moyenne * 3), q_ref)
    q_possibles = sorted(set([int(q_ref)] + [max(1, round(x)) for x in np.geomspace(q_min, q_max, 18)]))
    rop_max = max(1, math.ceil(hebdo * delai * 3))
    rop_possibles = sorted(set(max(0, round(x)) for x in np.linspace(0, rop_max, 30)))
    meilleur = None
    meilleur_score = None
    total = 0
    admissibles = 0
    service_max = 0.0
    for q in q_possibles:
        for rop in rop_possibles:
            mouvements, kpi = simuler_rop(
                ventes_mensuelles=list(demandes),
                stock_initial=stock,
                quantite_commande=q,
                point_commande=rop,
                delai_semaines=delai,
                cout_unitaire=cout,
            )
            total += 1
            service = float(kpi["Taux de service (%)"])
            service_max = max(service_max, service)
            if service + 1e-9 < cible:
                continue
            admissibles += 1
            score = (float(kpi["Stock moyen"]), int(kpi["Nombre de commandes"]))
            if meilleur_score is None or score < meilleur_score:
                meilleur_score = score
                meilleur = {"q": q, "rop": rop, "mouvements": mouvements, "kpi": kpi}
    return meilleur, total, admissibles, service_max


dossier = Path(__file__).resolve().parent
fichier = Path(__file__).resolve().parent / "Base de donnees.xlsx"

if not fichier.exists():
    st.error("Fichier Excel introuvable.")
    st.write("Dossier de l'application :", str(dossier))
    st.write("Fichiers présents :", [p.name for p in dossier.iterdir()])
    st.stop()

try:
    produits, demande = charger_donnees(str(fichier), fichier.stat().st_mtime)
except Exception as exc:
    st.error(f"Lecture du fichier Excel impossible : {exc}")
    st.stop()


@st.cache_data(show_spinner=False)
def calculer_abc(produits, demande):
    """ABC selon la valeur demandee sur 24 mois, independante des scenarios."""
    catalogue = produits.copy()
    if catalogue["SKU"].duplicated().any():
        raise ValueError("Des SKU sont en double dans le catalogue.")
    if "Unit cost" not in catalogue.columns:
        raise ValueError("La colonne Unit cost est absente.")
    couts = pd.to_numeric(catalogue["Unit cost"], errors="coerce")
    if couts.isna().any() or (couts < 0).any():
        raise ValueError("Certains couts unitaires sont invalides.")

    demande_sku = demande.iloc[:, 0].astype(str).str.strip()
    valeurs = demande.iloc[:, 3:27].apply(pd.to_numeric, errors="coerce")
    if valeurs.shape[1] != 24 or valeurs.isna().any().any() or (valeurs < 0).any().any():
        raise ValueError("Les historiques doivent comporter 24 mois valides.")
    if demande_sku.duplicated().any():
        raise ValueError("Des SKU sont en double dans la demande.")
    volumes = pd.Series(valeurs.sum(axis=1).to_numpy(), index=demande_sku)
    if not catalogue["SKU"].isin(volumes.index).all():
        raise ValueError("Des produits n'ont pas d'historique de demande.")

    catalogue["Volume 24 mois"] = catalogue["SKU"].map(volumes).astype(float)
    catalogue["Valeur 24 mois (USD)"] = catalogue["Volume 24 mois"] * couts
    catalogue = catalogue.sort_values("Valeur 24 mois (USD)", ascending=False, kind="stable")
    total = float(catalogue["Valeur 24 mois (USD)"].sum())
    if total <= 0:
        raise ValueError("Impossible de classer des produits sans valeur de consommation.")
    parts = catalogue["Valeur 24 mois (USD)"] / total
    # Classe selon la part cumulee AVANT chaque produit, afin de ne pas
    # exclure de A le produit qui franchit le seuil de 80 %.
    avant = parts.cumsum() - parts
    catalogue["ABC"] = np.select(
        [avant < 0.80, avant < 0.95], ["A", "B"], default="C"
    )
    catalogue["Part valeur (%)"] = (parts * 100).round(1)
    return catalogue.sort_index()


try:
    produits = calculer_abc(produits, demande)
except Exception as exc:
    st.error(f"Classification ABC impossible : {exc}")
    st.stop()


# Navigation de l'application
PAGES = [
    "Method Note & Guide",
    "Comparer les politiques",
    "Tableau de bord",
    "Analyse de la demande",
    "Catalogue",
    "Automatic Replenishment",
    "Import Database",
]

if "page_active" not in st.session_state:
    st.session_state.page_active = "Tableau de bord"

# Focused product navigation: three primary jobs; advanced tools are secondary.
MAIN_NAV = [
    ("Tableau de bord", "01  Overview", "home"),
    ("Automatic Replenishment", "02  Purchase planning", "plan"),
    ("Comparer les politiques", "03  Policy analysis", "lab"),
]
SECONDARY_NAV = [
    ("Analyse de la demande", "Demand history"),
    ("Catalogue", "Product catalogue"),
    ("Import Database", "Data management"),
    ("Method Note & Guide", "Method & help"),
]
st.markdown("""<div class="app-brand"><div class="app-symbol">MD</div><div><strong>Maison Delorme</strong><small>Inventory Intelligence</small></div><div class="app-tag">DEMO WORKSPACE · SYNTHETIC DATA</div></div>""", unsafe_allow_html=True)
nav = st.columns([1.05,1.35,1.12,.78], gap="small")
for c, (dest, title, slug) in zip(nav[:3], MAIN_NAV):
    with c:
        if st.button(title, key="main_"+slug, use_container_width=True, type="primary" if st.session_state.page_active==dest else "secondary"):
            st.session_state.page_active=dest
            st.rerun()
with nav[3]:
    with st.popover("More tools  ▾", use_container_width=True):
        for dest, title in SECONDARY_NAV:
            if st.button(title, key="extra_"+dest, use_container_width=True):
                st.session_state.page_active=dest
                st.rerun()
page=st.session_state.page_active
st.markdown('<div class="app-rule"></div>',unsafe_allow_html=True)
# Keep the product selector only on product-specific screens.
if page in ("Comparer les politiques", "Analyse de la demande", "Catalogue"):
    reference=st.selectbox("Product to analyse", produits["SKU"].dropna().tolist(), key="active_sku")
else:
    if "active_sku" not in st.session_state or st.session_state.active_sku not in produits["SKU"].tolist():
        st.session_state.active_sku=produits["SKU"].dropna().iloc[0]
    reference=st.session_state.active_sku

try:
    p = produits.loc[produits["SKU"] == reference].iloc[0]
    nom = str(p["Name"])
    cout = float(p["Unit cost"])
    stock = int(p["Initial Stock"])
    q_ref = int(p["Order_Quantity"])
    rop_ref = max(0, math.ceil(float(p["Reorder_Point"])))
    delai = max(1, math.ceil(float(p["Lead time weeks"])))
    lignes = demande.loc[demande.iloc[:, 0].astype(str).str.strip() == reference]
    ventes = pd.to_numeric(lignes.iloc[0].iloc[3:27], errors="coerce")
    if len(ventes) != 24 or ventes.isna().any() or (ventes < 0).any():
        raise ValueError("Les 24 mois de demande sont incomplets ou invalides.")
    if stock < 0 or q_ref <= 0 or cout < 0:
        raise ValueError("Stock, quantité commandée ou coût unitaire invalides.")
except Exception as exc:
    st.error(f"Données invalides pour {reference} : {exc}")
    st.stop()

ventes_liste = tuple(float(v) for v in ventes)
moyenne = float(ventes.mean())


# The tour is a visual walkthrough only. It never writes simulator parameters.
if "tour_open" not in st.session_state:
    st.session_state.tour_open = True  # Automatically shown once per new session.
if "tour_step" not in st.session_state:
    st.session_state.tour_step = 0

TOUR_TITLES = [
    "Welcome to Stock Intelligence",
    "1 · Choose a product",
    "2 · Explore the data",
    "3 · Configure the simulation",
    "4 · Understand the two policies",
    "5 · Read the results",
    "6 · Try another scenario",
]


def tour_panel(content):
    st.markdown(
        '<div style="background:#fff;border:1px solid #e3e8ef;border-radius:14px;'
        'padding:20px;margin:12px 0;color:#142338">' + content + '</div>',
        unsafe_allow_html=True,
    )


def tour_close():
    st.session_state.tour_open = False


@st.dialog("Maison Delorme · Guided Tour", width="large", on_dismiss=tour_close)
def show_guided_tour():
    step = st.session_state.tour_step
    st.progress(step / 6)
    st.caption(f"STEP {step + 1} OF 7 · INTERACTIVE VISUAL WALKTHROUGH")
    st.subheader(TOUR_TITLES[step])

    if step == 0:
        st.write("Discover the simulator in under three minutes. The screens below are **visual demonstrations**: you do not need to change any settings.")
        tour_panel(
            '<div style="font-size:13px;color:#BE9252;letter-spacing:2px">MAISON DELORME</div>'
            '<div style="font-size:26px;font-weight:750;margin:9px 0">STOCK INTELLIGENCE</div>'
            '<div style="color:#64748b">Excel data → Product → Parameters → ROP vs Periodic Review → KPIs</div>'
        )
        st.info("Goal: reach the desired service level with the lowest average inventory value.")

    elif step == 1:
        st.write("**Look at the sidebar.** This is where you choose the SKU to study. All pages then use the selected product.")
        tour_panel(
            '<div style="background:#142338;border-radius:10px;padding:17px;color:white">'
            '<div style="font-weight:700;margin-bottom:12px">🥃 Maison Delorme</div>'
            '<div style="font-size:12px;opacity:.8">Navigation</div>'
            '<div style="padding:8px">◉ Comparer les politiques</div>'
            '<div style="padding:8px">○ Tableau de bord</div>'
            '<div style="padding:8px">○ Analyse de la demande</div>'
            '<div style="padding:8px">○ Catalogue</div>'
            '<div style="border:2px solid #e5b66b;border-radius:8px;padding:12px;margin-top:12px">'
            '➜ Référence produit &nbsp; <b>' + str(reference) + '</b></div></div>'
        )
        st.caption(f"Current example: {reference} · {nom}. This is a preview, not a clickable selector.")

    elif step == 2:
        st.write("**Explore the three data pages** before comparing stock policies. The chart uses the 24 monthly values for your selected SKU.")
        tab1, tab2, tab3 = st.tabs(["Dashboard", "Demand Analysis", "ABC Catalogue"])
        with tab1:
            x, y = st.columns(2)
            x.metric("Initial stock", f"{stock:,} bottles")
            y.metric("Monthly average demand", f"{moyenne:,.0f} bottles")
            st.caption("Open « Tableau de bord » in the sidebar to find these indicators.")
        with tab2:
            chart = go.Figure(go.Bar(x=list(range(1, 25)), y=list(ventes_liste), marker_color=GOLD))
            chart.update_layout(height=230, margin=dict(l=8,r=8,t=8,b=8), xaxis_title="Month", yaxis_title="Bottles", paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(chart, use_container_width=True, key="tour_demand_chart")
            st.caption("Open « Analyse de la demande » to see the full historical demand chart.")
        with tab3:
            a,b,c=st.columns(3)
            for col, cl in zip((a,b,c),("A","B","C")):
                col.metric(f"Class {cl}", int((produits["ABC"] == cl).sum()))
            st.caption(f"Selected SKU belongs to class {p['ABC']}. ABC is based on 24-month consumption value (quantity × unit cost).")

    elif step == 3:
        st.write("**These are the fields you will see in « Paramètres de simulation ».** The highlighted values below are examples only.")
        tour_panel(
            '<div style="font-weight:700;font-size:18px;margin-bottom:12px">▾ Paramètres de simulation</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
            '<div style="border:2px solid #BE9252;border-radius:8px;padding:10px">Service cible théorique<br><b>95 %</b></div>'
            '<div style="border:1px solid #dbe2eb;border-radius:8px;padding:10px">Délai fournisseur L<br><b>2 semaines</b></div>'
            '<div style="border:1px solid #dbe2eb;border-radius:8px;padding:10px">Stock initial<br><b>500 bouteilles</b></div>'
            '<div style="border:1px solid #dbe2eb;border-radius:8px;padding:10px">Quantité fixe ROP · Q<br><b>200 bouteilles</b></div>'
            '<div style="border:1px solid #dbe2eb;border-radius:8px;padding:10px">Période de revue · R<br><b>4 semaines</b></div>'
            '<div style="border:1px solid #dbe2eb;border-radius:8px;padding:10px">Stock cible · S<br><b>Calculated, editable</b></div>'
            '</div>'
        )
        st.info("The service target is used to size safety stock. It is **not** the same metric as the realized fill rate.")

    elif step == 4:
        st.write("**Watch how the two replenishment rules differ.** This is an illustrative diagram, not the operational simulation.")
        mode = st.segmented_control("Visualize policy", ["ROP", "Periodic Review"], default="ROP", key="tour_policy")
        weeks=list(range(1,13))
        if mode == "ROP":
            values=[180,150,120,90,60,160,130,100,70,170,140,110]
            threshold=75
            explanation="ROP: when inventory position reaches the reorder point, a fixed order of Q bottles is placed. Delivery occurs after lead time."
        else:
            values=[180,150,120,90,190,160,130,100,200,170,140,110]
            threshold=100
            explanation="Periodic Review: every R weeks, an order raises inventory position toward target S. Delivery occurs after lead time."
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=weeks,y=values,mode="lines+markers",name="Illustrative stock",line=dict(color=NAVY,width=3)))
        fig.add_hline(y=threshold,line_dash="dash",line_color=GOLD,annotation_text="Reference level")
        fig.update_layout(height=280,margin=dict(l=5,r=5,t=15,b=10),xaxis_title="Week",yaxis_title="Illustrative bottles",paper_bgcolor="white",plot_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True,key="tour_policy_chart")
        st.info(explanation)
        st.caption("In the actual model, ordering is based on inventory position (including outstanding orders), not just the stock line shown here.")

    elif step == 5:
        st.write("**Here is how to read « Résultats comparés ».** The numbers below are illustrative, not calculated outputs.")
        example = pd.DataFrame({
            "Indicator": ["Realized fill rate", "Lost sales", "Average inventory", "Average inventory value", "Number of orders"],
            "ROP": ["96 %", "40", "180", "3,600 USD", "12"],
            "Periodic Review": ["93 %", "70", "150", "3,000 USD", "8"],
        })
        st.dataframe(example,hide_index=True,use_container_width=True)
        st.success("Example target = 95%: ROP qualifies; Periodic Review does not. ROP is therefore recommended even though it holds more inventory.")
        st.caption("Real recommendation rule: meet the realized service target first, then minimize average stock value; break ties using number of orders.")

    else:
        st.write("**Try the scenario comparison in the real simulator.** You will change only one control: « Service cible théorique (%) ».")
        demo_target=st.segmented_control("Preview service target",["95 %","80 %"],default="95 %",key="tour_target")
        st.metric("Selected theoretical target",demo_target)
        st.markdown("**What to observe:**")
        st.write("1. The calculated safety stock and reorder point may change.\n2. ROP and Periodic Review results may change.\n3. The recommended policy may change or neither may meet the realized target.")
        st.caption("No live simulator parameter has been modified. Demand variability, lead time and other inputs also influence the outcome.")
        st.info("Assumptions: synthetic data; monthly demand spread uniformly over weeks; fixed lead times; unmet demand is lost; ordering and holding costs are not modeled.")

    st.divider()
    left, middle, right = st.columns([1,1,1.3])
    with left:
        if st.button("← Previous",disabled=step==0,use_container_width=True,key="tour_back"):
            st.session_state.tour_step -= 1
            st.rerun()
    with middle:
        if st.button("Skip tutorial",use_container_width=True,key="tour_skip"):
            tour_close()
            st.rerun()
    with right:
        label="Finish & start simulation" if step==6 else "Next →"
        if st.button(label,type="primary",use_container_width=True,key="tour_forward"):
            if step==6:
                tour_close()
                st.session_state.page_active="Comparer les politiques"
            else:
                st.session_state.tour_step += 1
            st.rerun()


if st.session_state.tour_open:
    show_guided_tour()

if page == "Method Note & Guide":
    hero("Guided experience", "Discover every feature through a visual, interactive product tour.", "HELP CENTER / ONBOARDING")
    st.write("A visual, step-by-step tour of Maison Delorme Stock Intelligence.")
    st.info("The tutorial demonstrates the interface without changing your simulator settings.")
    if st.button("▶ Open guided tour",type="primary",use_container_width=True):
        st.session_state.tour_step=0
        st.session_state.tour_open=True
        st.rerun()
    st.caption("You can replay this tutorial anytime using the sidebar button.")

elif page == "Comparer les politiques":
    hero("Inventory policy lab", "Compare reorder point and periodic review policies on the same demand history.", "SIMULATION / POLICY COMPARISON")
    st.caption(f"{reference} · {nom} · Simulation sur 24 mois de demande synthétique")
    st.markdown(badge_abc(p["ABC"]), unsafe_allow_html=True)

    section("01 · Simulation parameters")
    with st.expander("Paramètres de simulation", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cible = st.slider("Service cible théorique (%)", 80, 99, 95, 1)
            delai_test = st.number_input("Délai fournisseur (semaines)", min_value=1, max_value=52, value=int(delai), step=1)
        with c2:
            stock_test = st.number_input("Stock initial (bouteilles)", min_value=0, value=int(stock), step=10)
            q_test = st.number_input("Quantité fixe ROP — Q", min_value=1, value=int(q_ref), step=10)
        with c3:
            periode = st.number_input("Période de revue — R (semaines)", min_value=1, max_value=26, value=4, step=1)
            mode_rop = st.radio("Point de commande", ["Calculé", "Excel"], horizontal=True)

    # Statistiques calculees sur la meme serie hebdomadaire que la simulation.
    # La repartition intra-mensuelle uniforme reste une hypothese simplificatrice.
    semaines_demande = preparer_demande(ventes_liste)
    valeurs_hebdo = np.array([s["Demande"] for s in semaines_demande], dtype=float)
    mu_semaine = float(np.mean(valeurs_hebdo))
    sigma_semaine = float(np.std(valeurs_hebdo, ddof=1))
    z = NormalDist().inv_cdf(cible / 100)
    securite_rop = z * sigma_semaine * math.sqrt(delai_test)
    rop_calcule = max(0, math.ceil(mu_semaine * delai_test + securite_rop))
    rop_utilise = rop_calcule if mode_rop == "Calculé" else rop_ref

    # La revue périodique couvre le délai ET l'intervalle jusqu'à la revue suivante.
    protection = delai_test + periode
    securite_periodique = z * sigma_semaine * math.sqrt(protection)
    cible_periodique_calculee = max(0, math.ceil(mu_semaine * protection + securite_periodique))
    cible_periodique = st.number_input(
        "Stock cible Periodic Review — S (bouteilles)",
        min_value=0, value=int(cible_periodique_calculee), step=10,
        help="Valeur calculée automatiquement à partir de la période de protection R + L. Vous pouvez la modifier."
    )

    rop_hist, rop_kpi = simuler_rop(
        ventes_mensuelles=list(ventes_liste), stock_initial=int(stock_test),
        quantite_commande=int(q_test), point_commande=int(rop_utilise),
        delai_semaines=int(delai_test), cout_unitaire=cout
    )
    pr_hist, pr_kpi = simuler_periodic_review(
        ventes_mensuelles=list(ventes_liste), stock_initial=int(stock_test),
        stock_cible=int(cible_periodique), periode_revision=int(periode),
        delai_semaines=int(delai_test), cout_unitaire=cout
    )

    section("02 · Policy performance")
    tableau = pd.DataFrame([
        {"Indicateur": "Service réalisé (fill rate)", "ROP": f'{rop_kpi["Taux de service (%)"]:.1f} %', "Periodic Review": f'{pr_kpi["Taux de service (%)"]:.1f} %'},
        {"Indicateur": "Demande non satisfaite (bouteilles)", "ROP": fmt(rop_kpi["Demande non satisfaite"]), "Periodic Review": fmt(pr_kpi["Demande non satisfaite"])},
        {"Indicateur": "Semaines avec rupture", "ROP": fmt(rop_kpi["Semaines avec rupture"]), "Periodic Review": fmt(pr_kpi["Semaines avec rupture"])},
        {"Indicateur": "Stock moyen (bouteilles)", "ROP": fmt(rop_kpi["Stock moyen"]), "Periodic Review": fmt(pr_kpi["Stock moyen"])},
        {"Indicateur": "Valeur moyenne du stock", "ROP": euro(rop_kpi["Valeur du stock moyen"]), "Periodic Review": euro(pr_kpi["Valeur du stock moyen"])},
        {"Indicateur": "Nombre de commandes", "ROP": fmt(rop_kpi["Nombre de commandes"]), "Periodic Review": fmt(pr_kpi["Nombre de commandes"])},
    ])
    st.dataframe(tableau, hide_index=True, use_container_width=True)

    # Recommandation fondée sur le service réalisé, puis le stock moyen.
    # Le nombre de commandes départage uniquement les stocks équivalents.
    politiques = [
        ("ROP", rop_kpi),
        ("Periodic Review", pr_kpi),
    ]
    eligibles = [
        (nom_pol, indicateurs)
        for nom_pol, indicateurs in politiques
        if float(indicateurs["Taux de service (%)"]) + 1e-9 >= cible
    ]

    section("03 · Recommendation")
    if not eligibles:
        st.warning(
            f"Aucune politique n'atteint {cible} % de service. "
            "Ajustez les paramètres avant de choisir."
        )
    else:
        gagnant, kpi_gagnant = min(
            eligibles,
            key=lambda item: (
                float(item[1]["Valeur du stock moyen"]),
                int(item[1]["Nombre de commandes"]),
            ),
        )
        autre_nom, kpi_autre = next(
            (nom_pol, indicateurs)
            for nom_pol, indicateurs in politiques
            if nom_pol != gagnant
        )
        st.success(f"Politique recommandée : **{gagnant}**")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Service réalisé", f'{kpi_gagnant["Taux de service (%)"]:.1f} %')
        with m2:
            st.metric("Stock moyen", euro(kpi_gagnant["Valeur du stock moyen"]))
        with m3:
            st.metric("Commandes", fmt(kpi_gagnant["Nombre de commandes"]))

        if float(kpi_autre["Taux de service (%)"]) + 1e-9 < cible:
            st.caption(f"{autre_nom} n'atteint pas le service cible de {cible} %.")
        else:
            ecart_valeur = (
                float(kpi_autre["Valeur du stock moyen"])
                - float(kpi_gagnant["Valeur du stock moyen"])
            )
            ecart_commandes = (
                int(kpi_autre["Nombre de commandes"])
                - int(kpi_gagnant["Nombre de commandes"])
            )
            if ecart_valeur > 0.005:
                justification = f"{euro(ecart_valeur)} de stock moyen en moins"
            else:
                justification = "Valeur moyenne du stock équivalente"
            if ecart_commandes > 0:
                justification += f" ; {ecart_commandes} commande(s) en moins."
            elif ecart_commandes < 0:
                justification += f" ; {-ecart_commandes} commande(s) en plus."
            else:
                justification += " ; même nombre de commandes."
            st.caption(justification)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("ROP utilisé", fmt(rop_utilise) + " bt")
    with c2:
        st.metric("Stock de sécurité ROP", fmt(securite_rop) + " bt")
    with c3:
        st.metric("Stock cible périodique", fmt(cible_periodique) + " bt")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rop_hist["Date"], y=rop_hist["Stock_fin"], name="ROP", line=dict(color=NAVY, width=2)))
    fig.add_trace(go.Scatter(x=pr_hist["Date"], y=pr_hist["Stock_fin"], name="Periodic Review", line=dict(color=GOLD, width=2)))
    fig.update_layout(height=370, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis_title="Date", yaxis_title="Stock disponible (bouteilles)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Comprendre les calculs et les hypothèses"):
        st.markdown(f"""
        **Reorder Point (ROP)** : on commande **Q = {fmt(q_test)}** bouteilles lorsque la position de stock est inférieure ou égale à **ROP = {fmt(rop_utilise)}**.

        - Demande hebdomadaire moyenne : **{mu_semaine:.1f}** bouteilles.
        - Écart-type des demandes hebdomadaires simulées : **{sigma_semaine:.1f}** bouteilles.
        - Coefficient normal *z* pour {cible} % : **{z:.2f}**.
        - Stock de sécurité : `SS = z × σ_semaine × √L` = **{securite_rop:.0f}** bouteilles.
        - Point de commande théorique : `ROP = μ_semaine × L + SS` = **{fmt(rop_calcule)}** bouteilles.

        **Periodic Review (R, S)** : tous les **{periode}** semaines, on commande la quantité nécessaire pour ramener la position de stock à **S = {fmt(cible_periodique)}**.

        - Période de protection : `L + R = {delai_test} + {periode} = {protection}` semaines.
        - Stock de sécurité périodique : `SS = z × σ_semaine × √(L + R)` = **{securite_periodique:.0f}** bouteilles.
        - Stock cible théorique : `S = μ_semaine × (L + R) + SS` = **{fmt(cible_periodique_calculee)}** bouteilles.

        **Attention :** le niveau de service choisi est un objectif de dimensionnement théorique (probabilité de ne pas connaître de rupture sur un cycle, sous hypothèses statistiques), tandis que le **service réalisé** est la part des unités demandées effectivement livrées (*fill rate*). Les deux mesures ne sont pas interchangeables.
        """)
        st.caption("La moyenne et l’écart-type sont calculés sur la série hebdomadaire utilisée par le moteur. Celle-ci est reconstruite à partir de données mensuelles en répartissant la demande uniformément dans chaque mois : la variabilité réelle à l’intérieur des mois est inconnue. La saisonnalité peut fausser la formule normale ; ces stocks de sécurité restent des estimations pédagogiques, non une garantie de service. Délais fixes, ventes perdues non reportées, pas de coût de passation ni de stockage. Les données sont synthétiques. Les résultats doivent être validés sur des cas tests.")
        st.caption("Les commandes sont déclenchées après la demande hebdomadaire ; leur réception intervient après le délai indiqué. La valeur moyenne du stock utilise le coût unitaire du fichier Excel (USD).")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Historique ROP**")
            st.dataframe(rop_hist, hide_index=True, use_container_width=True)
        with c2:
            st.write("**Historique Periodic Review**")
            st.dataframe(pr_hist, hide_index=True, use_container_width=True)

elif page == "Tableau de bord":
    st.markdown('<div class="app-eyebrow">INVENTORY / HOME</div>',unsafe_allow_html=True)
    st.title("Inventory overview")
    st.caption("See the portfolio, identify priorities and move directly to purchasing decisions.")
    x1,x2,x3,x4=st.columns(4)
    x1.metric("Products monitored",len(produits))
    x2.metric("High-value / class A",int((produits["ABC"]=="A").sum()))
    x3.metric("Demand · last 24 months",fmt(produits["Volume 24 mois"].sum())+" bt")
    x4.metric("Historical consumption value",euro(produits["Valeur 24 mois (USD)"].sum()))
    st.markdown('<div class="app-gap"></div>',unsafe_allow_html=True)
    left,right=st.columns([1.65,1],gap="large")
    with left:
        st.subheader("Demand over time")
        # Portfolio demand, not a randomly selected product.
        portfolio_months=pd.to_numeric(demande.iloc[:,3:27].stack(),errors="coerce")
        month_totals=demande.iloc[:,3:27].apply(pd.to_numeric,errors="coerce").sum(axis=0).values
        fig=go.Figure(go.Scatter(x=pd.date_range("2024-10-01",periods=24,freq="MS"),y=month_totals,mode="lines",line=dict(color="#2563EB",width=3),fill="tozeroy",fillcolor="rgba(37,99,235,.08)"))
        fig.update_layout(height=305,margin=dict(l=12,r=12,t=12,b=12),paper_bgcolor="white",plot_bgcolor="white",showlegend=False,xaxis_title=None,yaxis_title="Bottles")
        st.plotly_chart(fig,use_container_width=True)
    with right:
        st.subheader("Product mix")
        counts=produits["ABC"].value_counts().reindex(["A","B","C"],fill_value=0)
        fig=go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=.68,marker=dict(colors=["#2563EB","#8B9BB0","#CBD5E1"]),textinfo="label+value",sort=False))
        fig.update_layout(height=305,margin=dict(l=8,r=8,t=8,b=8),paper_bgcolor="white",showlegend=False,annotations=[dict(text=f"{len(produits)} SKUs",x=.5,y=.5,font_size=16,showarrow=False)])
        st.plotly_chart(fig,use_container_width=True)
    st.subheader("What would you like to do?")
    a,b,c=st.columns(3,gap="medium")
    with a:
        st.markdown("**Generate a purchase plan**")
        st.caption("Recommended quantities, dates, costs and exceptions.")
        if st.button("Open purchase planning →",key="go_plan",type="primary",use_container_width=True):
            st.session_state.page_active="Automatic Replenishment";st.rerun()
    with b:
        st.markdown("**Understand a policy**")
        st.caption("Compare reorder point and periodic review.")
        if st.button("Open policy analysis →",key="go_lab",use_container_width=True):
            st.session_state.page_active="Comparer les politiques";st.rerun()
    with c:
        st.markdown("**Explore the products**")
        st.caption("Find SKUs, consumption and ABC classes.")
        if st.button("Open product catalogue →",key="go_products",use_container_width=True):
            st.session_state.page_active="Catalogue";st.rerun()
    st.info("Demo dataset: historical stock and demand. No live stock feed and no orders transmitted.",icon="ℹ️")

elif page == "Analyse de la demande":
    hero("Demand intelligence", "Explore historical consumption and detect changes in demand.", "ANALYTICS / DEMAND")
    st.caption(f"{reference} · {nom}")
    st.markdown(badge_abc(p["ABC"]), unsafe_allow_html=True)
    section("Historical monthly demand")
    hist = pd.DataFrame({"Mois": pd.date_range("2024-10-01", periods=24, freq="MS"), "Demande": ventes_liste})
    fig = go.Figure(go.Bar(x=hist["Mois"], y=hist["Demande"], marker_color=GOLD))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis_title="Mois", yaxis_title="Bouteilles")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Demande moyenne mensuelle", fmt(moyenne))
    with st.expander("Données mensuelles"):
        st.dataframe(hist, hide_index=True, use_container_width=True)

elif page == "Catalogue":
    hero("Product catalogue", "Explore the complete product portfolio, segmentation and inventory value.", "MASTER DATA / ABC ANALYSIS")
    section("Portfolio segmentation")
    c1, c2, c3 = st.columns(3)
    for colonne, classe in zip((c1, c2, c3), ("A", "B", "C")):
        groupe = produits.loc[produits["ABC"] == classe]
        with colonne:
            fond, texte, bord = ABC_COLORS[classe]
            st.markdown(
                f'<div style="background:{fond};border:1px solid {bord};'
                f'border-radius:12px;padding:16px 18px;color:{texte}">'
                f'<div style="font-size:0.85rem;font-weight:600">Classe {classe}</div>'
                f'<div style="font-size:1.8rem;font-weight:750">{len(groupe)}</div>'
                f'<div style="font-size:0.8rem">produits</div></div>',
                unsafe_allow_html=True,
            )

    f1, f2 = st.columns(2)
    with f1:
        classe_filtre = st.selectbox("Priorité ABC", ["Toutes", "A", "B", "C"])
    with f2:
        categories = ["Toutes"] + sorted(produits["Category"].dropna().unique().tolist())
        categorie = st.selectbox("Catégorie", categories)
    tableau = produits.copy()
    if classe_filtre != "Toutes":
        tableau = tableau.loc[tableau["ABC"] == classe_filtre]
    if categorie != "Toutes":
        tableau = tableau.loc[tableau["Category"] == categorie]
    colonnes = ["SKU", "Name", "Category", "ABC", "Volume 24 mois", "Valeur 24 mois (USD)", "Part valeur (%)"]
    vue_abc = tableau[colonnes].sort_values("Valeur 24 mois (USD)", ascending=False)
    st.dataframe(vue_abc.style.map(couleur_cellule_abc, subset=["ABC"]), hide_index=True, use_container_width=True)
    with st.expander("Méthode ABC et données complètes"):
        st.caption("ABC calculé sur les 24 mois : demande totale × coût unitaire (USD). Produits classés par valeur décroissante ; A jusqu'au franchissement de 80 % de valeur cumulée, B jusqu'à 95 %, C au-delà. La classe ne change pas avec les paramètres de simulation.")
        st.dataframe(tableau, hide_index=True, use_container_width=True)

elif page == "Automatic Replenishment":
    from datetime import date
    from policy_optimizer import compare_and_plan
    st.markdown('<div class="app-eyebrow">PLANNING / DECISION WORKSPACE</div>',unsafe_allow_html=True)
    st.title("Purchase planning")
    st.caption("One workflow: set your scenario → generate recommendations → review exceptions → export.")
    with st.container(border=True):
        st.markdown("**01 / Planning scenario**")
        a,b,c=st.columns(3)
        with a:
            planning_date=st.date_input("Planning start",value=date(2026,10,1),min_value=date(2026,10,1),max_value=date(2027,3,31),key="auto_plan_date")
        with b:
            horizon=st.slider("Horizon (weeks)",4,24,12)
        with c:
            target=st.slider("Target fill rate (%)",80,99,95)
        with st.expander("Advanced settings · economic assumptions",expanded=False):
            st.caption("Illustrative values. Replace with verified company data before operational use.")
            e1,e2,e3=st.columns(3)
            with e1: order_cost=st.number_input("Cost per order (USD)",min_value=0.0,value=25.0,step=5.0)
            with e2: holding_rate=st.number_input("Annual holding rate (%)",min_value=0.0,max_value=100.0,value=20.0,step=1.0)
            with e3: shortage_cost=st.number_input("Lost-sale penalty (USD/bottle)",min_value=0.0,value=10.0,step=1.0)
        params=(planning_date,horizon,target,order_cost,holding_rate,shortage_cost)
        if st.button("Generate purchase recommendations →",type="primary",use_container_width=True,key="generate_plan"):
            try:
                with st.spinner("Comparing policies and calculating proposals..."):
                    comparison,decisions,orders=compare_and_plan(produits,demande,as_of=planning_date,weeks=horizon,service_target=target/100,order_cost=order_cost,annual_holding_rate=holding_rate/100,stockout_cost=shortage_cost)
                st.session_state["policy_optimization_result"]=(comparison,decisions,orders)
                st.session_state["policy_optimization_params"]=params
            except Exception as exc:
                st.error(f"Planning failed: {exc}")
    result=st.session_state.get("policy_optimization_result")
    if result is None:
        st.info("Configure the scenario above, then select Generate purchase recommendations to view the action plan.",icon="ℹ️")
    else:
        comparison,decisions,orders=result
        stale=st.session_state.get("policy_optimization_params")!=params
        if stale: st.warning("Scenario settings changed. Regenerate before using or exporting these results.")
        st.markdown("### 02 / Planning results")
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Products analysed",len(decisions))
        m2.metric("Service target met",int(decisions["Meets target"].sum()))
        m3.metric("Require review",int((~decisions["Meets target"]).sum()))
        m4.metric("Modeled logistics cost",f"${decisions['Total modeled cost (USD)'].sum():,.0f}")
        if (~decisions["Meets target"]).any():
            st.warning("Some products do not meet the service target. Their orders require manual review.")
        tab_orders,tab_exceptions,tab_decisions,tab_detail=st.tabs(["Purchase proposals","Exceptions","Policy decisions","Explain a product"])
        with tab_orders:
            st.caption("Suggested orders only · nothing is transmitted to suppliers.")
            if orders.empty: st.success("No orders suggested for this scenario.")
            else:
                st.dataframe(orders,hide_index=True,use_container_width=True)
                st.download_button("Export purchase proposals · CSV",orders.to_csv(index=False).encode("utf-8-sig"),file_name="maison_delorme_purchase_proposals.csv",mime="text/csv",disabled=stale)
        with tab_exceptions:
            flagged=decisions.loc[~decisions["Meets target"]]
            if flagged.empty: st.success("All selected policies meet the modeled target.")
            else:
                st.caption("Review these SKUs before acting. The model cannot guarantee the target with the tested settings.")
                st.dataframe(flagged,hide_index=True,use_container_width=True)
        with tab_decisions:
            st.caption("One policy per SKU, selected from the modeled scenarios.")
            st.dataframe(decisions,hide_index=True,use_container_width=True)
        with tab_detail:
            sku=st.selectbox("Select a product",decisions["SKU"].tolist(),key="auto_sku")
            st.dataframe(comparison.loc[comparison["SKU"]==sku],hide_index=True,use_container_width=True)
            st.caption("Comparison based on the same forecast. Estimated costs include holding, ordering and stockout penalties; purchase expenditure is excluded.")
        with st.expander("Model assumptions and limitations"):
            st.write("Historical demand ends September 2026. The October 1 stock snapshot is assumed and is not refreshed for later planning dates. Forecasts are estimates. The optimizer searches a limited parameter grid; results are not a global optimum. Existing purchase orders, minimum order quantities, pack sizes and variable lead times are not modeled. Economic inputs are scenario assumptions. Validate stock, suppliers and constraints before using any proposal.")

elif page == "Import Database":
    hero("Database manager", "Prepare a replacement Excel dataset and review its structure before future activation.", "DATA MANAGEMENT / PREVIEW")
    st.markdown('<div class="md-note"><b>Preview feature.</b> Uploads are inspected locally in this session. The live simulator continues to use its existing Excel dataset.</div>',unsafe_allow_html=True)
    section("Upload an Excel workbook")
    uploaded=st.file_uploader("Choose a workbook (.xlsx)",type=["xlsx"],key="db_preview_upload")
    if uploaded is not None:
        try:
            book=pd.ExcelFile(uploaded)
            st.success(f"Workbook received: {uploaded.name}")
            st.write("Sheets detected:",", ".join(book.sheet_names))
            selected_sheet=st.selectbox("Preview sheet",book.sheet_names,key="db_preview_sheet")
            preview=pd.read_excel(book,sheet_name=selected_sheet,nrows=12)
            st.dataframe(preview,hide_index=True,use_container_width=True)
            st.caption("Preview only — no validation or replacement is performed.")
        except Exception as exc:
            st.error(f"Unable to preview workbook: {exc}")
    st.button("Apply new database — available in final integration",disabled=True,use_container_width=True)
