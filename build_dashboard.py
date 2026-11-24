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
DEPOT_URL = "https://github.com/mariecourraud/subventions-morbihan"
LIEN_DEPOT = "Méthode, code et limites (GitHub)"

# ---------------------------------------------------------------- Affichage sur écran étroit
# Script ajouté à la page : sous 600 px de large (téléphone), les graphiques à panneaux passent
# sur 2 colonnes, les noms longs des axes sont raccourcis (nom complet au survol) et la carte de
# chaleur masque sa colonne « Type ». Au-delà, la mise en page d'origine est restaurée.
JS_ECRAN_ETROIT = r"""
(function () {
  var SEUIL = 600;
  var GRILLES = {"fig-flux": true};   // graphiques à panneaux
  var NOMS = {"fig-top": 15, "fig-types": 30, "fig-hors_fse": 18};             // longueur max des noms d'axe
  function court(t, n) { return t.length > n ? t.slice(0, n - 1).trim() + "…" : t; }
  function recouper(t, n) {   // recoupe un titre en lignes de n caractères au plus
    var mots = t.replace(/<br>/g, " ").split(" "), lignes = [], l = "";
    mots.forEach(function (m) { if (l && (l + " " + m).length > n) { lignes.push(l); l = m; } else { l = l ? l + " " + m : m; } });
    if (l) lignes.push(l);
    return lignes.join("<br>");
  }
  function axes(gd, l) {
    return Object.keys(gd.layout).filter(function (k) { return new RegExp("^" + l + "axis\\d*$").test(k); })
      .sort(function (a, b) { return (parseInt(a.slice(5)) || 1) - (parseInt(b.slice(5)) || 1); });
  }
  function memoriser(gd) {
    if (gd._origine) return;
    var o = {height: gd.layout.height, hauteurBloc: gd.parentElement.style.height,
             marginL: (gd.layout.margin || {}).l, ann: [], ax: {}};
    (gd.layout.annotations || []).forEach(function (a) {
      o.ann.push({x: a.x, y: a.y, visible: a.visible !== false, text: a.text, ax: a.ax, ay: a.ay,
                  taille: (a.font || {}).size});
    });
    axes(gd, "x").concat(axes(gd, "y")).forEach(function (k) {
      o.ax[k] = {domain: (gd.layout[k].domain || [0, 1]).slice(), showticklabels: gd.layout[k].showticklabels};
    });
    gd._origine = o;
  }
  function etroit(gd) {
    var u = {}, o = gd._origine;
    if (GRILLES[gd.id]) {
      var xs = axes(gd, "x"), ys = axes(gd, "y"), n = xs.length, lignes = Math.ceil(n / 2);
      // Titres des panneaux = annotations de tête en coordonnées « paper » (il peut y avoir
      // moins de titres que d'emplacements, ex. 11 graphiques dans une grille de 12)
      var nt = 0, an = gd.layout.annotations || [];
      while (nt < an.length && an[nt].xref === "paper" && an[nt].yref === "paper") nt++;
      var hP = 150, hT = 78, P = lignes * hP + (lignes - 1) * hT;
      var m = gd.layout.margin || {};
      u.height = P + (m.t || 40) + (m.b || 40) + (gd.id === "fig-flux" ? 30 : 0);
      for (var i = 0; i < n; i++) {
        var c = i % 2, r = Math.floor(i / 2);
        var x0 = c * 0.56, x1 = x0 + 0.44, haut = r * (hP + hT), bas = haut + hP;
        u[xs[i] + ".domain"] = [x0, x1];
        u[ys[i] + ".domain"] = [1 - bas / P, 1 - haut / P];
        if (gd.id === "fig-flux") u[ys[i] + ".showticklabels"] = (c === 0);
        if (i < nt) {   // titre du panneau
          u["annotations[" + i + "].x"] = (x0 + x1) / 2;
          u["annotations[" + i + "].y"] = 1 - haut / P;
          u["annotations[" + i + "].text"] = recouper(o.ann[i].text, 17);
          u["annotations[" + i + "].font.size"] = 11;
        }
      }
      // Autres annotations (ex. « sans MH ») : décalage en pixels réduit pour rester dans leur panneau
      for (var j = nt; j < o.ann.length; j++) {
        if (o.ann[j].ax !== undefined) {
          u["annotations[" + j + "].ax"] = 8; u["annotations[" + j + "].ay"] = 60;
          u["annotations[" + j + "].font.size"] = 11;
        }
      }
    }
    if (NOMS[gd.id]) {
      var tr = gd.data[gd.data.length > 1 ? 1 : 0], noms = tr.y || [];
      u["yaxis.tickmode"] = "array"; u["yaxis.tickvals"] = noms;
      u["yaxis.ticktext"] = noms.map(function (t) { return court(String(t), NOMS[gd.id]); });
      if (gd.id !== "fig-hors_fse") u["xaxis.showticklabels"] = false;   // montants déjà écrits au bout des barres
    }
    if (gd.id === "fig-hors_fse") {
      u["margin.l"] = 148;
      u["xaxis.domain"] = [0, 0.62]; u["xaxis2.domain"] = [0.66, 1];   // colonne Total plus large
      var ans = gd.data[1].x || [];                                     // années abrégées : ’20, ’21…
      u["xaxis.tickmode"] = "array"; u["xaxis.tickvals"] = ans; u["xaxis.tickangle"] = 0;
      u["xaxis.ticktext"] = ans.map(function (a) { return "’" + String(a).slice(-2); });
      (gd.layout.annotations || []).forEach(function (a, i) { u["annotations[" + i + "].visible"] = false; });
    }
    return u;
  }
  function large(gd) {
    var u = {}, o = gd._origine;
    if (GRILLES[gd.id]) {
      u.height = o.height;
      Object.keys(o.ax).forEach(function (k) {
        u[k + ".domain"] = o.ax[k].domain;
        if (o.ax[k].showticklabels !== undefined) u[k + ".showticklabels"] = o.ax[k].showticklabels;
      });
      o.ann.forEach(function (a, i) {
        u["annotations[" + i + "].x"] = a.x; u["annotations[" + i + "].y"] = a.y;
        u["annotations[" + i + "].text"] = a.text;
        if (a.taille !== undefined) u["annotations[" + i + "].font.size"] = a.taille;
        if (a.ax !== undefined) { u["annotations[" + i + "].ax"] = a.ax; u["annotations[" + i + "].ay"] = a.ay; }
      });
    }
    if (NOMS[gd.id]) {
      u["yaxis.tickmode"] = "auto"; u["yaxis.tickvals"] = null; u["yaxis.ticktext"] = null;
      if (gd.id !== "fig-hors_fse") u["xaxis.showticklabels"] = true;
    }
    if (gd.id === "fig-hors_fse") {
      u["margin.l"] = o.marginL;
      u["xaxis.domain"] = o.ax.xaxis.domain; u["xaxis2.domain"] = o.ax.xaxis2.domain;
      u["xaxis.tickmode"] = "auto"; u["xaxis.tickvals"] = null; u["xaxis.ticktext"] = null;
      u["xaxis.tickangle"] = "auto";
      o.ann.forEach(function (a, i) { u["annotations[" + i + "].visible"] = a.visible; });
    }
    return u;
  }
  function adapter() {
    document.querySelectorAll(".js-plotly-plot").forEach(function (gd) {
      if (!GRILLES[gd.id] && !NOMS[gd.id]) return;
      memoriser(gd);
      var e = gd.parentElement.clientWidth < SEUIL;
      if (gd._etroit === e) return;
      gd._etroit = e;
      var u = e ? etroit(gd) : large(gd);
      u.width = null; u.autosize = true;   // la largeur suit toujours le bloc (plotly la fige sinon)
      // plotly enveloppe chaque graphique dans un bloc de hauteur fixe : il doit suivre la nouvelle hauteur
      if (u.height) gd.parentElement.style.height = e ? u.height + "px" : gd._origine.hauteurBloc;
      Plotly.relayout(gd, u).then(function () { Plotly.Plots.resize(gd); });   // recale la largeur
    });
  }
  var minuteur;
  window.addEventListener("load", adapter);
  window.addEventListener("resize", function () { clearTimeout(minuteur); minuteur = setTimeout(adapter, 200); });
})();
"""

