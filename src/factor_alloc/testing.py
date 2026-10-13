"""Part 1: which factors are real? t-stats, the Harvey-Liu-Zhu hurdle, and BY-FDR.

Returns are signed in the published direction, so every test is one-sided (H1: mean > 0).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests


def factor_tstats(returns: pd.DataFrame, nw_lags: int | None = None) -> pd.DataFrame:
    """Per-factor mean, t-stat and one-sided p-value over each factor's non-missing months.

    With ``nw_lags`` set, the t-stat uses Newey-West standard errors with that many lags.
    Factors with fewer than 2 months get NaN.
    """
    rows = {}
    for fid, r in returns.items():
        r = r.dropna()
        n = len(r)
        if n < 2:
            rows[fid] = {"n_months": n, "mean": np.nan, "t_stat": np.nan, "p_one_sided": np.nan}
            continue
        if nw_lags is None:
            t = r.mean() / (r.std(ddof=1) / np.sqrt(n))
        else:
            fit = sm.OLS(r.to_numpy(), np.ones(n)).fit(
                cov_type="HAC", cov_kwds={"maxlags": nw_lags}
            )
            t = fit.tvalues[0]
        rows[fid] = {
            "n_months": n,
            "mean": r.mean(),
            "t_stat": t,
            "p_one_sided": stats.t.sf(t, df=n - 1),
        }
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "factor_id"
    return out


def hlz_survivors(t: pd.Series, hurdle: float = 3.0) -> pd.Series:
    """True where the t-stat clears the Harvey-Liu-Zhu hurdle (one-sided: t > hurdle)."""
    return t > hurdle


def by_fdr(p: pd.Series, alpha: float = 0.05) -> pd.Series:
    """Benjamini-Yekutieli FDR rejections at level ``alpha``. NaN p-values are not rejected
    and do not count toward the number of tests."""
    out = pd.Series(False, index=p.index)
    valid = p.dropna()
    if len(valid):
        reject, *_ = multipletests(valid.to_numpy(), alpha=alpha, method="fdr_by")
        out.loc[valid.index] = reject
    return out


def in_sample_returns(returns: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Mask months outside each factor's original sample ``[sample_start, sample_end]``.

    Factors with no metadata row or a missing sample bound are fully masked.
    """
    m = meta.set_index("factor_id").reindex(returns.columns)
    dates = returns.index.to_numpy()[:, None]
    start = m["sample_start"].to_numpy()[None, :]
    end = m["sample_end"].to_numpy()[None, :]
    mask = (dates >= start) & (dates <= end)
    return returns.where(mask)


def survivor_counts(t: pd.DataFrame, alpha: float = 0.05) -> dict:
    """Counts of factors clearing t > 1.96, the HLZ t > 3 hurdle, and BY-FDR at ``alpha``.

    ``t`` is the output of ``factor_tstats``.
    """
    valid = t["t_stat"].notna()
    return {
        "factors": int(valid.sum()),
        "t>1.96": int((t["t_stat"] > 1.96).sum()),
        "HLZ t>3": int(hlz_survivors(t["t_stat"]).sum()),
        f"BY-FDR {alpha:.0%}": int(by_fdr(t["p_one_sided"], alpha).sum()),
    }
