# My Audit — Caroline Romero

## What I audited
- Feature: Top-10 ranked district list (`python -m src.analysis --top 10`)
- Number: Persistence rate (active months / eligible months)
- Version checked: `main` at commit 87a892a; audit files on branch `caroline-module9-audit`

## Intended user and requirement
- User: LA Bureau of Street Lighting planning manager
- Task: decide which LAPD reporting districts get on-site lighting assessments first
- Requirement: BUILD_SPEC section 8 lists the ranked table's columns in order; section 6 defines
  persistence rate = active months / eligible months, where active = months with at least one
  nighttime (18:00–05:59) reported offense, and eligible = calendar months from 2025-01-01 to the
  last date in the data.

## Feature audit
Steps: from the repo root, run `.venv/bin/python -m src.analysis --top 10`
- Works: Columns appear in the order BUILD_SPEC section 8 lists (Rank, RPT Dist No, AREA NAME, Priority score, ...). District codes keep leading zeros (0182, 0636). Recent period shows 2026-06-01 to 2026-08-31, matching the spec's stated default.
- Hard to use: The output is difficult for the planning manager to read. Each district's row wraps across three lines, so it's hard to match values to their column headers, and some numbers are split in half. For example, district 0182's valid mapped nighttime offenses (1167) appears as "11" at the end of one line and "67" at the start of the next. Values also show more decimal places than a manager needs (e.g., a priority score of 87.679181), and the output doesn't explain what "nighttime" means or how the priority score is calculated.
- Observation: All 10 top districts have a persistence rate of 1.0 (nighttime offenses in all 21 of 21 months). Because they are tied on persistence, it does not help the planning manager choose between them; their order is decided by nighttime offense volume, which decreases down the ranking (1,167 for rank 1, then 1,097, 978, 953, 939…).

## Number audit: persistence rate
- What it should mean: share of the 21 eligible months in which a district had at least one nighttime reported offense.
- Sanity checks: must be between 0 and 1; active months can never exceed 21; denominator is calendar months, not offenses. Observed range: 0.0 to 1.0. 
- Cases I calculated by hand:
  - District 0122: 18 active months → 18 / 21 = 0.857143 (tool shows 0.857143) 
  - District 0116: 1 active month → 1 / 21 = 0.047619 (tool shows 0.047619) 
  - District 0182 (rank 1): 21 / 21 = 1.0 (tool shows 1.0) 
- Independent recomputation: `audits/caroline/check_persistence.py` (full code in Appendix) Run from repo root: `.venv/bin/python audits/caroline/check_persistence.py`
  The script does NOT use the team's `is_night` or `offense_month` columns. It rebuilds nighttime from the raw `Time OCC` text (hour >= 18 or < 6, valid HHMM only), filters dates from 2025-01-01 to the data's max date, counts distinct months per district, and divides by the number of eligible months. It then compares every district to `ranked_districts()`.
- Result: Data ends 2026-09-19; eligible months = 21; 1,172 districts compared;
  0 districts disagree.

## Conclusion and remaining uncertainty
- Conclusion: The persistence rate is calculated correctly for the default full-period ranking. My independent recomputation matched the tool for all 1,172 districts (0 disagreements), and my hand calculations for districts 0122, 0116, and 0182 matched the displayed values. I found no defect in this number.
- Not tested: filtered views (area, offense type, custom date ranges); I only checked the default full-period ranking. My check reuses the team's cleaned Parquet file, so a cleaning error upstream would affect both answers equally.
- District "01" appears with a nonstandard 2-digit code; I did not investigate whether it is a valid district.

## Change requests
- AUDIT-03: Make the CLI ranked output readable for the planning manager (see change-requests.md). No change request for persistence rate, since no defect was found.

