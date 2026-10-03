# LAPD NIBRS Data Cleaning

## Project

This project cleans the LAPD NIBRS Offenses Dataset to support prioritization of geographic areas for on-site street-lighting assessments. The analysis does not claim that lighting conditions caused reported offenses.

## Data source

- **Dataset:** LAPD NIBRS Offenses Dataset.
- **Official source:** https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep
- **Raw filename:** `lapd_nibrs_offenses_raw.csv`.
- **Download date:** October 3, 2026 (confirmed by Olga).
- **Version (SHA-256):** `8003ffd45a3e17938913b5794a5bad0a8078bfafec736591123005212614d1cf`.
- **Coverage:** Supplied export, not the earlier 2,500-row sample; completeness against the live dataset is unverified.

The original raw file is not modified and is excluded from Git.

## Files

- Cleaning notebook: `notebooks/data_cleaning.ipynb`.
- Raw data: `data/raw/lapd_nibrs_offenses_raw.csv`.
- Cleaned sample: `data/cleaned/lapd_nibrs_cleaned_sample.csv`.
- Decision log: `data/cleaned/cleaning_decision_log.csv`.
- Record verification: `data/cleaned/five_record_checks.csv`.
- Dependencies: `requirements.txt`.

## How to run

1. From the repository root, install dependencies with `pip install -r requirements.txt`.
2. Place the original LAPD CSV at `data/raw/lapd_nibrs_offenses_raw.csv`.
3. Open `notebooks/data_cleaning.ipynb` and select the Python environment with the installed dependencies.
4. Run all cells from top to bottom.
5. Find the three generated outputs in `data/cleaned/`.

## Expected outputs

- `lapd_nibrs_cleaned_sample.csv`: Up to 50 cleaned records with selection reasons.
- `cleaning_decision_log.csv`: Cleaning rules, reasons, affected counts, and limitations.
- `five_record_checks.csv`: Expected and actual results for five individual record checks.

Audits, reconciliation, metrics, and compact district/month previews are displayed in the notebook. Complete result tables remain in memory; their shapes appear in section 11. The full cleaned master remains in memory as `df`. No builder script is needed.

## Submission information

- **Branch:** `Olga`.
- **Branch URL:** https://github.com/zayra-rwx/community-safety-resource-planner/tree/Olga.
- Verified analysis commit: 30c9809
