# factor-alloc

Point-in-time factor allocation research on free, public data.

## Research question

> Can any allocation method beat an equal-weighted mix of published equity factors out of
> sample, after correcting for multiple testing, accounting for post-publication decay, and
> only using factors an investor would have known about at the time?

The project answers this in four parts:

1. **Which factors are real?** Full-sample t-stats for about 200 published signals, tested
   against the Harvey-Liu-Zhu t > 3 hurdle and a Benjamini-Yekutieli false discovery rate
   correction.
2. **Post-publication decay.** A replication of McLean and Pontiff (2016), comparing factor
   returns in-sample, post-sample but pre-publication, and post-publication.
3. **Factor allocation (main result).** A walk-forward comparison of allocators against a
   1/N baseline. A factor can only receive weight after its publication date.
4. **Global out-of-sample test.** Allocation choices fit on US data, then evaluated on
   non-US regions without refitting.

The end product is this repository plus a 4 to 6 page research writeup.

## Data

All data is free and public. No WRDS, CRSP, or Compustat data is used.

| Source | Use |
|---|---|
| [Open Source Asset Pricing](https://www.openassetpricing.com/) (Chen and Zimmermann) | ~200 US signal portfolio returns, plus original sample periods and publication years |
| [JKP Global Factor Data](https://jkpfactors.com/) (Jensen, Kelly, Pedersen) | 153 factors across US, developed, emerging, and frontier regions |
| [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | FF5 plus momentum, for validation and alpha regressions |
| FRED, Goyal-Welch predictors | Macro and valuation predictors (ML allocator only, planned) |

Factor returns are monthly, long-short, gross of trading costs, and signed in their published
direction.

## Research integrity rules

These rules apply to every result in the project:

- **No look-ahead.** Weights at rebalance date t use only returns strictly before t, and
  earn the return of month t+1.
- **Publication gating.** A factor is eligible only after its publication date (December 31
  of the publication year when only the year is known) and after 60 months of history.
- **Past-only estimation.** Normalization, hyperparameter tuning, and volatility estimates
  use only past data.
- **Trial log.** Every backtest run appends a row to `results/trials.csv`, and rows are never
  deleted. The deflated Sharpe ratio uses this count of trials.
- **Honest reporting.** Null and negative results are reported as they are.

## Planned allocators

| Name | Description |
|---|---|
| `equal_weight` | 1/N over eligible factors; the baseline to beat (DeMiguel, Garlappi, Uppal 2009) |
| `mv_shrink` | Long-only mean-variance with Ledoit-Wolf covariance |
| `ridge_sdf` | Kozak-Nagel-Santosh style ridge SDF, penalty chosen by time-series CV |
| `factor_momentum` | Gupta-Kelly style: equal weight in factors with positive trailing 12-month return |
| `ml_timing` | Ridge and LightGBM forecasts of next-month factor returns |

All portfolios are scaled to 10% annualized volatility before comparison. Results are
reported at 0, 10, 25, and 50 bps of one-way turnover cost, with alphas versus FF5 plus
momentum, subperiod splits, and deflated Sharpe ratios.

## Roadmap and current status

| Milestone | Scope | Status |
|---|---|---|
| 1. Ingest and validate | Download OSAP, JKP, and French data; build return panels and factor metadata | Done (one documented gap, see below) |
| 2. Parts 1 and 2 | Multiple-testing counts; McLean-Pontiff decay regressions | Done (see below) |
| 3. Backtest engine | Walk-forward engine, costs, trial log, `equal_weight`, `mv_shrink`, look-ahead tests | Not started |
| 4. More allocators | `ridge_sdf`, `factor_momentum`, deflated Sharpe, subperiods, first draft | Not started |
| 5. Global test and ML | US-fit / global-test evaluation, `ml_timing`, final writeup | Not started |

### Milestone 1 status

Ingest is built and the processed panels exist: 179 OSAP value-weighted signals and 212
OSAP original-paper signals (1926 to 2024), 153 JKP factors for the US and each region,
and French FF5 plus momentum. Every factor has a publication date; 11 JKP factors without
a citation are dated by hand (see `JKP_PUB_YEAR_OVERRIDES` in `meta.py`).

Validation against French factors, with full details in
[`results/m1_validation.md`](results/m1_validation.md):

| Check | Best correlation | Threshold | Result |
|---|---|---|---|
| JKP US market vs French Mkt-RF | 0.974 | 0.95 | Pass |
| OSAP `Mom12m` (VW quintiles) vs French UMD | 0.906 | 0.90 | Pass |
| JKP US `be_me` (capped VW) vs French HML | 0.816 | 0.90 | Fail, accepted as a known gap |

The HML gap is a construction difference. French HML averages small-cap and large-cap
value legs from a 2x3 sort, while the free series are single sorts weighted toward large
caps. Matching it would need stock-level data, which is out of scope.

### Milestone 2 results

Full tables are in [`results/m2_results.md`](results/m2_results.md), and per-factor
t-stats are in `results/m2_factor_tstats.csv`.

**Part 1 (which factors are real).** Counts are for t-stats over each factor's original
sample period. All tests are one-sided.

| Panel | Factors | t > 1.96 | HLZ t > 3 | BY-FDR 5% |
|---|---|---|---|---|
| OSAP original-paper construction | 212 | 186 | 122 | 150 |
| OSAP value-weighted deciles | 179 | 79 | 42 | 45 |
| JKP US (capped VW) | 153 | 81 | 49 | 58 |

Our original-sample t-stats correlate 0.74 with the t-stats reported in the papers.
Value weighting cuts the survivor count sharply. The drop is concentrated in signals
whose original paper equal-weighted.

**Part 2 (post-publication decay).** Declines are a share of the in-sample mean. The
primary panel is OSAP original-paper construction.

| Spec | Post-sample | Post-publication |
|---|---|---|
| McLean and Pontiff (2016) | -26% | -58% |
| OSAP op, raw | -37% | -55% |
| OSAP op, scaled by own in-sample mean | -29% | -58% |
| OSAP op, sample cut at 2013 (raw) | -36% | -50% |
| OSAP VW deciles (raw) | -43% | -68% |
| JKP US (raw) | -7% (not significant) | -53% |

The post-publication decay replicates. Post-sample decay is close in the scaled spec but
larger in the raw spec. Year-level dates are a likely contributor; the report discusses
each gap.

## Repository layout

```
src/factor_alloc/
  ingest.py     # download raw data and build wide monthly return panels (Parquet)
  meta.py       # factor metadata table with a common schema for OSAP and JKP
  validate.py   # Milestone 1 acceptance checks; writes results/m1_validation.md
  testing.py    # Part 1: t-stats, HLZ hurdle, BY-FDR
  decay.py      # Part 2: McLean-Pontiff decay regression
  m2_report.py  # Milestone 2 report; writes results/m2_results.md
tests/          # pytest suite
results/        # validation reports, trial log, tables, figures
data/raw/       # downloads (gitignored)
data/processed/ # Parquet panels (gitignored)
```

Planned modules: `allocators.py`, `backtest.py`, `evaluate.py`,
`regions.py`, `trials.py`.

## Usage

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m factor_alloc.ingest     # download and build data/processed/
uv run python -m factor_alloc.validate   # write results/m1_validation.md
uv run python -m factor_alloc.m2_report  # write results/m2_results.md
uv run pytest
uv run ruff check .
```

Downloads are skipped when a raw file already exists, so a file placed manually in
`data/raw/` is used as is.

## Known limitations

- Factor returns are gross of costs, and long-short factors built on small stocks overstate
  what an investor could earn. Capped value-weighted variants and turnover costs partly
  address this.
- No stock-level models, because stock-level data requires WRDS.
- Publication dates are approximate (year-level).
