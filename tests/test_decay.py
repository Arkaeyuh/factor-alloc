import numpy as np
import pandas as pd
import pytest

from factor_alloc.decay import decay_regression, period_dummies


def _meta(ids, start, end, pub):
    return pd.DataFrame(
        {
            "factor_id": ids,
            "sample_start": pd.to_datetime(start),
            "sample_end": pd.to_datetime(end),
            "pub_date": pd.to_datetime(pub),
        }
    )


def test_period_dummy_boundaries():
    idx = pd.date_range("1989-11-30", "1993-01-31", freq="ME")
    r = pd.DataFrame({"a": 0.01}, index=idx)
    meta = _meta(["a"], ["1990-01-01"], ["1990-12-31"], ["1992-12-31"])
    p = period_dummies(r, meta).set_index("date")
    assert p.index.min() == pd.Timestamp("1990-01-31")  # pre-sample months dropped
    assert p.loc["1990-12-31", ["post_sample", "post_pub"]].tolist() == [0, 0]
    assert p.loc["1991-01-31", ["post_sample", "post_pub"]].tolist() == [1, 0]
    assert p.loc["1992-12-31", ["post_sample", "post_pub"]].tolist() == [1, 0]
    assert p.loc["1993-01-31", ["post_sample", "post_pub"]].tolist() == [0, 1]


def test_factors_without_pub_date_are_dropped():
    idx = pd.date_range("1990-01-31", periods=24, freq="ME")
    r = pd.DataFrame({"a": 0.01, "b": 0.01, "c": 0.01}, index=idx)
    meta = _meta(["a", "b"], ["1990-01-01"] * 2, ["1990-12-31"] * 2, ["1990-12-31", None])
    p = period_dummies(r, meta)
    assert set(p["factor_id"]) == {"a"}
    assert p.attrs["dropped"] == ["b", "c"]


def _synthetic_panel(seed=0):
    """Three factors with in-sample, post-sample and post-pub means 1.0, 0.7 and 0.4 times
    each factor's own scale, staggered dates, and small noise."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1970-01-31", "2010-12-31", freq="ME")
    specs = {
        "a": (0.010, "1970-01-01", "1979-12-31", "1984-12-31"),
        "b": (0.010, "1975-01-01", "1989-12-31", "1994-12-31"),
        "c": (0.010, "1972-01-01", "1985-12-31", "1990-12-31"),
    }
    cols = {}
    for fid, (mu, _s, e, pub) in specs.items():
        level = np.where(idx <= e, mu, np.where(idx <= pub, 0.7 * mu, 0.4 * mu))
        cols[fid] = level + rng.normal(0, 1e-5, len(idx))
    r = pd.DataFrame(cols, index=idx)
    meta = _meta(
        list(specs), [v[1] for v in specs.values()], [v[2] for v in specs.values()],
        [v[3] for v in specs.values()],
    )
    return period_dummies(r, meta)


@pytest.mark.parametrize("scaled", [False, True])
def test_decay_regression_recovers_known_decay(scaled):
    res = decay_regression(_synthetic_panel(), scaled=scaled)
    assert res.pct_post_sample == pytest.approx(-0.3, abs=1e-3)
    assert res.pct_post_pub == pytest.approx(-0.6, abs=1e-3)
    assert res.n_factors == 3
    assert res.t_post_pub < -10
