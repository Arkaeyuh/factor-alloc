import numpy as np
import pandas as pd
import pytest

from factor_alloc.ingest import long_to_wide, parse_french_csv, positive_mean_share, to_month_end

FRENCH_SAMPLE = (
    "This file was created using the 202608 CRSP database.\r\n"
    "\r\n"
    ",Mkt-RF,SMB,HML\r\n"
    "196307,   -0.39,   -0.48,   -0.84\r\n"
    "196308,    5.08,  -99.99,    1.72\r\n"
    "\r\n"
    " Annual Factors: January-December \r\n"
    ",Mkt-RF,SMB,HML\r\n"
    "  1964,   12.59,    0.52,    9.72\r\n"
)


def test_parse_french_monthly_block_only():
    df = parse_french_csv(FRENCH_SAMPLE)
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML"]
    assert list(df.index) == [pd.Timestamp("1963-07-31"), pd.Timestamp("1963-08-31")]
    assert df.loc["1963-07-31", "Mkt-RF"] == pytest.approx(-0.0039)
    assert np.isnan(df.loc["1963-08-31", "SMB"])


def test_parse_french_renames_mom():
    text = ",Mom\n192701,   0.57\n\nAnnual Factors:\n,Mom\n  1927, 1.0\n"
    df = parse_french_csv(text)
    assert list(df.columns) == ["UMD"]
    assert df.iloc[0, 0] == pytest.approx(0.0057)


def test_to_month_end_maps_trading_days():
    idx = to_month_end(["1951-09-28", "2024-02-29", "2024-03-01"])
    assert list(idx) == [
        pd.Timestamp("1951-09-30"),
        pd.Timestamp("2024-02-29"),
        pd.Timestamp("2024-03-31"),
    ]


def test_long_to_wide_aligns_and_scales():
    long = pd.DataFrame(
        {
            "date": ["2000-01-31", "2000-02-29", "2000-01-28"],
            "id": ["a", "a", "b"],
            "ret": [1.0, 2.0, 3.0],
        }
    )
    wide = long_to_wide(long, "date", "id", "ret", scale=0.01)
    assert list(wide.columns) == ["a", "b"]
    assert wide.loc["2000-01-31", "b"] == pytest.approx(0.03)
    assert np.isnan(wide.loc["2000-02-29", "b"])
    assert wide.index.is_monotonic_increasing


def test_long_to_wide_rejects_duplicate_months():
    long = pd.DataFrame({"date": ["2000-01-28", "2000-01-31"], "id": ["a", "a"], "ret": [1.0, 2.0]})
    with pytest.raises(ValueError, match="duplicate"):
        long_to_wide(long, "date", "id", "ret")


def test_positive_mean_share():
    df = pd.DataFrame({"a": [0.01, 0.02], "b": [-0.01, -0.03], "c": [0.0, 0.01]})
    assert positive_mean_share(df) == pytest.approx(2 / 3)
