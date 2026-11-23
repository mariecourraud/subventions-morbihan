"""Étape 3 : catégorisation des subventions.

Entrée  : data/subventions_clean.csv (produit par clean.py)
Référentiels (décisions humaines) :
          ref/fusions.csv            fusions d'identifiants (appliquées via fusions.py)
          ref/objets_politiques.csv  objet -> politique publique / sectorielle
                                     (segmentation stratégique du Département au 01/01/2025)
Sortie  : data/subventions_final.csv (UTF-8)

Ajoute les colonnes : nom_affichage, idBeneficiaire_original, politique_publique,
politique_sectorielle, type_beneficiaire, inclus_totaux.
Les montants à 0 € restent dans le fichier mais sont exclus des totaux (inclus_totaux = False).
"""
from pathlib import Path
import re

import pandas as pd

from clean import cle_nom
from fusions import appliquer_fusions, lire_csv

RACINE = Path(__file__).parent
SOURCE = RACINE / "data" / "subventions_clean.csv"
OBJETS = RACINE / "ref" / "objets_politiques.csv"
SORTIE = RACINE / "data" / "subventions_final.csv"

# --------------------------------------------------------------- Type de bénéficiaire
# Règles appliquées dans l'ordre, sur le nom normalisé (majuscules, sans accents ni
# ponctuation, cf. clean.cle_nom). La première règle qui correspond l'emporte.
# Les noms sans indice suffisant tombent dans « Autre ».
REGLES_TYPE = [
    ("Autre",                 r"^TIERS ANONYMISE$"),                       # anonymisé : type inconnu
    ("Collège",               r"\bCOLLEGE\b|\bOGEC\b"),
    ("Bailleur social",       r"^(?!.*HUMANISME)(?!.*ASSOCIATION).*(\bHABITAT\b|\bHABITATIONS\b|\bHLM\b)"
                              r"|^AIGUILLON CONSTRUCTION$|^LE LOGIS BRETON$|^LE FOYER D ARMOR$|^NEOTOA$"),
    ("Commune",               r"\bCOMMUNE( NOUVELLE)?$"),                  # « XXX (COMMUNE) »
    ("Association",           r"\bUNIVERSITE (DU TEMPS LIBRE|TOUS AGES)\b"),  # avant « Communauté »
    ("Intercommunalité",      r"\bC COM\b|\bCOMMUNAUTE DE COMMUNES\b|^(?!CIAS).*\bCOMMUNAUTE$"
                              r"|\bLOUDEAC COMMUNAUTE\b|\bAGGLOMERATION\b|^CAP ATLANTIQUE$"
                              r"|\bSYNDICAT MIXTE\b|\bSYND INT\b|\bSYNDICAT INTERCOMMUNAL\b"
                              r"|\bSYND ASSAIN\b|^SYNDICAT DE L EAU DU MORBIHAN$|\bSIAEP\b|\bSIVU\b|\bSIVOM\b"),
    ("Établissement public",  r"\bCCAS\b|\bCIAS\b|\bCENTRE HOSPITALIER\b|\bHOPITAL\b|\bEHPAD\b|\bEPMS\b"
                              r"|^CONSEIL (DEPARTEMENTAL|REGIONAL)\b(?!.*ACCES AU DROIT)"
                              r"|^UNIVERSITE (DE|EVRY)\b|\bCROUS\b|\bCHAMBRE D AGRICULTURE\b"
                              r"|\bSERVICE DEPARTEMENTAL D INCENDIE\b|\bEPCC\b|\bEPTB\b|\bMINISTERE\b"
                              r"|\bCONSERVATOIRE DE L ESPACE LITTORAL\b"),
    ("Autre",                 r"\b(SASP|SAS|SARL|SA|EARL|GAEC|SCEA|SCI|EURL|SEM|SPL|SCOP|SCIC)\b"),  # sociétés
    ("Association",           r"\bASS(OC|OCIATION|O)?\b|\bCLUB\b|\bCOMITE\b|\bFEDERATION\b|\bAMICALE\b"
                              r"|\bUNION SPORTIVE\b|\bMISSION LOCALE\b|\bSECOURS POPULAIRE\b|\bCROIX ROUGE\b"
                              r"|\bRESTAURANTS DU COEUR\b|\bBAGAD\b|\bCERCLE\b|\bFESTIVAL\b|\bGEM\b"
                              r"|\bFOOTBALL\b|\bHANDBALL\b|\bBASKET\b|\bRUGBY\b|\bTENNIS\b|\bJUDO\b|\bATHLETI"
                              r"|\bCYCLISTE\b|\bNAUTIQUE\b|\bVOILE\b|\bYACHT\b|\bSPORTS?\b|\bSPORTIVES?\b|\bOLYMPI"
                              r"|\bAVIRON\b|\bNATATION\b|\bESCRIME\b|\bGYM|\bKAYAK\b|\bCANOE\b|\bHANDISPORT\b"
                              r"|\bPATRONAGE\b|\bFOYER LAIQUE\b|\bCPIE\b|\bCENTRE SOCIO CULTUREL\b|\bCENTRE SOCIAL\b"
                              r"|\bGROUPEMENT CULTUREL\b|\bCONFEDERATION\b|\bUDAF\b|\bAMIS\b|\bCOMPAGNIE$"
                              r"|\bSOCIETE DES REGATES\b|\bSOCIETE NATIONALE DE SAUVETAGE\b|\bSAINT VINCENT DE PAUL\b"),
]
_REGLES = [(t, re.compile(m)) for t, m in REGLES_TYPE]