## My contribution and how AI helped
What I did:
- Found the team repo and updated `main` with the latest work
- Read BUILD_SPEC to understand who the user is and what the tool should do
- Checked teammates' claims (Olga, Ansel) so I would pick something different
- Chose my feature (top-10 list) and number (persistence rate) from options Claude suggested
- Set up Python and ran the team's tool
- Looked at the output as the planning manager and decided what was hard to read
- Ran the independent check script, reviewed what each part does, and read the results
- Checked the math by hand (18 ÷ 21, 1 ÷ 21, 21 ÷ 21)
- Concluded that persistence doesn't separate the top 10, and that offense volume decides the order
- Wrote the check script (`audits/caroline/check_persistence.py`) and explained each step

How AI helped:
- AI helped review and verify my code worked
- AI helped me point out specific details in the output (like the split of the numbers)
- AI helped polish my wording of my answers; the judgments and conclusions are my own

## Appendix: check script (audits/caroline/check_persistence.py)
Also committed on branch `caroline-module9-audit` in the team repo.
Run from the repo root: `.venv/bin/python audits/caroline/check_persistence.py`

```python
# Caroline Romero - Module 9 audit
# Independent check of "Persistence rate" = active months / eligible months
# Run from the repo root:  .venv/bin/python audits/caroline/check_persistence.py
import sys, os
sys.path.insert(0, os.getcwd())
import pandas as pd
from src.analysis import load_processed, ranked_districts, Filters

df = pd.read_parquet("data/processed/lapd_nibrs_offenses.parquet")

# MY OWN nighttime rule, from the original time text (HHMM)
t = df["Time OCC"].astype("string").str.zfill(4)
hour = pd.to_numeric(t.str[:2], errors="coerce")
minute = pd.to_numeric(t.str[2:], errors="coerce")
valid_time = hour.between(0, 23) & minute.between(0, 59)
night = valid_time & ((hour >= 18) | (hour < 6))

# MY OWN date window: Jan 1 2025 through the last date in the data
day = df["Date OCC"].dt.normalize()
end = day.max()
in_window = (day >= "2025-01-01") & (day <= end)
eligible = len(pd.period_range("2025-01", end, freq="M"))

keep = night & in_window & df["RPT Dist No"].notna() & df["UniqueNIBRNo"].notna()
q = df[keep].copy()
q["district"] = q["RPT Dist No"].astype(str)
q["month"] = q["Date OCC"].dt.to_period("M")
my_active = q.groupby("district")["month"].nunique()

# The TEAM tool's answer
team = ranked_districts(load_processed(), Filters())
team.index = team["RPT Dist No"].astype(str)

c = pd.DataFrame({
    "team_active": team["Active months"],
    "my_active": my_active,
    "team_rate": team["Persistence rate"],
}).fillna(0)
c["my_rate"] = c["my_active"] / eligible
c["diff"] = (c["team_rate"] - c["my_rate"]).abs()

print("Data ends on:", end.date(), "| Eligible months:", eligible)
print("Districts compared:", len(c))
print("Districts where team and I disagree:", (c["diff"] > 1e-9).sum())
print("Rate range:", c["team_rate"].min(), "to", c["team_rate"].max())
print()
print("District 0182:")
print(c.loc["0182"])
print()
print("Some districts with persistence below 1.0:")
print(c[(c["my_active"] > 0) & (c["my_active"] < eligible)].head(5))
```

Output (Oct 25, 2026):
```
Data ends on: 2026-09-19 | Eligible months: 21
Districts compared: 1172
Districts where team and I disagree: 0
Rate range: 0.0 to 1.0

District 0182: team_active 21, my_active 21, team_rate 1.0, my_rate 1.0, diff 0.0

Some districts with persistence below 1.0:
      team_active  my_active  team_rate   my_rate  diff
01              3        3.0   0.142857  0.142857   0.0
0109            7        7.0   0.333333  0.333333   0.0
0112           16       16.0   0.761905  0.761905   0.0
0116            1        1.0   0.047619  0.047619   0.0
0122           18       18.0   0.857143  0.857143   0.0
```