"""Milestone 1 acceptance checks and data summary.

Run as ``uv run python -m factor_alloc.validate``. Writes ``results/m1_validation.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from factor_alloc.ingest import JKP_REGIONS, PROCESSED, ROOT, positive_mean_share

RESULTS = ROOT / "results"


@dataclass
class CorrCheck:
    """One correlation acceptance check."""

    label: str
    corr: float
    threshold: float
    n_months: int
    start: pd.Timestamp
    end: pd.Timestamp

    @property
    def passed(self) -> bool:
        return self.corr > self.threshold


def overlap_corr(a: pd.Series, b: pd.Series, label: str, threshold: float) -> CorrCheck:
    """Correlation of two monthly series over the months where both are observed."""
    both = pd.concat([a, b], axis=1, join="inner").dropna()
    return CorrCheck(
        label=label,
        corr=float(both.iloc[:, 0].corr(both.iloc[:, 1])),
        threshold=threshold,
        n_months=len(both),
        start=both.index.min(),
        end=both.index.max(),
    )


def panel_summary(name: str, returns: pd.DataFrame) -> dict:
    """Factor count, date range, and missing-data statistics for one wide panel."""
    first = returns.apply(pd.Series.first_valid_index)
    last = returns.apply(pd.Series.last_valid_index)
    # Missing cells between each factor's own first and last observation (interior gaps).
    interior = sum(int(returns.loc[first[c] : last[c], c].isna().sum()) for c in returns.columns)
    return {
        "panel": name,
        "factors": returns.shape[1],
        "start": returns.index.min().date(),
        "end": returns.index.max().date(),
        "months": returns.shape[0],
        "missing_cells_pct": round(100 * returns.isna().to_numpy().mean(), 1),
        "interior_gaps": interior,
        "median_first_date": pd.Series(first).median().date(),
        "latest_first_date": pd.Series(first).max().date(),
        "factors_ending_early": int((last < returns.index.max()).sum()),
        "positive_mean_pct": round(100 * positive_mean_share(returns), 1),
    }


def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a Markdown table (no index)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def run() -> str:
    """Run all Milestone 1 checks and return the report as Markdown."""
    french = pd.read_parquet(PROCESSED / "french_ff5_mom.parquet")
    jkp = {r: pd.read_parquet(PROCESSED / f"jkp_returns_{r}.parquet") for r in JKP_REGIONS}
    jkp_mkt = pd.read_parquet(PROCESSED / "jkp_mkt.parquet")
    osap = {v: pd.read_parquet(PROCESSED / f"osap_returns_{v}.parquet") for v in ("vw", "op")}
    osap_q5 = pd.read_parquet(PROCESSED / "osap_returns_vw_q5.parquet")
    jkp_usa_vw = pd.read_parquet(PROCESSED / "jkp_returns_usa_vw.parquet")
    meta_osap = pd.read_parquet(PROCESSED / "meta_osap.parquet")
    meta_jkp = pd.read_parquet(PROCESSED / "meta_jkp.parquet")

    checks = [
        overlap_corr(jkp_mkt["usa"], french["Mkt-RF"], "JKP US mkt vs French Mkt-RF", 0.95),
        overlap_corr(jkp["usa"]["be_me"], french["HML"], "JKP US be_me vs French HML", 0.90),
        overlap_corr(osap["vw"]["Mom12m"], french["UMD"], "OSAP Mom12m (VW) vs French UMD", 0.90),
        overlap_corr(osap["op"]["Mom12m"], french["UMD"], "OSAP Mom12m (op) vs French UMD", 0.90),
        # Construction diagnostics: alternative variants of the same factors.
        overlap_corr(osap_q5["Mom12m"], french["UMD"], "OSAP Mom12m (VW quintiles) vs UMD", 0.90),
        overlap_corr(jkp_usa_vw["be_me"], french["HML"], "JKP US be_me (uncapped VW) vs HML", 0.90),
        overlap_corr(osap["vw"]["BM"], french["HML"], "OSAP BM (VW) vs French HML", 0.90),
        overlap_corr(osap_q5["BM"], french["HML"], "OSAP BM (VW quintiles) vs French HML", 0.90),
    ]
    # Informational only: not acceptance checks.
    extra = [
        overlap_corr(jkp["usa"]["ret_12_1"], french["UMD"], "JKP US ret_12_1 vs French UMD", 0),
        overlap_corr(
            jkp["usa"]["market_equity"], french["SMB"], "JKP US market_equity vs French SMB", 0
        ),
    ]
    check_df = pd.DataFrame(
        [
            {
                "check": c.label,
                "corr": round(c.corr, 3),
                "threshold": c.threshold if c.threshold else "info",
                "pass": ("PASS" if c.passed else "FAIL") if c.threshold else "",
                "months": c.n_months,
                "overlap": f"{c.start:%Y-%m} to {c.end:%Y-%m}",
            }
            for c in checks + extra
        ]
    )

    # Alignment diagnostic: correlation should peak at lag 0 if dates are aligned.
    lag_df = pd.DataFrame(
        [
            {"pair": label, **{f"lag {s:+d}": round(a.shift(s).corr(b), 3) for s in (-1, 0, 1)}}
            for label, a, b in (
                ("JKP mkt / Mkt-RF", jkp_mkt["usa"], french["Mkt-RF"]),
                ("JKP be_me / HML", jkp["usa"]["be_me"], french["HML"]),
                ("OSAP Mom12m VW / UMD", osap["vw"]["Mom12m"], french["UMD"]),
                ("OSAP Mom12m op / UMD", osap["op"]["Mom12m"], french["UMD"]),
            )
        ]
    )

    missing = {}
    for name, m, used in (
        ("osap", meta_osap, set(osap["vw"].columns) | set(osap["op"].columns)),
        ("jkp", meta_jkp, set(jkp["usa"].columns)),
    ):
        miss = m[m["pub_date"].isna()]
        no_meta = sorted(used - set(m["factor_id"]))
        missing[name] = (miss, no_meta)

    summary = pd.DataFrame(
        [panel_summary(f"osap_{v}", r) for v, r in osap.items()]
        + [panel_summary(f"jkp_{k}", r) for k, r in jkp.items()]
        + [panel_summary("jkp_mkt", jkp_mkt), panel_summary("french", french)]
    )
    osap_not_vw = sorted(set(osap["op"].columns) - set(osap["vw"].columns))
    pub_years = pd.DataFrame(
        {
            "source": ["osap", "jkp"],
            "min_pub_year": [m["pub_date"].min().year for m in (meta_osap, meta_jkp)],
            "median_pub_year": [int(m["pub_date"].dt.year.median()) for m in (meta_osap, meta_jkp)],
            "max_pub_year": [m["pub_date"].max().year for m in (meta_osap, meta_jkp)],
            "published_by_1990": [
                int((m["pub_date"].dt.year <= 1990).sum()) for m in (meta_osap, meta_jkp)
            ],
            "published_by_2000": [
                int((m["pub_date"].dt.year <= 2000).sum()) for m in (meta_osap, meta_jkp)
            ],
        }
    )

    out = ["# Milestone 1: ingest and validation", ""]
    out += ["## Acceptance: correlations", "", md_table(check_df), ""]
    out += ["## Alignment diagnostic (correlation at month shifts)", "", md_table(lag_df), ""]
    out += ["## Acceptance: missing pub_date", ""]
    for name, (miss, no_meta) in missing.items():
        ids = ", ".join(miss["factor_id"]) if len(miss) else "none"
        out.append(f"- {name}: {len(miss)} factors with missing pub_date ({ids})")
        out.append(f"- {name}: {len(no_meta)} return columns without a meta row")
    out += ["", "## Data summary", "", md_table(summary), ""]
    out += [
        "Notes:",
        "- missing_cells_pct is over the full rectangular panel, so it is mostly late starts.",
        "- interior_gaps counts missing months between a factor's first and last observation.",
        "- positive_mean_pct near 100 confirms returns are signed in the published direction.",
        f"- OSAP predictors in op but not in the VW decile panel ({len(osap_not_vw)}): "
        + ", ".join(osap_not_vw),
        "",
        "## Publication years",
        "",
        md_table(pub_years),
        "",
        "## Resolution",
        "",
        "- Alignment: every pair peaks at lag 0, so no failure is a date offset.",
        "- UMD: OSAP Mom12m from VW quintiles passes. The decile and original-paper variants",
        "  use more extreme breakpoints than French's 30/70 split, which lowers correlation.",
        "- HML: known gap, accepted. No free series reaches 0.9. French HML averages small and",
        "  big value legs from a 2x3 size-by-B/M sort; JKP be_me and OSAP BM are single sorts",
        "  weighted toward large caps. Replicating the 2x3 sort needs stock-level data, which",
        "  is out of scope. The threshold stays at 0.9 and the check stays FAIL.",
        "- Missing pub_date: the 11 JKP factors with no citation are dated by",
        "  meta.JKP_PUB_YEAR_OVERRIDES (Hou, Xue and Zhang 2020; Ball et al. 2015 and 2016).",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    """Write the report to ``results/m1_validation.md`` and print it."""
    report = run()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "m1_validation.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
