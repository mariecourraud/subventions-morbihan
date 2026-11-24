# Morbihan Department grants: monitoring pipeline

## Purpose

A dashboard to monitor the grants awarded by the Département du Morbihan (France), built as a
semi-automated pipeline: scripts do the repetitive cleaning, and the judgement calls are recorded
in plain CSV files that a person fills in and that the scripts then apply.

## Data

- **Source:** data.gouv.fr, *Subventions aux personnes morales*, published by the Département du
  Morbihan: <https://www.data.gouv.fr/datasets/subventions-aux-personnes-morales/>
  (downloaded on 23 November 2026)
- **Licence:** Licence Ouverte (Etalab open licence)
- **Coverage:** 2020–2023, 12,514 grants to 1,900 beneficiaries, €417.0 M in total
- **Format:** SCDL (the French national schema for grant data), `;`-separated, Windows-1252

| Year | Grants | Total amount |
|---|--:|--:|
| 2020 | 2,543 | €82.0 M |
| 2021 | 3,292 | €108.4 M |
| 2022 | 3,534 | €121.8 M |
| 2023 | 3,145 | €104.8 M |

## Pipeline

| Step | File | Status |
|---|---|---|
| 1. Cleaning | `clean.py` → `data/subventions_clean.csv`, `data/a_verifier.csv` | done |
| 2. Beneficiary merges | `fusions.py` + `ref/fusions.csv` (decisions) | done |
| 3. Categorisation | `categorize.py` + `ref/objets_politiques.csv` → `data/subventions_final.csv` | done |
| 4. Dashboard | `build_dashboard.py` → `dashboard.html` | done |

`categorize.py` applies the merges, gives each beneficiary ID a single display name
(`nom_affichage`), maps each of the 131 grant objects to the Department's official strategic
segmentation as of 1 January 2025 (7 public policies, 26 sector policies, see below), infers
a beneficiary type from the name (municipality, inter-municipal body, school, social landlord,
association, public body, other) with ordered keyword rules, and flags €0 grants so that they are
left out of totals.

`build_dashboard.py` writes `dashboard.html`, a single self-contained page (plotly embedded, works
offline) in French: key figures, amounts by year and public policy, one small chart per policy,
breakdown by beneficiary type, top 15 beneficiaries, and a data quality and limitations box. Each
chart has a data table underneath.

Requires Python 3, pandas and plotly. To rebuild everything from the raw file:

```
python clean.py
python categorize.py
python build_dashboard.py
```

`python fusions.py` only regenerates the blank decision file `ref/fusions.csv`, and refuses to
overwrite an existing one, so recorded decisions cannot be lost by accident.

**Policy grid.** The 2025 segmentation is applied retroactively to 2020–2023 on two levels
(`politique_publique` / `politique_sectorielle`). Each grant is classed by its *object*, never by
who receives it. Objects too generic to be classed with certainty are marked *Non ventilé*
(unallocated) rather than guessed.

| Public policy | 2020 | 2021 | 2022 | 2023 | Total (€M) | Share |
|---|--:|--:|--:|--:|--:|--:|
| Solidarités humaines | 14.9 | 11.6 | 10.8 | 14.6 | 51.9 | 12.5% |
| Solidarité des territoires | 26.2 | 42.1 | 55.0 | 36.6 | 159.9 | 38.4% |
| Infrastructures et mobilité | 3.6 | 6.2 | 6.6 | 8.0 | 24.3 | 5.8% |
| Environnement | 4.6 | 5.6 | 6.2 | 7.0 | 23.5 | 5.6% |
| Éducation | 20.3 | 22.5 | 21.5 | 21.9 | 86.2 | 20.7% |
| Attractivité et animation territoriales | 10.3 | 11.1 | 15.4 | 11.2 | 48.0 | 11.5% |
| Ressources | 0.3 | 0.3 | 0.4 | 0.1 | 1.1 | 0.3% |
| *Non ventilé* | 1.8 | 9.0 | 5.9 | 5.3 | 22.0 | 5.3% |
| **Total** | **82.0** | **108.4** | **121.8** | **104.8** | **417.0** | **100%** |

## Data quality issues found

- **Encoding:** the source file is Windows-1252, not UTF-8; the outputs are written in UTF-8.
- **SIRET damaged by Excel:** the grantor's SIRET number (`idAttribuant`) appears as `2,26E+13`
  (2,543 rows) or `2,256E+13` (9,971 rows). Excel turned it into scientific notation and the digits
  are lost, so the column was dropped. 8 other columns were empty or constant and were dropped too
  (15 → 8 columns).
- **Inconsistent names:** 62 beneficiary IDs carry more than one name (e.g. `CAMOEL` / `CAMOËL`).
  46 IDs were harmonised to their most frequent name (109 rows); the original is kept in
  `nomBeneficiaire_original`. The other 16 mix a real name with "Tiers anonymisé".
- **€0 amounts:** 120 grants of €0, 75 of them in 2021.
- **Same organisation, several IDs:** 14 names appear under several IDs (29 name–ID pairs).
  12 were confirmed as the same organisation: 7 changed ID in 2021, 3 in 2023, 1 between 2021 and
  2023, and 1 was a duplicate within the same year.

## Human decisions

- **Merges** are decided case by case in `ref/fusions.csv` (kept ID + reason). 12 names were
  merged (30 rows); *Club de l'amitié* and *Club du bel âge* were kept separate because these names
  belong to different clubs in different towns.
- **€0 amounts** are kept in the data and listed in `data/a_verifier.csv` for review, but they are
  excluded from totals (`inclus_totaux = False`) so they do not distort counts or averages.
- **Anonymised beneficiaries** ("Tiers anonymisé", 61 rows) are never renamed, even when their ID
  also appears with a real name, so the publisher's anonymisation is respected.
- **Policy grid:** I chose to use the Department's official 2025 strategic segmentation rather than
  an ad hoc grid, to classify by grant object only, and to leave generic objects unallocated
  instead of guessing.
- **Categories:** each of the 131 grant objects has a public policy, a sector policy, a
  justification and a confidence level in `ref/objets_politiques.csv` (89 high, 26 medium,
  9 manual, 7 low = the 7 objects still unallocated). I reviewed and validated the 17 medium-
  and low-confidence objects above €500k (€73.4 M).
- **Manual reclassification:** I reclassified by hand 9 objects that had been left *Non ventilé*,
  based on my knowledge of the Department's reports (marked `manuel` in the confidence column).
  They cover 664 grants and €17.6 M. The unallocated share falls from 9.5% (€39.6 M) to 5.3%
  (€22.0 M).

## Use of AI

### What Claude Code did

### What I checked

### What I chose not to do

## Limitations and next steps

- The open dataset stops at 2023.
- The grid is the one in force on 1 January 2025, applied retroactively to grants voted in
  2020–2023.
- Categories are assigned per grant object, not per grant: 7 generic objects (231 grants,
  €22.0 M, 5.3% of the total) stay *Non ventilé*, led by "Rapports spéciaux" (€18.7 M).
  Splitting them would need a grant-by-grant review.
- The 9 manual reclassifications rest on my reading of the Department's reports, not on the
  grant object alone.
- The 20 medium- and low-confidence objects below €500k (€2.3 M) were not reviewed individually.
- Five sector policies have no grant in the data (Aménagement numérique, Expertises et analyses
  en environnement, Moyens des services, Gestion et fonctionnement de l'assemblée, Ressources
  financières).
- The beneficiary type comes from the name only: 1,870 rows (€59.2 M) stay *Other*, mostly
  associations whose name gives no clue.
- Next step: extract 2024–2026 grants from the PDF reports of the Commission permanente.
