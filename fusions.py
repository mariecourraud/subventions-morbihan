"""Fusion manuelle des bénéficiaires ayant le même nom sous plusieurs identifiants.

Deux usages :
  python fusions.py        -> génère ref/fusions.csv à remplir (refuse d'écraser un fichier existant)
  from fusions import appliquer_fusions
  df = appliquer_fusions(df)   -> applique les décisions saisies dans ref/fusions.csv

Dans ref/fusions.csv, seules les lignes où id_retenu est rempli sont appliquées :
l'idBeneficiaire de ce couple (nom, identifiant) est remplacé par id_retenu.
"""
from pathlib import Path

import pandas as pd

from clean import ANONYME, cle_nom

RACINE = Path(__file__).parent
DONNEES = RACINE / "data" / "subventions_clean.csv"
A_VERIFIER = RACINE / "data" / "a_verifier.csv"
FUSIONS = RACINE / "ref" / "fusions.csv"

COLONNES = ["nomBeneficiaire", "idBeneficiaire", "nb_subventions", "montant_total",
            "annees", "objets", "id_retenu", "raison"]
MOTIF = "nom présent sous plusieurs idBeneficiaire"


def lire_csv(chemin: Path) -> pd.DataFrame:
    """Lit un CSV ';' en texte. Accepte l'UTF-8 et le Windows-1252
    (Excel réenregistre en Windows-1252 si on choisit « CSV » au lieu de « CSV UTF-8 »)."""
    try:
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    except UnicodeDecodeError:
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="cp1252", keep_default_na=False)


# ------------------------------------------------------------ Préparation
def preparer_fusions(chemin: Path = FUSIONS) -> pd.DataFrame:
    """Crée ref/fusions.csv : une ligne par couple (nom, identifiant) signalé dans a_verifier.csv."""
    if chemin.exists():
        raise FileExistsError(f"{chemin} existe déjà : supprimez-le d'abord pour le régénérer "
                              "(vos décisions seraient perdues).")

    df = pd.read_csv(DONNEES, sep=";", encoding="utf-8-sig", dtype={"idBeneficiaire": str})
    verif = lire_csv(A_VERIFIER)
    couples = (verif[verif["motif"].str.contains(MOTIF, regex=False)]
               [["nomBeneficiaire", "idBeneficiaire"]].drop_duplicates())

    lignes = df.merge(couples, on=["nomBeneficiaire", "idBeneficiaire"])
    top3 = lambda s: " | ".join(s.value_counts().head(3).index)
    table = (
        lignes.groupby(["nomBeneficiaire", "idBeneficiaire"])
        .agg(nb_subventions=("id", "size"),
             montant_total=("montant", "sum"),
             annees=("annee", lambda a: ", ".join(map(str, sorted(a.unique())))),
             objets=("objet", top3))
        .reset_index()
    )
    table["montant_total"] = table["montant_total"].round(2)
    table["id_retenu"] = ""
    table["raison"] = ""
    # Regroupe les variantes d'un même nom (casse, accents) les unes sous les autres
    table["_cle"] = table["nomBeneficiaire"].map(cle_nom)
    table = table.sort_values(["_cle", "idBeneficiaire"]).drop(columns="_cle")[COLONNES]

    chemin.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(chemin, sep=";", index=False, encoding="utf-8-sig")
    print(f"{chemin.relative_to(RACINE)} créé : {len(table)} couples (nom, identifiant), "
          f"{table['nomBeneficiaire'].map(cle_nom).nunique()} noms")
    return table


# ------------------------------------------------------------ Application
def appliquer_fusions(df: pd.DataFrame, chemin: Path = FUSIONS) -> pd.DataFrame:
    """Remplace idBeneficiaire par id_retenu pour les couples (nom, identifiant) décidés.

    Retourne une copie de df avec une colonne idBeneficiaire_original
    (identifiant avant fusion, identique à idBeneficiaire pour les lignes non fusionnées).
    """
    df = df.copy()
    if "idBeneficiaire_original" not in df.columns:
        df.insert(df.columns.get_loc("idBeneficiaire") + 1, "idBeneficiaire_original",
                  df["idBeneficiaire"])

    decisions = lire_csv(chemin)
    decisions = decisions.apply(lambda s: s.str.strip())
    decisions = decisions[decisions["id_retenu"] != ""]
    if decisions.empty:
        print("Fusions : aucune décision saisie dans ref/fusions.csv, rien à fusionner.")
        return df

    inconnus = set(decisions["id_retenu"]) - set(df["idBeneficiaire_original"].astype(str))
    if inconnus:
        print(f"  Attention : id_retenu absents des données (faute de frappe ?), lignes ignorées : "
              f"{sorted(inconnus)}")
        decisions = decisions[~decisions["id_retenu"].isin(inconnus)]

    cle = pd.MultiIndex.from_frame(df[["nomBeneficiaire", "idBeneficiaire_original"]].astype(str))
    correspondance = decisions.set_index(["nomBeneficiaire", "idBeneficiaire"])["id_retenu"]
    nouvel_id = pd.Series(cle.map(correspondance), index=df.index)

    sans_correspondance = len(decisions) - correspondance.index.isin(cle).sum()
    if sans_correspondance:
        print(f"  Attention : {sans_correspondance} ligne(s) de fusions.csv ne correspondent à "
              "aucun couple (nom, identifiant) des données.")

    fusionnees = nouvel_id.notna() & (nouvel_id != df["idBeneficiaire_original"].astype(str))
    df.loc[fusionnees, "idBeneficiaire"] = nouvel_id[fusionnees]
    print(f"Fusions : {fusionnees.sum()} lignes fusionnées "
          f"({df.loc[fusionnees, 'idBeneficiaire_original'].nunique()} identifiants remplacés, "
          f"{len(decisions)} décisions lues)")
    return df


if __name__ == "__main__":
    preparer_fusions()
