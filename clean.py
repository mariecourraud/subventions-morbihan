"""Nettoyage des subventions du Département du Morbihan (SCDL, 2020-2023).

Entrée  : data/cd56-subventions.csv (séparateur ';', encodage Windows-1252)
Sorties : data/subventions_clean.csv  (UTF-8)
          data/a_verifier.csv         (lignes à contrôler, colonne 'motif')
"""
from pathlib import Path
import re
import unicodedata

import pandas as pd

DATA = Path(__file__).parent / "data"
SOURCE = DATA / "cd56-subventions.csv"
SORTIE = DATA / "subventions_clean.csv"
A_VERIFIER = DATA / "a_verifier.csv"

ANONYME = "Tiers anonymisé"
# Colonnes inexploitables même si elles ne sont ni vides ni constantes.
COLONNES_CORROMPUES = {
    "idAttribuant": "SIRET converti en notation scientifique par Excel (ex. 2,26E+13), illisible",
}


# ---------------------------------------------------------------- 1. Lecture
def lire(chemin: Path) -> pd.DataFrame:
    """Lit le CSV en Windows-1252, tout en texte pour ne rien interpréter à tort."""
    df = pd.read_csv(chemin, sep=";", encoding="cp1252", dtype=str, keep_default_na=False)
    # Chaînes vides / blancs -> valeurs manquantes
    return df.apply(lambda s: s.str.strip()).replace("", pd.NA)