def type_beneficiaire(nom: str) -> str:
    cle = cle_nom(nom)
    for type_, motif in _REGLES:
        if motif.search(cle):
            return type_
    return "Autre"


# --------------------------------------------------------------- Nom d'affichage
ANONYME = "Tiers anonymisé"


def ajouter_nom_affichage(df: pd.DataFrame) -> pd.DataFrame:
    """Un seul nom par idBeneficiaire (après fusion) : le plus fréquent, puis le plus récent.
    nomBeneficiaire n'est pas modifié. Les lignes « Tiers anonymisé » gardent ce nom
    (ne pas lever l'anonymisation) et ne comptent pas dans le choix du nom."""
    nommes = df[df["nomBeneficiaire"] != ANONYME]
    stats = (
        nommes.groupby(["idBeneficiaire", "nomBeneficiaire"])
        .agg(n=("id", "size"), derniere=("dateConvention", "max"))
        .reset_index()
        .sort_values(["idBeneficiaire", "n", "derniere"], ascending=[True, False, False])
    )
    choix = stats.drop_duplicates("idBeneficiaire").set_index("idBeneficiaire")["nomBeneficiaire"]

    affichage = df["idBeneficiaire"].map(choix).where(df["nomBeneficiaire"] != ANONYME, ANONYME)
    df.insert(df.columns.get_loc("nomBeneficiaire") + 1, "nom_affichage", affichage)

    diff = df["nom_affichage"] != df["nomBeneficiaire"]
    print(f"Noms d'affichage : {diff.sum()} lignes affichées sous un autre nom "
          f"({df.loc[diff, 'idBeneficiaire'].nunique()} identifiants)")
    return df


# --------------------------------------------------------------- Politiques
# Segmentation stratégique officielle du Département au 01/01/2025 (deux niveaux),
# appliquée rétroactivement aux données 2020-2023.
GRILLE = {
    "SOLIDARITÉS HUMAINES": [
        "Enfance et famille",
        "Insertion et développement social",
        "Personnes handicapées",
        "Personnes âgées",
    ],
    "SOLIDARITÉ DES TERRITOIRES": [
        "Accompagnement des territoires (dont aides aux territoires, animation locale)",
        "Aménagement numérique",
        "Prévention des risques et sécurité civile (dont SDIS)",
        "Habitat",
        "Aménagement foncier rural",
    ],
    "INFRASTRUCTURES ET MOBILITÉ": [
        "Routes départementales et ouvrages d'art",
        "Aménagements cyclables",
        "Développement portuaire (dont Compagnie des ports)",
        "Développement ferroviaire",
    ],
    "ENVIRONNEMENT": [
        "Espaces naturels et activités de nature (dont ENS, randonnées, bocage et forêts)",
        "Eau",
        "Soutien au monde agricole",
        "Expertises et analyses en environnement",
    ],
    "ÉDUCATION": [
        "Collèges",
        "Jeunesse et partenariats éducatifs (dont plan jeunesse, enseignement supérieur, "
        "université tous les âges)",
    ],
    "ATTRACTIVITÉ ET ANIMATION TERRITORIALES": ["Culture", "Sports", "Tourisme"],
    "RESSOURCES": [
        "Ressources humaines (dont action sociale du personnel)",
        "Moyens des services",
        "Gestion et fonctionnement de l'assemblée",
        "Ressources financières",
    ],
}
# Objet trop générique pour être classé avec certitude (dans les deux colonnes)
NON_VENTILE = "Non ventilé"


