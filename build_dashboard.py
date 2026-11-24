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
POLITIQUES = [*GRILLE, NON_VENTILE]
COULEUR_CLE = {p: f"s{i}" for i, p in enumerate(GRILLE)} | {NON_VENTILE: "nv"}


def couleurs(mode: str) -> dict:
    c = {f"s{i}": h for i, h in enumerate(SERIES[mode])}
    c["nv"] = GRIS_NV[mode]
    return c


def libelle(p: str) -> str:
    """« SOLIDARITÉS HUMAINES » -> « Solidarités humaines »."""
    return p if p == NON_VENTILE else p[0] + p[1:].lower()


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
    for p in POLITIQUES:
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


def fig_multiples(t: pd.DataFrame) -> go.Figure:
    """Un petit graphique par politique publique, chacun avec sa propre échelle."""
    c = couleurs("light")
    pols = [p for p in POLITIQUES if p in t.index]
    ncol = 4
    nrow = -(-len(pols) // ncol)
    fig = make_subplots(rows=nrow, cols=ncol, subplot_titles=[libelle(p) for p in pols],
                        vertical_spacing=0.2, horizontal_spacing=0.06)
    annees = [str(a) for a in t.columns]
    for i, p in enumerate(pols):
        r, col = i // ncol + 1, i % ncol + 1
        v = t.loc[p] / 1e6
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
    return mise_en_page(fig, 220 * nrow + 40)


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


# ---------------------------------------------------------------- Programme principal
def main() -> None:
    df = pd.read_csv(SOURCE, sep=";", encoding="utf-8-sig",
                     dtype={"idBeneficiaire": str, "idBeneficiaire_original": str, "id": str})
    tot = df[df["inclus_totaux"]]

    # Chiffres clés
    montant = tot["montant"].sum()
    nb_subv = len(tot)
    nb_benef = tot["idBeneficiaire"].nunique()
    a_min, a_max = tot["annee"].min(), tot["annee"].max()

    # Données des graphiques
    t = tot.pivot_table(index="politique_publique", columns="annee", values="montant",
                        aggfunc="sum", fill_value=0)
    t = t.loc[[p for p in POLITIQUES if p in t.index]]

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
        "multiples": fig_multiples(t),
        "types": fig_barres_h(
            types.index.tolist(), types["montant"],
            [f"{fr(r.subventions, 0)} subventions · {fr(r.beneficiaires, 0)} bénéficiaires"
             for r in types.itertuples()], 330),
        "top": fig_barres_h(
            top["nom"].tolist(), top["montant"],
            [f"{escape(r.type)} · {fr(r.subventions, 0)} subventions" for r in top.itertuples()], 560),
    }
    config = dict(displayModeBar=False, responsive=True)
    div = {k: f.to_html(full_html=False, include_plotlyjs=False, div_id=f"fig-{k}", config=config)
           for k, f in figs.items()}

    # Tableaux (équivalent accessible de chaque graphique)
    tab_pol = t.copy()
    tab_pol["Total"] = tab_pol.sum(axis=1)
    tab_pol.loc["Total"] = tab_pol.sum()
    part = tab_pol["Total"] / tab_pol.loc["Total", "Total"] * 100
    tab_pol = tab_pol.map(lambda x: fr(x / 1e6))
    tab_pol["Part"] = [f"{fr(x)} %" for x in part]
    tab_pol.index = [libelle(p) for p in tab_pol.index]
    tab_pol = tab_pol.reset_index().rename(columns={"index": "Politique publique (M€)"})
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
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --page: {THEME['dark']['page']}; --surface: {THEME['dark']['surface']}; --ink: {THEME['dark']['ink']};
    --ink2: {THEME['dark']['ink2']}; --muted: {THEME['dark']['muted']}; --grid: {THEME['dark']['grid']};
    --border: {THEME['dark']['border']};
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page: {THEME['dark']['page']}; --surface: {THEME['dark']['surface']}; --ink: {THEME['dark']['ink']};
  --ink2: {THEME['dark']['ink2']}; --muted: {THEME['dark']['muted']}; --grid: {THEME['dark']['grid']};
  --border: {THEME['dark']['border']};
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
  <p class="sous">En millions d'euros. Total de l'année au-dessus de chaque barre.</p>
  {div['empile']}
  <details><summary>Voir les données</summary>{table_html(tab_pol)}</details>
</section>

<section class="card">
  <h2>Évolution de chaque politique publique, {a_min}–{a_max}</h2>
  <p class="sous">En millions d'euros. Attention : chaque graphique a sa propre échelle, pour rendre lisibles les petites politiques ; comparez les montants, pas les hauteurs.</p>
  {div['multiples']}
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
