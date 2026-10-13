import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from factor_alloc.testing import by_fdr, factor_tstats, hlz_survivors, in_sample_returns


def _idx(n, start="2000-01-31"):
    return pd.date_range(start, periods=n, freq="ME")


def test_tstat_matches_hand_calculation():
    r = pd.DataFrame({"a": [0.01, 0.03, -0.01, 0.05]}, index=_idx(4))
    t = factor_tstats(r).loc["a"]
    x = np.array([0.01, 0.03, -0.01, 0.05])
    expected = x.mean() / (x.std(ddof=1) / np.sqrt(4))
    assert t["t_stat"] == pytest.approx(expected)
    assert t["n_months"] == 4
    assert 0 < t["p_one_sided"] < 0.5


def test_tstat_ignores_missing_months_and_short_series():
    r = pd.DataFrame({"a": [0.01, np.nan, 0.03], "b": [np.nan, np.nan, 0.02]}, index=_idx(3))
    t = factor_tstats(r)
    assert t.loc["a", "n_months"] == 2
    assert np.isnan(t.loc["b", "t_stat"])


def test_newey_west_runs_and_differs_from_plain():
    rng = np.random.default_rng(0)
    r = pd.DataFrame({"a": rng.normal(0.01, 0.05, 120)}, index=_idx(120))
    plain = factor_tstats(r).loc["a", "t_stat"]
    nw = factor_tstats(r, nw_lags=6).loc["a", "t_stat"]
    assert np.isfinite(nw) and nw != pytest.approx(plain)


def test_hlz_is_one_sided():
    t = pd.Series([3.5, -4.0, 2.9])
    assert hlz_survivors(t).tolist() == [True, False, False]


def test_by_fdr_hand_example():
    # m = 4, c(m) = 1 + 1/2 + 1/3 + 1/4 = 25/12. Thresholds k * 0.05 / (4 * 25/12):
    # 0.006, 0.012, 0.018, 0.024. Sorted p: 0.001 and 0.010 pass, 0.03 and 0.2 fail.
    p = pd.Series([0.010, 0.2, 0.001, 0.03], index=list("abcd"))
    assert by_fdr(p).tolist() == [True, False, True, False]


def test_by_fdr_is_stricter_than_bh_and_skips_nan():
    p = pd.Series([0.001, 0.008, 0.012, 0.02, 0.04, np.nan])
    by = by_fdr(p)
    bh = multipletests(p.dropna(), alpha=0.05, method="fdr_bh")[0]
    assert by.dropna().iloc[:5].sum() <= bh.sum()
    assert not by.iloc[-1]
    # NaN does not count as a test: same result as without it.
    assert by.iloc[:5].tolist() == by_fdr(p.dropna()).tolist()


def test_in_sample_mask_boundaries():
    idx = pd.date_range("1999-11-30", "2001-02-28", freq="ME")
    r = pd.DataFrame({"a": 1.0, "b": 1.0}, index=idx)
    meta = pd.DataFrame(
        {
            "factor_id": ["a", "b"],
            "sample_start": pd.to_datetime(["2000-01-01", pd.NaT]),
            "sample_end": pd.to_datetime(["2000-12-31", "2000-12-31"]),
        }
    )
    out = in_sample_returns(r, meta)
    kept = out["a"].dropna().index
    assert kept.min() == pd.Timestamp("2000-01-31")
    assert kept.max() == pd.Timestamp("2000-12-31")
    assert out["b"].isna().all()
