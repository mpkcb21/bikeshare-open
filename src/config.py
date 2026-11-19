"""Single source of truth for paths, columns, and split dates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bike_daily.csv"
PROCESSED = ROOT / "data" / "processed" / "features.parquet"
METRICS = ROOT / "reports" / "metrics.json"

# Daily Capital Bikeshare counts (Fanaee-T & Gama). Canonical home:
#   https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
# We use the processed copy from Molnar's "Interpretable Machine Learning"
# because the UCI host blocks some campus networks. It differs from UCI:
#   - 728 rows, 2011-01-03 to 2012-12-31 (UCI has 731 from 2011-01-01)
#   - 2011-03-10 is absent (the UCI row records humidity 0, a sensor
#     artefact, and the mirror's cleaning dropped the whole day)
#   - `weather` is the labels GOOD / MISTY / BAD, not UCI's codes 1-4
#   - two extra columns: `days_since_2011` and `cnt_2d_bfr`
DATA_URL = (
    "https://raw.githubusercontent.com/christophM/"
    "interpretable-ml-book/master/data/bike.csv"
)

# First 16 hex chars of the sha256 of the committed raw CSV. load_raw()
# refuses any file that does not match, so an edit to data/raw/bike_daily.csv
# (by hand, by a tool, or by a changed upstream mirror) fails `make data` and
# every test that loads the raw data. Change this only after deciding, on
# purpose, that the new file is the one we want.
EXPECTED_RAW_SHA256_PREFIX = "a6bed1577f6e4de5"

TARGET = "cnt"

# --- Three reasons a column is kept out of the feature set --------------

# 1. Leakage: the target or an arithmetic restatement of it.
#    casual + registered == cnt exactly, on every row. A model handed these
#    scores R^2 ~ 1.0 and has learned addition. At prediction time you would
#    not know either input: they are components of the thing being predicted.
LEAKAGE_COLS = {"casual", "registered", "cnt"}

# 2. Time indexes: not leakage, but a bad bet. A tree splits on "after date
#    X" and predicts a flat constant for every future date; a linear model
#    extrapolates a two-year trend we have no reason to trust. Excluding
#    them keeps the model comparison about what each does with lagged demand.
TIME_INDEX_COLS = {"instant", "yr", "days_since_2011"}

# 3. Unverified: `cnt_2d_bfr` is a two-day lag of cnt that shipped with the
#    mirror. It is NOT leakage -- a two-day-old count is known at prediction
#    time -- but we did not build it and cannot test how it was aligned, so we
#    build our own lags from the target and test those instead.
UNVERIFIED_COLS = {"cnt_2d_bfr"}

# 4. Redundant: string labels restating calendar facts that build_features
#    derives from dteday itself (month_sin/cos, dayofweek). Not leakage; we
#    simply do not read them, and listing them here means a new raw column
#    cannot slip in unclassified (tests/test_contract.py).
REDUNDANT_COLS = {"season", "mnth", "weekday"}

# What feature_columns() and the tests actually enforce.
FORBIDDEN = LEAKAGE_COLS | TIME_INDEX_COLS | UNVERIFIED_COLS | REDUNDANT_COLS

# Every raw column build_features reads, whether passed through unchanged
# (temp, hum, ...) or transformed (holiday -> is_holiday, weather ->
# weather_severity). This is a raw-column allowlist, not the feature list:
# feature_columns() still derives that from FORBIDDEN. It must be explicit
# because feature_columns() admits any numeric non-FORBIDDEN column, so a new
# numeric upstream column would otherwise classify itself as a "feature".
FEATURE_INPUT_COLS = {
    "temp", "atemp", "hum", "windspeed",
    "holiday", "workday", "weather",
}

# Temporal split: train on 2011, validate on H1 2012, test on H2 2012.
TRAIN_END = "2011-12-31"
VALID_END = "2012-06-30"

# Longest lag window in src/features.py. The first LAG_WARMUP calendar days
# have no complete history and are dropped; tests/test_contract.py uses this
# to bound how many rows may legitimately disappear.
LAG_WARMUP = 7