# ---------------------------------------------------------------- Palette
# Une paire (foncé, clair) par politique, tirée d'une palette de 9 gammes (2e et 4e teinte de
# chaque gamme ; Éducation prend les 3e et 4e de « Dusk », dont Attractivité garde la 2e).
# La teinte foncée sert partout (barres, pastilles) ; la claire, sur fond sombre (courbes des blocs).
# « Non ventilé » reste en gris neutre. Thème clair uniquement.
TEINTES = {
    "b0": ("#D4A017", "#F7E7B5"),   # Enfance et famille – Mustard
    "b1": ("#9D174D", "#F7A1B3"),   # Insertion et développement social – Berry
    "b2": ("#7D6CC4", "#E7D6F7"),   # Autonomie – Lavender
    "s1": ("#F9844A", "#FDD9B5"),   # Solidarité des territoires – Sunset
    "s2": ("#184965", "#A8DADC"),   # Infrastructures et mobilité – Ocean
    "s3": ("#527F5B", "#DCEAD9"),   # Environnement – Sage
    "s4": ("#C57598", "#F08A8A"),   # Éducation – Dusk (roses)
    "s5": ("#42426F", "#D9D9E2"),   # Attractivité et animation territoriales – Dusk (indigo ; clair dérivé)
    "s6": ("#1E88E5", "#BBDEFB"),   # Ressources – Arctic
    "nv": ("#898781", "#BCBAB3"),   # Non ventilé – gris
}
# Gris des graphiques qui ne portent pas sur une politique (les couleurs restent réservées aux politiques)
GRIS_ACCENT, GRIS_FONCE, GRIS_CLAIR = "#1f1f1d", "#5b5a56", "#bcbab3"
THEME = {
    "light": dict(surface="#fcfcfb", page="#f9f9f7", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", border="rgba(11,11,11,0.10)"),
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

# Clé de couleur de chaque politique (voir TEINTES) ; s1…s6 suivent l'ordre de GRILLE
COULEUR_CLE = ({EF: "b0", IDS: "b1", AUTONOMIE: "b2"}
               | {p: f"s{i + 1}" for i, p in enumerate(AUTRES)} | {NON_VENTILE: "nv"})
assert [p.split()[0] for p in AUTRES] == ["SOLIDARITÉ", "INFRASTRUCTURES", "ENVIRONNEMENT", "ÉDUCATION",
                                         "ATTRACTIVITÉ", "RESSOURCES"], "ordre des politiques ≠ TEINTES"

# Insertion découpée, subvention par subvention selon l'objet, en deux sous-groupes.
# Utilisé uniquement dans le graphique d'évolution et les tableaux de bénéficiaires ;
# politique_affichage (et donc l'analyse du renouvellement) garde les trois groupes.
OBJET_FSE = "Subventions FSE"
MORBIHAN_HABITAT = "MORBIHAN HABITAT"  # retiré d'Autonomie dans une courbe de comparaison
IDS_FSE = "Insertion – fonds européens (FSE)"
IDS_HORS = "Insertion – hors FSE"
GROUPES_EVOL = [EF, IDS_FSE, IDS_HORS, AUTONOMIE, *AUTRES, NON_VENTILE]
COULEUR_CLE |= {IDS_FSE: "b1", IDS_HORS: "b1"}  # même couleur que le groupe Insertion


def groupe_evolution(df: pd.DataFrame) -> pd.Series:
    """politique_affichage, avec Insertion séparée en FSE / hors FSE selon l'objet."""
    ins = df["politique_affichage"] == IDS
    fse = df["objet"] == OBJET_FSE
    if (fse & ~ins).any():
        raise ValueError(f"Des subventions « {OBJET_FSE} » sont hors du groupe Insertion")
    return df["politique_affichage"].mask(ins & fse, IDS_FSE).mask(ins & ~fse, IDS_HORS)


def couleurs(mode: str = "light") -> dict:
    """Teinte foncée de chaque clé de couleur."""
    return {k: f for k, (f, _) in TEINTES.items()}


def clairs() -> dict:
    """Teinte claire de chaque clé de couleur."""
    return {k: c for k, (_, c) in TEINTES.items()}


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
FONT = '"Poppins", system-ui, -apple-system, "Segoe UI", sans-serif'
FONT_TITRE = 'Georgia, "Times New Roman", serif'


# ---------------------------------------------------------------- Blocs d'évolution
def sparkline(v: list, w: list | None = None, annees: list | None = None) -> str:
    """Petite courbe SVG de la couleur du texte du bloc (valeurs en M€) ; w = courbe de comparaison en pointillés."""
    W, H, px, py = 220, 64, 6, 8
    vmax = max(max(v), max(w) if w else 0) or 1
    def pts(s):
        n = len(s)
        return [(px + i * (W - 2 * px) / (n - 1), H - py - x / vmax * (H - 2 * py)) for i, x in enumerate(s)]
    p = pts(v)
    ligne = " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
    aire = f"M{p[0][0]:.1f},{H} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in p) + f" L{p[-1][0]:.1f},{H} Z"
    svg = [f'<svg viewBox="0 0 {W} {H}" class="spark" aria-hidden="true" focusable="false">',
           f'<path d="{aire}" fill="currentColor" fill-opacity=".14"/>']
    if w:
        lw = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts(w))
        svg.append(f'<polyline points="{lw}" fill="none" stroke="currentColor" stroke-opacity=".6" '
                   'stroke-width="1.6" stroke-dasharray="4 3"/>')
    svg.append(f'<polyline points="{ligne}" fill="none" stroke="currentColor" stroke-width="2.4" '
               'stroke-linejoin="round" stroke-linecap="round"/>')
    for i, (x, y) in enumerate(p):
        dernier = i == len(p) - 1
        titre = f"<title>{annees[i]} : {fr(v[i])} M€</title>" if annees else ""
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.2 if dernier else 3}" fill="currentColor" '
                   f'fill-opacity="{1 if dernier else .85}">{titre}</circle>')
    svg.append("</svg>")
    return "".join(svg)


