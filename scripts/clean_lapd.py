# clean_lapd.py
# DSO 576 Module 6 - Project Data Cleaning
# Caroline Romero - Community Safety Resource Planner (Vision B)
# Sections are numbered to match the 14 checklist items in the submitted PDF.

import os
import sys
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

# ===== Section 0: Load the original data =====
RAW_FILE = "data/LAPD_NIBRS_Offenses_Dataset_20261004.csv"
df = pd.read_csv(RAW_FILE, dtype=str)   # Rule 1: read every column as text to keep leading zeros
print("--- Section 0: Load the original data ---")
print("Loaded rows and columns:", df.shape)

# ===== Section 1: Project vision and question =====
# Vision B: help the City of Los Angeles prioritize locations for street-lighting assessment.
# Question: Which LA locations have recurring nighttime reported offenses, and is the pattern persistent?
# Main metric: nighttime offenses per area per month, within the analysis window (Jan 2025 - Aug 2026).
print("\n--- Section 1: Project vision ---")
print("Vision B: street-lighting assessment prioritization")
print("Metric: nighttime offenses per area per month (Jan 2025 - Aug 2026)")

# ===== Section 2: Define one row =====
print("\n--- Section 2: Define one row ---")
print("Rows:", len(df))
print("Unique UniqueNIBRNo:", df["UniqueNIBRNo"].nunique())
print("Unique CaseNo:", df["CaseNo"].nunique())

# ===== Section 3: Preserve the source =====
print("\n--- Section 3: Preserve the source ---")
print("Original file (never modified):", RAW_FILE)
clean = df.copy()
print("All cleaning is applied to a working copy; original columns are kept unchanged.")

# ===== Section 4: Convert types (Rules 3, 4, 7) =====
print("\n--- Section 4: Convert types ---")

# Rule 3: Date OCC text -> real date
clean["date_occ"] = pd.to_datetime(clean["Date OCC"].str.strip(), format="%Y %b %d %I:%M:%S %p", errors="coerce")
print("Date OCC failed conversions:", clean["date_occ"].isna().sum())

# Rule 4: Time OCC "1421" -> hour of day (14)
time_num = pd.to_numeric(clean["Time OCC"].str.strip(), errors="coerce")
print("Time OCC failed conversions:", time_num.isna().sum())
clean["hour_occ"] = time_num // 100
bad_time = (time_num % 100 > 59) | (clean["hour_occ"] > 23)
print("Time OCC impossible values:", bad_time.sum())

# Rule 7 (part 1): LAT/LON text -> numbers
clean["lat"] = pd.to_numeric(clean["LAT"].str.strip(), errors="coerce")
clean["lon"] = pd.to_numeric(clean["LON"].str.strip(), errors="coerce")
print("LAT failed conversions (beyond the 131 blanks):", clean["lat"].isna().sum() - df["LAT"].isna().sum())
print("LON failed conversions (beyond the 131 blanks):", clean["lon"].isna().sum() - df["LON"].isna().sum())

# ===== Section 5: Standardize text (Rule 2) =====
print("\n--- Section 5: Standardize text ---")
text_cols = list(df.columns)
for col in text_cols:
    clean[col] = clean[col].str.strip()
clean[text_cols] = clean[text_cols].replace("", pd.NA)

print("AREA NAME before:", repr(df.loc[0, "AREA NAME"]))
print("AREA NAME after: ", repr(clean.loc[0, "AREA NAME"]))
print("AREA code after (leading zero kept):", repr(clean.loc[0, "AREA"]))
print("Distinct AREA NAME before:", df["AREA NAME"].nunique())
print("Distinct AREA NAME after: ", clean["AREA NAME"].nunique())

changed = (df.fillna("") != clean[text_cols].fillna("")).sum()
print("Cells changed per column:")
print(changed[changed > 0])

# ===== Section 6: Duplicates =====
print("\n--- Section 6: Duplicates ---")
print("Exact duplicate rows:", df.duplicated().sum())
print("Rows sharing a CaseNo with another row:", len(df) - df["CaseNo"].nunique())

# ===== Section 7: Missing values before and after cleaning =====
print("\n--- Section 7: Missing values before and after cleaning ---")
missing_before = df.isna().sum()
missing_after = clean[text_cols].isna().sum()
compare = pd.DataFrame({"before": missing_before, "after": missing_after})
print(compare[(compare["before"] > 0) | (compare["after"] > 0)])
print("(Cleaned lat/lon missing values are reported in Section 8.)")

# ===== Section 8: Flag suspicious values (Rules 5, 6, 7, 8, 9) =====
print("\n--- Section 8: Flag suspicious values ---")

# Rule 5: possible placeholder times
clean["time_possible_placeholder"] = clean["Time OCC"].isin(["0000", "1200"])
print("Possible placeholder times (0000 or 1200):", clean["time_possible_placeholder"].sum())

# Rule 6: nighttime flag (CONFIRM DEFINITION WITH TEAM)
NIGHT_START = 18   # 6:00 PM
NIGHT_END = 6      # 6:00 AM
clean["is_night"] = (clean["hour_occ"] >= NIGHT_START) | (clean["hour_occ"] < NIGHT_END)
print("Nighttime offenses:", clean["is_night"].sum())

