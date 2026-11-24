"""Étape 4 : tableau de bord HTML autonome (plotly embarqué, ouvrable hors connexion).

Entrée  : data/subventions_final.csv (produit par categorize.py)
Sortie  : dashboard.html
"""
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

from categorize import GRILLE, NON_VENTILE

RACINE = Path(__file__).parent
SOURCE = RACINE / "data" / "subventions_final.csv"
SORTIE = RACINE / "dashboard.html"

SOURCE_URL = "https://www.data.gouv.fr/datasets/subventions-aux-personnes-morales/"
DATE_TELECHARGEMENT = "23 novembre 2026"

# ---------------------------------------------------------------- Palette
# Palette catégorielle de référence (ordre fixe, validé pour les paires adjacentes),
# avec une variante claire et une variante sombre. « Non ventilé » est en gris neutre.
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"],
    "dark":  ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9"],
}
GRIS_NV = {"light": "#898781", "dark": "#898781"}
THEME = {
    "light": dict(surface="#fcfcfb", page="#f9f9f7", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", border="rgba(11,11,11,0.10)"),
    "dark":  dict(surface="#1a1a19", page="#0d0d0d", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                  grid="#2c2c2a", axis="#383835", border="rgba(255,255,255,0.10)"),
}
# ---------------------------------------------------------------- Groupes d'affichage
# « Solidarités humaines » est découpée en trois groupes (colonne politique_affichage) ;
# politique_publique et politique_sectorielle ne sont pas modifiées.
SH = "SOLIDARITÉS HUMAINES"
_SECT = {ps.split(" (")[0]: ps for ps in GRILLE[SH]}
EF, IDS = "Enfance et famille", "Insertion et développement social"
AUTONOMIE = "Autonomie (personnes âgées et personnes handicapées)"
SH_GROUPES = {_SECT["Enfance et famille"]: EF, _SECT["Insertion et développement social"]: IDS,
              _SECT["Personnes âgées"]: AUTONOMIE, _SECT["Personnes handicapées"]: AUTONOMIE}
AUTRES = [p for p in GRILLE if p != SH]
GROUPES = [EF, IDS, AUTONOMIE, *AUTRES, NON_VENTILE]

# Couleurs : les trois groupes Solidarités sont trois nuances d'un même bleu (ce sont des
# subdivisions d'une même politique, et la palette n'a que 8 teintes) ; les six autres
# politiques gardent les teintes 2 à 7 dans l'ordre fixe ; « Non ventilé » reste gris.
BLEUS = {"light": ["#104281", "#2a78d6", "#86b6ef"], "dark": ["#184f95", "#3987e5", "#9ec5f4"]}
COULEUR_CLE = ({EF: "b0", IDS: "b1", AUTONOMIE: "b2"}
               | {p: f"s{i + 1}" for i, p in enumerate(AUTRES)} | {NON_VENTILE: "nv"})

# Insertion découpée, subvention par subvention selon l'objet, en deux sous-groupes.
# Utilisé uniquement dans le graphique d'évolution et les tableaux de bénéficiaires ;
# politique_affichage (et donc l'analyse du renouvellement) garde les trois groupes.
OBJET_FSE = "Subventions FSE"
MORBIHAN_HABITAT = "MORBIHAN HABITAT"  # retiré d'Autonomie dans une courbe de comparaison
IDS_FSE = "Insertion – fonds européens (FSE)"
IDS_HORS = "Insertion – hors FSE"
GROUPES_EVOL = [EF, IDS_FSE, IDS_HORS, AUTONOMIE, *AUTRES, NON_VENTILE]
COULEUR_CLE |= {IDS_FSE: "b1", IDS_HORS: "b1"}  # même bleu que le groupe Insertion


def groupe_evolution(df: pd.DataFrame) -> pd.Series:
    """politique_affichage, avec Insertion séparée en FSE / hors FSE selon l'objet."""
    ins = df["politique_affichage"] == IDS
    fse = df["objet"] == OBJET_FSE
    if (fse & ~ins).any():
        raise ValueError(f"Des subventions « {OBJET_FSE} » sont hors du groupe Insertion")
    return df["politique_affichage"].mask(ins & fse, IDS_FSE).mask(ins & ~fse, IDS_HORS)


def couleurs(mode: str) -> dict:
    c = {f"s{i}": h for i, h in enumerate(SERIES[mode])}
    c |= {f"b{i}": h for i, h in enumerate(BLEUS[mode])}
    c["nv"] = GRIS_NV[mode]
    return c


def politique_affichage(df: pd.DataFrame) -> pd.Series:
    sh = df["politique_publique"] == SH
    groupe = df.loc[sh, "politique_sectorielle"].map(SH_GROUPES)
    if groupe.isna().any():
        raise ValueError(f"Politiques sectorielles non prévues : {set(df.loc[sh][groupe.isna()]['politique_sectorielle'])}")
    return df["politique_publique"].where(~sh, groupe)


def libelle(p: str) -> str:
    """« SOLIDARITÉ DES TERRITOIRES » -> « Solidarité des territoires » (les autres inchangés)."""
    return p[0] + p[1:].lower() if p.isupper() else p


def fr(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def meur(x: float) -> str:
    return f"{fr(x / 1e6)} M€"


# ---------------------------------------------------------------- Mise en forme commune
L = THEME["light"]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def mise_en_page(fig: go.Figure, hauteur: int, **kw) -> go.Figure:
    fig.update_layout(
        height=hauteur, margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor=L["surface"], plot_bgcolor=L["surface"],
        font=dict(family=FONT, size=13, color=L["ink2"]),
        hoverlabel=dict(font=dict(family=FONT, size=13)),
        separators=", ", **kw,
    )
    fig.update_xaxes(showgrid=False, linecolor=L["axis"], zerolinecolor=L["axis"],
                     tickfont=dict(color=L["muted"]))
    fig.update_yaxes(gridcolor=L["grid"], linecolor=L["axis"], zerolinecolor=L["axis"],
                     tickfont=dict(color=L["muted"]))
    return fig


def table_html(df: pd.DataFrame) -> str:
    tete = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    lignes = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in r) + "</tr>"
                     for r in df.itertuples(index=False))
    return f'<table><thead><tr>{tete}</tr></thead><tbody>{lignes}</tbody></table>'


