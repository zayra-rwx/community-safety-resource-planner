## Context

- **Name:** Olga Tovstogan.
- **Team app and version or commit checked:** Community Safety Resource Planner / Streetlight Assessment, existing command-line implementation at commit `87a892a392727cfaff176d3c0fbbf6019a60eb4a` in the [team repository](https://github.com/zayra-rwx/community-safety-resource-planner/tree/87a892a392727cfaff176d3c0fbbf6019a60eb4a).
- **Intended user and decision:** A Bureau of Street Lighting planning manager deciding which Los Angeles reporting districts to prioritize for an on-site lighting assessment.

## 1. Feature audit

- **Feature and intended behavior:** Request a ranked list of districts for a selected period. The existing CLI should return districts in priority order with supporting counts, consistent with the README and the metric definitions in `BUILD_SPEC.md` sections 5–6 and 11.

- **Inputs and steps to reproduce:** At the commit above, use the committed processed Parquet and install `requirements-phase2.txt`. From the repository root, run the following commands, then repeat the first command:

  ```powershell
  .\.venv\Scripts\python.exe -m src.analysis --top 3
  .\.venv\Scripts\python.exe -m src.analysis --start 2026-09-19 --end 2025-01-01 --top 3
  ```

- **Expected behavior:** The default command returns the three highest-priority districts. Repeating it returns the same results. Under the documented backend behavior, a reversed date interval returns an empty result.

- **Actual behavior and evidence:** Codex's recorded runs returned districts **0182, 1494, and 0636**, in that order, with scores **87.679181, 87.627986, and 87.576792**. The repeated output was identical. Reversed dates returned exit code 0 and `Empty DataFrame`, without an explanation. Commands and captured output are recorded in `audits/olga/feature-output.txt`; the commands above reproduce the cases using the committed implementation.

- **Conclusion and any recommended change:** **Pass with limitation.** The tested ranking and repeat behavior worked. However, the empty result does not explain whether the dates are invalid or there are no matching records. I recommend a short explanatory message while preserving the backend's documented behavior. This usability recommendation is recorded as **AUDIT-01** in the team's `change-requests.md`.

## 2. Number audit

- **Number audited and its meaning:** District **0182's priority score, 87.679181**. It is a relative assessment-priority index, not an 87.68% probability of crime or evidence of poor lighting.

- **Formula, units, population, and time window:** The score is dimensionless and ranges from 0 to 100:

  ```text
  Persistence = active months / eligible months
  Each percentile = ascending average rank / number of districts
  Score = 100 × (0.60 × frequency percentile + 0.40 × persistence percentile)
  Districts with zero qualifying nighttime offenses receive score 0.
  ```

  The default period is **January 1, 2025–September 19, 2026**, covering 21 eligible calendar months and 1,172 represented districts. Frequency counts distinct qualifying nighttime offense IDs. District 0182 has 1,167 such offenses and is active in all 21 months. The two percentile denominators are 1,172; the persistence denominator is 21.

- **Relevant data assumptions:** Nighttime is 18:00–05:59, including midnight. Records need valid dates/times and a nonmissing district and offense ID. Missing coordinates do not exclude an offense. The scoring population includes represented districts with only daytime records. Partial endpoint months count as eligible months, and tied values receive their average rank.

- **Code checked: file path, function name, and relevant line numbers or a short code excerpt:** At the recorded commit, `src/analysis.py`, `ranked_districts()` begins at line 108. Lines 133–137 calculate percentiles with `rank(method='average', pct=True)`, combine the 60/40 weights, and apply the zero-offense override. The weights are defined in `src/config.py`.

- **What this code computes, in my own words:** It compares each district's offense frequency and persistence with the other included districts, then combines those relative positions. This means the score depends on the comparison population as well as the district's own records.

- **Small test case and expected result:** Consider three districts over January–March 2025:

  | District | Nighttime offenses | Active / eligible months | Expected score |
  |---|---:|---:|---:|
  | A | 2 | 2 / 3 | 83⅓ |
  | B | 2 | 2 / 3 | 83⅓ |
  | C, daytime records only | 0 | 0 / 3 | 0 |

  A and B tie at positions 2 and 3 for both measures. Their average rank is `(2 + 3) / 2 = 2.5`, and their percentile is `2.5 / 3 = 5/6`. Their expected score is `100 × (0.60 × 5/6 + 0.40 × 5/6) = 83⅓`. C receives 0 through the explicit override. Removing C changes A and B's percentile to `1.5 / 2`, so each scores 75.

- **Actual result:** The recorded verification produced **83.33333333333334** for A and B, 0 for C, and 75 for both districts after removing C. For district 0182, the unrounded score was **87.67918088737201**, displayed as **87.679181**. The independent calculation and production result differed by 0.0.

- **Independent calculation or check of a specific assumption/code line:** The key assumption checked was average ranking for ties. Although district 0182 has maximum persistence, 723 districts share that value and 449 have lower persistence. Its average persistence rank is `449 + (723 + 1) / 2 = 811`. Its frequency percentile is 1, so:

  ```text
  Score = 100 × (0.60 × 1 + 0.40 × 811/1172)
        = 87.67918088737201
  ```

  Using maximum rank for the persistence tie instead would produce 100. The following standalone check exercises the same Pandas ranking line against the small case's expected arithmetic and reproduces district 0182's arithmetic from the recorded group counts. With Pandas installed, save it as `score_check.py` and run `python score_check.py`:

  ```python
  from math import isclose
  import pandas as pd

  counts = pd.Series([2, 2, 0], index=["A", "B", "C"])
  persistence = pd.Series([2/3, 2/3, 0], index=counts.index)
  frequency_pct = counts.rank(method="average", pct=True)
  persistence_pct = persistence.rank(method="average", pct=True)
  scores = 100 * (0.60 * frequency_pct + 0.40 * persistence_pct)
  scores = scores.where(counts.ne(0), 0)
  assert all(isclose(x, y, abs_tol=1e-10)
             for x, y in zip(scores, [250/3, 250/3, 0]))

  without_c = 100 * counts.loc[["A", "B"]].rank(method="average", pct=True)
  assert all(isclose(x, 75, abs_tol=1e-10) for x in without_c)
  district_0182 = 100 * (0.60 + 0.40 * (449 + (723 + 1)/2) / 1172)
  assert isclose(district_0182, 87.67918088737201, abs_tol=1e-10)

  print("Small case:", scores.round(6).to_dict())
  print("Without C:", without_c.to_dict())
  print("District 0182:", f"{district_0182:.6f}")
  ```

- **What the evidence establishes and what remains uncertain:** The selected score agrees with the documented calculation, and the reproducible check shows how average ties and the comparison population affect the result. This compact check isolates the ranking assumption; it does not independently verify the recorded source counts or repeat data cleaning. Agreement does not establish source completeness, justify the 60/40 policy weights, measure lighting quality, or show that additional lighting would reduce crime. Other metrics and all filter combinations were not audited.

- **Recommended change, if any:** No numeric correction is requested. I would interpret and describe this as a relative priority score rather than an absolute risk measure.

## My contribution

- **What I personally checked and concluded:** I reviewed the audit's scope and assignment coverage and followed up on the missing shared claim file. I recommend explaining reversed-date empty results and interpreting the score as a relative comparison.
- **How AI helped, if used:** Codex inspected the source, ran the CLI and full-data checks, created verification scripts, and drafted the technical findings. ChatGPT helped review the interpretation, shorten the report, and prepare and run the compact ranking check above.
