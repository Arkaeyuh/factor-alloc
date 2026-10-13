"""Factor metadata tables with a common schema for OSAP and JKP.

Schema: factor_id, source, name, theme, sample_start, sample_end, pub_date, direction.
When only a publication year is known, pub_date is December 31 of that year (conservative).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

META_COLUMNS = [
    "factor_id",
    "source",
    "name",
    "theme",
    "sample_start",
    "sample_end",
    "pub_date",
    "direction",
]


def year_to_pub_date(year) -> pd.Series:
    """Map publication years to December 31 of that year; missing years become NaT."""
    y = pd.to_numeric(pd.Series(year), errors="coerce")
    return pd.to_datetime({"year": y, "month": 12, "day": 31}, errors="coerce").where(y.notna())


def year_to_start(year) -> pd.Series:
    """Map years to January 1 of that year; missing years become NaT."""
    y = pd.to_numeric(pd.Series(year), errors="coerce")
    return pd.to_datetime({"year": y, "month": 1, "day": 1}, errors="coerce").where(y.notna())


def parse_cite_year(cite) -> float:
    """Extract the publication year from a citation like ``Banz (1981)``."""
    if not isinstance(cite, str):
        return np.nan
    m = re.search(r"\((\d{4})", cite) or re.search(r"\b(19\d{2}|20\d{2})\b", cite)
    return float(m.group(1)) if m else np.nan


def parse_period(period) -> tuple[float, float]:
    """Parse an in-sample period like ``1963 - 2013`` into (start_year, end_year)."""
    if not isinstance(period, str):
        return (np.nan, np.nan)
    years = re.findall(r"\d{4}", period)
    if len(years) < 2:
        return (np.nan, np.nan)
    return (float(years[0]), float(years[1]))


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    df = df[META_COLUMNS].sort_values("factor_id").reset_index(drop=True)
    df["direction"] = df["direction"].astype("Int64")
    return df


def build_osap_meta(doc: pd.DataFrame) -> pd.DataFrame:
    """Build OSAP metadata from the signal documentation table."""
    out = pd.DataFrame(
        {
            "factor_id": doc["Acronym"].to_numpy(),
            "source": "osap",
            "name": doc["LongDescription"].to_numpy(),
            "theme": doc["Cat.Economic"].to_numpy(),
            "sample_start": year_to_start(doc["SampleStartYear"].to_numpy()),
            "sample_end": year_to_pub_date(doc["SampleEndYear"].to_numpy()),
            "pub_date": year_to_pub_date(doc["Year"].to_numpy()),
            "direction": doc["Sign"].to_numpy(),
        }
    )
    return _finish(out)


def build_jkp_meta(details: pd.DataFrame, clusters: pd.DataFrame) -> pd.DataFrame:
    """Build JKP metadata from ``factor_details.xlsx`` and ``cluster_labels.csv``.

    Uses only JKP's own metadata (no matching to OSAP signals).
    """
    d = details[details["abr_jkp"].notna()].copy()
    periods = d["in-sample period"].map(parse_period)
    theme = clusters.set_index("characteristic")["cluster"]
    out = pd.DataFrame(
        {
            "factor_id": d["abr_jkp"].to_numpy(),
            "source": "jkp",
            "name": d["name_new"].to_numpy(),
            "theme": d["abr_jkp"].map(theme).to_numpy(),
            "sample_start": year_to_start([p[0] for p in periods]),
            "sample_end": year_to_pub_date([p[1] for p in periods]),
            "pub_date": year_to_pub_date(d["cite"].map(parse_cite_year).to_numpy()),
            "direction": d["direction"].to_numpy(),
        }
    )
    return _finish(out)
