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
.stApp {background:#F5F7FA}
.block-container {max-width:1250px;padding-top:2rem}
[data-testid="stSidebar"] {background:#142338}
[data-testid="stSidebar"] * {color:#F5F7FA}
[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] [data-baseweb="input"] *,
[data-testid="stSidebar"] input {color:#18283C!important;-webkit-text-fill-color:#18283C!important}
[data-testid="stSidebar"] [data-baseweb="select"] > div {background:white!important}
[role="option"] *,[role="listbox"] * {color:#18283C!important}
h1,h2,h3 {color:#142338}
[data-testid="stMetric"] {background:white;border:1px solid #E6EAF0;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"] {color:#6B7788}
[data-testid="stMetricValue"] {color:#142338}
[data-testid="stPlotlyChart"] {background:white;border:1px solid #E6EAF0;border-radius:12px;padding:8px}
</style>
""", unsafe_allow_html=True)


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
]

if "page_active" not in st.session_state:
    st.session_state.page_active = "Method Note & Guide"

with st.sidebar:
    st.markdown("## 🥃 Maison Delorme")
    st.caption("STOCK INTELLIGENCE")
    st.divider()

    page = st.radio(
        "Navigation",
        PAGES,
        key="page_active"
    )

    st.divider()
    reference = st.selectbox(
        "Référence produit",
        produits["SKU"].dropna().tolist()
    )
    st.caption("VERSION 1.2 · IDENTITÉ ABC")

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


if page == "Method Note & Guide":
    # Independent learning space: never changes the operational simulator.
    st.markdown("""
    <style>
    .guide-hero{background:linear-gradient(115deg,#142338,#263f5c);color:white;
      padding:28px 32px;border-radius:18px;margin-bottom:18px}
    .guide-hero h1{color:white!important;margin:5px 0 10px;font-size:2.1rem}
    .guide-hero p{color:#dce5ef;margin:0;line-height:1.6}
    .guide-eyebrow{color:#e5bd7e;letter-spacing:2px;font-size:12px;font-weight:700}
    .guide-card{background:white;border:1px solid #e5eaf0;border-radius:14px;
      padding:18px 20px;margin:8px 0 14px}
    .guide-card h4{margin:0 0 7px;color:#142338}
    .guide-card p{margin:0;color:#526176;line-height:1.6}
    .guide-flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0 20px}
    .guide-pill{background:#e9eef4;border-radius:10px;padding:10px 14px;
      color:#142338;font-weight:600;font-size:13px}
    .guide-arrow{color:#be9252;font-weight:700}
    </style>
    <div class="guide-hero">
      <div class="guide-eyebrow">MAISON DELORME · STOCK INTELLIGENCE</div>
      <h1>Learn the simulator, step by step.</h1>
      <p>Six short interactive lessons. Discover how inventory decisions work,
      explore real product data and launch your own comparison.</p>
    </div>
    """, unsafe_allow_html=True)

    guide_names = ["01 · Choose a product", "02 · Explore the data",
                   "03 · Set the parameters", "04 · Compare the policies",
                   "05 · Read the KPIs", "06 · Try a scenario"]
    if "guide_step" not in st.session_state:
        st.session_state.guide_step = 0
    guide_step = st.radio("LEARNING PATH", list(range(6)),
                          format_func=lambda i: guide_names[i],
                          horizontal=True, key="guide_step")
    st.progress((guide_step + 1) / 6, text=f"Lesson {guide_step + 1} of 6")

    if guide_step == 0:
        st.subheader("Choose a product")
        st.write("Start with a product in the left sidebar. Every product has its own demand, stock and supplier settings.")
        a, b, c = st.columns(3)
        a.metric("Selected product", reference)
        b.metric("Initial stock", f"{fmt(stock)} bottles")
        c.metric("Supplier lead time", f"{delai} weeks")
        st.markdown(f"""<div class="guide-card"><h4>{nom}</h4>
          <p>Unit cost: <b>{cout:,.2f} USD</b> · Order quantity: <b>{q_ref} bottles</b><br>
          Historical demand: <b>24 months</b> · ABC class: <b>{p['ABC']}</b></p></div>""",
          unsafe_allow_html=True)
        st.info("Try selecting another product in the sidebar: these values will change immediately. The Excel data stays unchanged.")

    elif guide_step == 1:
        st.subheader("Explore demand and ABC classification")
        st.write("The simulator uses 24 months of synthetic demand for 20 products. Demand is not the same every month.")
        demand_chart = go.Figure(go.Bar(
            x=list(range(1, 25)), y=list(ventes_liste),
            marker_color=GOLD, name="Monthly demand"))
        demand_chart.add_hline(y=moyenne, line_dash="dash", line_color=NAVY,
                               annotation_text="Monthly average")
        demand_chart.update_layout(height=290, xaxis_title="Month", yaxis_title="Bottles",
                                   margin=dict(l=10, r=10, t=20, b=10),
                                   paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(demand_chart, use_container_width=True)
        st.markdown("**ABC = total demand over 24 months × unit cost.** Higher-value products receive priority.")
        abc_counts = produits["ABC"].value_counts()
        abc_chart = go.Figure(go.Bar(
            x=["A", "B", "C"], y=[int(abc_counts.get(x, 0)) for x in "ABC"],
            marker_color=["#176B43", "#C39A37", "#D48446"],
            text=[int(abc_counts.get(x, 0)) for x in "ABC"], textposition="auto"))
        abc_chart.update_layout(height=230, yaxis_title="Number of products",
                                margin=dict(l=10, r=10, t=10, b=10),
                                paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(abc_chart, use_container_width=True)
        st.caption("The ABC groups are based on cumulative consumption value (approximately 80% / 15% / 5%), not on the number of products.")

    elif guide_step == 2:
        st.subheader("Understand the reorder point")
        st.write("Experiment with a small example to see why demand and supplier lead time matter.")
        st.caption("EDUCATIONAL EXAMPLE — independent of the real simulation")
        a, b, c = st.columns(3)
        with a:
            demo_demand = st.slider("Weekly demand · bottles", 5, 50, 20, 5, key="gdemand")
        with b:
            demo_lead = st.slider("Lead time · weeks", 1, 5, 2, key="glead")
        with c:
            demo_buffer = st.slider("Safety buffer · bottles", 0, 50, 15, 5, key="gbuffer")
        demo_expected = demo_demand * demo_lead
        demo_rop = demo_expected + demo_buffer
        x, y, zcol = st.columns(3)
        x.metric("Expected demand during lead time", f"{demo_expected} bt")
        y.metric("Safety buffer", f"{demo_buffer} bt")
        zcol.metric("Illustrative reorder point", f"{demo_rop} bt")
        fig_demo = go.Figure(go.Bar(
            x=["Expected demand", "Safety buffer"],
            y=[demo_expected, demo_buffer],
            marker_color=[NAVY, GOLD],
            text=[demo_expected, demo_buffer], textposition="auto"))
        fig_demo.update_layout(height=260, yaxis_title="Bottles", margin=dict(l=10,r=10,t=10,b=10),
                               paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig_demo, use_container_width=True)
        st.success(f"Reorder point = {demo_expected} + {demo_buffer} = {demo_rop} bottles. A higher demand or longer lead time raises the threshold.")
        with st.expander("How does the actual application calculate safety stock?"):
            st.markdown("**Safety stock = z × weekly demand standard deviation × √lead time**")
            st.write("The coefficient z depends on the theoretical service target. The real application calculates the buffer from the selected product's weekly demand variability; it is not the manually chosen buffer above.")
            st.write("For Periodic Review, the protection period is **lead time + review period (L + R)**.")

    elif guide_step == 3:
        st.subheader("Two ways to replenish stock")
        st.write("Both policies serve the same demand, but they decide **when to order** differently.")
        left, right = st.columns(2)
        with left:
            st.markdown("""<div class="guide-card"><h4>ROP · Reorder Point</h4>
            <p>Check stock each week.<br>When inventory position reaches the threshold,
            place an order for a fixed quantity <b>Q</b>.</p></div>""", unsafe_allow_html=True)
        with right:
            st.markdown("""<div class="guide-card"><h4>Periodic Review · (R, S)</h4>
            <p>Check inventory every <b>R</b> weeks.<br>At each review, order enough
            to bring inventory position up to target <b>S</b>.</p></div>""", unsafe_allow_html=True)
        st.markdown("**See the difference over 8 illustrative weeks**")
        demo_week = st.slider("Advance the example to week", 1, 8, 4, key="gweek")
        weeks = list(range(1, 9))
        rop_levels = [85, 68, 51, 34, 79, 62, 45, 90]
        periodic_levels = [85, 68, 51, 89, 72, 55, 38, 83]
        fig_policies = go.Figure()
        fig_policies.add_trace(go.Scatter(x=weeks[:demo_week], y=rop_levels[:demo_week],
                            mode="lines+markers", name="ROP example", line=dict(color=NAVY, width=3)))
        fig_policies.add_trace(go.Scatter(x=weeks[:demo_week], y=periodic_levels[:demo_week],
                            mode="lines+markers", name="Periodic example", line=dict(color=GOLD, width=3)))
        fig_policies.update_layout(height=320, xaxis_title="Week", yaxis_title="Illustrative stock level (bottles)",
                                   xaxis=dict(range=[1, 8], dtick=1), yaxis=dict(range=[0, 110]),
                                   margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig_policies, use_container_width=True)
        st.caption("Conceptual illustration only: the curves are fixed teaching examples, not the output of the simulation engine. Order arrivals are simplified.")
        st.info("ROP responds to a stock threshold. Periodic Review responds to a scheduled review date.")

    elif guide_step == 4:
        st.subheader("Learn to read the results")
        st.write("The comparison table tells you whether customer demand is served and how much inventory each policy requires.")
        kpi_choices = {
            "Fill rate": ("98%", "Out of 100 bottles requested, 98 are delivered. Higher is better."),
            "Lost sales": ("2 bottles", "Demand that cannot be fulfilled is lost, not delivered later. Lower is better."),
            "Average inventory": ("60 bottles", "The typical number of bottles held during the simulation. Lower reduces stock tied up."),
            "Average inventory value": ("1,200 USD", "Average inventory multiplied by the product's unit cost. Lower means less capital tied up."),
            "Number of orders": ("12 orders", "How many replenishment orders were placed. Fewer is not always better if service suffers."),
            "Weeks with stockouts": ("3 weeks", "Weeks when customer demand exceeded available stock. Lower is better."),
        }
        selected_kpi = st.selectbox("Choose a KPI to understand", list(kpi_choices), key="gkpi")
        kpi_example, kpi_explain = kpi_choices[selected_kpi]
        st.metric(f"Illustrative {selected_kpi.lower()}", kpi_example)
        st.info(kpi_explain)
        st.markdown("**How the recommendation works**")
        st.markdown("""<div class="guide-flow">
          <span class="guide-pill">1 · Meet the service target</span>
          <span class="guide-arrow">→</span>
          <span class="guide-pill">2 · Minimize inventory value</span>
          <span class="guide-arrow">→</span>
          <span class="guide-pill">3 · Tie-break: fewer orders</span>
        </div>""", unsafe_allow_html=True)
        st.warning("If neither policy meets the target, the application does not recommend a winner. The theoretical service target and the realized fill rate are different measures.")

    else:
        st.subheader("Ready for a real scenario?")
        st.write("Now use the actual simulator. The parameters below are suggestions for a first experiment.")
        st.markdown("""<div class="guide-card"><h4>Your first experiment</h4>
          <p><b>1.</b> Open Compare Inventory Policies.<br>
          <b>2.</b> Set theoretical service target to <b>95%</b>.<br>
          <b>3.</b> Observe safety stock, fill rate and average inventory value.<br>
          <b>4.</b> Reduce the target to <b>80%</b>.<br>
          <b>5.</b> Compare both policies again. Restore 95% if needed.</p></div>""",
          unsafe_allow_html=True)
        st.info("The results are recalculated by the real simulation engine. The guide's examples never change the operational data.")
        if st.button("Start Simulation", type="primary", use_container_width=True, key="guide_start"):
            st.session_state.page_active = "Comparer les politiques"
            st.rerun()

    st.divider()
    with st.expander("Methodology & limitations · Read before interpreting results"):
        st.markdown("""
        **Data:** 20 products and 24 months of synthetic demand from Excel. ABC classes use
        24-month demand multiplied by unit cost, ranked by cumulative value.

        **Simulation:** Monthly demand is distributed uniformly into weekly demand.
        Supplier lead times are fixed, and unmet demand is counted as lost sales.
        Orders arrive after the selected lead time.

        **Stock parameters:** The application estimates safety stock with a normal-distribution
        coefficient, weekly demand variability and lead time. ROP covers expected demand during
        lead time plus safety stock. Periodic Review covers lead time plus review interval.

        **Important distinction:** The selected service target is a theoretical sizing input;
        realized fill rate is the share of actual demand fulfilled. They are not interchangeable.

        **Limitations:** Synthetic data, simplified weekly demand, fixed lead times, and no
        ordering or holding costs. This is an educational decision-support prototype.
        """)
    nav_left, nav_right = st.columns(2)
    with nav_left:
        if st.button("← Previous lesson", disabled=guide_step == 0,
                     use_container_width=True, key="guide_prev"):
            st.session_state.guide_step -= 1
            st.rerun()
    with nav_right:
        if st.button("Next lesson →", disabled=guide_step == 5,
                     use_container_width=True, key="guide_next"):
            st.session_state.guide_step += 1
            st.rerun()

elif page == "Comparer les politiques":
    st.title("Comparaison des politiques de stock")
    st.caption(f"{reference} · {nom} · Simulation sur 24 mois de demande synthétique")
    st.markdown(badge_abc(p["ABC"]), unsafe_allow_html=True)

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

    st.markdown("### Résultats comparés")
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

    st.markdown("### Recommandation")
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
    st.title("Tableau de bord")
    st.caption(f"{reference} · {nom}")
    st.markdown(badge_abc(p["ABC"]), unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Stock initial", fmt(stock))
    with c2:
        st.metric("Demande moyenne mensuelle", fmt(moyenne))
    with c3:
        st.metric("Couverture initiale", f"{stock / moyenne:.1f} mois" if moyenne > 0 else "—")
    st.info("La page Comparer les politiques permet de tester ROP et Periodic Review sur le même historique.")

elif page == "Analyse de la demande":
    st.title("Analyse de la demande")
    st.caption(f"{reference} · {nom}")
    st.markdown(badge_abc(p["ABC"]), unsafe_allow_html=True)
    hist = pd.DataFrame({"Mois": pd.date_range("2024-10-01", periods=24, freq="MS"), "Demande": ventes_liste})
    fig = go.Figure(go.Bar(x=hist["Mois"], y=hist["Demande"], marker_color=GOLD))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis_title="Mois", yaxis_title="Bouteilles")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Demande moyenne mensuelle", fmt(moyenne))
    with st.expander("Données mensuelles"):
        st.dataframe(hist, hide_index=True, use_container_width=True)

else:
    st.title("Catalogue produits")
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
