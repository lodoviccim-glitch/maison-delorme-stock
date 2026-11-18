
import math
from datetime import timedelta

import pandas as pd


# ============================================================
# PREPARATION DE LA DEMANDE
# ============================================================

def preparer_demande(ventes_mensuelles):
    """
    Transforme 24 mois de demande en semaines.

    Hypothese :
    la demande est repartie uniformement sur les jours
    de chaque mois, puis agregee par semaine.
    """

    if len(ventes_mensuelles) != 24:
        raise ValueError(
            "La simulation exige exactement 24 mois de demande."
        )

    mois = pd.date_range(
        start="2024-10-01",
        periods=24,
        freq="MS"
    )

    fin_simulation = pd.Timestamp("2026-10-01")

    demande_journaliere = {}

    for date_mois, quantite in zip(
        mois, ventes_mensuelles
    ):
        quantite = float(quantite)

        if not math.isfinite(quantite) or quantite < 0:
            raise ValueError(
                "La demande doit etre positive ou nulle."
            )

        jours = date_mois.days_in_month

        for jour in range(jours):
            date = date_mois + timedelta(days=jour)

            demande_journaliere[date] = (
                quantite / jours
            )

    semaines = []
    debut = mois[0]

    while debut < fin_simulation:
        fin = min(
            debut + timedelta(days=7),
            fin_simulation
        )

        demande_semaine = sum(
            demande_journaliere.get(jour, 0)
            for jour in pd.date_range(
                debut,
                fin - timedelta(days=1),
                freq="D"
            )
        )

        semaines.append({
            "Date": debut,
            "Demande_theorique": demande_semaine
        })

        debut = fin

    cumul_demande = 0
    cumul_arrondi = 0

    for semaine in semaines:
        cumul_demande += semaine["Demande_theorique"]

        nouveau_cumul = round(cumul_demande)

        semaine["Demande"] = (
            nouveau_cumul - cumul_arrondi
        )

        cumul_arrondi = nouveau_cumul

    return semaines


# ============================================================
# CALCUL DES INDICATEURS
# ============================================================

def calculer_kpi(resultats, cout_unitaire):
    """
    Calcule les memes indicateurs pour les deux politiques.
    """

    total_demande = int(
        resultats["Demande"].sum()
    )

    total_servi = int(
        resultats["Ventes"].sum()
    )

    total_rupture = int(
        resultats["Rupture"].sum()
    )

    taux_service = (
        total_servi / total_demande * 100
        if total_demande > 0
        else 100.0
    )

    stock_moyen = (
        (
            resultats["Stock_debut"]
            + resultats["Stock_fin"]
        ) / 2
    ).mean()

    semaines_rupture = int(
        (resultats["Rupture"] > 0).sum()
    )

    nombre_commandes = int(
        (resultats["Commande"] > 0).sum()
    )

    stock_final = int(
        resultats["Stock_fin"].iloc[-1]
    )

    return {
        "Taux de service (%)": taux_service,
        "Demande totale": total_demande,
        "Demande satisfaite": total_servi,
        "Demande non satisfaite": total_rupture,
        "Semaines avec rupture": semaines_rupture,
        "Stock moyen": stock_moyen,
        "Valeur du stock moyen": (
            stock_moyen * cout_unitaire
        ),
        "Nombre de commandes": nombre_commandes,
        "Stock final": stock_final
    }


# ============================================================
# POLITIQUE 1 : REORDER POINT (ROP)
# ============================================================