# ---------------------------------------------------------------- Graphiques
def fig_empile(t: pd.DataFrame) -> go.Figure:
    """Montants par année, empilés par politique publique."""
    c = couleurs("light")
    fig = go.Figure()
    annees = [str(a) for a in t.columns]
    for p in GROUPES:
        if p not in t.index:
            continue
        v = t.loc[p]
        fig.add_bar(
            x=annees, y=v / 1e6, name=libelle(p), meta=COULEUR_CLE[p],
            marker=dict(color=c[COULEUR_CLE[p]], line=dict(color=L["surface"], width=2)),
            customdata=[meur(x) for x in v],
            hovertemplate="%{x} · " + escape(libelle(p)) + "<br><b>%{customdata}</b><extra></extra>",
        )
    tot = t.sum()
    for i, x in enumerate(tot):  # position par rang : « 2020 » serait lu comme l'indice 2020
        fig.add_annotation(x=i, y=x / 1e6, text=f"<b>{meur(x)}</b>", showarrow=False, yshift=12,
                           font=dict(color=L["ink"]))
    fig.update_layout(barmode="stack", bargap=0.45, barcornerradius=4,
                      legend=dict(orientation="h", y=-0.12, x=0, traceorder="normal",
                                  font=dict(color=L["ink2"])))
    fig.update_yaxes(title_text="M€", title_font=dict(color=L["muted"]), rangemode="tozero")
    fig.update_xaxes(type="category")
    return mise_en_page(fig, 480)


def fig_multiples(t: pd.DataFrame, comparaisons: dict | None = None) -> go.Figure:
    """Un petit graphique par politique publique, chacun avec sa propre échelle."""
    c = couleurs("light")
    pols = [p for p in GROUPES_EVOL if p in t.index]
    ncol = 4
    nrow = -(-len(pols) // ncol)
    def titre(p: str, largeur: int = 26) -> str:
        """Coupe les titres longs sur deux lignes pour éviter les chevauchements."""
        mots, l1 = libelle(p).split(), ""
        while mots and len(l1 + " " + mots[0]) <= largeur:
            l1 = (l1 + " " + mots.pop(0)).strip()
        return l1 + ("<br>" + " ".join(mots) if mots else "")

    fig = make_subplots(rows=nrow, cols=ncol, subplot_titles=[titre(p) for p in pols],
                        vertical_spacing=0.2, horizontal_spacing=0.06)
    annees = [str(a) for a in t.columns]
    for i, p in enumerate(pols):
        r, col = i // ncol + 1, i % ncol + 1
        v = t.loc[p] / 1e6
        if comparaisons and p in comparaisons:
            # Courbe de comparaison en gris, tracée SOUS la courbe principale : elle n'apparaît
            # que là où les deux diffèrent ; étiquette courte au premier écart.
            nom, court_nom, w = comparaisons[p]
            w = w.reindex(t.columns, fill_value=0) / 1e6
            ecart = [k for k, (a, b) in enumerate(zip(v, w)) if abs(a - b) > 0.005]
            if ecart:
                # Annotation dans la zone vide sous les courbes, flèche vers le premier écart.
                # x = rang de la catégorie (une étiquette « 2020 » serait lue comme l'indice 2020).
                k = ecart[0]
                fig.add_annotation(x=k, y=w.iloc[k], text=f"{fr(w.iloc[k])} {court_nom}",
                                   showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=L["muted"],
                                   ax=34, ay=48, xanchor="left", font=dict(size=11, color=L["ink2"]),
                                   row=r, col=col)
            fig.add_scatter(
                x=annees, y=w, mode="lines+markers", meta="nv", showlegend=False,
                line=dict(color=c["nv"], width=2),
                marker=dict(size=8, color=c["nv"], line=dict(color=L["surface"], width=2)),
                customdata=[meur(x * 1e6) for x in w],
                hovertemplate="%{x}<br><b>%{customdata}</b><extra>" + escape(f"{libelle(p)} {nom}") + "</extra>",
                row=r, col=col,
            )
        fig.add_scatter(
            x=annees, y=v, mode="lines+markers+text", meta=COULEUR_CLE[p], showlegend=False,
            line=dict(color=c[COULEUR_CLE[p]], width=2),
            marker=dict(size=8, color=c[COULEUR_CLE[p]], line=dict(color=L["surface"], width=2)),
            text=[""] * (len(v) - 1) + [fr(v.iloc[-1])], textposition="top center",
            textfont=dict(color=L["ink2"], size=12),
            customdata=[meur(x * 1e6) for x in v],
            hovertemplate="%{x}<br><b>%{customdata}</b><extra>" + escape(libelle(p)) + "</extra>",
            row=r, col=col,
        )
        fig.update_yaxes(rangemode="tozero", range=[0, v.max() * 1.3 or 1], nticks=4, row=r, col=col)
    fig.update_annotations(font=dict(size=13, color=L["ink"]))
    fig.update_xaxes(type="category")
    fig = mise_en_page(fig, 240 * nrow + 40)
    fig.update_layout(margin=dict(t=40))
    return fig


def fig_barres_h(noms, valeurs, survol, hauteur) -> go.Figure:
    """Barres horizontales classées, une seule couleur (une seule série)."""
    c = couleurs("light")
    fig = go.Figure(go.Bar(
        y=noms, x=valeurs / 1e6, orientation="h", meta="s0",
        marker=dict(color=c["s0"], line=dict(color=L["surface"], width=2)),
        text=[meur(v) for v in valeurs], textposition="outside", cliponaxis=False,
        textfont=dict(color=L["ink2"]),
        customdata=survol, hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
    ))
    fig.update_layout(bargap=0.35, barcornerradius=4)
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False,
                     range=[0, valeurs.max() / 1e6 * 1.22])
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=L["ink2"]), automargin=True)
    return mise_en_page(fig, hauteur)


# ---------------------------------------------------------------- Solidarités : renouvellement
def court(g: str) -> str:
    """Libellé court pour les axes : « Autonomie (personnes âgées… » -> « Autonomie<br>(PA et PH) »."""
    return {"Autonomie (personnes âgées et personnes handicapées)": "Autonomie<br>(pers. âgées et handicapées)",
            "Insertion et développement social": "Insertion et<br>développement social",
            "Total solidarités humaines": "<b>Total solidarités<br>humaines</b>"}.get(g, g)


def fig_taux(syn: pd.DataFrame) -> go.Figure:
    """Taux d'entrée et de sortie par groupe (rapportés aux bénéficiaires de 2020)."""
    c = couleurs("light")
    groupes = list(syn.index)
    fig = go.Figure()
    for col, nom, cle, eff in [("taux d'entrée (%)", "Taux d'entrée", "s0", "entrants"),
                               ("taux de sortie (%)", "Taux de sortie", "s1", "sortants")]:
        fig.add_bar(
            y=[court(g) for g in groupes], x=syn[col], name=nom, orientation="h", meta=cle,
            marker=dict(color=c[cle], line=dict(color=L["surface"], width=2)),
            text=[f"{fr(v)} %" for v in syn[col]], textposition="outside", cliponaxis=False,
            textfont=dict(color=L["ink2"]),
            customdata=[f"{int(n)} {eff} sur {int(b)} bénéficiaires en 2020"
                        for n, b in zip(syn[eff], syn.iloc[:, 0])],
            hovertemplate="<b>" + nom + " : %{x:.1f} %</b><br>%{customdata}<extra></extra>",
        )
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08, barcornerradius=4,
                      legend=dict(orientation="h", y=-0.08, x=0, font=dict(color=L["ink2"])))
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False,
                     range=[0, max(syn["taux d'entrée (%)"].max(), syn["taux de sortie (%)"].max()) * 1.2])
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=L["ink2"]), automargin=True)
    return mise_en_page(fig, 400)