def ajouter_politique(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute politique_publique et politique_sectorielle d'après l'objet de la subvention."""
    ref = lire_csv(OBJETS)[["objet", "politique_publique", "politique_sectorielle"]]
    manquants = set(df["objet"]) - set(ref["objet"])
    if manquants:
        raise ValueError(f"Objets absents de {OBJETS.name} (à classer d'abord) : {sorted(manquants)}")
    if ref["objet"].duplicated().any():
        raise ValueError(f"Objets en double dans {OBJETS.name}")

    couples_valides = {(pp, ps) for pp, liste in GRILLE.items() for ps in liste}
    couples_valides.add((NON_VENTILE, NON_VENTILE))
    invalides = ref[[c not in couples_valides
                     for c in zip(ref["politique_publique"], ref["politique_sectorielle"])]]
    if not invalides.empty:
        raise ValueError(f"Intitulés hors grille dans {OBJETS.name} :\n{invalides.to_string()}")

    ref = ref.set_index("objet")
    pos = df.columns.get_loc("objet") + 1
    df.insert(pos, "politique_publique", df["objet"].map(ref["politique_publique"]))
    df.insert(pos + 1, "politique_sectorielle", df["objet"].map(ref["politique_sectorielle"]))
    return df


# --------------------------------------------------------------- Programme principal
def main() -> pd.DataFrame:
    df = pd.read_csv(SOURCE, sep=";", encoding="utf-8-sig",
                     dtype={"idBeneficiaire": str, "id": str})
    print(f"{len(df)} lignes lues depuis {SOURCE.relative_to(RACINE)}")

    df = appliquer_fusions(df)
    df = ajouter_nom_affichage(df)
    df = ajouter_politique(df)
    # Type déduit du nom d'affichage : un seul type par identifiant
    df.insert(df.columns.get_loc("idBeneficiaire_original") + 1, "type_beneficiaire",
              df["nom_affichage"].map(type_beneficiaire))
    df["inclus_totaux"] = df["montant"] > 0

    df.to_csv(SORTIE, sep=";", index=False, encoding="utf-8-sig")
    print(f"-> {SORTIE.relative_to(RACINE)} ({len(df)} lignes, {df.shape[1]} colonnes)")

    exclus = ~df["inclus_totaux"]
    print(f"Montants à 0 € exclus des totaux : {exclus.sum()} lignes")

    print("\nType de bénéficiaire (lignes)")
    print(df["type_beneficiaire"].value_counts().to_string())

    print("\nMontants par politique publique et par année (M€, hors montants à 0 €)")
    print(tableau_politiques(df).to_string())
    return df


def tableau_politiques(df: pd.DataFrame) -> pd.DataFrame:
    """Montants (M€, 1 décimale) par politique publique et par année, avec la part du total.
    Ordre de la grille officielle, « Non ventilé » en dernier."""
    totaux = df[df["inclus_totaux"]]
    t = totaux.pivot_table(index="politique_publique", columns="annee", values="montant",
                           aggfunc="sum", fill_value=0)
    ordre = [p for p in [*GRILLE, NON_VENTILE] if p in t.index]
    t = t.loc[ordre]
    t["Total"] = t.sum(axis=1)
    t.loc["Total"] = t.sum()
    part = (t["Total"] / t.loc["Total", "Total"] * 100).round(1)
    t = (t / 1e6).round(1)
    t.columns = [str(c) for c in t.columns]
    t["Part (%)"] = part
    return t


if __name__ == "__main__":
    main()
