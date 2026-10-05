# Record checks

Expected results were written in plan.md (section 8) before the transformations were run.

## R1: `25088246_290_2`

Why difficult: Multi-offense case (3 rows); case-level totals repeated; daytime

| Field | Original value(s) | Expected | Actual | Match |
|---|---|---|---|---|
| in_scope | Date OCC='2025 May 15 02:21:00 PM' | True | True | Yes |
| occ_year_month | Date OCC='2025 May 15 02:21:00 PM' | 2025-05 | 2025-05 | Yes |
| RPT Dist No | RPT Dist No='0558' | 0558 | 0558 | Yes |
| AREA NAME | AREA NAME='Harbor              ' | Harbor | Harbor | Yes |
| TotalOffenseCount | TotalOffenseCount='3' | 3 | 3 | Yes |
| TotalVictimCount | TotalVictimCount='5' | 5 | 5 | Yes |
| case_rows_in_file | CaseNo='25088246' | 3 | 3 | Yes |
| toc_mismatch | TotalOffenseCount='3' | False | False | Yes |
| Gang-related Crime | Gang-related Crime='Yes' | True | True | Yes |
| map_eligible | LAT='33.746'; LON='-118.2817' | True | True | Yes |
| coord_outside_basic_range | LAT='33.746'; LON='-118.2817' | False | False | Yes |
| coord_far_from_district_review | LAT='33.746'; LON='-118.2817'; RPT Dist No='0558' | False | False | Yes |
| location_suspected_generalized | LOCATION='400 N Palos Verdes St'; RPT Dist No='0558' | False | False | Yes |
| district_eligible | RPT Dist No='0558' | True | True | Yes |
| night | Time OCC='1421' | False | False | Yes |
| counts_in_night_incl_0000 | Date OCC='2025 May 15 02:21:00 PM'; Time OCC='1421'; RPT Dist No='0558' | False | False | Yes |

## R2: `26172245_220_0`

Why difficult: Time OCC 0000; month 2026-08; weapon missing

| Field | Original value(s) | Expected | Actual | Match |
|---|---|---|---|---|
| in_scope | Date OCC='2026 Aug 31 12:00:00 AM' | True | True | Yes |
| occ_year_month | Date OCC='2026 Aug 31 12:00:00 AM' | 2026-08 | 2026-08 | Yes |
| calendar_coverage | Date OCC='2026 Aug 31 12:00:00 AM' | complete | complete | Yes |
| time_is_0000 | Time OCC='0000' | True | True | Yes |
| night | Time OCC='0000' | True | True | Yes |
| counts_in_night_incl_0000 | Date OCC='2026 Aug 31 12:00:00 AM'; Time OCC='0000'; RPT Dist No='1555' | True | True | Yes |
| counts_in_night_excl_0000 | Date OCC='2026 Aug 31 12:00:00 AM'; Time OCC='0000'; RPT Dist No='1555' | False | False | Yes |
| Weapon Used Cd | Weapon Used Cd=NA | NA | NA | Yes |
| Weapon Desc | Weapon Desc=NA | NA | NA | Yes |
| report_lag_days | Date Rptd='2026 Sep 01 08:22:37 PM'; Date OCC='2026 Aug 31 12:00:00 AM' | ≈1.85 | 1.849 | Yes |

## R3: `C259005916_23H_0`

Why difficult: Area-only RPT Dist No; (0, 0) coordinates; C-prefixed case

| Field | Original value(s) | Expected | Actual | Match |
|---|---|---|---|---|
| in_scope | Date OCC='2025 Feb 10 03:00:00 PM' | True | True | Yes |
| RPT Dist No | RPT Dist No='10' | 10 | 10 | Yes |
| rpt_dist_area_only | RPT Dist No='10' | True | True | Yes |
| district_eligible | RPT Dist No='10' | False | False | Yes |
| coord_zero | LAT='0'; LON='0' | True | True | Yes |
| LAT | LAT='0' | NA | NA | Yes |
| LON | LON='0' | NA | NA | Yes |
| map_eligible | LAT='0'; LON='0' | False | False | Yes |
| case_prefix | CaseNo='C259005916' | C | C | Yes |
| night | Time OCC='1500' | False | False | Yes |
| counts_in_night_incl_0000 | Date OCC='2025 Feb 10 03:00:00 PM'; Time OCC='1500'; RPT Dist No='10' | False | False | Yes |

## R4: `25000271_13B_0`

Why difficult: Scope boundary: occurred 2024-12-31 23:55, reported 2025-01-01

| Field | Original value(s) | Expected | Actual | Match |
|---|---|---|---|---|
| in_scope | Date OCC='2024 Dec 31 11:55:00 PM' | False | False | Yes |
| scope_reason | Date OCC='2024 Dec 31 11:55:00 PM' | 2024_rms_transition | 2024_rms_transition | Yes |
| night | Time OCC='2355' | True | True | Yes |
| counts_in_night_incl_0000 | Date OCC='2024 Dec 31 11:55:00 PM'; Time OCC='2355'; RPT Dist No='0647' | False | False | Yes |
| occ_year_month | Date OCC='2024 Dec 31 11:55:00 PM' | 2024-12 | 2024-12 | Yes |

## R5: `26173656_90D_0`

Why difficult: Coordinates ~32 km from district median; partial month; 06:45

| Field | Original value(s) | Expected | Actual | Match |
|---|---|---|---|---|
| in_scope | Date OCC='2026 Sep 03 06:45:00 AM' | True | True | Yes |
| LAT | LAT='34.1244' | 34.1244 | 34.1244 | Yes |
| LON | LON='-117.9063' | -117.9063 | -117.9063 | Yes |
| coord_outside_basic_range | LAT='34.1244'; LON='-117.9063' | True | True | Yes |
| coord_far_from_district_review | LAT='34.1244'; LON='-117.9063'; RPT Dist No='0138' | True | True | Yes |
| map_eligible | LAT='34.1244'; LON='-117.9063' | True | True | Yes |
| district_eligible | RPT Dist No='0138' | True | True | Yes |
| occ_year_month | Date OCC='2026 Sep 03 06:45:00 AM' | 2026-09 | 2026-09 | Yes |
| calendar_coverage | Date OCC='2026 Sep 03 06:45:00 AM' | partial | partial | Yes |
| night | Time OCC='0645' | False | False | Yes |
| counts_in_night_incl_0000 | Date OCC='2026 Sep 03 06:45:00 AM'; Time OCC='0645'; RPT Dist No='0138' | False | False | Yes |
