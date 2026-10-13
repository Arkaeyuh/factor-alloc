"""Download raw data (OSAP, JKP, Ken French) and tidy it into wide monthly return panels.

Run as ``uv run python -m factor_alloc.ingest``. Downloads are skipped when the raw file
already exists, so a manually downloaded file in ``data/raw/`` is used as is.
"""

from __future__ import annotations

import re
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from factor_alloc import meta

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

FRENCH_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
FRENCH_FILES = {
    "ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
    "mom": "F-F_Momentum_Factor_CSV.zip",
}

JKP_BASE = "https://jkpfactors.s3.amazonaws.com/public"
JKP_REPO = "https://raw.githubusercontent.com/bkelly-lab/jkp-data/main/src/jkp/data/resources"
JKP_REGIONS = ["usa", "world_ex_us", "developed", "emerging", "frontier"]
JKP_WEIGHTING = "vw_cap"

# OSAP dataset names in openassetpricing. "deciles_vw" is the primary panel; "op" follows
# each original paper's construction and is kept for the decay analysis and robustness.
OSAP_VARIANTS = ["deciles_vw", "op"]
OSAP_FILE_TAG = {"deciles_vw": "vw", "op": "op"}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def to_month_end(dates) -> pd.DatetimeIndex:
    """Map any dates (or YYYYMM integers) to calendar month-end timestamps."""
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return idx.to_period("M").to_timestamp() + pd.offsets.MonthEnd(0)


def long_to_wide(
    df: pd.DataFrame, date_col: str, id_col: str, ret_col: str, scale: float = 1.0
) -> pd.DataFrame:
    """Pivot long returns to wide (index = month-end, columns = factor id), times ``scale``.

    Raises if a factor has two rows in the same month, since that signals a parsing error.
    """
    out = df[[date_col, id_col, ret_col]].copy()
    out[date_col] = to_month_end(out[date_col])
    dup = out.duplicated([date_col, id_col])
    if dup.any():
        raise ValueError(f"{dup.sum()} duplicate (date, factor) rows after month-end mapping")
    wide = out.pivot(index=date_col, columns=id_col, values=ret_col).sort_index()
    wide = wide.sort_index(axis=1) * scale
    wide.index.name = "date"
    wide.columns.name = "factor_id"
    return wide.astype(float)


def positive_mean_share(returns: pd.DataFrame) -> float:
    """Share of factors with a positive full-sample mean. Near 1 means returns are signed."""
    return float((returns.mean() > 0).mean())


def download_file(url: str, dest: Path, overwrite: bool = False) -> Path:
    """Download ``url`` to ``dest`` unless it already exists."""
    if dest.exists() and not overwrite:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(url, timeout=300)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Download failed for {url} ({exc}). Please download it manually to {dest}."
        ) from exc
    dest.write_bytes(resp.content)
    return dest


def _write(df: pd.DataFrame, name: str) -> Path:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / name
    df.to_parquet(path)
    return path


# ---------------------------------------------------------------------------
# Ken French
# ---------------------------------------------------------------------------


def parse_french_csv(text: str) -> pd.DataFrame:
    """Parse the monthly block of a Ken French CSV into decimal returns.

    The monthly block starts at the first header line (beginning with a comma) and ends at
    the first line that is not a ``YYYYMM,`` data row (a blank line or the annual block).
    """
    lines = text.replace("\r", "").split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith(","))
    cols = [c.strip() for c in lines[start].split(",")[1:]]
    rows = []
    for ln in lines[start + 1 :]:
        if not re.match(r"^\s*\d{6}\s*,", ln):
            break
        parts = [p.strip() for p in ln.split(",")]
        rows.append([parts[0], *map(float, parts[1:])])
    df = pd.DataFrame(rows, columns=["yyyymm", *cols])
    df.index = to_month_end(pd.to_datetime(df.pop("yyyymm"), format="%Y%m"))
    df.index.name = "date"
    df = df.replace([-99.99, -999.0], np.nan) / 100.0
    return df.rename(columns={"Mom": "UMD"})


def download_french() -> None:
    """Download the FF5 (2x3) and momentum zip files."""
    for fname in FRENCH_FILES.values():
        download_file(f"{FRENCH_BASE}/{fname}", RAW / "french" / fname)


def _read_zipped_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        (name,) = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        return zf.read(name).decode("latin-1")


def build_french() -> pd.DataFrame:
    """Build ``french_ff5_mom.parquet``: Mkt-RF, SMB, HML, RMW, CMA, RF, UMD."""
    ff5 = parse_french_csv(_read_zipped_text(RAW / "french" / FRENCH_FILES["ff5"]))
    mom = parse_french_csv(_read_zipped_text(RAW / "french" / FRENCH_FILES["mom"]))
    out = ff5.join(mom, how="outer")
    _write(out, "french_ff5_mom.parquet")
    return out


