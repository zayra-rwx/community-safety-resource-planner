# Project Starting Point

## Team and GitHub

| Team name | GitHub repository |
|---|---|
| Community Safety Resource Planner | https://github.com/zayra-rwx/community-safety-resource-planner |

## Selected project area

Community Safety Resource Planning using LAPD NIBRS data

## Why our team is interested in it

Our team is interested in exploring how reported-offense data can support community safety decisions beyond traditional enforcement responses. We want to examine how location and time patterns could help public agencies prioritize limited resources while clearly acknowledging the data’s limitations and the need for additional evidence.

## Candidate Vision A - Community Outreach

A Community Safety Partnership Bureau manager at the Los Angeles Police Department must decide which geographic areas and time periods should be prioritized for a pilot expansion of non-enforcement community outreach resources.

## Candidate Vision B - Lighting Reviews

A street-lighting program manager at the City of Los Angeles Bureau of Street Lighting must decide which geographic areas with recurring nighttime reported offenses should be prioritized for on-site lighting assessments.

## Side-by-side candidate assessment

| Assessment | Vision A | Vision B |
|---|---|---|
| Evidence found so far | The LAPD NIBRS Offenses Dataset includes the hundred-block location, latitude, and longitude associated with reported offenses. The FBI NIBRS overview confirms that NIBRS captures details such as incident location and time of day. These fields could support analysis of recurring geographic and time patterns for further outreach review.| The LAPD NIBRS Offenses Dataset includes hundred-block locations and associated coordinates. NIBRS also captures time-related incident information, which could help identify areas with recurring nighttime reported offenses for further inspection. |
| Core-data fit | Partial. The data can help identify geographic areas and time periods with recurring reported-offense patterns, but it does not directly measure community needs, existing services, resident preferences, or the likely effectiveness of outreach resources. |Partial. The data can identify geographic areas with recurring nighttime reported offenses, but it does not measure street-light locations, illumination levels, maintenance conditions, or whether lighting contributed to an offense. |
| Biggest risk | Using reported-offense patterns as a substitute for community need could reinforce differences in reporting or enforcement and direct resources toward areas without sufficient community input or supporting evidence. | The team could mistakenly imply that inadequate lighting causes crime. The results must be presented only as a way to prioritize on-site assessments, with separate lighting-condition evidence required before recommending improvements.|

## Core data source we confirmed we can access

Our primary source is the City of Los Angeles LAPD NIBRS Offenses Dataset. Its official catalog page opened successfully and provides public access to the data in CSV, JSON, and XML formats. The source confirms that the dataset includes the hundred-block location of an offense and the corresponding latitude and longitude.

The legacy LAPD crime dataset covering 2020–2024 also opened successfully and is available in CSV, JSON, and XML formats. However, LAPD transitioned to a new NIBRS-aligned Records Management System on March 7, 2024. Because the legacy and NIBRS systems use different reporting structures, the team must investigate comparability before combining records or comparing offense counts across the transition.

Possible auxiliary sources include the Census American Community Survey API for neighborhood-level context and the FBI NIBRS overview for documentation about what NIBRS records represent.

The exact LAPD export fields, row definition, dataset size, missingness, and time-field completeness still need to be inspected using a small sample.

## Three questions we still need to resolve

1. What does one row in the LAPD NIBRS Offenses Dataset represent, and which exact location, date, time, and offense fields are sufficiently complete for the proposed analyses?
2. How should the team handle the transition between the legacy LAPD reporting system and the newer NIBRS-aligned system without making invalid comparisons across reporting structures?
3. Which reliable auxiliary sources could provide information about community-service coverage or streetlight locations and conditions, and at what geographic level could those sources connect to the LAPD data?

## Role-file progress

Use one of these status labels: **Not started**, **In progress**, **Ready for team review**, **Complete**, or **Not applicable**.

| Role file | Owner | Status |
|---|---|---|
| [`objectives.md`](objectives.md) | Olga Tovstovan (olga-tovstogan) | Not started |
| [`alternatives.md`](alternatives.md) | Ansel Lin (anselyulin) | Not started |
| [`data-fit.md`](data-fit.md) | Thomas Yin (jiatongy-svg) | Not started |
| [`auxiliary.md`](auxiliary.md) | Caroline Romero (carolineromero19) | Not started |
| [`technical.md`](technical.md) | Zayra Martinez (zayra-rwx) | Not started |
| [`objections.md`](objections.md) | Not applicable—five-person team | Not applicable |

## Team check

- [x] We added our team name and the correct private GitHub repository link.
- [X] We selected the area based first on genuine team interest.
- [X] A and B are distinct candidate Visions within the same area.
- [X] The candidate comparison uses verified evidence rather than unsupported claims.
- [X] At least one data source opened, or we recorded the access blocker.
- [X] We preserved three real questions instead of hiding uncertainty.
- [X] Every active role file has an owner and a current status.
- [X] Every teammate reviewed this provisional starting point.
