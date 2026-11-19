"""Stage 1: fetch the raw dataset and assert its shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

import pandas as pd

from src import config
from src.config import DATA_URL, RAW

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def check_raw_hash(path: Path) -> None:
    """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
    expected = config.EXPECTED_RAW_SHA256_PREFIX
    actual = sha256_of(path)
    if not actual.startswith(expected):
        raise AssertionError(
            f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
            f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
            f"file has changed; restore it (git checkout -- {path.name}) or, if "
            f"the change is intended, review it and update the prefix."
        )


def load_raw() -> pd.DataFrame:
    # config.RAW is read at call time (not the import-time RAW) so tests can
    # point the loader at a copy.
    path = config.RAW
    check_raw_hash(path)
    df = pd.read_csv(path, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
