"""Renouvellement des bénéficiaires des Solidarités humaines, 2020-2023.

Unité : le couple bénéficiaire (identifiant après fusion) × groupe d'affichage
(Enfance et famille ; Insertion et développement social ; Autonomie).
La ligne « Total solidarités humaines » compte chaque organisation une seule fois,
tous groupes confondus.

Statut d'un couple, d'après sa première et sa dernière année de subvention :
  présent  : première année 2020 et dernière année 2023 (des trous sont possibles entre les deux)
  entrant  : première année après 2020, encore financé en 2023
  sortant  : financé dès 2020, dernière année avant 2023
  ponctuel : arrivé après 2020 et reparti avant 2023

Exclusions : « Tiers anonymisé », montants à 0 €, les couples entrant/sortant dont le nom
normalisé est identique dans le même groupe, et les paires de noms proches listées dans
ref/renouvellement_exclusions.csv (décision manuelle) : changements d'identifiant probables.

Financements pluriannuels : le fichier source ne renseigne ni la période ni les conditions de
versement (colonnes vides). Les couples au rythme irrégulier sont marqués « pluriannuel probable »
(voir pluriannuel()) ; les résultats sont donnés avec et sans les entrants/sortants concernés.

Usage : python renouvellement.py   (affiche les résultats, écrit data/renouvellement_solidarites.csv
                                    et data/pluriannuels_solidarites.csv)
"""
from pathlib import Path

import pandas as pd

from build_dashboard import ANONYME, AUTONOMIE, EF, IDS, OBJET_FSE, politique_affichage
from clean import cle_nom
from fusions import lire_csv

RACINE = Path(__file__).parent
SOURCE = RACINE / "data" / "subventions_final.csv"
EXCLUSIONS = RACINE / "ref" / "renouvellement_exclusions.csv"
LISTES = RACINE / "data" / "renouvellement_solidarites.csv"
PLURIANNUELS = RACINE / "data" / "pluriannuels_solidarites.csv"
GROUPES_SH = [EF, IDS, AUTONOMIE]
TOTAL = "Total solidarités humaines"
STATUTS = ["présent", "entrant", "sortant", "ponctuel"]


def charger(chemin: Path = SOURCE) -> pd.DataFrame:
    df = pd.read_csv(chemin, sep=";", encoding="utf-8-sig",
                     dtype={"idBeneficiaire": str, "idBeneficiaire_original": str, "id": str})
    df["politique_affichage"] = politique_affichage(df)
    return df


def lignes_sh(df: pd.DataFrame) -> pd.DataFrame:
    """Subventions des trois groupes Solidarités, hors 0 € et hors tiers anonymisés."""
    return df[df["inclus_totaux"] & df["politique_affichage"].isin(GROUPES_SH)
              & (df["nom_affichage"] != ANONYME)].copy()