def evolution_pct(v0: float, v1: float) -> str:
    if v0 <= 0:
        return "nouveau"
    d = (v1 / v0 - 1) * 100
    return f"{'+' if d >= 0 else '−'}{fr(abs(d))} %"


def titre_bloc(nom: str) -> str:
    """« Autonomie (personnes âgées…) » -> titre court + précision en petit dessous."""
    if " (" in nom and nom.endswith(")"):
        court_nom, precision = nom[:-1].split(" (", 1)
        return f'{escape(court_nom)}<small>{escape(precision)}</small>'
    return escape(nom)


def cartes_evolution(t: pd.DataFrame, comparaisons: dict | None = None) -> str:
    """Un bloc gris foncé par politique, repéré par une pastille de sa couleur : montant de la
    dernière année, évolution depuis la première, petite courbe sur la période (chaque bloc a
    sa propre échelle)."""
    annees = [str(a) for a in t.columns]
    a0, a1 = annees[0], annees[-1]
    blocs = []
    for p in [p for p in GROUPES_EVOL if p in t.index]:
        v = (t.loc[p] / 1e6).tolist()
        w, extra = None, ""
        if comparaisons and p in comparaisons:
            nom, _, serie = comparaisons[p]
            w = (serie.reindex(t.columns, fill_value=0) / 1e6).tolist()
            extra = (f'<div class="evo-x"><span class="tiret" aria-hidden="true"></span>'
                     f'{escape(nom)} : {evolution_pct(w[0], w[-1])}</div>')
        d = evolution_pct(v[0], v[-1])
        fleche = "" if d == "nouveau" else ("▲" if v[-1] >= v[0] else "▼")
        blocs.append(
            f'<article class="evo">'
            f'<h3 class="evo-t"><span class="pastille" data-cle="{COULEUR_CLE[p]}"></span>'
            f'<span>{titre_bloc(libelle(p))}</span></h3>'
            f'<div class="evo-v">{fr(v[-1])}<span> M€ en {a1}</span></div>'
            f'<div class="evo-d"><span class="puce">{fleche} {d}</span> depuis {a0}</div>'
            f'{extra}{sparkline(v, w, annees)}'
            f'<div class="evo-a"><span>{a0}</span><span>Total {fr(sum(v))} M€</span><span>{a1}</span></div>'
            f'</article>')
    return f'<div class="evo-grille">{"".join(blocs)}</div>'


def legende_empile(t: pd.DataFrame) -> str:
    """Légende HTML placée à côté du graphique empilé : même ordre que l'empilement
    (haut en premier), avec le total de la période et la part de chaque politique."""
    total = t.values.sum()
    lignes = []
    for p in reversed([p for p in GROUPES if p in t.index]):
        s = t.loc[p].sum()
        lignes.append(f'<li><span class="pastille" data-cle="{COULEUR_CLE[p]}"></span>'
                      f'<span class="lg-nom">{escape(libelle(p))}</span>'
                      f'<span class="lg-v">{fr(s / 1e6)} M€<small>{fr(s / total * 100)} %</small></span></li>')
    return f'<ul class="legende" aria-label="Légende et total de la période">{"".join(lignes)}</ul>'


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
        # « Non ventilé » hachuré : montant dont la politique n'a pas pu être déterminée
        motif = dict(shape="/", fgcolor=L["surface"], size=7, solidity=0.25) if p == NON_VENTILE else None
        fig.add_bar(
            x=annees, y=v / 1e6, name=libelle(p), meta=COULEUR_CLE[p],
            marker=dict(color=c[COULEUR_CLE[p]], line=dict(width=0), pattern=motif),
            customdata=[meur(x) for x in v],
            hovertemplate="%{x} · " + escape(libelle(p)) + "<br><b>%{customdata}</b><extra></extra>",
        )
    tot = t.sum()
    for i, x in enumerate(tot):  # position par rang : « 2020 » serait lu comme l'indice 2020
        # Total dans une pastille gris foncé au-dessus de chaque barre
        fig.add_annotation(x=i, y=x / 1e6, text=f"<b>{meur(x)}</b>", showarrow=False, yshift=20,
                           bgcolor=GRIS_FONCE, borderpad=5,
                           font=dict(color=L["surface"], size=13))
    fig.update_layout(barmode="stack", bargap=0.32, barcornerradius=8, showlegend=False)
    fig.update_yaxes(rangemode="tozero", ticksuffix=" M€", griddash="dot", showline=False,
                     zeroline=False, nticks=6, range=[0, tot.max() / 1e6 * 1.14])
    fig.update_xaxes(type="category", showline=False, tickfont=dict(size=14))
    return mise_en_page(fig, 440)


