# Evaluation cases

The brief asks for a typical case, a boundary case, an out-of-scope case and repeated runs. Each case
below is encoded in `tests/test_engine.py` and can be re-run with `python -m unittest -v`. Expected
values are quoted from the source document the rule cites, so a reviewer can check them without the tool.

## 1. Typical: 998 E 19th Ave, as approved by Council (25 Jul 2024)

Inputs: `sites/998-e-19th-ave.json`, `options/998-e-19th-ave-as-approved.json`, rules as of 2026-10-23.

| What the engine must say | Expected | Where to check |
|---|---|---|
| FSR | 8,299.0 / 2,810.7 = 2.953, above the RM-1 outright 1.20 → "no outright, by rezoning" | Referral report rr1.pdf, Existing zoning and Proposed statistics |
| Height | 22.3 m above the RM-1 outright 10.7 m; above the 19.9 to 21.3 m staff benchmark → conditional | rr1.pdf, Height section |
| Family units | 26 + 12 = 38 of 105 = 36.2% ≥ 35% → pass | rr1.pdf, Unit mix; 1992 High-Density Housing for Families with Children Guidelines |
| Trees | Schedule C: 2,811 m² → 20 required; 1 retained + 16 planted = 17 → shortfall 3 → $3,000 cash in lieu → conditional | Protection of Trees By-law 9958, Schedule C and s.4.5 |
| Social housing definition | 30% below HILs, non-profit owner, 60-year agreement → pass | Zoning and Development By-law s.2 definition |
| SSMUH | RM-1 is not a restricted (single-detached) zone → not applicable | Local Government Act s.481.3; Provincial Policy Manual |
| CHF | rent-tier split, accessible units, land tenure missing → uncertain, with the grant at 2025-26 rates stated ($171,211 × 105) | CHF RFP #1070-2526-022 |
| BC Builds | below-market share not stated → uncertain; non-residential 15.1% under the 30% cap | BC Builds program page |

## 2. Boundary

| Case | Expected |
|---|---|
| R1-1 lot of exactly 280 m² | SSMUH minimum 3 homes |
| R1-1 lot of 281 m² | SSMUH minimum 4 homes |
| 300 m² lot, frequent bus stop confirmed within 400 m | 6 homes, no parking minimum |
| Same lot, bus distance unknown | status *uncertain*, with the 4-home floor stated and the 6-home case named |
| Family share exactly 35.0% (7 of 20) | pass |
| Family share 33.3% (7 of 21) | fail |
| Tree bands | 365 m² → 2; 366 m² → 3; 2,810.7 m² → 20; 3,300 m² → 31 |

## 3. Out of scope

| Case | Expected |
|---|---|
| SSMUH on an RM-1 site | *not applicable*, with the reason ("written for R1-1, RS, RT districts; this site is zoned RM-1") |
| SSMUH on an R1-1 site inside a transit-oriented area | *not applicable* (TOA prevails); the TOA rule reports the tier's minimum storeys (tier 2 → 12) |
| Interim Rezoning Policy on a site outside the former Community Vision areas | *not applicable*, pointing to the 1989 Affordable Housing Policies |
| Missing unit mix or height | *uncertain* with a named action, never an exception |

## 4. Repeated runs

Two evaluations of the same inputs produce byte-identical ledgers and the same 16-character stamp.
The massing built from the same ledger is byte-identical too. There is no model call and no clock
other than the `--as-of` date, so there is nothing to vary.

## 5. Rule version switch (the resilience claim)

The family-unit rule carries two dated versions: 35% two-bedroom-plus until 2026-10-26, and 35% plus
a 5% three-bedroom-plus minimum from 2026-10-27 (City of Vancouver, Housing options for families page, amendment effective 27 Oct 2026). Running the same option with
`--as-of 2026-10-26` and `--as-of 2026-10-27`:

- picks the right version each time (the memo prints the version date next to the rule);
- changes the stamp (`20e44f1445ecaff9` → `6d1b07fe59dd3775` on the current rule files);
- the `--previous` diff lists exactly one changed rule, `cov.family_units`;
- an option with 3.8% three-bedroom units passes on the 26th and fails on the 27th.

## 6. Version stamp

Editing one parameter in one rule file changes that file's hash, the overall rules hash and the
stamp, and leaves the other files' hashes unchanged, so a reviewer can see which layer moved.

## What is not yet evaluated

Checked by a person, not by the tests: that the RM-1 figures match the consolidated district
schedule (the referral report is the cited source), the transit-oriented-area tier for the site, and
the placeholders in the site file (red pine DBH, setbacks). These are listed in the memo's
third section so the user knows they are open.
