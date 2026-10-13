# Milestone 1: ingest and validation

## Acceptance: correlations

| check | corr | threshold | pass | months | overlap |
|---|---|---|---|---|---|
| JKP US mkt vs French Mkt-RF | 0.974 | 0.95 | PASS | 726 | 1963-07 to 2023-12 |
| JKP US be_me vs French HML | 0.816 | 0.9 | FAIL | 738 | 1963-07 to 2024-12 |
| OSAP Mom12m (VW) vs French UMD | 0.873 | 0.9 | FAIL | 1176 | 1927-01 to 2024-12 |
| OSAP Mom12m (op) vs French UMD | 0.801 | 0.9 | FAIL | 1176 | 1927-01 to 2024-12 |
| OSAP Mom12m (VW quintiles) vs UMD | 0.906 | 0.9 | PASS | 1176 | 1927-01 to 2024-12 |
| JKP US be_me (uncapped VW) vs HML | 0.781 | 0.9 | FAIL | 738 | 1963-07 to 2024-12 |
| OSAP BM (VW) vs French HML | 0.591 | 0.9 | FAIL | 738 | 1963-07 to 2024-12 |
| OSAP BM (VW quintiles) vs French HML | 0.682 | 0.9 | FAIL | 738 | 1963-07 to 2024-12 |
| JKP US ret_12_1 vs French UMD | 0.965 | info |  | 1176 | 1927-01 to 2024-12 |
| JKP US market_equity vs French SMB | 0.895 | info |  | 738 | 1963-07 to 2024-12 |

## Alignment diagnostic (correlation at month shifts)

| pair | lag -1 | lag +0 | lag +1 |
|---|---|---|---|
| JKP mkt / Mkt-RF | 0.078 | 0.974 | 0.054 |
| JKP be_me / HML | 0.155 | 0.816 | 0.115 |
| OSAP Mom12m VW / UMD | 0.078 | 0.873 | 0.073 |
| OSAP Mom12m op / UMD | 0.077 | 0.801 | 0.023 |

## Acceptance: missing pub_date

- osap: 0 factors with missing pub_date (none)
- osap: 0 return columns without a meta row
- jkp: 0 factors with missing pub_date (none)
- jkp: 0 return columns without a meta row

## Data summary

| panel | factors | start | end | months | missing_cells_pct | interior_gaps | median_first_date | latest_first_date | factors_ending_early | positive_mean_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| osap_vw | 179 | 1926-01-31 | 2024-12-31 | 1188 | 30.6 | 136 | 1953-07-31 | 2001-07-31 | 15 | 88.3 |
| osap_op | 212 | 1926-01-31 | 2024-12-31 | 1188 | 31.2 | 346 | 1953-07-31 | 2000-07-31 | 17 | 96.2 |
| jkp_usa | 153 | 1926-01-31 | 2024-12-31 | 1188 | 20.4 | 18 | 1951-06-30 | 1971-11-30 | 0 | 88.9 |
| jkp_world_ex_us | 153 | 1986-01-31 | 2024-12-31 | 468 | 7.9 | 764 | 1986-02-28 | 2006-01-31 | 0 | 87.6 |
| jkp_developed | 153 | 1986-01-31 | 2024-12-31 | 468 | 7.9 | 764 | 1986-02-28 | 2006-01-31 | 0 | 86.9 |
| jkp_emerging | 153 | 1987-09-30 | 2024-12-31 | 442 | 17.0 | 343 | 1993-05-31 | 2008-05-31 | 0 | 85.0 |
| jkp_frontier | 131 | 2006-09-30 | 2024-12-31 | 214 | 23.1 | 5063 | 2007-10-31 | 2017-11-30 | 40 | 74.0 |
| jkp_mkt | 5 | 1926-01-31 | 2024-12-31 | 1188 | 50.2 | 0 | 1986-01-31 | 1993-08-31 | 1 | 100.0 |
| french | 7 | 1927-01-31 | 2026-08-31 | 1196 | 31.4 | 0 | 1963-07-31 | 1963-07-31 | 0 | 100.0 |

Notes:
- missing_cells_pct is over the full rectangular panel, so it is mostly late starts.
- interior_gaps counts missing months between a factor's first and last observation.
- positive_mean_pct near 100 confirms returns are signed in the published direction.
- OSAP predictors in op but not in the VW decile panel (33): AccrualsBM, ChForecastAccrual, ChNAnalyst, CitationsRD, ConsRecomm, ConvDebt, CredRatDG, DebtIssuance, DivInit, DivOmit, DivSeason, DivYieldST, DownRecomm, ExchSwitch, Governance, IndIPO, MS, MomRev, MomVol, OScore, PatentsRD, RDIPO, RIO_Disp, RIO_MB, RIO_Turnover, RIO_Volatility, Recomm_ShortInterest, ShareRepurchase, ShareVol, Spinoff, SurpriseRD, UpRecomm, sinAlgo

## Publication years

| source | min_pub_year | median_pub_year | max_pub_year | published_by_1990 | published_by_2000 |
|---|---|---|---|---|---|
| osap | 1973 | 2006 | 2016 | 14 | 51 |
| jkp | 1973 | 2006 | 2020 | 11 | 37 |

## Resolution

- Alignment: every pair peaks at lag 0, so no failure is a date offset.
- UMD: OSAP Mom12m from VW quintiles passes. The decile and original-paper variants
  use more extreme breakpoints than French's 30/70 split, which lowers correlation.
- HML: known gap, accepted. No free series reaches 0.9. French HML averages small and
  big value legs from a 2x3 size-by-B/M sort; JKP be_me and OSAP BM are single sorts
  weighted toward large caps. Replicating the 2x3 sort needs stock-level data, which
  is out of scope. The threshold stays at 0.9 and the check stays FAIL.
- Missing pub_date: the 11 JKP factors with no citation are dated by
  meta.JKP_PUB_YEAR_OVERRIDES (Hou, Xue and Zhang 2020; Ball et al. 2015 and 2016).