def fig_flux(flux: pd.DataFrame, groupes: list) -> go.Figure:
    """Entrées (au-dessus de zéro) et sorties (en dessous) par année, un panneau par groupe."""
    c = couleurs("light")
    fig = make_subplots(rows=1, cols=len(groupes), shared_yaxes=True, horizontal_spacing=0.03,
                        subplot_titles=[court(g).replace("<b>", "").replace("</b>", "") for g in groupes])
    for i, g in enumerate(groupes, 1):
        x = flux[flux.groupe == g]
        annees = [str(a) for a in x.annee]
        for col, nom, cle, signe in [("entrants", "Entrées", "s0", 1), ("sortants", "Sorties", "s1", -1)]:
            fig.add_bar(
                x=annees, y=signe * x[col], name=nom, meta=cle, showlegend=(i == 1), legendgroup=nom,
                marker=dict(color=c[cle], line=dict(color=L["surface"], width=2)),
                customdata=x[col],
                hovertemplate="%{x} · " + nom + " : <b>%{customdata}</b><extra>" + escape(g) + "</extra>",
                row=1, col=i,
            )
    fig.update_layout(barmode="relative", bargap=0.35, barcornerradius=4,
                      legend=dict(orientation="h", y=-0.15, x=0, font=dict(color=L["ink2"])))
    fig.update_xaxes(type="category")
    # Axe en valeurs absolues : les sorties sont sous zéro mais restent des effectifs positifs
    m = int(max(flux["entrants"].max(), flux["sortants"].max()))
    pas = 20 if m > 40 else 10
    ticks = list(range(-((m // pas) + 1) * pas, ((m // pas) + 1) * pas + 1, pas))
    fig.update_yaxes(zeroline=True, zerolinewidth=1, tickvals=ticks, ticktext=[str(abs(t)) for t in ticks],
                     range=[ticks[0], ticks[-1]])
    fig.update_yaxes(title_text="Bénéficiaires", title_font=dict(color=L["muted"]), row=1, col=1)
    fig.update_annotations(font=dict(size=12, color=L["ink"]))
    fig = mise_en_page(fig, 340)
    fig.update_layout(margin=dict(t=56))
    return fig


def section_renouvellement(df: pd.DataFrame) -> tuple[dict, str]:
    """Figures et HTML de la section « Solidarités : renouvellement des bénéficiaires »."""
    # import ici : renouvellement importe ce module
    from renouvellement import GROUPES_SH, TOTAL, analyser, sans_pluriannuels, synthese
    c, paires, syn, flux, _ = analyser(df)
    syn_sp = synthese(sans_pluriannuels(c))
    es = c[(c.politique_affichage != TOTAL) & c.pluriannuel_probable]
    n_pe, n_ps = int((es.statut == "entrant").sum()), int((es.statut == "sortant").sum())
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    groupes = [*GROUPES_SH, TOTAL]
    figs = {"taux": fig_taux(syn), "flux": fig_flux(flux, groupes)}

    tab = pd.DataFrame({
        "Groupe": syn.index,
        f"Bénéf. {a0}": syn[f"bénéficiaires {a0}"],
        "Présents toute la période": syn["présents toute la période"],
        "Entrants": syn["entrants"], "Sortants": syn["sortants"], "Ponctuels": syn["ponctuels"],
        "Taux d'entrée": [f"{fr(v)} %" for v in syn["taux d'entrée (%)"]],
        "Taux de sortie": [f"{fr(v)} %" for v in syn["taux de sortie (%)"]],
        "Solde net": [f"{v:+d}".replace("-", "−") for v in syn["solde net"]],
        f"Montant {a1} des entrants": [euros(v) for v in syn[f"montant {a1} des entrants (€)"]],
    })
    tab_sp = pd.DataFrame({
        "Groupe": syn_sp.index,
        "Entrants": [f"{a} → {b}" for a, b in zip(syn["entrants"], syn_sp["entrants"])],
        "Sortants": [f"{a} → {b}" for a, b in zip(syn["sortants"], syn_sp["sortants"])],
        "Taux d'entrée": [f"{fr(a)} → {fr(b)} %" for a, b in zip(syn["taux d'entrée (%)"], syn_sp["taux d'entrée (%)"])],
        "Taux de sortie": [f"{fr(a)} → {fr(b)} %" for a, b in zip(syn["taux de sortie (%)"], syn_sp["taux de sortie (%)"])],
        "Solde net": [f"{int(a):+d} → {int(b):+d}".replace("-", "−")
                      for a, b in zip(syn["solde net"], syn_sp["solde net"])],
    })
    t_tot, t_sp = syn.loc[TOTAL], syn_sp.loc[TOTAL]
    solde_av, solde_ap = (f"{int(x):+d}".replace("-", "−") for x in (t_tot["solde net"], t_sp["solde net"]))
    annees_fse = set(df.loc[df["inclus_totaux"] & (df["objet"] == OBJET_FSE), "annee"])
    sans_fse = ", ".join(str(a) for a in range(a0, a1 + 1) if a not in annees_fse) or "aucune année"
    tab_flux = flux.pivot(index="annee", columns="groupe", values=["entrants", "sortants"])
    lignes = [{"Année": a, **{f"{g} (entrées / sorties)": f"+{tab_flux.loc[a, ('entrants', g)]} / "
                              f"−{tab_flux.loc[a, ('sortants', g)]}" for g in groupes}}
              for a in tab_flux.index]

    seuls_a1 = int(((c.statut == "entrant") & (c.premiere == a1) & (c.politique_affichage != TOTAL)).sum())
    nb_ent = int(((c.statut == "entrant") & (c.politique_affichage != TOTAL)).sum())
    html = f"""
<section class="card">
  <h2>Solidarités : renouvellement des bénéficiaires, {a0}–{a1}</h2>
  <p class="sous">Unité : le couple bénéficiaire × groupe. Une organisation financée dans deux groupes compte dans chacun ; la ligne « Total » la compte une seule fois.</p>
  <div class="duo">
    <div><h3 class="h3">Taux d'entrée et de sortie</h3><p class="sous">Rapportés aux bénéficiaires de {a0}.</p>{{div_taux}}</div>
    <div class="encadre">
      <h3 class="h3">Définitions et limites</h3>
      <ul>
        <li><b>Présent</b> : financé en {a0} et en {a1} (des interruptions entre les deux sont possibles). <b>Entrant</b> : première subvention après {a0}, encore financé en {a1}. <b>Sortant</b> : financé dès {a0}, dernière subvention avant {a1}. <b>Ponctuel</b> : arrivé après {a0} et reparti avant {a1}.</li>
        <li><b>Quatre années seulement.</b> On ne sait pas qui était nouveau en {a0} (première année des données), ni qui s'arrêtera après {a1}. {seuls_a1} des {nb_ent} couples entrants (tous groupes) n'apparaissent qu'en {a1} : certains se révéleront ponctuels.</li>
        <li><b>Financements pluriannuels non identifiables</b> : le fichier ne renseigne ni la période ni les conditions de versement. Un financement pluriannuel ou irrégulier peut créer une fausse entrée ou sortie. {n_pe} entrants et {n_ps} sortants ont un rythme qui le laisse penser (financés une année sur deux ou sur trois, ou une année à plus de 2 fois leur montant médian ; subventions FSE non prises en compte, faute de FSE en {sans_fse}). Sans eux, le taux d'entrée total passe de {fr(t_tot["taux d'entrée (%)"])} % à {fr(t_sp["taux d'entrée (%)"])} %, le taux de sortie de {fr(t_tot["taux de sortie (%)"])} % à {fr(t_sp["taux de sortie (%)"])} % et le solde net de {solde_av} à {solde_ap}.</li>
        <li><b>Petits effectifs</b> : quelques dizaines d'organisations par groupe ; un taux bouge de plusieurs points pour quelques bénéficiaires.</li>
        <li><b>Ces chiffres décrivent qui est financé, pas pourquoi</b> : une sortie peut venir de la fin d'un projet, d'un changement de dispositif ou de financeur, d'une fusion, ou d'un passage dans un autre groupe.</li>
        <li><b>Exclus</b> : tiers anonymisés, montants à 0 €, et {len(paires)} paires entrant/sortant aux noms proches, jugées comme des changements d'identifiant probables (<code>ref/renouvellement_exclusions.csv</code>).</li>
      </ul>
    </div>
  </div>
  <h3 class="h3">Entrées et sorties par année</h3>
  <p class="sous">Entrées : première apparition dans l'année (ponctuels compris). Sorties : dernière apparition l'année précédente. Pas d'entrées mesurables en {a0}.</p>
  {{div_flux}}
  <details><summary>Voir les données</summary>{table_html(tab)}{table_html(pd.DataFrame(lignes))}
  <p class="note">Avec → sans les entrants et sortants « pluriannuel probable » :</p>{table_html(tab_sp)}
  <p class="note">Listes nominatives : <code>data/renouvellement_solidarites.csv</code> (entrants, sortants, ponctuels) et <code>data/pluriannuels_solidarites.csv</code> (pluriannuels probables).</p></details>
</section>"""
    return figs, html


# ---------------------------------------------------------------- Carte de chaleur : Insertion – hors FSE
TYPE_COURT = {"Association": "Assoc.", "Intercommunalité": "Interco.", "Établissement public": "Étab. public",
              "Bailleur social": "Bailleur", "Commune": "Commune", "Collège": "Collège", "Autre": "Autre"}
SYMBOLE_PLURI = "◆"
# Gamme séquentielle bleue (clair = faible, foncé = élevé) ; elle démarre au cran 150 pour qu'un
# petit montant reste nettement bleu, distinct des cases vides (gris neutre).
GAMME_BLEUE = [[0, "#b7d3f6"], [0.25, "#86b6ef"], [0.5, "#3987e5"], [0.75, "#1c5cab"], [1, "#0d366b"]]


def carte_hors_fse(df: pd.DataFrame, tot: pd.DataFrame, n: int = 40) -> tuple[go.Figure, str]:
    """Carte de chaleur des n premiers bénéficiaires d'« Insertion – hors FSE », par année + Total."""
    import numpy as np
    from renouvellement import couples, lignes_sh  # import ici : renouvellement importe ce module

    s = tot[tot["groupe_evolution"] == IDS_HORS]
    anon = s["nom_affichage"] == ANONYME
    zeros = int(((~df["inclus_totaux"]) & (df["groupe_evolution"] == IDS_HORS)).sum())
    nommes = s[~anon]
    annees = sorted(tot["annee"].unique())
    p = nommes.pivot_table(index=["idBeneficiaire", "nom_affichage"], columns="annee", values="montant",
                           aggfunc="sum").reindex(columns=annees)
    p["Total"] = p.sum(axis=1)
    p = p.sort_values("Total", ascending=False)
    nb_benef, total_groupe = len(p), p["Total"].sum()
    p = p.head(n)

    # Type et « pluriannuel probable » (calculé, dans renouvellement.py, sur le groupe Insertion hors FSE)
    types = nommes.groupby("idBeneficiaire")["type_beneficiaire"].first()
    c = couples(lignes_sh(df))
    pl = c[c["politique_affichage"] == IDS].set_index("idBeneficiaire")
    ids = p.index.get_level_values(0)
    noms = p.index.get_level_values(1)
    pluri = [bool(pl["pluriannuel_probable"].get(i, False)) for i in ids]
    motif = [pl["motif_pluriannuel"].get(i, "") for i in ids]

    def raccourci(nom: str, lg: int = 34) -> str:
        return nom if len(nom) <= lg else nom[:lg - 1].rstrip() + "…"
    # Libellé de ligne : symbole + nom raccourci ; le type est écrit à part, dans une colonne alignée à gauche
    etiquettes = [f"{SYMBOLE_PLURI + ' ' if pr else ''}{raccourci(nm)}" for nm, pr in zip(noms, pluri)]
    if len(set(etiquettes)) < len(etiquettes):  # deux noms raccourcis identiques : on les distingue
        etiquettes = [f"{e} ({i})" for e, i in zip(etiquettes, ids)]

    val = p[annees].to_numpy(dtype=float)
    vide = np.isnan(val)
    tot_col = p[["Total"]].to_numpy(dtype=float)
    lg = lambda a: np.log10(np.where(a > 0, a, np.nan))
    zmin, zmax = np.nanmin(lg(val)), np.nanmax(lg(val))
    ticks = [t for t in range(3, 8) if zmin - 0.3 <= t <= zmax + 0.3]
    etiq_ticks = {3: "1 k€", 4: "10 k€", 5: "100 k€", 6: "1 M€", 7: "10 M€"}

    survol = [[f"<b>{escape(nm)}</b><br>{escape(types[i])}<br>{a} : "
               + (euros(v) if not np.isnan(v) else "aucune subvention")
               + (f"<br>{SYMBOLE_PLURI} pluriannuel probable : {escape(mo)}" if pr else "")
               for a, v in zip(annees, ligne)]
              for i, nm, ligne, pr, mo in zip(ids, noms, val, pluri, motif)]
    survol_tot = [[f"<b>{escape(nm)}</b><br>Total {annees[0]}–{annees[-1]} : {euros(t)}"]
                  for nm, t in zip(noms, tot_col[:, 0])]

    x_an = [str(a) for a in annees]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.8, 0.2],
                        horizontal_spacing=0.025)
    # Cases vides : trace grise séparée, sous la trace des montants
    fig.add_heatmap(z=np.where(vide, 1.0, np.nan), x=x_an, y=etiquettes, meta="vide",
                    colorscale=[[0, L["grid"]], [1, L["grid"]]], showscale=False, xgap=2, ygap=2,
                    customdata=survol, hovertemplate="%{customdata}<extra></extra>", row=1, col=1)
    fig.add_heatmap(z=lg(val), x=x_an, y=etiquettes, colorscale=GAMME_BLEUE, zmin=zmin, zmax=zmax,
                    xgap=2, ygap=2, customdata=survol, hovertemplate="%{customdata}<extra></extra>",
                    colorbar=dict(title=dict(text="Montant de l'année (échelle log)", side="top"),
                                  orientation="h", x=0.4, xanchor="center", y=-0.01, yanchor="top",
                                  len=0.6, thickness=10, tickvals=ticks,
                                  ticktext=[etiq_ticks[t] for t in ticks], outlinewidth=0),
                    row=1, col=1)
    # Colonne Total, séparée, sur sa propre échelle, avec le montant écrit dans la case
    fig.add_heatmap(z=lg(tot_col), x=["Total"], y=etiquettes, colorscale=GAMME_BLEUE, showscale=False,
                    xgap=2, ygap=2, text=[[f"{fr(t / 1e3, 0)} k€"] for t in tot_col[:, 0]],
                    texttemplate="%{text}", textfont=dict(size=11),
                    customdata=survol_tot, hovertemplate="%{customdata}<extra></extra>", row=1, col=2)
    marge_g = 330
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11, color=L["ink2"]), showgrid=False,
                     automargin=False)
    fig.update_yaxes(showticklabels=False, row=1, col=2)
    fig.update_xaxes(type="category", side="top", showgrid=False, showline=False,
                     tickfont=dict(color=L["ink2"]))
    # Colonne « type » : annotations calées sur le bord gauche de la figure (décalage en pixels)
    fig.add_annotation(x=0, y=-0.5, xref="paper", yref="y", text="<b>Type</b>", showarrow=False,
                       xanchor="left", xshift=-marge_g + 8, yshift=14, font=dict(size=11, color=L["ink2"]))
    for e, i in zip(etiquettes, ids):
        fig.add_annotation(x=0, y=e, xref="paper", yref="y", text=TYPE_COURT.get(types[i], types[i]),
                           showarrow=False, xanchor="left", xshift=-marge_g + 8,
                           font=dict(size=11, color=L["muted"]))
    fig = mise_en_page(fig, 24 * len(p) + 160)
    fig.update_layout(margin=dict(l=marge_g, t=40, b=80))

    note_excl = ("Exclus : les tiers anonymisés"
                 + (f" ({int(anon.sum())} subventions, {euros(s.loc[anon, 'montant'].sum())})" if anon.any()
                    else " (aucun dans ce sous-groupe)")
                 + f" et les montants à 0 € ({zeros} subvention{'s' if zeros > 1 else ''}).")
    html = f"""
<section class="card">
  <h2>Insertion – hors FSE : les {len(p)} premiers bénéficiaires par année, {annees[0]}–{annees[-1]}</h2>
  <p class="sous">Subventions du groupe Insertion et développement social dont l'objet n'est pas « {OBJET_FSE} ». Couleur : montant de l'année, du clair (faible) au foncé (élevé), sur une échelle logarithmique ; case grise = aucune subvention cette année-là. Colonne Total sur sa propre échelle. {SYMBOLE_PLURI} = pluriannuel probable. Ces {len(p)} bénéficiaires représentent {fr(p['Total'].sum() / total_groupe * 100)} % des {meur(total_groupe)} du sous-groupe ({nb_benef} bénéficiaires nommés).</p>
  {{div_hors_fse}}
  <p class="note">Les montants sont enregistrés l'année de la décision : une convention pluriannuelle apparaît en une seule fois, suivie d'années sans montant, sans que le financement ait cessé.</p>
  <p class="note">{escape(note_excl)} {SYMBOLE_PLURI} Pluriannuel probable : financé une année sur deux ou sur trois, ou une année à plus de 2 fois son montant médian. Noms raccourcis : nom complet au survol.</p>
</section>"""
    return fig, html


