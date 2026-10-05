# LAPD NIBRS Data Cleaning – Caroline Romero

DSO 576, Module 6: Project Data Cleaning (individual assignment)
Team project: Community Safety Resource Planner, Vision B (street-lighting assessment prioritization)

- **Branch:** carolineromero19
- **Branch URL:** https://github.com/zayra-rwx/community-safety-resource-planner/tree/carolineromero19
- **Commit ID:** 9e887e8 (cleaning script, sample, and requirements)

## Data source
- LAPD NIBRS Offenses dataset (City of Los Angeles open data)
- File: `LAPD_NIBRS_Offenses_Dataset_20261004.csv` (team's official copy), downloaded October 4, 2026
- 489,955 rows, 31 columns
- The raw data is **not** included in this repository (`data/` is listed in `.gitignore`). To run the code, place the file at `data/LAPD_NIBRS_Offenses_Dataset_20261004.csv`. The original file is never modified.

## How to run
Requires Python 3.14 and pandas 3.0.6. From the repository's main folder:

    python3 -m pip install -r requirements.txt
    python3 scripts/clean_lapd.py

The script prints labeled checks for each section (Sections 0–14), matching the checklist items in the submitted PDF.

## Expected output files
- `data/clean/lapd_nibrs_clean.csv`: full cleaned dataset, 489,955 rows × 40 columns (not pushed to GitHub because of size and the data folder rule)
- `sample/lapd_nibrs_clean_sample.csv`: 50 cleaned rows (included in this repository)

## Columns added by cleaning
| Column | Meaning |
|---|---|
| date_occ | Date OCC converted to a date |
| hour_occ | Hour of day (0–23) from Time OCC |
| lat, lon | Numeric coordinates; 0,0 and out-of-area values set to missing |
| time_possible_placeholder | True if Time OCC is 0000 or 1200 |
| is_night | True if hour is 18–23 or 0–5 (definition pending team confirmation) |
| has_valid_coords | True if lat and lon are present and inside Los Angeles |
| date_invalid | True if Date OCC is before 2000 |
| in_analysis_window | True if Date OCC is 2025-01-01 through 2026-08-31 |

## How the sample was chosen
The 50 rows were selected on purpose to include difficult cases: 5 midnight placeholder times, 3 noon placeholder times, 5 rows with 0,0 coordinates, 5 rows with coordinates outside Los Angeles, 3 rows with originally blank coordinates, 5 rows dated before 2000, both offenses from case 25088246 (one case with multiple offenses), 4 rows outside the analysis window, and 18 ordinary in-window rows. Random picks use `random_state=576`, so the same rows are selected every run.