def fig_barres_h(noms, valeurs, survol, hauteur) -> go.Figure:
    """Barres horizontales classées, toutes en gris foncé, montant écrit au bout de chaque barre."""
    vmax = valeurs.max() / 1e6
    fig = go.Figure(go.Bar(
        y=noms, x=valeurs / 1e6, orientation="h", showlegend=False,
        marker=dict(color=GRIS_FONCE, line=dict(width=0)),
        text=[meur(v) for v in valeurs], textposition="outside", cliponaxis=False,
        textfont=dict(color=L["ink2"], size=12),
        customdata=survol, hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
    ))
    fig.update_layout(bargap=0.38, barcornerradius=3)
    fig.update_xaxes(showgrid=True, gridcolor=L["grid"], zeroline=False, showline=False,
                     ticksuffix=" M€", nticks=5, range=[0, vmax * 1.02])
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=L["ink2"], size=13), automargin=True,
                     showline=False, ticks="outside", ticklen=8, tickcolor="rgba(0,0,0,0)")
    fig = mise_en_page(fig, hauteur)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(margin=dict(r=80))   # marge fixe pour les montants, quelle que soit la largeur
    return fig


# ---------------------------------------------------------------- Solidarités : renouvellement
def court(g: str) -> str:
    """Libellé court pour les axes : « Autonomie (personnes âgées… » -> « Autonomie<br>(PA et PH) »."""
    return {"Autonomie (personnes âgées et personnes handicapées)": "Autonomie<br>(pers. âgées et handicapées)",
            "Insertion et développement social": "Insertion et<br>développement social",
            "Total solidarités humaines": "<b>Total solidarités<br>humaines</b>"}.get(g, g)


def fig_taux(syn: pd.DataFrame) -> go.Figure:
    """Taux d'entrée et de sortie par groupe (rapportés aux bénéficiaires de 2020)."""
    groupes = list(syn.index)
    fig = go.Figure()
    # Entrées / sorties en gris (foncé / clair) : les couleurs restent réservées aux politiques
    for col, nom, teinte, eff in [("taux d'entrée (%)", "Taux d'entrée", GRIS_FONCE, "entrants"),
                                  ("taux de sortie (%)", "Taux de sortie", GRIS_CLAIR, "sortants")]:
        fig.add_bar(
            y=[court(g) for g in groupes], x=syn[col], name=nom, orientation="h",
            marker=dict(color=teinte, line=dict(color=L["surface"], width=2)),
            text=[f"{fr(v)} %" for v in syn[col]], textposition="outside", cliponaxis=False,
            textfont=dict(color=L["ink2"]),
            customdata=[f"{int(n)} {eff} sur {int(b)} bénéficiaires en 2020"
                        for n, b in zip(syn[eff], syn.iloc[:, 0])],
            hovertemplate="<b>" + nom + " : %{x:.1f} %</b><br>%{customdata}<extra></extra>",
        )
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08, barcornerradius=3,
                      legend=dict(orientation="h", y=-0.08, x=0, font=dict(color=L["ink2"])))
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False,
                     range=[0, max(syn["taux d'entrée (%)"].max(), syn["taux de sortie (%)"].max()) * 1.2])
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=L["ink2"]), automargin=True)
    return mise_en_page(fig, 400)