# ---------------------------------------------------------------- Solidarités : principaux bénéficiaires
ANONYME = "Tiers anonymisé"


def euros(x: float) -> str:
    return f"{fr(x, 0)} €"


def bloc_solidarites(tot: pd.DataFrame, groupe: str, n: int = 10, colonne: str = "politique_affichage") -> str:
    """Tableau des n premiers bénéficiaires d'un groupe (ou sous-groupe) Solidarités.
    Un bénéficiaire = un identifiant (après fusion) sous son nom d'affichage ; ses montants
    sont ceux du (sous-)groupe seulement.
    Les « Tiers anonymisé » sont exclus (ils ne forment pas un bénéficiaire unique) et signalés."""
    s = tot[tot[colonne] == groupe]
    anon = s["nom_affichage"] == ANONYME
    nommes = s[~anon]
    cle = ["idBeneficiaire", "nom_affichage"]
    # Objet principal : celui qui représente le plus gros montant pour ce bénéficiaire dans le groupe
    par_objet = nommes.groupby(cle + ["objet"])["montant"].sum().reset_index()
    objet_principal = (par_objet.sort_values("montant", ascending=False)
                       .drop_duplicates(cle).set_index(cle)["objet"])
    top = (nommes.groupby(cle)
           .agg(type=("type_beneficiaire", "first"), subventions=("id", "size"),
                montant=("montant", "sum"))
           .join(objet_principal)
           .sort_values("montant", ascending=False).head(n).reset_index())
    tableau = pd.DataFrame({
        "Rang": range(1, len(top) + 1),
        "Bénéficiaire": top["nom_affichage"],
        "Type": top["type"],
        "Subventions": [fr(x, 0) for x in top["subventions"]],
        "Montant total": [euros(x) for x in top["montant"]],
        "Objet principal": top["objet"],
    })
    part_top = top["montant"].sum() / s["montant"].sum() * 100
    note = (f"Ces {len(top)} bénéficiaires reçoivent {fr(part_top)} % des {meur(s['montant'].sum())} du groupe "
            f"({fr(len(s), 0)} subventions, {fr(nommes['idBeneficiaire'].nunique(), 0)} bénéficiaires nommés).")
    if anon.any():
        n_sub, n_id = int(anon.sum()), s.loc[anon, "idBeneficiaire"].nunique()
        pl = lambda n, mot: f"{fr(n, 0)} {mot}{'s' if n > 1 else ''}"
        note += (f" Non {'listées' if n_sub > 1 else 'listée'} : {pl(n_sub, 'subvention')} à des tiers anonymisés "
                 f"({euros(s.loc[anon, 'montant'].sum())}, {pl(n_id, 'identifiant')}), "
                 "qui ne peuvent pas être additionnés comme un seul bénéficiaire.")
    return (f'<div class="bloc-sol"><h3><span class="pastille" data-cle="{COULEUR_CLE[groupe]}"></span>'
            f'{escape(groupe)}</h3><div class="table-scroll">{table_html(tableau)}</div>'
            f'<p class="note">{escape(note)}</p></div>')