# Rule 7 (part 2): fake or out-of-area coordinates -> missing
zero_coords = (clean["lat"] == 0) & (clean["lon"] == 0)
outside_la = ((clean["lat"] < 33.5) | (clean["lat"] > 34.5) | (clean["lon"] < -119) | (clean["lon"] > -118)) & ~zero_coords
print("Zero coordinates set to missing:", zero_coords.sum())
print("Out-of-area coordinates set to missing:", outside_la.sum())
clean.loc[zero_coords | outside_la, ["lat", "lon"]] = float("nan")
clean["has_valid_coords"] = clean["lat"].notna() & clean["lon"].notna()
print("Rows without valid coordinates:", (~clean["has_valid_coords"]).sum())
print("Cleaned lat/lon missing:", clean["lat"].isna().sum(), "/", clean["lon"].isna().sum())

# Rule 8: suspicious dates (before 2000; some may be genuine delayed reports)
clean["date_invalid"] = clean["date_occ"] < "2000-01-01"
print("Suspicious dates (before 2000):", clean["date_invalid"].sum())

# Rule 9: analysis window (2025-01-01 through 2026-08-31)
clean["in_analysis_window"] = (clean["date_occ"] >= "2025-01-01") & (clean["date_occ"] < "2026-09-01")
print("Rows in analysis window:", clean["in_analysis_window"].sum())

# ===== Section 9: Verify merges =====
print("\n--- Section 9: Verify merges ---")
print("Not applicable: no tables were merged (single source file).")

# ===== Section 10: Reconcile changes and save outputs =====
print("\n--- Section 10: Reconcile changes ---")
print("Starting rows:", len(df))
print("Final rows:   ", len(clean))
print("Rows removed: ", len(df) - len(clean))
print("Columns before:", df.shape[1], "| after:", clean.shape[1])

os.makedirs("data/clean", exist_ok=True)
clean.to_csv("data/clean/lapd_nibrs_clean.csv", index=False)
print("Saved: data/clean/lapd_nibrs_clean.csv")

# Sample: up to 50 cleaned rows, including difficult cases
os.makedirs("sample", exist_ok=True)
picks = pd.concat([
    clean[clean["Time OCC"] == "0000"].head(5),      # midnight placeholder time
    clean[clean["Time OCC"] == "1200"].head(3),      # noon placeholder time
    clean[zero_coords].head(5),                      # 0,0 coordinates
    clean[outside_la].head(5),                       # coordinates outside LA
    clean[df["LAT"].isna()].head(3),                 # originally blank coordinates
    clean[clean["date_invalid"]].head(5),            # dates before 2000
    clean[clean["CaseNo"] == "25088246"],            # one case, two offenses
    clean[~clean["in_analysis_window"] & ~clean["date_invalid"]].sample(4, random_state=576),  # outside analysis window
    clean[clean["in_analysis_window"]].sample(18, random_state=576),                         # ordinary rows
])
picks = picks.drop_duplicates(subset="UniqueNIBRNo").head(50)
picks.to_csv("sample/lapd_nibrs_clean_sample.csv", index=False)
print("Saved sample:", len(picks), "rows -> sample/lapd_nibrs_clean_sample.csv")

# ===== Section 11: Check calculations =====
print("\n--- Section 11: Check calculations ---")
window = clean[clean["in_analysis_window"]]
print("Rows in analysis window (denominator for trends):", len(window))
print("Missing AREA NAME in window:", window["AREA NAME"].isna().sum())
print("Nighttime offenses in window:", window["is_night"].sum())
print("Nighttime offenses in window, excluding placeholder times:",
      (window["is_night"] & ~window["time_possible_placeholder"]).sum())
print("Nighttime offenses in window with valid coordinates (map count):",
      (window["is_night"] & window["has_valid_coords"]).sum())
print("Share of window offenses at night: {:.1%}".format(window["is_night"].mean()))

# ===== Section 12: Verify individual records =====
check_ids = [
    "25088246_13A_0",                                                # ordinary daytime offense
    clean.loc[clean["Time OCC"] == "0000", "UniqueNIBRNo"].iloc[0],  # midnight placeholder
    clean.loc[zero_coords, "UniqueNIBRNo"].iloc[0],                  # 0,0 coordinates
    clean.loc[outside_la, "UniqueNIBRNo"].iloc[0],                   # coordinates outside LA
    clean.loc[clean["date_invalid"], "UniqueNIBRNo"].iloc[0],        # date before 2000
]
orig_cols = ["UniqueNIBRNo", "Date OCC", "Time OCC", "AREA NAME", "LAT", "LON"]
print("\n--- Section 12a: Original values for record checks ---")
print(df[df["UniqueNIBRNo"].isin(check_ids)][orig_cols])

clean_cols = ["UniqueNIBRNo", "AREA NAME", "date_occ", "hour_occ", "is_night",
              "time_possible_placeholder", "lat", "lon", "has_valid_coords",
              "date_invalid", "in_analysis_window"]
print("\n--- Section 12b: Cleaned values for record checks ---")
print(clean[clean["UniqueNIBRNo"].isin(check_ids)][clean_cols])

# ===== Section 13: Test reproducibility =====
print("\n--- Section 13: Reproducibility ---")
print("Python version:", sys.version.split()[0])
print("pandas version:", pd.__version__)
print("Outputs recreated from the original file on every run:")
print("  data/clean/lapd_nibrs_clean.csv")
print("  sample/lapd_nibrs_clean_sample.csv (random_state=576)")

# ===== Section 14: Remaining limitations =====
# See PDF item 14 for the full discussion. Key counts:
print("\n--- Section 14: Remaining limitations (key counts) ---")
print("Nighttime offenses in window with possible placeholder times:",
      (window["is_night"] & window["time_possible_placeholder"]).sum())
print("Rows without valid coordinates:", (~clean["has_valid_coords"]).sum())
print("Suspicious dates before 2000:", clean["date_invalid"].sum())
print("Rows outside analysis window:", (~clean["in_analysis_window"]).sum())