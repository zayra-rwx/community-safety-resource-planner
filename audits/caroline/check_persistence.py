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