# ---------------------------------------------------------------------------
# OSAP (Chen and Zimmermann)
# ---------------------------------------------------------------------------


def download_osap() -> None:
    """Download the OSAP signal documentation and portfolio files via openassetpricing."""
    targets = {"doc": RAW / "osap_signal_doc.parquet"}
    targets |= {v: RAW / f"osap_port_{v}.parquet" for v in OSAP_VARIANTS}
    if all(p.exists() for p in targets.values()):
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # the wrds dependency emits SyntaxWarnings on import
        import openassetpricing as oap

        client = oap.OpenAP()
    try:
        if not targets["doc"].exists():
            client.dl_signal_doc("pandas").to_parquet(targets["doc"])
        for variant in OSAP_VARIANTS:
            if not targets[variant].exists():
                client.dl_port(variant, "pandas").to_parquet(targets[variant])
    except Exception as exc:
        raise RuntimeError(
            f"OSAP download failed ({exc}). Please download the signal documentation and "
            f"portfolio files manually into {RAW}."
        ) from exc


def build_osap() -> dict[str, pd.DataFrame]:
    """Build OSAP returns (one panel per variant) and ``meta_osap.parquet``.

    Keeps long-short portfolios (``port == "LS"``) of signals classified as Predictor.
    OSAP long-short returns are already signed in the published direction, so no flip.
    """
    doc = pd.read_parquet(RAW / "osap_signal_doc.parquet")
    predictors = set(doc.loc[doc["Cat.Signal"] == "Predictor", "Acronym"])
    out = {}
    for variant in OSAP_VARIANTS:
        port = pd.read_parquet(RAW / f"osap_port_{variant}.parquet")
        ls = port[(port["port"] == "LS") & port["signalname"].isin(predictors)]
        wide = long_to_wide(ls, "date", "signalname", "ret", scale=0.01)
        _write(wide, f"osap_returns_{OSAP_FILE_TAG[variant]}.parquet")
        out[variant] = wide
    m = meta.build_osap_meta(doc[doc["Cat.Signal"] == "Predictor"])
    _write(m, "meta_osap.parquet")
    out["meta"] = m
    return out


# ---------------------------------------------------------------------------
# JKP (Jensen, Kelly and Pedersen)
# ---------------------------------------------------------------------------


def _jkp_url(region: str, kind: str) -> str:
    return f"{JKP_BASE}/[{region}]_[{kind}]_[monthly]_[{JKP_WEIGHTING}].zip"


def _jkp_raw(region: str, kind: str) -> Path:
    return RAW / "jkp" / f"{region}_{kind}_monthly_{JKP_WEIGHTING}.zip"


def download_jkp() -> None:
    """Download JKP factor and market returns per region, plus factor metadata files."""
    for region in JKP_REGIONS:
        for kind in ("all_factors", "mkt"):
            download_file(_jkp_url(region, kind), _jkp_raw(region, kind))
    for fname in ("factor_details.xlsx", "cluster_labels.csv"):
        download_file(f"{JKP_REPO}/{fname}", RAW / "jkp" / fname)


def build_jkp() -> dict[str, pd.DataFrame]:
    """Build ``jkp_returns_<region>.parquet``, ``jkp_mkt.parquet`` and ``meta_jkp.parquet``.

    JKP factor returns are already signed in the published direction, so no flip.
    """
    out = {}
    mkt = {}
    for region in JKP_REGIONS:
        f = pd.read_csv(_jkp_raw(region, "all_factors"))
        wide = long_to_wide(f, "date", "name", "ret")
        _write(wide, f"jkp_returns_{region}.parquet")
        out[region] = wide
        m = pd.read_csv(_jkp_raw(region, "mkt"))
        mkt[region] = long_to_wide(m, "date", "name", "ret")["mkt"]
    mkt_df = pd.DataFrame(mkt)
    mkt_df.columns.name = "region"
    _write(mkt_df, "jkp_mkt.parquet")
    out["mkt"] = mkt_df
    details = pd.read_excel(RAW / "jkp" / "factor_details.xlsx")
    clusters = pd.read_csv(RAW / "jkp" / "cluster_labels.csv")
    m = meta.build_jkp_meta(details, clusters)
    _write(m, "meta_jkp.parquet")
    out["meta"] = m
    return out


def main() -> None:
    """Download everything, then build all processed files."""
    download_french()
    download_osap()
    download_jkp()
    build_french()
    build_osap()
    build_jkp()
    for p in sorted(PROCESSED.glob("*.parquet")):
        df = pd.read_parquet(p)
        print(f"{p.name:32s} {df.shape}")


if __name__ == "__main__":
    main()
