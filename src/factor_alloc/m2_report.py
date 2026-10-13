"""Milestone 2 report: Part 1 (multiple testing) and Part 2 (post-publication decay).

Run as ``uv run python -m factor_alloc.m2_report``. Writes ``results/m2_results.md`` and
``results/m2_factor_tstats.csv``.
"""

from __future__ import annotations

import pandas as pd

from factor_alloc.decay import DecayResult, decay_regression, period_dummies
from factor_alloc.ingest import PROCESSED, RAW
from factor_alloc.testing import (
    by_fdr,
    factor_tstats,
    hlz_survivors,
    in_sample_returns,
    survivor_counts,
)
from factor_alloc.validate import RESULTS, md_table

# McLean and Pontiff (2016) headline declines, as a fraction of the in-sample mean.
MP_POST_SAMPLE = -0.26
MP_POST_PUB = -0.58
MP_SAMPLE_END = pd.Timestamp("2013-12-31")
NW_LAGS = 6


def load_panels() -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """Return ``{name: (returns, meta)}`` for the three panels used in Milestone 2."""
    meta_osap = pd.read_parquet(PROCESSED / "meta_osap.parquet")
    meta_jkp = pd.read_parquet(PROCESSED / "meta_jkp.parquet")
    return {
        "OSAP op": (pd.read_parquet(PROCESSED / "osap_returns_op.parquet"), meta_osap),
        "OSAP VW": (pd.read_parquet(PROCESSED / "osap_returns_vw.parquet"), meta_osap),
        "JKP US": (pd.read_parquet(PROCESSED / "jkp_returns_usa.parquet"), meta_jkp),
    }


def part1(panels) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Survivor counts per panel and window, and the long per-factor t-stat table."""
    counts, per_factor = [], []
    for name, (returns, meta) in panels.items():
        windows = {"full sample": returns, "original sample": in_sample_returns(returns, meta)}
        for window, r in windows.items():
            t = factor_tstats(r)
            nw = factor_tstats(r, nw_lags=NW_LAGS)
            counts.append(
                {
                    "panel": name,
                    "window": window,
                    **survivor_counts(t),
                    f"HLZ t>3 (NW{NW_LAGS})": int(hlz_survivors(nw["t_stat"]).sum()),
                }
            )
            t = t.assign(
                t_stat_nw=nw["t_stat"],
                hlz=hlz_survivors(t["t_stat"]),
                by_fdr=by_fdr(t["p_one_sided"]),
            )
            per_factor.append(t.reset_index().assign(panel=name, window=window))
    long = pd.concat(per_factor, ignore_index=True)
    lead = ["panel", "window", "factor_id"]
    return pd.DataFrame(counts), long[lead + [c for c in long.columns if c not in lead]]


def tstat_replication(per_factor: pd.DataFrame) -> dict:
    """Compare OSAP op original-sample t-stats with the t-stats reported in the papers."""
    doc = pd.read_parquet(RAW / "osap_signal_doc.parquet").set_index("Acronym")["T-Stat"]
    ours = per_factor[
        (per_factor["panel"] == "OSAP op") & (per_factor["window"] == "original sample")
    ].set_index("factor_id")["t_stat"]
    both = pd.concat([ours, pd.to_numeric(doc, errors="coerce")], axis=1, join="inner").dropna()
    both.columns = ["ours", "paper"]
    return {
        "signals": len(both),
        "corr": round(both["ours"].corr(both["paper"]), 3),
        "median ours": round(both["ours"].median(), 2),
        "median paper": round(both["paper"].median(), 2),
        "share ours > 1.96": round((both["ours"] > 1.96).mean(), 3),
    }


def _decay_row(panel: str, spec: str, res: DecayResult) -> dict:
    return {
        "panel": panel,
        "spec": spec,
        "IS mean (%/mo)": round(100 * res.in_sample_mean, 3),
        "b post-sample": round(res.b_post_sample, 4),
        "t": round(res.t_post_sample, 2),
        "b post-pub": round(res.b_post_pub, 4),
        "t ": round(res.t_post_pub, 2),
        "post-sample %": f"{res.pct_post_sample:+.0%}",
        "post-pub %": f"{res.pct_post_pub:+.0%}",
        "MP post-sample": f"{MP_POST_SAMPLE:+.0%}",
        "MP post-pub": f"{MP_POST_PUB:+.0%}",
        "factors": res.n_factors,
        "months": res.n_months,
        "obs": res.n_obs,
    }


def part2(panels) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Decay regressions: OSAP op (primary), OSAP VW, JKP US, and OSAP op cut at 2013."""
    rows, dropped = [], {}
    for name, (returns, meta) in panels.items():
        panel = period_dummies(returns, meta)
        dropped[f"{name} (no dates)"] = panel.attrs["dropped"]
        for scaled in (False, True):
            res = decay_regression(panel, scaled=scaled)
            rows.append(_decay_row(name, "scaled" if scaled else "raw", res))
            if scaled:
                extra = sorted(set(res.dropped) - set(panel.attrs["dropped"]))
                dropped[f"{name} (scaled: IS mean <= 0 or t < 1)"] = extra
    returns, meta = panels["OSAP op"]
    cut = period_dummies(returns.loc[:MP_SAMPLE_END], meta)
    for scaled in (False, True):
        res = decay_regression(cut, scaled=scaled)
        rows.append(_decay_row("OSAP op to 2013", "scaled" if scaled else "raw", res))
    return pd.DataFrame(rows), dropped


