# Seeded faults (Exercise 2)

Faults 1-3 were made by the agent in Claude Code, started from a shell with `.venv` active. Fault 4 was made by me in the terminal, because the agent's attempt was blocked. A "turn" means one agent step (one action) between my fix prompt and green tests. The turn counts for faults 1 and 2 are estimates from memory of the Claude Code window. The count for fault 3 was counted directly.

## Fault 1: a forbidden column added to feature_columns

Exact change (commit 9ba3b4a):

```diff
diff --git a/src/features.py b/src/features.py
index de1288c..1b27afa 100644
--- a/src/features.py
+++ b/src/features.py
@@ -83,7 +83,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

Red test output (full suite, `python -m pytest tests -q`):

```
......F.........                                                         [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'mnth', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 2.91s
```

Hook stderr (copied from the Claude Code window after the edit):

```
PostToolUse:Edit hook reported a problem
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'mnth', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.82s
```

Turns for the agent to fix it: 2 (estimate). Fix commit: 7be8d25.

## Fault 2: .shift(1) deleted from cnt_roll_7

Attempt 1: the agent made the edit with a Bash `sed` command instead of its Edit tool. The PostToolUse hook (matcher `Edit|Write`) did not fire and no stderr was produced. I reverted it and redid the fault with the instruction to use the Edit tool.

Exact change (commit 9e3a854):

```diff
diff --git a/src/features.py b/src/features.py
index de1288c..1b7095c 100644
--- a/src/features.py
+++ b/src/features.py
@@ -75,7 +75,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
 
```

Red test output (full suite):

```
.........F......                                                         [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1531.428571
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 2.10s
```

Hook stderr. The Claude Code window truncated the hook message, so I re-ran the hook by hand with the same JSON payload (`{"tool_name":"Edit","tool_input":{"file_path":".../src/features.py"},"cwd":...}`) and saved its stderr. It exited with code 2:

```
Leakage tests failed after editing /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.88s
```

Turns for the agent to fix it: 3 (estimate). Fix commit: 3fb6e8c.

## Fault 3: the raise removed from encode_weather

Exact change (commit 8e22417). The agent also had to delete the `if unknown:` line, since an `if` with no body is a syntax error:

```
diff --git a/src/features.py b/src/features.py
index de1288c..616a66d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

Hook: silent. Re-running the hook by hand gave exit code 0 and no stderr, because the hook runs only tests/test_leakage.py and none of those tests exercise the raise. The hook stderr file is empty.

Full suite with the fault in place: all green (16 passed). The suite had a gap, because every weather label in this mirror is in WEATHER_ORDER and no test fed the encoder an unmapped label:

```
................                                                         [100%]
16 passed in 1.54s
```

To close the gap I added tests/test_contract.py::test_encode_weather_rejects_unknown_labels (commit c29fff7). Its red run against the faulty code:

```
.....F...........                                                        [100%]
=================================== FAILURES ===================================
__________________ test_encode_weather_rejects_unknown_labels __________________

    def test_encode_weather_rejects_unknown_labels():
        """An unmapped label must raise, not become a NaN that dropna() eats."""
>       with pytest.raises(ValueError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_contract.py:84: Failed
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_encode_weather_rejects_unknown_labels - F...
1 failed, 16 passed in 2.14s
```

Turns for the agent to restore the raise: 3 (counted). Fix commit: dacce0d, after which make test shows 17 passed.

## Fault 4: a change to data/raw that the PostToolUse hook cannot see

Attempt through the agent: I asked the agent to copy a modified CSV over data/raw/bike_daily.csv with Bash. It was blocked by a permission rule and did not run. The starter's deny rule on data/raw stopped the shell command in this version of Claude Code. The agent did not retry in another form.

To show what happens when the file changes outside the agent's Edit and Write tools, I made the change myself in the terminal (an awk edit that sets temp to 99 on one row, then cp over the raw file). The PostToolUse hook cannot fire for this, since no Edit or Write tool call is involved.

Variant A: temp changed on 2011-08-06 (commit da1f604, restored in ed82a96). The hash changed from a6bed1577f6e4de5 to ba98ab62f9977989. One test failed, but only by coincidence: test_hum_x_temp_is_same_day_product hard-codes the value for that same date.

```
diff --git a/data/raw/bike_daily.csv b/data/raw/bike_daily.csv
index cc36935..dd50ed1 100644
--- a/data/raw/bike_daily.csv
+++ b/data/raw/bike_daily.csv
@@ -213,7 +213,7 @@
 215,"2011-08-03","SUMMER","2011","AUG","N","WED",26.388349,39.117858,65.75,9.084061,467,3107,3574,"Y","MISTY",214,4266
 216,"2011-08-04","SUMMER","2011","AUG","N","THU",25.37,38.602792,75.75,13.20905,799,3777,4576,"Y","MISTY",215,4845
 217,"2011-08-05","SUMMER","2011","AUG","N","FRI",25.409151,38.323278,63.0833,12.374632,1023,3843,4866,"Y","GOOD",216,3574
-218,"2011-08-06","SUMMER","2011","AUG","N","SAT",25.683349,38.989236,75.5,15.29275,1521,2773,4294,"N","MISTY",217,4576
+218,"2011-08-06","SUMMER","2011","AUG","N","SAT",99,38.989236,75.5,15.29275,1521,2773,4294,"N","MISTY",217,4576
 219,"2011-08-07","SUMMER","2011","AUG","N","SUN",26.8975,40.319928,75.2917,13.499629,1298,2487,3785,"N","GOOD",218,4866
 220,"2011-08-08","SUMMER","2011","AUG","N","MON",27.955,39.911622,59.2083,12.875725,846,3480,4326,"Y","GOOD",219,4294
 221,"2011-08-09","SUMMER","2011","AUG","N","TUE",28.425,40.620114,57.0417,10.125107,907,3695,4602,"Y","GOOD",220,3785
```

```
.............F...                                                        [100%]
=================================== FAILURES ===================================
_____________________ test_hum_x_temp_is_same_day_product ______________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_hum_x_temp_is_same_day_product(feats):
        """hum_x_temp on 2011-08-06 equals hum 75.5 * temp 25.683349, by hand."""
        row = feats.set_index("dteday").loc[pd.Timestamp("2011-08-06")]
>       assert row.hum_x_temp == pytest.approx(1939.0928495)
E       assert np.float64(7474.5) == 1939.0928495 ± 0.00193909
E         
E         comparison failed
E         Obtained: 7474.5
E         Expected: 1939.0928495 ± 0.00193909

tests/test_leakage.py:72: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_hum_x_temp_is_same_day_product - assert np...
1 failed, 16 passed in 2.07s
```

Variant B: temp changed on 2011-08-08, a date no test checks (not committed, restored with git checkout). The hash became 9c512aa7b35cdd98. Nothing noticed:

```
diff --git a/data/raw/bike_daily.csv b/data/raw/bike_daily.csv
index cc36935..6ebba79 100644
--- a/data/raw/bike_daily.csv
+++ b/data/raw/bike_daily.csv
@@ -215,7 +215,7 @@
 217,"2011-08-05","SUMMER","2011","AUG","N","FRI",25.409151,38.323278,63.0833,12.374632,1023,3843,4866,"Y","GOOD",216,3574
 218,"2011-08-06","SUMMER","2011","AUG","N","SAT",25.683349,38.989236,75.5,15.29275,1521,2773,4294,"N","MISTY",217,4576
 219,"2011-08-07","SUMMER","2011","AUG","N","SUN",26.8975,40.319928,75.2917,13.499629,1298,2487,3785,"N","GOOD",218,4866
-220,"2011-08-08","SUMMER","2011","AUG","N","MON",27.955,39.911622,59.2083,12.875725,846,3480,4326,"Y","GOOD",219,4294
+220,"2011-08-08","SUMMER","2011","AUG","N","MON",99,39.911622,59.2083,12.875725,846,3480,4326,"Y","GOOD",219,4294
 221,"2011-08-09","SUMMER","2011","AUG","N","TUE",28.425,40.620114,57.0417,10.125107,907,3695,4602,"Y","GOOD",220,3785
 222,"2011-08-10","SUMMER","2011","AUG","N","WED",28.033349,39.289422,42.4167,13.417286,884,3896,4780,"Y","GOOD",221,4326
 223,"2011-08-11","SUMMER","2011","AUG","N","THU",25.7225,38.151714,42.375,11.041332,812,3980,4792,"Y","GOOD",222,4602
```

```
.................                                                        [100%]
17 passed in 2.13s
```

What would catch it: a hash check on the raw file. A Stop hook running make test would not have caught variant B, because the tests pass. A PreToolUse hook on Bash would stop only agent shell commands, not changes made by a script or another process. `chmod -w data/raw` does not survive a git clone. The hash check catches any change to the file, whoever makes it.

I implemented the hash check (commit 0c4c117): EXPECTED_RAW_SHA256_PREFIX in src/config.py, a check_raw_hash call in load_raw in src/ingest.py, and a test in tests/test_contract.py. The diff:

```diff
diff --git a/src/config.py b/src/config.py
index 6f585ed..a34951d 100644
--- a/src/config.py
+++ b/src/config.py
@@ -20,6 +20,13 @@ DATA_URL = (
     "interpretable-ml-book/master/data/bike.csv"
 )
 
+# First 16 hex chars of the sha256 of the committed raw CSV. load_raw()
+# refuses any file that does not match, so an edit to data/raw/bike_daily.csv
+# (by hand, by a tool, or by a changed upstream mirror) fails `make data` and
+# every test that loads the raw data. Change this only after deciding, on
+# purpose, that the new file is the one we want.
+EXPECTED_RAW_SHA256_PREFIX = "a6bed1577f6e4de5"
+
 TARGET = "cnt"
 
 # --- Three reasons a column is kept out of the feature set --------------
diff --git a/src/ingest.py b/src/ingest.py
index 6654075..2060777 100644
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -2,11 +2,14 @@
 
 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request
+from pathlib import Path
 
 import pandas as pd
 
+from src import config
 from src.config import DATA_URL, RAW
 
 EXPECTED_MIN_ROWS = 700
@@ -20,8 +23,33 @@ def download(force: bool = False) -> None:
     urllib.request.urlretrieve(DATA_URL, RAW)
 
 
+def sha256_of(path: Path) -> str:
+    h = hashlib.sha256()
+    with open(path, "rb") as f:
+        for chunk in iter(lambda: f.read(1 << 16), b""):
+            h.update(chunk)
+    return h.hexdigest()
+
+
+def check_raw_hash(path: Path) -> None:
+    """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
+    expected = config.EXPECTED_RAW_SHA256_PREFIX
+    actual = sha256_of(path)
+    if not actual.startswith(expected):
+        raise AssertionError(
+            f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
+            f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
+            f"file has changed; restore it (git checkout -- {path.name}) or, if "
+            f"the change is intended, review it and update the prefix."
+        )
+
+
 def load_raw() -> pd.DataFrame:
-    df = pd.read_csv(RAW, parse_dates=["dteday"])
+    # config.RAW is read at call time (not the import-time RAW) so tests can
+    # point the loader at a copy.
+    path = config.RAW
+    check_raw_hash(path)
+    df = pd.read_csv(path, parse_dates=["dteday"])
     missing = REQUIRED_COLS - set(df.columns)
     if missing:
         raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
diff --git a/tests/test_contract.py b/tests/test_contract.py
index 9fdb23d..abfb47d 100644
--- a/tests/test_contract.py
+++ b/tests/test_contract.py
@@ -79,6 +79,25 @@ def test_every_raw_column_is_classified():
     assert not unclassified, f"unclassified raw columns: {sorted(unclassified)}"
 
 
+def test_load_raw_rejects_modified_csv(tmp_path, monkeypatch):
+    """A single changed value in the raw CSV must fail the sha256 check,
+    before any parsing -- even when the file is still a valid, plausible CSV."""
+    original = config.RAW.read_text()
+    lines = original.splitlines(keepends=True)
+    header = [h.strip('"') for h in lines[0].rstrip("\n").split(",")]
+    cnt_idx = header.index("cnt")
+    fields = lines[1].rstrip("\n").split(",")
+    fields[cnt_idx] = str(int(fields[cnt_idx]) + 1)
+    lines[1] = ",".join(fields) + "\n"
+    modified = tmp_path / "bike_daily.csv"
+    modified.write_text("".join(lines))
+    assert modified.read_text() != original
+
+    monkeypatch.setattr(config, "RAW", modified)
+    with pytest.raises(AssertionError, match="raw data hash mismatch"):
+        load_raw()
+
+
 def test_encode_weather_rejects_unknown_labels():
     """An unmapped label must raise, not become a NaN that dropna() eats."""
     with pytest.raises(ValueError):
```

With variant B re-applied, `make data` now fails:

```
python -m src.ingest
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/src/ingest.py", line 63, in <module>
    df = load_raw()
         ^^^^^^^^^^
  File "/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/src/ingest.py", line 51, in load_raw
    check_raw_hash(path)
  File "/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/src/ingest.py", line 39, in check_raw_hash
    raise AssertionError(
AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.
make: *** [data] Error 1
```

and the suite fails (4 passed, 14 errors at fixture setup):

```
EEE....EEEEEEEEEEE                                                       [100%]
==================================== ERRORS ====================================
__________ ERROR at setup of test_calendar_is_complete_before_lagging __________

    @pytest.fixture(scope="module")
    def raw():
>       return load_raw().sort_values("dteday").reset_index(drop=True)
               ^^^^^^^^^^

tests/test_contract.py:20: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
____________ ERROR at setup of test_only_expected_rows_are_dropped _____________

    @pytest.fixture(scope="module")
    def raw():
>       return load_raw().sort_values("dteday").reset_index(drop=True)
               ^^^^^^^^^^

tests/test_contract.py:20: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
________________ ERROR at setup of test_beats_the_mean_baseline ________________

    @pytest.fixture(scope="module")
    def raw():
>       return load_raw().sort_values("dteday").reset_index(drop=True)
               ^^^^^^^^^^

tests/test_contract.py:20: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
________________ ERROR at setup of test_leakage_identity_holds _________________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
_________________ ERROR at setup of test_no_forbidden_features _________________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
______________ ERROR at setup of test_lags_are_true_calendar_lags ______________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
_________________ ERROR at setup of test_lag_is_not_the_target _________________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
______________ ERROR at setup of test_rolling_mean_excludes_today ______________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
___________________ ERROR at setup of test_no_missing_values ___________________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
______________ ERROR at setup of test_dates_are_sorted_and_unique ______________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
____________ ERROR at setup of test_hum_x_temp_is_same_day_product _____________

    @pytest.fixture(scope="module")
    def feats():
>       return build_features(load_raw())
                              ^^^^^^^^^^

tests/test_leakage.py:17: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
___________________ ERROR at setup of test_splits_non_empty ____________________

    @pytest.fixture(scope="module")
    def splits():
>       return temporal_split(build_features(load_raw()))
                                             ^^^^^^^^^^

tests/test_split.py:13: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
______________ ERROR at setup of test_splits_are_ordered_in_time _______________

    @pytest.fixture(scope="module")
    def splits():
>       return temporal_split(build_features(load_raw()))
                                             ^^^^^^^^^^

tests/test_split.py:13: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
_________________ ERROR at setup of test_no_overlapping_dates __________________

    @pytest.fixture(scope="module")
    def splits():
>       return temporal_split(build_features(load_raw()))
                                             ^^^^^^^^^^

tests/test_split.py:13: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/ingest.py:51: in load_raw
    check_raw_hash(path)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

path = PosixPath('/Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv')

    def check_raw_hash(path: Path) -> None:
        """Raise AssertionError unless `path` is the committed raw CSV, byte for byte."""
        expected = config.EXPECTED_RAW_SHA256_PREFIX
        actual = sha256_of(path)
        if not actual.startswith(expected):
>           raise AssertionError(
                f"raw data hash mismatch for {path}: sha256 is {actual}, expected it "
                f"to start with {expected} (config.EXPECTED_RAW_SHA256_PREFIX). The "
                f"file has changed; restore it (git checkout -- {path.name}) or, if "
                f"the change is intended, review it and update the prefix."
            )
E           AssertionError: raw data hash mismatch for /Users/madhavpudukottaikrishnaraj/Downloads/bikeshare-open/data/raw/bike_daily.csv: sha256 is 9c512aa7b35cdd98c3965c4176eb266f45c7527b6c4eba002de3b0195423fa79, expected it to start with a6bed1577f6e4de5 (config.EXPECTED_RAW_SHA256_PREFIX). The file has changed; restore it (git checkout -- bike_daily.csv) or, if the change is intended, review it and update the prefix.

src/ingest.py:39: AssertionError
=========================== short test summary info ============================
ERROR tests/test_contract.py::test_calendar_is_complete_before_lagging - Asse...
ERROR tests/test_contract.py::test_only_expected_rows_are_dropped - Assertion...
ERROR tests/test_contract.py::test_beats_the_mean_baseline - AssertionError: ...
ERROR tests/test_leakage.py::test_leakage_identity_holds - AssertionError: ra...
ERROR tests/test_leakage.py::test_no_forbidden_features - AssertionError: raw...
ERROR tests/test_leakage.py::test_lags_are_true_calendar_lags - AssertionErro...
ERROR tests/test_leakage.py::test_lag_is_not_the_target - AssertionError: raw...
ERROR tests/test_leakage.py::test_rolling_mean_excludes_today - AssertionErro...
ERROR tests/test_leakage.py::test_no_missing_values - AssertionError: raw dat...
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - AssertionErro...
ERROR tests/test_leakage.py::test_hum_x_temp_is_same_day_product - AssertionE...
ERROR tests/test_split.py::test_splits_non_empty - AssertionError: raw data h...
ERROR tests/test_split.py::test_splits_are_ordered_in_time - AssertionError: ...
ERROR tests/test_split.py::test_no_overlapping_dates - AssertionError: raw da...
4 passed, 14 errors in 1.47s
```

After git checkout the hash is a6bed1577f6e4de5 again, and make test shows 18 passed.
