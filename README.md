# Morbihan Department grants: monitoring pipeline

## Purpose

A dashboard to monitor the grants awarded by the Département du Morbihan (France), built as a
semi-automated pipeline: scripts do the repetitive cleaning, and the judgement calls are recorded
in plain CSV files that a person fills in and that the scripts then apply.

## Data

- **Source:** data.gouv.fr, *Subventions aux personnes morales*, published by the Département du
  Morbihan: <!-- TODO: add dataset URL -->
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
| 3. Categorisation | `categorize.py` (will apply the merges via `appliquer_fusions()`) | to do |
| 4. Dashboard | — | to do |

Requires Python 3 and pandas. To rebuild the cleaned data from the raw file:

```
python clean.py
```

`python fusions.py` only regenerates the blank decision file `ref/fusions.csv`, and refuses to
overwrite an existing one, so recorded decisions cannot be lost by accident.

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
- **€0 amounts** are kept in the data and listed in `data/a_verifier.csv` for review.
- **Anonymised beneficiaries** ("Tiers anonymisé", 61 rows) are never renamed, even when their ID
  also appears with a real name, so the publisher's anonymisation is respected.
- **Categories** will be validated by hand before they are used in the dashboard.

## Use of AI

### What Claude Code did

### What I checked

### What I chose not to do

## Limitations and next steps

- The open dataset stops at 2023.
- Next step: extract 2024–2026 grants from the PDF reports of the Commission permanente.