def simuler_rop(
    ventes_mensuelles,
    stock_initial,
    quantite_commande,
    point_commande,
    delai_semaines,
    cout_unitaire=0
):
    """
    Politique a point de commande.

    Lorsque la position de stock <= ROP :
    une commande de quantite fixe Q est lancee.

    La position de stock comprend :
    stock disponible + commandes en cours.
    """

    semaines = preparer_demande(
        ventes_mensuelles
    )

    if stock_initial < 0:
        raise ValueError(
            "Le stock initial ne peut pas etre negatif."
        )

    if quantite_commande <= 0:
        raise ValueError(
            "La quantite commandee doit etre positive."
        )

    if delai_semaines < 1:
        raise ValueError(
            "Le delai doit etre d'au moins une semaine."
        )

    stock = int(round(stock_initial))
    q = int(math.ceil(quantite_commande))
    rop = int(math.ceil(point_commande))
    delai = int(math.ceil(delai_semaines))

    commandes_en_cours = []
    historique = []

    for numero, semaine in enumerate(semaines):

        date = semaine["Date"]
        demande = int(semaine["Demande"])

        # Reception des commandes arrivees
        reception = 0
        commandes_restantes = []

        for commande in commandes_en_cours:
            if commande["arrivee"] <= numero:
                reception += commande["quantite"]
            else:
                commandes_restantes.append(commande)

        commandes_en_cours = commandes_restantes

        stock += reception
        stock_debut = stock

        # Satisfaction de la demande
        ventes = min(stock, demande)
        rupture = demande - ventes
        stock -= ventes

        # Position de stock
        en_commande = sum(
            c["quantite"]
            for c in commandes_en_cours
        )

        position_stock = stock + en_commande

        # Decision de commande
        quantite_lancee = 0

        if position_stock <= rop:
            quantite_lancee = q

            commandes_en_cours.append({
                "arrivee": numero + delai,
                "quantite": q
            })

        historique.append({
            "Date": date,
            "Demande": demande,
            "Stock_debut": stock_debut,
            "Ventes": ventes,
            "Rupture": rupture,
            "Reception": reception,
            "Commande": quantite_lancee,
            "Stock_fin": stock,
            "Position_stock": position_stock
        })

    resultats = pd.DataFrame(historique)

    kpi = calculer_kpi(
        resultats,
        cout_unitaire
    )

    return resultats, kpi


# ============================================================
# POLITIQUE 2 : PERIODIC REVIEW
# ============================================================

def simuler_periodic_review(
    ventes_mensuelles,
    stock_initial,
    stock_cible,
    periode_revision,
    delai_semaines,
    cout_unitaire=0
):
    """
    Politique de revision periodique (R, S).

    R = periode de revision, en semaines.
    S = stock cible.

    Toutes les R semaines :
    si la position de stock est inferieure a S,
    une commande est lancee pour atteindre S.

    La quantite commandee est variable.
    """

    semaines = preparer_demande(
        ventes_mensuelles
    )

    if stock_initial < 0:
        raise ValueError(
            "Le stock initial ne peut pas etre negatif."
        )

    if stock_cible < 0:
        raise ValueError(
            "Le stock cible ne peut pas etre negatif."
        )

    if periode_revision < 1:
        raise ValueError(
            "La periode de revision doit etre positive."
        )

    if delai_semaines < 1:
        raise ValueError(
            "Le delai doit etre d'au moins une semaine."
        )

    stock = int(round(stock_initial))
    cible = int(math.ceil(stock_cible))
    periode = int(math.ceil(periode_revision))
    delai = int(math.ceil(delai_semaines))

    commandes_en_cours = []
    historique = []

    for numero, semaine in enumerate(semaines):

        date = semaine["Date"]
        demande = int(semaine["Demande"])

        # Reception des commandes arrivees
        reception = 0
        commandes_restantes = []

        for commande in commandes_en_cours:
            if commande["arrivee"] <= numero:
                reception += commande["quantite"]
            else:
                commandes_restantes.append(commande)

        commandes_en_cours = commandes_restantes

        stock += reception
        stock_debut = stock

        # Satisfaction de la demande
        ventes = min(stock, demande)
        rupture = demande - ventes
        stock -= ventes

        # Position de stock
        en_commande = sum(
            c["quantite"]
            for c in commandes_en_cours
        )

        position_stock = stock + en_commande

        # Decision uniquement aux dates de revision
        quantite_lancee = 0

        if numero % periode == 0:

            quantite_lancee = max(
                0,
                cible - position_stock
            )

            if quantite_lancee > 0:
                commandes_en_cours.append({
                    "arrivee": numero + delai,
                    "quantite": quantite_lancee
                })

        historique.append({
            "Date": date,
            "Demande": demande,
            "Stock_debut": stock_debut,
            "Ventes": ventes,
            "Rupture": rupture,
            "Reception": reception,
            "Commande": quantite_lancee,
            "Stock_fin": stock,
            "Position_stock": position_stock
        })

    resultats = pd.DataFrame(historique)

    kpi = calculer_kpi(
        resultats,
        cout_unitaire
    )

    return resultats, kpi