def run() -> tuple[str, pd.DataFrame]:
    """Run Parts 1 and 2 and return the Markdown report and the per-factor t-stat table."""
    panels = load_panels()
    counts, per_factor = part1(panels)
    rep = tstat_replication(per_factor)
    decay, dropped = part2(panels)

    out = ["# Milestone 2: which factors are real, and how much do they decay?", ""]
    out += [
        "## Part 1: multiple testing",
        "",
        "One-sided tests (returns are signed in the published direction). HLZ is the",
        "Harvey-Liu-Zhu t > 3 hurdle; BY-FDR is Benjamini-Yekutieli at 5%. Original sample",
        "is each factor's in-sample period from the paper that introduced it.",
        "",
        md_table(counts),
        "",
        "### Replication check: OSAP op original-sample t vs t reported in the paper",
        "",
        md_table(pd.DataFrame([rep])),
        "",
        "## Part 2: post-publication decay (McLean and Pontiff 2016)",
        "",
        "`r_it = a_i + b1 PostSample_it + b2 PostPub_it + e_it`, factor fixed effects,",
        "standard errors clustered by month. Raw: decay % = b / pooled in-sample mean.",
        "Scaled: each factor's returns divided by its own in-sample mean, so b is the % change.",
        "OSAP op raw is the primary specification. MP columns are McLean and Pontiff's",
        "headline estimates.",
        "",
        md_table(decay),
        "",
        "### Dropped factors",
        "",
    ]
    for k, ids in dropped.items():
        out.append(f"- {k}: {len(ids)}" + (f" ({', '.join(ids)})" if ids else ""))
    out += ["", *GAP_NOTES, ""]
    return "\n".join(out), per_factor


# Written after reviewing the 2026-10-13 run. "Likely" marks causes that are not yet tested.
GAP_NOTES = [
    "## Comparison with McLean and Pontiff",
    "",
    "- Primary (OSAP op): post-publication decay matches closely (-55% raw, -58% scaled vs",
    "  -58%). Post-sample decay is larger in the raw spec (-37% vs -26%) and close in the",
    "  scaled spec (-29%). The raw spec divides pooled coefficients by the pooled in-sample",
    "  mean, so high-mean factors carry more weight; the scaled spec weights factors equally.",
    "- Post-sample window: publication and sample-end dates are year-level (December 31),",
    "  so months in the publication year count as post-sample. McLean and Pontiff use the",
    "  publication month. This likely moves some post-publication months into post-sample.",
    "- Longer sample: cutting OSAP op at 2013 lowers post-publication decay to -50% raw and",
    "  -48% scaled, so 2014 to 2024 adds decay. Our post-publication estimate on the full",
    "  sample is therefore not directly comparable to theirs.",
    "- OSAP VW: decay is larger (-68% raw post-publication). Value-weighted deciles have",
    "  lower in-sample means (0.53%/mo vs 0.67%/mo), and 50 factors fail the scaled-spec",
    "  filter, so that row covers a different factor set.",
    "- JKP US: post-sample decay is small and insignificant (-7% raw, t = -0.39), while",
    "  post-publication decay (-53%) is in line. Likely causes: capped value weighting",
    "  (in-sample mean only 0.27%/mo), and JKP's sample periods and citations, which follow",
    "  Hou-Xue-Zhang replications rather than the original papers.",
    "- Part 1: on original-paper construction, 122 of 212 OSAP signals clear t > 3 in their",
    "  own samples; on value-weighted deciles only 42 of 179 do. The gap is concentrated in",
    "  equal-weighted originals: for those 157 signals the median",
    "  original-sample t falls from 3.43 (op) to 1.62 (VW deciles); for the 22 originally",
    "  value-weighted it is unchanged (2.57 vs 2.54). Source: the doc's `Stock Weight`.",
]


def main() -> None:
    """Write ``results/m2_results.md`` and ``results/m2_factor_tstats.csv``."""
    report, per_factor = run()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "m2_results.md").write_text(report)
    per_factor.to_csv(RESULTS / "m2_factor_tstats.csv", index=False)
    print(report)


if __name__ == "__main__":
    main()