def couples(d: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par couple groupe × identifiant (plus les lignes « Total », par identifiant)."""
    tout = pd.concat([d, d.assign(politique_affichage=TOTAL)])
    a0, a1 = int(d["annee"].min()), int(d["annee"].max())
    cle = ["politique_affichage", "idBeneficiaire"]
    c = (tout.groupby(cle)
         .agg(nom=("nom_affichage", "first"), type=("type_beneficiaire", "first"),
              premiere=("annee", "min"), derniere=("annee", "max"),
              nb_annees=("annee", "nunique"), subventions=("id", "size"),
              montant_total=("montant", "sum"))
         .reset_index())
    par_an = tout.pivot_table(index=cle, columns="annee", values="montant", aggfunc="sum", fill_value=0)
    par_an.columns = [f"montant_{a}" for a in par_an.columns]
    c = c.join(par_an, on=cle)
    # Montants hors FSE : aucune subvention FSE n'est versée en 2022, ce qui créerait de faux
    # rythmes « une année sur deux » et de faux pics en 2023 ; la détection pluriannuelle les ignore.
    hors = tout[tout["objet"] != OBJET_FSE]
    hors_an = (hors.pivot_table(index=cle, columns="annee", values="montant", aggfunc="sum", fill_value=0)
               .reindex(columns=range(a0, a1 + 1), fill_value=0))
    hors_an.columns = [f"hors_fse_{a}" for a in hors_an.columns]
    c = c.join(hors_an, on=cle)
    c[hors_an.columns] = c[hors_an.columns].fillna(0)
    c["statut"] = "ponctuel"
    c.loc[(c.premiere == a0) & (c.derniere == a1), "statut"] = "présent"
    c.loc[(c.premiere > a0) & (c.derniere == a1), "statut"] = "entrant"
    c.loc[(c.premiere == a0) & (c.derniere < a1), "statut"] = "sortant"
    c["cle_nom"] = c["nom"].map(cle_nom)
    c.attrs["a0"], c.attrs["a1"] = a0, a1
    return pluriannuel(c)


def pluriannuel(c: pd.DataFrame) -> pd.DataFrame:
    """Repère les financements pluriannuels probables (les colonnes datesPeriodeVersement et
    conditionsVersement du fichier source sont vides : on ne peut que les déduire du rythme).

    Un couple est « pluriannuel probable » s'il a au moins deux années financées et :
      - un rythme régulier « une année sur deux » (écarts de 2 ans) ou « une sur trois » (écart de 3 ans) ;
      - ou une année dont le montant dépasse 2 fois le montant médian de ses autres années financées.
    Seuls les montants hors FSE sont examinés (pas de FSE en 2022) : un couple financé
    uniquement par le FSE n'est jamais marqué.
    """
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    annees = list(range(a0, a1 + 1))
    m = c[[f"hors_fse_{a}" for a in annees]].to_numpy()
    motifs = []
    for ligne in m:
        fin = [a for a, v in zip(annees, ligne) if v > 0]
        mot = []
        if len(fin) >= 2:
            ecarts = {b - a for a, b in zip(fin, fin[1:])}
            if ecarts == {2}:
                mot.append("une année sur deux")
            elif ecarts == {3}:
                mot.append("une année sur trois")
            vals = {a: v for a, v in zip(annees, ligne) if v > 0}
            for a, v in vals.items():
                autres = [x for b, x in vals.items() if b != a]
                med = pd.Series(autres).median()
                if v > 2 * med:
                    mot.append(f"pic en {a} ({v / med:.1f} × la médiane des autres années)")
        motifs.append(" ; ".join(mot))
    c = c.copy()
    c["motif_pluriannuel"] = motifs
    c["pluriannuel_probable"] = c["motif_pluriannuel"] != ""
    return c


def suspects(c: pd.DataFrame) -> pd.DataFrame:
    """Paires entrant/sortant de même nom normalisé, dans le même groupe, sous deux identifiants."""
    es = c[c["statut"].isin(["entrant", "sortant"])]
    paires = es[es.statut == "sortant"].merge(es[es.statut == "entrant"],
                                             on=["politique_affichage", "cle_nom"],
                                             suffixes=("_sortant", "_entrant"))
    return paires[paires.idBeneficiaire_sortant != paires.idBeneficiaire_entrant]


def exclusions_manuelles(chemin: Path = EXCLUSIONS) -> pd.DataFrame:
    """Paires de noms proches (non identiques) jugées comme des changements d'identifiant."""
    if not chemin.exists():
        return pd.DataFrame(columns=["politique_affichage", "idBeneficiaire_sortant", "idBeneficiaire_entrant"])
    return lire_csv(chemin)


def exclure_suspects(c: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    """Retire les deux couples de chaque paire, dans leur groupe et dans la ligne « Total »."""
    exclus = set()
    for g, ids, ide in zip(s.politique_affichage, s.idBeneficiaire_sortant, s.idBeneficiaire_entrant):
        exclus |= {(g, ids), (g, ide), (TOTAL, ids), (TOTAL, ide)}
    garde = [k not in exclus for k in zip(c.politique_affichage, c.idBeneficiaire)]
    out = c[garde].copy()
    out.attrs = c.attrs
    return out


def synthese(c: pd.DataFrame) -> pd.DataFrame:
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    lignes = []
    for g in [*GROUPES_SH, TOTAL]:
        x = c[c.politique_affichage == g]
        n = x.statut.value_counts()
        base = int((x[f"montant_{a0}"] > 0).sum())
        ent, sor = int(n.get("entrant", 0)), int(n.get("sortant", 0))
        lignes.append({
            "groupe": g,
            f"bénéficiaires {a0}": base,
            "présents toute la période": int(n.get("présent", 0)),
            "entrants": ent, "sortants": sor, "ponctuels": int(n.get("ponctuel", 0)),
            "taux d'entrée (%)": round(ent / base * 100, 1) if base else None,
            "taux de sortie (%)": round(sor / base * 100, 1) if base else None,
            "solde net": ent - sor,
            f"montant {a1} des entrants (€)": round(x.loc[x.statut == "entrant", f"montant_{a1}"].sum()),
            f"bénéficiaires {a1}": int((x[f"montant_{a1}"] > 0).sum()),
        })
    return pd.DataFrame(lignes).set_index("groupe")


def flux_annuels(c: pd.DataFrame) -> pd.DataFrame:
    """Par année : nouveaux entrants (première apparition cette année-là) et sortants
    (dernière apparition l'année précédente). Inconnu en {a0} (entrées) et pour {a1} (sorties futures)."""
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    lignes = []
    for g in [*GROUPES_SH, TOTAL]:
        x = c[c.politique_affichage == g]
        for a in range(a0 + 1, a1 + 1):
            lignes.append({"groupe": g, "annee": a,
                           "entrants": int((x.premiere == a).sum()),
                           "sortants": int((x.derniere == a - 1).sum()),
                           "bénéficiaires": int((x[f"montant_{a}"] > 0).sum())})
    return pd.DataFrame(lignes)


def analyser(df: pd.DataFrame | None = None):
    """Retourne (couples retenus, paires exclues, synthèse, flux annuels, synthèse avant exclusion)."""
    df = charger() if df is None else df
    c_brut = couples(lignes_sh(df))
    auto = suspects(c_brut).assign(origine="nom normalisé identique")
    manuel = exclusions_manuelles().assign(origine="noms proches (décision manuelle)")
    # Contrôle : chaque paire manuelle doit bien être un sortant et un entrant du groupe indiqué
    st = c_brut.set_index(["politique_affichage", "idBeneficiaire"])["statut"]
    for g, ids, ide in zip(manuel.politique_affichage, manuel.idBeneficiaire_sortant, manuel.idBeneficiaire_entrant):
        if st.get((g, ids)) != "sortant" or st.get((g, ide)) != "entrant":
            raise ValueError(f"Paire d'exclusion incohérente dans {EXCLUSIONS.name} : {g} / {ids} -> {ide}")
    cols = ["politique_affichage", "idBeneficiaire_sortant", "idBeneficiaire_entrant", "origine"]
    s = pd.concat([auto[cols], manuel[cols]], ignore_index=True)
    c = exclure_suspects(c_brut, s)
    return c, s, synthese(c), flux_annuels(c), synthese(c_brut)


def sans_pluriannuels(c: pd.DataFrame) -> pd.DataFrame:
    """Retire les entrants et sortants « pluriannuel probable » (leur entrée ou sortie
    peut n'être qu'un effet du rythme de financement). Présents et ponctuels sont gardés."""
    out = c[~(c["pluriannuel_probable"] & c["statut"].isin(["entrant", "sortant"]))].copy()
    out.attrs = c.attrs
    return out


def ecrire_listes(c: pd.DataFrame, chemin: Path = LISTES) -> pd.DataFrame:
    """Entrants, sortants et ponctuels de chaque groupe, avec leurs montants par année."""
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    out = c[c.statut.isin(["entrant", "sortant", "ponctuel"]) & (c.politique_affichage != TOTAL)]
    cols = (["politique_affichage", "statut", "nom", "idBeneficiaire", "type", "premiere", "derniere",
             "nb_annees", "subventions", "montant_total"] + [f"montant_{a}" for a in range(a0, a1 + 1)]
            + ["pluriannuel_probable", "motif_pluriannuel"])
    out = out[cols].sort_values(["politique_affichage", "statut", "montant_total"],
                                ascending=[True, True, False]).round(2)
    out.to_csv(chemin, sep=";", index=False, encoding="utf-8-sig")
    return out


def ecrire_pluriannuels(c: pd.DataFrame, chemin: Path = PLURIANNUELS) -> pd.DataFrame:
    """Couples « pluriannuel probable » de chaque groupe, avec leurs montants par année."""
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    out = c[c.pluriannuel_probable & (c.politique_affichage != TOTAL)]
    cols = (["politique_affichage", "statut", "nom", "idBeneficiaire", "type", "motif_pluriannuel",
             "subventions", "montant_total"] + [f"montant_{a}" for a in range(a0, a1 + 1)]
            + [f"hors_fse_{a}" for a in range(a0, a1 + 1)])
    out = out[cols].sort_values(["politique_affichage", "montant_total"], ascending=[True, False]).round(2)
    out.to_csv(chemin, sep=";", index=False, encoding="utf-8-sig")
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 60)
    c, s, syn, flux, syn_brut = analyser()
    a0, a1 = c.attrs["a0"], c.attrs["a1"]
    print("=== PAIRES EXCLUES (changements d'identifiant probables)")
    print(s.to_string() if len(s) else "aucune")
    print("\n=== SYNTHÈSE (paires exclues)")
    print(syn.T.to_string())
    print("\n=== SYNTHÈSE AVANT EXCLUSION")
    print(syn_brut[["entrants", "sortants", f"bénéficiaires {a0}"]].T.to_string())
    print("\n=== FLUX ANNUELS (entrants : première apparition ; sortants : dernière apparition l'année précédente)")
    print(flux.pivot(index="annee", columns="groupe").to_string())
    print(f"\nRappel : on ne sait pas qui est nouveau en {a0} (première année des données),"
          f" ni qui s'arrêtera après {a1} (dernière année).")
    print("\n=== SYNTHÈSE SANS LES ENTRANTS/SORTANTS « PLURIANNUEL PROBABLE »")
    print(synthese(sans_pluriannuels(c)).T.to_string())
    out = ecrire_listes(c)
    print(f"\n-> {LISTES.relative_to(RACINE)} ({len(out)} lignes)")
    out = ecrire_pluriannuels(c)
    print(f"-> {PLURIANNUELS.relative_to(RACINE)} ({len(out)} lignes)")