def fig_flux(flux: pd.DataFrame, groupes: list) -> go.Figure:
    """Entrées (au-dessus de zéro) et sorties (en dessous) par année, un panneau par groupe."""
    fig = make_subplots(rows=1, cols=len(groupes), shared_yaxes=True, horizontal_spacing=0.03,
                        subplot_titles=[court(g).replace("<b>", "").replace("</b>", "") for g in groupes])
    for i, g in enumerate(groupes, 1):
        x = flux[flux.groupe == g]
        annees = [str(a) for a in x.annee]
        for col, nom, teinte, signe in [("entrants", "Entrées", GRIS_FONCE, 1), ("sortants", "Sorties", GRIS_CLAIR, -1)]:
            fig.add_bar(
                x=annees, y=signe * x[col], name=nom, showlegend=(i == 1), legendgroup=nom,
                marker=dict(color=teinte, line=dict(color=L["surface"], width=2)),
                customdata=x[col],
                hovertemplate="%{x} · " + nom + " : <b>%{customdata}</b><extra>" + escape(g) + "</extra>",
                row=1, col=i,
            )
    fig.update_layout(barmode="relative", bargap=0.35, barcornerradius=3,
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
<section class="card" id="renouvellement">
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
# Gamme séquentielle de la couleur d'Insertion (clair = faible, foncé = élevé) ; elle démarre
# assez soutenue pour qu'un petit montant reste distinct des cases vides (gris neutre).
GAMME_INSERTION = [[0, "#F7A1B3"], [0.35, "#E3356A"], [0.7, "#9D174D"], [1, "#6B0F3C"]]


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
    fig.add_heatmap(z=lg(val), x=x_an, y=etiquettes, colorscale=GAMME_INSERTION, zmin=zmin, zmax=zmax,
                    xgap=2, ygap=2, customdata=survol, hovertemplate="%{customdata}<extra></extra>",
                    colorbar=dict(title=dict(text="Montant de l'année (échelle log)", side="top"),
                                  orientation="h", x=0.4, xanchor="center", y=-0.01, yanchor="top",
                                  len=0.6, thickness=10, tickvals=ticks,
                                  ticktext=[etiq_ticks[t] for t in ticks], outlinewidth=0),
                    row=1, col=1)
    # Colonne Total, séparée, sur sa propre échelle, avec le montant écrit dans la case
    fig.add_heatmap(z=lg(tot_col), x=["Total"], y=etiquettes, colorscale=GAMME_INSERTION, showscale=False,
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
<section class="card" id="hors-fse">
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
               "Dans le bloc Autonomie, la courbe en pointillés (« sans Morbihan Habitat ») le retire pour montrer "
               "l'évolution à périmètre comparable ; elle se confond avec la courbe pleine dès que Morbihan Habitat "
               "n'y figure plus.")

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

    tab_evol = t_evol.map(lambda x: fr(x / 1e6))
    tab_evol["Évolution"] = [evolution_pct(r.iloc[0], r.iloc[-1]) for _, r in t_evol.iterrows()]
    tab_evol.index = [libelle(p) for p in tab_evol.index]
    tab_evol = tab_evol.reset_index().rename(columns={"index": "Politique (M€)"})
    tab_evol.columns = [str(c) for c in tab_evol.columns]

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

    # Onglets : un tableau visible à la fois (tous visibles sans script et à l'impression)
    onglets = [
        ("ef", "Enfance et famille", bloc_solidarites(tot, EF), EF),
        ("fse", "Insertion – FSE", bloc_solidarites(tot, IDS_FSE, colonne="groupe_evolution"), IDS_FSE),
        ("hors", "Insertion – hors FSE", bloc_solidarites(tot, IDS_HORS, colonne="groupe_evolution"), IDS_HORS),
        ("auto", "Autonomie", bloc_solidarites(tot, AUTONOMIE), AUTONOMIE),
    ]
    boutons = "".join(
        f'<button type="button" role="tab" id="onglet-{k}" aria-controls="panneau-{k}" '
        f'aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">'
        f'<span class="pastille" data-cle="{COULEUR_CLE[g]}"></span>{escape(lib)}</button>'
        for i, (k, lib, _, g) in enumerate(onglets))
    panneaux = "".join(
        f'<div role="tabpanel" id="panneau-{k}" aria-labelledby="onglet-{k}" class="panneau">{bloc}</div>'
        for k, _, bloc, _ in onglets)
    solidarites_html = (f'<div class="onglets" data-onglets>'
                        f'<div role="tablist" aria-label="Groupe des Solidarités humaines">{boutons}</div>'
                        f'{panneaux}</div>')


    nb_ans = a_max - a_min + 1
    icones = {
        "euro": '<path d="M17 7.5A6 6 0 1 0 17 16.5"/><path d="M5 10.5h8M5 13.5h8"/>',
        "doc": '<rect x="6" y="3" width="12" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
        "gens": '<circle cx="9" cy="8" r="3"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/>'
                '<circle cx="17" cy="9" r="2.5"/><path d="M15.5 14.2A4.5 4.5 0 0 1 21 19"/>',
        "cal": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    }
    kpis = [
        ("euro", meur(montant), "Montant total attribué", f"≈ {meur(montant / nb_ans)} par an"),
        ("doc", fr(nb_subv, 0), "Subventions", f"{fr(montant / nb_subv / 1e3, 0)} k€ en moyenne"),
        ("gens", fr(nb_benef, 0), "Bénéficiaires distincts", "personnes morales"),
        ("cal", f"{a_min}–{a_max}", f"Années couvertes", f"{nb_ans} exercices"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-tete"><span class="kpi-i"><svg viewBox="0 0 24 24" aria-hidden="true">'
        f'{icones[i]}</svg></span><span class="kpi-l">{escape(l)}</span></div>'
        f'<div class="kpi-v">{v}</div><div class="kpi-s">{escape(s)}</div></div>'
        for i, v, l, s in kpis)

    # Variables CSS (couleurs des séries, habillage, bandeau gris) ; thème clair uniquement
    BANDEAU = {
        "light": dict(band1="#f3f2ee", band2="#e2e0da", tile="rgba(255,255,255,.72)",
                      tileb="rgba(255,255,255,.95)", iconbg="#3b3b38", iconfg="#ffffff",
                      ombre="0 1px 2px rgba(20,20,10,.04), 0 6px 20px rgba(20,20,10,.05)"),
    }
    def vars_css(m: str) -> str:
        th, b, s = THEME[m], BANDEAU[m], couleurs(m)
        return (f"--page:{th['page']};--surface:{th['surface']};--ink:{th['ink']};--ink2:{th['ink2']};"
                f"--muted:{th['muted']};--grid:{th['grid']};--border:{th['border']};"
                + "".join(f"--{k}:{v};" for k, v in s.items())
                + f"--band1:{b['band1']};--band2:{b['band2']};--tile:{b['tile']};--tileb:{b['tileb']};"
                f"--iconbg:{b['iconbg']};--iconfg:{b['iconfg']};--ombre:{b['ombre']};")
    pastilles_css = "\n".join(f'.pastille[data-cle="{k}"] {{ background: var(--{k}); }}' for k in couleurs("light"))

    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subventions du Morbihan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap">
<script>{get_plotlyjs()}</script>
<style>
:root {{ color-scheme: light; {vars_css('light')} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink); font-family: {FONT}; line-height: 1.55; font-size: 15px; }}
h1, h2, h3, .h3 {{ font-family: {FONT_TITRE}; font-weight: 700; letter-spacing: -.005em; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; }}

/* Bandeau du haut */
.bandeau {{ position: relative; overflow: hidden; overflow: clip; border-radius: 22px; padding: 28px 32px 32px;
  background: linear-gradient(135deg, var(--band1), var(--band2)); border: 1px solid var(--border);
  box-shadow: var(--ombre); margin-bottom: 20px; }}
.bandeau::before, .bandeau::after {{ content: ""; position: absolute; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, rgba(255,255,255,.55), rgba(255,255,255,0) 70%); }}
.bandeau::before {{ width: 420px; height: 420px; right: -120px; top: -180px; }}
.bandeau::after {{ width: 260px; height: 260px; right: 220px; bottom: -170px; opacity: .6; }}
.bandeau > * {{ position: relative; }}
.bandeau h1 {{ font-size: 2.1rem; line-height: 1.2; margin: 0 0 8px; max-width: 820px; }}
.bandeau .chapeau {{ margin: 0; color: var(--ink2); max-width: 820px; }}
.provisoire {{ display: inline-block; margin-top: 10px; padding: 2px 10px; border-radius: 999px; font-size: .8rem;
  font-weight: 500; color: var(--ink2); background: var(--tile); border: 1px solid var(--tileb); }}