# ---------------------------------------------------------------- Programme principal
def main() -> None:
    df = pd.read_csv(SOURCE, sep=";", encoding="utf-8-sig",
                     dtype={"idBeneficiaire": str, "idBeneficiaire_original": str, "id": str})
    df["politique_affichage"] = politique_affichage(df)
    df["groupe_evolution"] = groupe_evolution(df)
    tot = df[df["inclus_totaux"]]

    # Chiffres clés
    montant = tot["montant"].sum()
    nb_subv = len(tot)
    nb_benef = tot["idBeneficiaire"].nunique()
    a_min, a_max = tot["annee"].min(), tot["annee"].max()

    # Données des graphiques
    t = tot.pivot_table(index="politique_affichage", columns="annee", values="montant",
                        aggfunc="sum", fill_value=0)
    t = t.loc[[p for p in GROUPES if p in t.index]]
    t_evol = tot.pivot_table(index="groupe_evolution", columns="annee", values="montant",
                             aggfunc="sum", fill_value=0)
    t_evol = t_evol.loc[[p for p in GROUPES_EVOL if p in t_evol.index]]
    assert abs(t_evol.values.sum() - t.values.sum()) < 0.01

    # Autonomie sans Morbihan Habitat (identifié par son nom d'affichage, un seul identifiant)
    ids_mh = tot.loc[tot["nom_affichage"] == MORBIHAN_HABITAT, "idBeneficiaire"].unique()
    if len(ids_mh) != 1:
        raise ValueError(f"{MORBIHAN_HABITAT} : {len(ids_mh)} identifiants trouvés, 1 attendu")
    auto = tot[tot["groupe_evolution"] == AUTONOMIE]
    mh_auto = auto[auto["idBeneficiaire"] == ids_mh[0]]
    auto_sans_mh = auto[auto["idBeneficiaire"] != ids_mh[0]].groupby("annee")["montant"].sum()
    mh_annees = sorted(mh_auto["annee"].unique())
    mh_note = (f"Morbihan Habitat reçoit {euros(mh_auto['montant'].sum())} de subventions classées en Autonomie "
               f"({', '.join(f'{euros(x)} en {a}' for a, x in mh_auto.groupby('annee')['montant'].sum().items())}), "
               f"puis plus aucune après {max(mh_annees)} : cet organisme a ensuite été rattaché à une autre politique "
               "(ses subventions suivantes relèvent de Solidarité des territoires / Habitat). "
               "La courbe grise d'Autonomie (« sans MH ») le retire pour montrer l'évolution à périmètre "
               "comparable ; elle se confond avec la courbe bleue dès que Morbihan Habitat n'y figure plus.")

    types = (tot.groupby("type_beneficiaire")
             .agg(montant=("montant", "sum"), subventions=("id", "size"),
                  beneficiaires=("idBeneficiaire", "nunique"))
             .sort_values("montant", ascending=False))

    # Groupé par identifiant ET nom d'affichage : les lignes « Tiers anonymisé » d'un identifiant
    # qui a aussi des lignes nommées restent séparées (ni mélange, ni levée d'anonymat).
    top = (tot.groupby(["idBeneficiaire", "nom_affichage"])
           .agg(type=("type_beneficiaire", "first"),
                montant=("montant", "sum"), subventions=("id", "size"))
           .reset_index().rename(columns={"nom_affichage": "nom"})
           .sort_values("montant", ascending=False).head(15))

    # Qualité des données
    zeros = int((~df["inclus_totaux"]).sum())
    fus = df["idBeneficiaire"] != df["idBeneficiaire_original"]
    nv = tot.loc[tot["politique_publique"] == NON_VENTILE, "montant"].sum()
    nv_par_objet = (tot.loc[tot["politique_publique"] == NON_VENTILE]
                    .groupby("objet")["montant"].sum().sort_values(ascending=False))
    nv_objets = len(nv_par_objet)
    nv_exemples = ", ".join(f"« {escape(o)} »" for o in nv_par_objet.index[:2])
    nb_objets = tot["objet"].nunique()

    figs = {
        "empile": fig_empile(t),
        "multiples": fig_multiples(t_evol, {AUTONOMIE: ("sans Morbihan Habitat", "sans MH", auto_sans_mh)}),
        "types": fig_barres_h(
            types.index.tolist(), types["montant"],
            [f"{fr(r.subventions, 0)} subventions · {fr(r.beneficiaires, 0)} bénéficiaires"
             for r in types.itertuples()], 330),
        "top": fig_barres_h(
            top["nom"].tolist(), top["montant"],
            [f"{escape(r.type)} · {fr(r.subventions, 0)} subventions" for r in top.itertuples()], 560),
    }
    figs_renouv, renouv_html = section_renouvellement(df)
    figs |= figs_renouv
    figs["hors_fse"], hors_fse_html = carte_hors_fse(df, tot)
    config = dict(displayModeBar=False, responsive=True)
    div = {k: f.to_html(full_html=False, include_plotlyjs=False, div_id=f"fig-{k}", config=config)
           for k, f in figs.items()}
    renouv_html = renouv_html.replace("{div_taux}", div["taux"]).replace("{div_flux}", div["flux"])
    hors_fse_html = hors_fse_html.replace("{div_hors_fse}", div["hors_fse"])

    # Tableaux (équivalent accessible de chaque graphique)
    tab_pol = t.copy()
    tab_pol["Total"] = tab_pol.sum(axis=1)
    tab_pol.loc["Total"] = tab_pol.sum()
    part = tab_pol["Total"] / tab_pol.loc["Total", "Total"] * 100
    tab_pol = tab_pol.map(lambda x: fr(x / 1e6))
    tab_pol["Part"] = [f"{fr(x)} %" for x in part]
    tab_pol.index = [libelle(p) for p in tab_pol.index]
    tab_pol = tab_pol.reset_index().rename(columns={"index": "Politique (M€)"})
    tab_pol.columns = [str(c) for c in tab_pol.columns]

    tab_types = pd.DataFrame({
        "Type de bénéficiaire": types.index,
        "Montant (M€)": [fr(x / 1e6) for x in types["montant"]],
        "Part": [f"{fr(x / montant * 100)} %" for x in types["montant"]],
        "Subventions": [fr(x, 0) for x in types["subventions"]],
        "Bénéficiaires": [fr(x, 0) for x in types["beneficiaires"]],
    })
    tab_top = pd.DataFrame({
        "Rang": range(1, len(top) + 1),
        "Bénéficiaire": top["nom"].values,
        "Type": top["type"].values,
        "Montant (M€)": [fr(x / 1e6) for x in top["montant"]],
        "Subventions": [fr(x, 0) for x in top["subventions"]],
    })

    solidarites_html = (bloc_solidarites(tot, EF)
                        + bloc_solidarites(tot, IDS_FSE, colonne="groupe_evolution")
                        + bloc_solidarites(tot, IDS_HORS, colonne="groupe_evolution")
                        + bloc_solidarites(tot, AUTONOMIE))

    # Thème sombre : couleurs des séries et de l'habillage, appliquées par script
    theme_js = {m: dict(**THEME[m], series=couleurs(m)) for m in THEME}

    kpis = [
        (meur(montant), "Montant total attribué"),
        (fr(nb_subv, 0), "Subventions"),
        (fr(nb_benef, 0), "Bénéficiaires distincts"),
        (f"{a_min}–{a_max}", f"Années couvertes ({a_max - a_min + 1} ans)"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{escape(l)}</div></div>'
                       for v, l in kpis)

    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subventions du Morbihan</title>
<script>{get_plotlyjs()}</script>
<style>
:root {{
  color-scheme: light;
  --page: {L['page']}; --surface: {L['surface']}; --ink: {L['ink']}; --ink2: {L['ink2']};
  --muted: {L['muted']}; --grid: {L['grid']}; --border: {L['border']};
  --b0: {BLEUS['light'][0]}; --b1: {BLEUS['light'][1]}; --b2: {BLEUS['light'][2]};
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --page: {THEME['dark']['page']}; --surface: {THEME['dark']['surface']}; --ink: {THEME['dark']['ink']};
    --ink2: {THEME['dark']['ink2']}; --muted: {THEME['dark']['muted']}; --grid: {THEME['dark']['grid']};
    --border: {THEME['dark']['border']};
    --b0: {BLEUS['dark'][0]}; --b1: {BLEUS['dark'][1]}; --b2: {BLEUS['dark'][2]};
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page: {THEME['dark']['page']}; --surface: {THEME['dark']['surface']}; --ink: {THEME['dark']['ink']};
  --ink2: {THEME['dark']['ink2']}; --muted: {THEME['dark']['muted']}; --grid: {THEME['dark']['grid']};
  --border: {THEME['dark']['border']};
  --b0: {BLEUS['dark'][0]}; --b1: {BLEUS['dark'][1]}; --b2: {BLEUS['dark'][2]};
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink); font-family: {FONT}; line-height: 1.5; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 32px 16px 48px; }}
header h1 {{ font-size: 1.75rem; margin: 0 0 4px; font-weight: 650; }}
header p {{ margin: 0; color: var(--ink2); }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
.kpi, .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }}
.kpi {{ padding: 16px 20px; }}
.kpi-v {{ font-size: 1.9rem; font-weight: 650; }}
.kpi-l {{ color: var(--ink2); font-size: .9rem; }}
.card {{ padding: 20px 20px 12px; margin-bottom: 16px; }}
.card h2 {{ font-size: 1.1rem; margin: 0 0 2px; font-weight: 650; }}
.card .sous {{ margin: 0 0 12px; color: var(--ink2); font-size: .9rem; }}
.duo {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.duo .card {{ margin-bottom: 16px; }}
details {{ margin: 8px 0 4px; font-size: .9rem; }}
summary {{ cursor: pointer; color: var(--ink2); }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); }}
td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
.qualite {{ border-left: 4px solid var(--muted); }}
.qualite ul {{ margin: 8px 0; padding-left: 20px; }}
.qualite li {{ margin-bottom: 6px; }}
.bloc-sol {{ margin: 16px 0 24px; }}
.bloc-sol h3 {{ font-size: 1rem; margin: 0 0 4px; font-weight: 650; display: flex; align-items: center; gap: 8px; }}
.bloc-sol table {{ font-size: .9rem; }}
.bloc-sol td, .bloc-sol th {{ text-align: left; vertical-align: top; }}
.bloc-sol td:nth-child(1), .bloc-sol th:nth-child(1),
.bloc-sol td:nth-child(4), .bloc-sol th:nth-child(4),
.bloc-sol td:nth-child(5), .bloc-sol th:nth-child(5) {{ text-align: right; white-space: nowrap; }}
.bloc-sol td:nth-child(6) {{ color: var(--ink2); }}
.pastille {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
.pastille[data-cle="b0"] {{ background: var(--b0); }}
.pastille[data-cle="b1"] {{ background: var(--b1); }}
.pastille[data-cle="b2"] {{ background: var(--b2); }}
.note {{ color: var(--ink2); font-size: .85rem; margin: 6px 0 0; }}
.table-scroll {{ overflow-x: auto; }}
.h3 {{ font-size: 1rem; margin: 12px 0 2px; font-weight: 650; }}
.encadre {{ border-left: 4px solid var(--muted); padding: 4px 0 4px 16px; font-size: .9rem; }}
.encadre ul {{ margin: 8px 0; padding-left: 18px; }}
.encadre li {{ margin-bottom: 6px; }}
code {{ font-size: .85em; }}
footer {{ color: var(--ink2); font-size: .85rem; margin-top: 24px; }}
footer a {{ color: inherit; }}
@media (max-width: 760px) {{
  .kpis {{ grid-template-columns: repeat(2, 1fr); }}
  .duo {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<main>
<header>
  <h1>Subventions du Département du Morbihan, {a_min}–{a_max}</h1>
  <p>Subventions aux personnes morales, ventilées selon la segmentation stratégique du Département au 1<sup>er</sup> janvier 2025.</p>
</header>

<section class="kpis" aria-label="Chiffres clés">{kpi_html}</section>

<section class="card">
  <h2>Montants par année et par politique publique</h2>
  <p class="sous">En millions d'euros. Total de l'année au-dessus de chaque barre. Les Solidarités humaines sont découpées en trois groupes (nuances de bleu).</p>
  {div['empile']}
  <details><summary>Voir les données</summary>{table_html(tab_pol)}</details>
</section>

<section class="card">
  <h2>Évolution de chaque politique publique, {a_min}–{a_max}</h2>
  <p class="sous">En millions d'euros. Attention : chaque graphique a sa propre échelle, pour rendre lisibles les petites politiques ; comparez les montants, pas les hauteurs. Le groupe Insertion est séparé en deux selon l'objet de chaque subvention : fonds européens (FSE) et hors FSE.</p>
  {div['multiples']}
  <p class="note">Les subventions FSE (Fonds social européen) sont des fonds européens gérés par le Département : elles ne relèvent pas uniquement de crédits départementaux propres.</p>
  <p class="note">{escape(mh_note)}</p>
</section>

<div class="duo">
<section class="card">
  <h2>Répartition par type de bénéficiaire</h2>
  <p class="sous">Montant total sur la période. Type déduit du nom du bénéficiaire.</p>
  {div['types']}
  <details><summary>Voir les données</summary>{table_html(tab_types)}</details>
</section>

<section class="card qualite">
  <h2>Qualité des données et limites</h2>
  <ul>
    <li><b>Montants à 0 € exclus :</b> {zeros} subventions à 0 € sont retirées des totaux et des comptages.</li>
    <li><b>Fusions d'identifiants :</b> {int(fus.sum())} subventions ont été rattachées à un autre identifiant ({df.loc[fus, 'idBeneficiaire_original'].nunique()} identifiants fusionnés), après vérification au cas par cas des organismes enregistrés sous plusieurs identifiants.</li>
    <li><b>« Non ventilé » :</b> {meur(nv)}, soit {fr(nv / montant * 100)} % du total ({nv_objets} objets sur {nb_objets}). L'intitulé de ces subventions est trop générique pour les rattacher à une politique sans deviner (principalement {nv_exemples}).</li>
    <li><b>Affichage des Solidarités humaines :</b> pour la lecture, la politique publique est découpée en trois groupes (Enfance et famille ; Insertion et développement social ; Autonomie, qui réunit Personnes âgées et Personnes handicapées). La classification officielle n'est pas modifiée.</li>
    <li><b>Grille appliquée après coup :</b> la segmentation stratégique en vigueur au 1<sup>er</sup> janvier 2025 est appliquée rétroactivement aux subventions votées de {a_min} à {a_max}, d'après l'objet de chaque subvention.</li>
    <li><b>Type de bénéficiaire :</b> déduit du nom ; {meur(tot.loc[tot['type_beneficiaire'] == 'Autre', 'montant'].sum())} restent en « Autre » faute d'indice dans le nom.</li>
  </ul>
</section>
</div>

<section class="card">
  <h2>Les 15 premiers bénéficiaires, {a_min}–{a_max}</h2>
  <p class="sous">Montant total reçu sur la période, après fusion des identifiants.</p>
  {div['top']}
  <details><summary>Voir les données</summary>{table_html(tab_top)}</details>
</section>

<section class="card">
  <h2>Solidarités : principaux bénéficiaires, {a_min}–{a_max}</h2>
  <p class="sous">Les 10 premiers bénéficiaires de chaque groupe des Solidarités humaines, par montant total ; le groupe Insertion est présenté en deux tableaux (FSE et hors FSE). Une structure qui reçoit les deux types de subventions apparaît dans les deux, avec le montant propre à chacun. Objet principal : celui qui représente le plus gros montant pour ce bénéficiaire dans le groupe.</p>
  {solidarites_html}
</section>
{hors_fse_html}
{renouv_html}

<footer>
  Source : Département du Morbihan, « Subventions aux personnes morales », data.gouv.fr, Licence Ouverte —
  <a href="{SOURCE_URL}">{SOURCE_URL}</a>. Fichier téléchargé le {DATE_TELECHARGEMENT}.
  Traitements : clean.py, fusions.py, categorize.py, build_dashboard.py.
</footer>
</main>
<script>
(function () {{
  var T = {pd.Series(theme_js).to_json(force_ascii=False)};
  function mode() {{
    var t = document.documentElement.getAttribute("data-theme");
    if (t === "dark" || t === "light") return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }}
  function appliquer() {{
    var th = T[mode()];
    document.querySelectorAll(".js-plotly-plot").forEach(function (gd) {{
      var lay = {{ paper_bgcolor: th.surface, plot_bgcolor: th.surface, "font.color": th.ink2 }};
      Object.keys(gd.layout).forEach(function (k) {{
        if (/^[xy]axis\\d*$/.test(k)) {{
          lay[k + ".gridcolor"] = th.grid; lay[k + ".linecolor"] = th.axis;
          lay[k + ".zerolinecolor"] = th.axis; lay[k + ".tickfont.color"] = th.muted;
        }}
      }});
      (gd.layout.annotations || []).forEach(function (a, i) {{ lay["annotations[" + i + "].font.color"] = th.ink; }});
      if (gd.layout.legend) lay["legend.font.color"] = th.ink2;
      Plotly.relayout(gd, lay);
      gd.data.forEach(function (tr, i) {{
        if (tr.meta === "vide") {{ Plotly.restyle(gd, {{ colorscale: [[[0, th.grid], [1, th.grid]]] }}, [i]); return; }}
        var c = th.series[tr.meta];
        if (!c) return;
        var s = {{ "marker.color": c, "marker.line.color": th.surface }};
        if (tr.type === "scatter") {{ s["line.color"] = c; s["textfont.color"] = th.ink2; }}
        else {{ s["textfont.color"] = th.ink2; }}
        Plotly.restyle(gd, s, [i]);
      }});
    }});
  }}
  window.addEventListener("load", appliquer);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", appliquer);
  new MutationObserver(appliquer).observe(document.documentElement, {{ attributes: true, attributeFilter: ["data-theme"] }});
}})();
</script>
</body>
</html>
"""
    SORTIE.write_text(html, encoding="utf-8")
    print(f"-> {SORTIE.name} ({SORTIE.stat().st_size / 1e6:.1f} Mo)")
    print(f"Chiffres clés : {meur(montant)} · {nb_subv} subventions · {nb_benef} bénéficiaires · {a_min}–{a_max}")


if __name__ == "__main__":
    main()