def vers_nombre(s: pd.Series) -> pd.Series:
    """Convertit '1 234,50 €', '1234.5', '1 234' ... en float."""
    propre = (
        s.astype("string")
        .str.replace(r"[\s  €]", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(propre, errors="coerce")


# ------------------------------------------------------- 2. Colonnes / année
def nettoyer_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    vides = [c for c in df.columns if df[c].isna().all()]
    constantes = [c for c in df.columns if c not in vides and df[c].nunique(dropna=False) == 1]
    corrompues = [c for c in COLONNES_CORROMPUES if c in df.columns]

    print(f"  Colonnes vides supprimées      : {vides}")
    print(f"  Colonnes constantes supprimées : "
          + ", ".join(f"{c} (= {df[c].iloc[0]!r})" for c in constantes))
    for c in corrompues:
        print(f"  Colonne corrompue supprimée    : {c} - {COLONNES_CORROMPUES[c]}")

    df = df.drop(columns=vides + constantes + corrompues)
    df["dateConvention"] = pd.to_datetime(df["dateConvention"], format="%Y%m%d", errors="coerce")
    df.insert(df.columns.get_loc("dateConvention") + 1, "annee",
              df["dateConvention"].dt.year.astype("Int64"))
    return df


# ------------------------------------------------------- 3. Harmonisation
def harmoniser_noms(df: pd.DataFrame) -> pd.DataFrame:
    """Un seul nom par idBeneficiaire : le plus fréquent, puis le plus récent.
    Les lignes 'Tiers anonymisé' ne sont jamais renommées (anonymisation volontaire)."""
    df["nomBeneficiaire_original"] = df["nomBeneficiaire"]
    nommes = df[df["nomBeneficiaire"] != ANONYME]

    stats = (
        nommes.groupby(["idBeneficiaire", "nomBeneficiaire"])
        .agg(n=("id", "size"), derniere=("dateConvention", "max"))
        .reset_index()
        .sort_values(["idBeneficiaire", "n", "derniere"], ascending=[True, False, False])
    )
    canonique = stats.drop_duplicates("idBeneficiaire").set_index("idBeneficiaire")["nomBeneficiaire"]

    a_renommer = (df["nomBeneficiaire"] != ANONYME) & df["idBeneficiaire"].isin(canonique.index)
    df.loc[a_renommer, "nomBeneficiaire"] = df.loc[a_renommer, "idBeneficiaire"].map(canonique)

    modifies = df["nomBeneficiaire"] != df["nomBeneficiaire_original"]
    print(f"  {df.loc[modifies, 'idBeneficiaire'].nunique()} identifiants harmonisés, "
          f"{modifies.sum()} lignes renommées")
    print(f"  {(df['nomBeneficiaire'] == ANONYME).sum()} lignes '{ANONYME}' laissées telles quelles")
    return df


# ------------------------------------------------------- 4. À vérifier
def cle_nom(nom: str) -> str:
    """Clé de comparaison : majuscules, sans accents ni ponctuation superflue."""
    nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    nom = re.sub(r"[^A-Z0-9]+", " ", nom.upper())
    return nom.strip()


def lignes_a_verifier(df: pd.DataFrame) -> pd.DataFrame:
    motifs = pd.Series("", index=df.index, dtype="string")

    def ajouter(masque, texte):
        motifs[masque] = motifs[masque].where(motifs[masque] == "", motifs[masque] + " | ") + texte

    ajouter(df["montant"].isna(), "montant non convertible")
    ajouter(df["montant"] == 0, "montant à 0 €")

    nommes = df["nomBeneficiaire"] != ANONYME
    cles = df["nomBeneficiaire"].map(cle_nom)
    nb_ids = df[nommes].groupby(cles[nommes])["idBeneficiaire"].transform("nunique")
    multi = pd.Series(False, index=df.index)
    multi[nb_ids.index] = nb_ids > 1
    ajouter(multi, "nom présent sous plusieurs idBeneficiaire")

    print(f"  Montants à 0 €               : {(df['montant'] == 0).sum()} lignes")
    print(f"  Montants non convertibles    : {df['montant'].isna().sum()} lignes")
    print(f"  Noms à plusieurs identifiants: {cles[multi].nunique()} noms, {multi.sum()} lignes")

    out = df[motifs != ""].copy()
    out.insert(0, "motif", motifs[motifs != ""])
    return out.sort_values(["motif", "nomBeneficiaire", "idBeneficiaire", "dateConvention"])


# ------------------------------------------------------- Programme principal
def main() -> pd.DataFrame:
    print("1. Lecture (Windows-1252) et conversion des montants")
    df = lire(SOURCE)
    print(f"  {len(df)} lignes, {df.shape[1]} colonnes")
    df["montant"] = vers_nombre(df["montant"])

    print("2. Colonnes vides/constantes et colonne année")
    df = nettoyer_colonnes(df)

    print("3. Harmonisation des noms par idBeneficiaire")
    df = harmoniser_noms(df)

    print("4. Lignes à vérifier")
    verif = lignes_a_verifier(df)
    verif.to_csv(A_VERIFIER, sep=";", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    print(f"  -> {A_VERIFIER.relative_to(DATA.parent)} ({len(verif)} lignes)")

    print("5. Enregistrement UTF-8")
    df.to_csv(SORTIE, sep=";", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    print(f"  -> {SORTIE.relative_to(DATA.parent)} ({len(df)} lignes, {df.shape[1]} colonnes)")

    print("\nRésumé par année")
    resume = df.groupby("annee").agg(
        subventions=("id", "size"),
        beneficiaires=("idBeneficiaire", "nunique"),
        montant_total=("montant", "sum"),
        montant_median=("montant", "median"),
        montants_a_zero=("montant", lambda m: int((m == 0).sum())),
    )
    resume.loc["Total"] = [
        len(df), df["idBeneficiaire"].nunique(), df["montant"].sum(),
        df["montant"].median(), int((df["montant"] == 0).sum()),
    ]
    fmt = lambda x: f"{x:,.0f}".replace(",", " ")
    print(resume.to_string(formatters={
        "subventions": fmt, "beneficiaires": fmt,
        "montant_total": lambda x: fmt(x) + " €", "montant_median": lambda x: fmt(x) + " €",
        "montants_a_zero": fmt,
    }))
    return df


if __name__ == "__main__":
    main()