.citation {{ margin: 20px 0 0; padding: 2px 0 2px 18px; border-left: 3px solid var(--ink2); max-width: 780px; }}
.citation p {{ margin: 0; font-family: {FONT_TITRE}; font-style: italic; color: var(--ink); font-size: 1.08rem; line-height: 1.5; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0 0; }}
.kpi {{ background: var(--tile); border: 1px solid var(--tileb); border-radius: 16px; padding: 14px 18px 16px;
  backdrop-filter: blur(6px); }}
.kpi-tete {{ display: flex; align-items: center; gap: 10px; }}
.kpi-i {{ width: 30px; height: 30px; border-radius: 9px; background: var(--iconbg); color: var(--iconfg);
  display: inline-grid; place-items: center; flex: none; }}
.kpi-i svg {{ width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.8;
  stroke-linecap: round; stroke-linejoin: round; }}
.kpi-l {{ color: var(--ink2); font-size: .85rem; font-weight: 500; }}
.kpi-v {{ font-size: 2rem; font-weight: 600; margin-top: 10px; line-height: 1.1; font-variant-numeric: tabular-nums; }}
.kpi-s {{ color: var(--muted); font-size: .8rem; margin-top: 4px; }}

/* Sommaire */
html {{ scroll-behavior: smooth; }}
@media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
section[id] {{ scroll-margin-top: 76px; }}
.sommaire {{ position: sticky; top: 10px; z-index: 10; display: flex; gap: 4px; overflow-x: auto;
  scrollbar-width: none; margin: 0 0 18px; padding: 6px; border-radius: 999px;
  background: rgba(252,252,251,.88); backdrop-filter: blur(8px); border: 1px solid var(--border); box-shadow: var(--ombre); }}
.sommaire::-webkit-scrollbar {{ display: none; }}
.sommaire a {{ flex: none; padding: 6px 14px; border-radius: 999px; font-size: .84rem; font-weight: 500;
  color: var(--ink2); text-decoration: none; white-space: nowrap; }}
.sommaire a:hover {{ background: var(--band1); color: var(--ink); }}
.sommaire a.actif {{ background: {GRIS_ACCENT}; color: #fff; }}
.sommaire a:focus-visible {{ outline: 2px solid {GRIS_ACCENT}; outline-offset: 2px; }}
@media print {{ .sommaire {{ display: none; }} }}

/* Cartes */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--ombre);
  padding: 22px 24px 14px; margin-bottom: 18px; }}
.card h2 {{ font-size: 1.3rem; margin: 0 0 4px; }}
.card .sous {{ margin: 0 0 14px; color: var(--ink2); font-size: .88rem; }}

/* Graphique empilé + légende latérale */
.empile {{ display: grid; grid-template-columns: minmax(0, 1fr) 290px; gap: 20px; align-items: center; }}
.legende {{ list-style: none; margin: 0; padding: 0; font-size: .85rem; }}
.legende li {{ display: grid; grid-template-columns: 12px 1fr auto; gap: 10px; align-items: center;
  padding: 7px 0; border-bottom: 1px solid var(--grid); }}
