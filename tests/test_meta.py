import numpy as np
import pandas as pd

from factor_alloc.meta import (
    META_COLUMNS,
    build_jkp_meta,
    build_osap_meta,
    parse_cite_year,
    parse_period,
    year_to_pub_date,
)


def test_year_to_pub_date_is_dec31_and_nat_when_missing():
    out = year_to_pub_date([2001, np.nan, 1981.0])
    assert out.iloc[0] == pd.Timestamp("2001-12-31")
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == pd.Timestamp("1981-12-31")


def test_parse_cite_year():
    assert parse_cite_year("Banz (1981)") == 1981
    assert parse_cite_year("Chan Jegadeesh and Lakonishok (1996) 1976/7") == 1996
    assert np.isnan(parse_cite_year(np.nan))
    assert np.isnan(parse_cite_year("no year here"))


def test_parse_period():
    assert parse_period("1963 - 2013") == (1963, 2013)
    assert parse_period("1971-1992") == (1971, 1992)
    assert all(np.isnan(x) for x in parse_period(None))


def test_build_osap_meta_schema():
    doc = pd.DataFrame(
        {
            "Acronym": ["BM", "Mom12m"],
            "LongDescription": ["Book to market", "Momentum"],
            "Cat.Economic": ["valuation", "momentum"],
            "SampleStartYear": [1963, 1965],
            "SampleEndYear": [1990, 1989],
            "Year": [1992, np.nan],
            "Sign": [1.0, 1.0],
        }
    )
    m = build_osap_meta(doc)
    assert list(m.columns) == META_COLUMNS
    assert (m["source"] == "osap").all()
    row = m.set_index("factor_id").loc["BM"]
    assert row["pub_date"] == pd.Timestamp("1992-12-31")
    assert row["sample_start"] == pd.Timestamp("1963-01-01")
    assert row["sample_end"] == pd.Timestamp("1990-12-31")
    assert pd.isna(m.set_index("factor_id").loc["Mom12m", "pub_date"])


def test_build_jkp_meta_schema():
    details = pd.DataFrame(
        {
            "abr_jkp": ["be_me", "market_equity", np.nan],
            "name_new": ["Book to market", "Size", "Unused"],
            "cite": ["Rosenberg et al. (1985)", "Banz (1981)", "X (2000)"],
            "in-sample period": ["1973 - 1984", "1926 - 1975", "1990 - 1999"],
            "direction": [1.0, -1.0, 1.0],
        }
    )
    clusters = pd.DataFrame(
        {"characteristic": ["be_me", "market_equity"], "cluster": ["Value", "Size"]}
    )
    m = build_jkp_meta(details, clusters)
    assert list(m.columns) == META_COLUMNS
    assert len(m) == 2
    row = m.set_index("factor_id").loc["market_equity"]
    assert row["theme"] == "Size"
    assert row["direction"] == -1
    assert row["pub_date"] == pd.Timestamp("1981-12-31")


def test_jkp_overrides_fill_only_missing_cites():
    details = pd.DataFrame(
        {
            "abr_jkp": ["op_at", "gp_atl1"],
            "name_new": ["Operating profits-to-book assets", "Gross profits-to-lagged assets"],
            "cite": ["Someone (1999)", np.nan],
            "in-sample period": ["1963 - 2013", "1967 - 2016"],
            "direction": [1.0, 1.0],
        }
    )
    clusters = pd.DataFrame({"characteristic": [], "cluster": []})
    m = build_jkp_meta(details, clusters).set_index("factor_id")
    # A parsed citation year wins over the override table.
    assert m.loc["op_at", "pub_date"] == pd.Timestamp("1999-12-31")
    assert m.loc["gp_atl1", "pub_date"] == pd.Timestamp("2020-12-31")
