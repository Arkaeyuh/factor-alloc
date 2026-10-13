"""Part 2: post-publication decay, after McLean and Pontiff (2016).

Panel regression ``r_it = a_i + b1 * PostSample_it + b2 * PostPub_it + e_it`` with factor
fixed effects and standard errors clustered by month.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm


def period_dummies(returns: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Long panel ``date, factor_id, ret, post_sample, post_pub`` for the decay regression.

    in-sample: ``sample_start <= date <= sample_end``; post-sample:
    ``sample_end < date <= pub_date``; post-pub: ``date > pub_date``. Months before
    ``sample_start`` are dropped. Factors missing a metadata row or any of the three dates
    are dropped; their ids are in ``panel.attrs["dropped"]``.
    """
    m = meta.set_index("factor_id")[["sample_start", "sample_end", "pub_date"]]
    m = m.reindex(returns.columns)
    complete = m.notna().all(axis=1)
    dropped = sorted(m.index[~complete])

    wide = returns.loc[:, complete.to_numpy()].rename_axis(index="date", columns="factor_id")
    long = wide.reset_index().melt(id_vars="date", var_name="factor_id", value_name="ret")
    long = long.dropna(subset=["ret"])
    long = long.join(m, on="factor_id")
    long = long[long["date"] >= long["sample_start"]]
    long["post_sample"] = (
        (long["date"] > long["sample_end"]) & (long["date"] <= long["pub_date"])
    ).astype(float)
    long["post_pub"] = (long["date"] > long["pub_date"]).astype(float)
    panel = long[["date", "factor_id", "ret", "post_sample", "post_pub"]].reset_index(drop=True)
    panel.attrs["dropped"] = dropped
    return panel


@dataclass
class DecayResult:
    """Decay regression estimates. ``pct_*`` are coefficients over the in-sample mean."""

    b_post_sample: float
    b_post_pub: float
    se_post_sample: float
    se_post_pub: float
    in_sample_mean: float
    n_obs: int
    n_factors: int
    n_months: int
    dropped: list[str] = field(default_factory=list)

    @property
    def t_post_sample(self) -> float:
        return self.b_post_sample / self.se_post_sample

    @property
    def t_post_pub(self) -> float:
        return self.b_post_pub / self.se_post_pub

    @property
    def pct_post_sample(self) -> float:
        return self.b_post_sample / self.in_sample_mean

    @property
    def pct_post_pub(self) -> float:
        return self.b_post_pub / self.in_sample_mean


def scale_by_in_sample_mean(panel: pd.DataFrame, min_t: float = 1.0) -> pd.DataFrame:
    """Divide each factor's returns by its own in-sample mean.

    Factors whose in-sample mean is not positive or whose in-sample t-stat is below
    ``min_t`` are dropped (dividing by a near-zero mean explodes the scaled returns); their
    ids are appended to ``attrs["dropped"]``.
    """
    ins = panel[(panel["post_sample"] == 0) & (panel["post_pub"] == 0)]
    g = ins.groupby("factor_id")["ret"]
    mean, sd, n = g.mean(), g.std(ddof=1), g.count()
    t = mean / (sd / np.sqrt(n))
    keep = mean[(mean > 0) & (t >= min_t)].index
    out = panel[panel["factor_id"].isin(keep)].copy()
    out["ret"] = out["ret"] / out["factor_id"].map(mean)
    all_ids = set(panel["factor_id"])
    out.attrs["dropped"] = list(panel.attrs.get("dropped", [])) + sorted(all_ids - set(keep))
    return out


def decay_regression(panel: pd.DataFrame, scaled: bool = False) -> DecayResult:
    """Fit the McLean-Pontiff decay regression on a ``period_dummies`` panel.

    Factor fixed effects are absorbed by demeaning ``ret`` and both dummies within factor;
    the regression has no constant and month-clustered standard errors. The absorbed fixed
    effects are not counted in the degrees of freedom, a minor difference under clustering.
    With ``scaled=True``, returns are first divided by each factor's in-sample mean
    (``scale_by_in_sample_mean``), so the coefficients are fractions of that mean.
    """
    if scaled:
        panel = scale_by_in_sample_mean(panel)
    cols = ["ret", "post_sample", "post_pub"]
    demeaned = panel[cols] - panel.groupby("factor_id")[cols].transform("mean")
    fit = sm.OLS(demeaned["ret"], demeaned[["post_sample", "post_pub"]]).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(panel["date"])[0]}
    )
    in_sample = (panel["post_sample"] == 0) & (panel["post_pub"] == 0)
    return DecayResult(
        b_post_sample=fit.params["post_sample"],
        b_post_pub=fit.params["post_pub"],
        se_post_sample=fit.bse["post_sample"],
        se_post_pub=fit.bse["post_pub"],
        in_sample_mean=panel.loc[in_sample, "ret"].mean(),
        n_obs=len(panel),
        n_factors=panel["factor_id"].nunique(),
        n_months=panel["date"].nunique(),
        dropped=list(panel.attrs.get("dropped", [])),
    )