.legende li:last-child {{ border-bottom: 0; }}
.legende .lg-nom {{ color: var(--ink2); line-height: 1.3; }}
.legende .lg-v {{ font-weight: 600; text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.legende small {{ display: block; font-weight: 400; color: var(--muted); font-size: .75rem; }}
.pastille[data-cle="nv"] {{ background: repeating-linear-gradient(135deg, var(--nv) 0 3px, var(--surface) 3px 4.5px); }}

/* Blocs d'évolution */
.evo-grille {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
.evo {{ border-radius: 18px; padding: 16px 16px 10px; display: flex; flex-direction: column;
  background: {GRIS_FONCE}; color: #fff; }}
.evo-t {{ display: flex; gap: 9px; align-items: flex-start; }}
.evo-t > span:last-child {{ min-width: 0; overflow-wrap: break-word; hyphens: auto; }}
.evo-t .pastille {{ flex: none; margin-top: .22em; width: 13px; height: 13px; box-shadow: 0 0 0 1.5px rgba(255,255,255,.85); }}
.evo-t {{ font-size: .98rem; line-height: 1.25; margin: 0 0 10px; min-height: 2.5em; position: relative; }}
.evo-t small {{ display: block; font-family: {FONT}; font-weight: 400; font-size: .72rem; opacity: .85; margin-top: 2px; }}
.evo-v {{ font-size: 1.85rem; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }}
.evo-v span {{ font-size: .78rem; font-weight: 400; opacity: .85; }}
.evo-d {{ font-size: .78rem; margin-top: 8px; opacity: .95; }}
.puce {{ display: inline-block; padding: 1px 8px; border-radius: 999px; background: color-mix(in srgb, currentColor 16%, transparent);
  font-weight: 600; margin-right: 2px; }}
.evo-x {{ font-size: .74rem; margin-top: 6px; opacity: .9; display: flex; align-items: center; gap: 6px; }}
.tiret {{ width: 16px; border-top: 2px dashed currentColor; opacity: .75; }}
.spark {{ display: block; width: 100%; height: auto; margin-top: auto; padding-top: 10px; overflow: visible; }}
.evo-a {{ display: flex; justify-content: space-between; font-size: .7rem; opacity: .8; margin-top: 2px; }}
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
{pastilles_css}
.note {{ color: var(--ink2); font-size: .85rem; margin: 6px 0 0; }}
.table-scroll {{ overflow-x: auto; }}
.h3 {{ font-size: 1rem; margin: 12px 0 2px; font-weight: 650; }}
.encadre {{ border-left: 4px solid var(--muted); padding: 4px 0 4px 16px; font-size: .9rem; }}
.encadre ul {{ margin: 8px 0; padding-left: 18px; }}
.encadre li {{ margin-bottom: 6px; }}
code {{ font-size: .85em; }}
footer {{ color: var(--ink2); font-size: .85rem; margin-top: 24px; }}
footer a {{ color: inherit; }}
.lien-depot {{ font-size: .85rem; color: var(--ink2); text-decoration: none; border-bottom: 1px solid var(--grid); }}
.lien-depot:hover, .lien-depot:focus-visible {{ color: var(--ink); border-bottom-color: currentColor; }}
.haut-depot {{ margin: 0 0 12px; }}
.bas-depot {{ margin: 8px 0 0; }}
.onglets [role="tablist"] {{ display: none; }}
.onglets.actifs [role="tablist"] {{ display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 1px solid var(--border); margin: 8px 0 0; }}
.onglets [role="tab"] {{ display: inline-flex; align-items: center; gap: 8px; font: inherit; font-size: .92rem;
  color: var(--ink2); background: none; border: 0; border-bottom: 3px solid transparent;
  padding: 8px 12px; margin-bottom: -1px; cursor: pointer; border-radius: 6px 6px 0 0; }}
.onglets [role="tab"]:hover {{ color: var(--ink); background: var(--page); }}
.onglets [role="tab"][aria-selected="true"] {{ color: var(--ink); font-weight: 650; border-bottom-color: var(--ink); }}
.onglets [role="tab"]:focus-visible {{ outline: 2px solid var(--ink); outline-offset: 2px; }}
.onglets.actifs .panneau[hidden] {{ display: none; }}
.onglets.actifs .bloc-sol {{ margin-top: 12px; }}
.onglets.actifs .bloc-sol h3 {{ display: none; }}
@media print {{
  .onglets [role="tablist"] {{ display: none !important; }}
  .onglets .panneau[hidden] {{ display: block !important; }}
  .onglets .bloc-sol h3 {{ display: flex !important; }}
}}
@media (max-width: 600px) {{
  .onglets.actifs [role="tablist"] {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }}
  .onglets [role="tab"] {{ padding: 8px 6px; font-size: .85rem; gap: 6px; text-align: left; }}
}}
@media (max-width: 960px) {{
  .evo-grille {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  .empile {{ grid-template-columns: 1fr; }}
  .legende {{ columns: 2; column-gap: 24px; }}
  .legende li {{ break-inside: avoid; }}
}}
@media (max-width: 760px) {{
  .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
  .kpi {{ padding: 12px; }}
  .duo {{ grid-template-columns: 1fr; }}
  .evo-grille {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
  .bandeau {{ padding: 22px 18px 20px; border-radius: 18px; }}
  .bandeau h1 {{ font-size: 1.6rem; }}
  .legende {{ columns: 1; }}
}}
@media (max-width: 420px) {{
  .kpi-v {{ font-size: 1.3rem; }}
  .kpi-tete {{ flex-direction: column; align-items: flex-start; gap: 6px; }}
  .kpi-l {{ line-height: 1.25; }}
  .evo {{ padding: 14px 12px 8px; }}
  .evo-v {{ font-size: 1.45rem; }}
  .evo-t {{ font-size: .82rem; gap: 6px; flex-direction: column; }}
  .evo-t .pastille {{ width: 11px; height: 11px; }}
  .evo-a span:nth-child(2) {{ display: none; }}
}}
</style>
</head>
<body>
<main>
<header class="bandeau">
  <p class="haut-depot"><a class="lien-depot" href="{DEPOT_URL}">{LIEN_DEPOT}</a></p>
  <h1>Subventions du Département du Morbihan, {a_min}–{a_max}</h1>
  <p class="chapeau">Subventions aux personnes morales, ventilées selon la segmentation stratégique du Département au 1<sup>er</sup> janvier 2025. Document provisoire, susceptible d'évoluer : les chiffres présentés ne constituent pas une donnée officielle.</p>
  <blockquote class="citation"><p>Une politique publique ne peut se mesurer à sa seule enveloppe budgétaire. Elle vaut aussi par la qualité du travail de celles et ceux qui la mettent en œuvre et par les conditions dans lesquelles ils exercent leur métier.</p></blockquote>
  <section class="kpis" aria-label="Chiffres clés">{kpi_html}</section>
</header>

<nav class="sommaire" aria-label="Sommaire">
  <a href="#montants">Montants</a><a href="#evolution">Évolution</a><a href="#types">Types de bénéficiaires</a><a href="#limites">Limites</a><a href="#top15">15 premiers</a><a href="#solidarites">Solidarités</a><a href="#hors-fse">Insertion hors FSE</a><a href="#renouvellement">Renouvellement</a>
</nav>

<section class="card" id="montants">
  <h2>Montants par année et par politique publique</h2>
  <p class="sous">En millions d'euros. Total de l'année au-dessus de chaque barre ; dans la légende, le total de chaque politique sur la période. Les Solidarités humaines sont découpées en trois groupes (Enfance et famille, Insertion, Autonomie) ; « Non ventilé » est hachuré.</p>
  <div class="empile"><div>{div['empile']}</div>{legende_empile(t)}</div>
  <details><summary>Voir les données</summary>{table_html(tab_pol)}</details>
</section>

<section class="card" id="evolution">
  <h2>Évolution de chaque politique publique, {a_min}–{a_max}</h2>
  <p class="sous">Montant de la dernière année et évolution depuis {a_min}. Attention : chaque courbe a sa propre échelle, pour rendre lisibles les petites politiques ; comparez les montants, pas les hauteurs (survolez un point pour son montant). Le groupe Insertion est séparé en deux selon l'objet de chaque subvention : fonds européens (FSE) et hors FSE.</p>
  {cartes_evolution(t_evol, {AUTONOMIE: ("sans Morbihan Habitat", "sans MH", auto_sans_mh)})}
  <details><summary>Voir les données</summary><div class="table-scroll">{table_html(tab_evol)}</div></details>
  <p class="note">Les subventions FSE (Fonds social européen) sont des fonds européens gérés par le Département : elles ne relèvent pas uniquement de crédits départementaux propres.</p>
  <p class="note">{escape(mh_note)}</p>
</section>

<div class="duo">
<section class="card" id="types">
  <h2>Répartition par type de bénéficiaire</h2>
  <p class="sous">Montant total sur la période. Type déduit du nom du bénéficiaire.</p>
  {div['types']}
  <details><summary>Voir les données</summary>{table_html(tab_types)}</details>
</section>

<section class="card qualite" id="limites">
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

<section class="card" id="top15">
  <h2>Les 15 premiers bénéficiaires, {a_min}–{a_max}</h2>
  <p class="sous">Montant total reçu sur la période, après fusion des identifiants.</p>
  {div['top']}
  <details><summary>Voir les données</summary>{table_html(tab_top)}</details>
</section>

<section class="card" id="solidarites">
  <h2>Solidarités : principaux bénéficiaires, {a_min}–{a_max}</h2>
  <p class="sous">Les 10 premiers bénéficiaires de chaque groupe des Solidarités humaines, par montant total : choisissez le groupe avec les onglets. Le groupe Insertion est présenté en deux tableaux (FSE et hors FSE). Une structure qui reçoit les deux types de subventions apparaît dans les deux, avec le montant propre à chacun. Objet principal : celui qui représente le plus gros montant pour ce bénéficiaire dans le groupe.</p>
  {solidarites_html}
</section>
{hors_fse_html}
{renouv_html}

<footer>
  Source : Département du Morbihan, « Subventions aux personnes morales », data.gouv.fr, Licence Ouverte —
  <a href="{SOURCE_URL}">{SOURCE_URL}</a>. Fichier téléchargé le {DATE_TELECHARGEMENT}.
  Traitements : clean.py, fusions.py, categorize.py, renouvellement.py, build_dashboard.py.
  <p class="bas-depot"><a class="lien-depot" href="{DEPOT_URL}">{LIEN_DEPOT}</a></p>
</footer>
</main>
<script>
(function () {{
  // Police Poppins chargée après coup : les graphiques recalculent la place de leurs textes
  if (document.fonts) document.fonts.ready.then(function () {{
    document.querySelectorAll(".js-plotly-plot").forEach(function (gd) {{ Plotly.Plots.resize(gd); }});
  }});
  // Sommaire : met en avant la section en cours de lecture
  var liens = Array.prototype.slice.call(document.querySelectorAll(".sommaire a"));
  if (!("IntersectionObserver" in window) || !liens.length) return;
  var visibles = {{}}, pause = 0;
  function marquer(id) {{
    liens.forEach(function (a) {{
      var on = a.getAttribute("href") === "#" + id;
      a.classList.toggle("actif", on);
      if (on) {{ a.setAttribute("aria-current", "true"); a.scrollIntoView({{ block: "nearest", inline: "nearest" }}); }}
      else a.removeAttribute("aria-current");
    }});
  }}
  var obs = new IntersectionObserver(function (entrees) {{
    entrees.forEach(function (e) {{ visibles[e.target.id] = e.isIntersecting; }});
    if (Date.now() < pause) return;
    // Première section visible dans l'ordre du sommaire (deux blocs côte à côte : celui de gauche)
    for (var i = 0; i < liens.length; i++) {{
      var id = liens[i].getAttribute("href").slice(1);
      if (visibles[id]) {{ marquer(id); return; }}
    }}
  }}, {{ rootMargin: "-25% 0px -55% 0px" }});
  liens.forEach(function (a) {{
    var cible = document.querySelector(a.getAttribute("href"));
    if (cible) obs.observe(cible);
    a.addEventListener("click", function () {{ pause = Date.now() + 1200; marquer(a.getAttribute("href").slice(1)); }});
  }});
}})();
</script>
<script>
document.querySelectorAll("[data-onglets]").forEach(function (box) {{
  var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));
  function choisir(t, focus) {{
    tabs.forEach(function (b) {{
      var on = b === t;
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.tabIndex = on ? 0 : -1;
      document.getElementById(b.getAttribute("aria-controls")).hidden = !on;
    }});
    if (focus) t.focus();
  }}
  tabs.forEach(function (b, i) {{
    b.addEventListener("click", function () {{ choisir(b); }});
    b.addEventListener("keydown", function (e) {{
      var j = {{ ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }}[e.key];
      if (j === undefined) return;
      e.preventDefault();
      choisir(tabs[(j + tabs.length) % tabs.length], true);
    }});
  }});
  box.classList.add("actifs");
  choisir(tabs[0]);
}});
</script>
<script>{JS_ECRAN_ETROIT}</script>
</body>
</html>
"""
    SORTIE.write_text(html, encoding="utf-8")
    print(f"-> {SORTIE.name} ({SORTIE.stat().st_size / 1e6:.1f} Mo)")
    print(f"Chiffres clés : {meur(montant)} · {nb_subv} subventions · {nb_benef} bénéficiaires · {a_min}–{a_max}")


if __name__ == "__main__":
    main()
