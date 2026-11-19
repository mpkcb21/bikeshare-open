"""Exercise 4: does a target transformation let a tree leave the 2011 range?

Fits clones of MODELS["hgb"] and MODELS["ridge"] under five target
transformations, always scoring predictions back on the original `cnt` scale.
Every inverse uses only columns known at prediction time for date d
(cnt_roll_7, cnt_lag_7 and cnt_lag_1 are all built from shift(1) or deeper).

Default run prints VALIDATION metrics only; the test split is never scored.
`--final TRANSFORM_NAME` prints test metrics for that one transformation, the
untransformed hgb and ridge, and persistence. Choose on validation first.

Run: python -m src.ex4_target_transform
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw
from src.train import MODELS, temporal_split

# name -> (forward: df -> transformed target, inverse: (pred, df) -> cnt)
TRANSFORMS = {
    "none": (
        lambda d: d[TARGET],
        lambda p, d: p,
    ),
    "log1p": (
        lambda d: np.log1p(d[TARGET]),
        lambda p, d: np.expm1(p),
    ),
    "ratio_roll7": (
        lambda d: d[TARGET] / d["cnt_roll_7"],
        lambda p, d: p * d["cnt_roll_7"].to_numpy(),
    ),
    "diff_lag7": (
        lambda d: d[TARGET] - d["cnt_lag_7"],
        lambda p, d: p + d["cnt_lag_7"].to_numpy(),
    ),
    "diff_lag1": (
        lambda d: d[TARGET] - d["cnt_lag_1"],
        lambda p, d: p + d["cnt_lag_1"].to_numpy(),
    ),
}
MODEL_NAMES = ("hgb", "ridge")


def _metrics(y_true, y_pred) -> tuple[float, float]:
    return float(r2_score(y_true, y_pred)), float(mean_absolute_error(y_true, y_pred))


def _fit_predict(model_name, transform, train, part, cols):
    forward, inverse = TRANSFORMS[transform]
    model = clone(MODELS[model_name]).fit(train[cols], forward(train))
    return inverse(model.predict(part[cols]), part)


def _persistence(train, part, cols):
    model = clone(MODELS["baseline_persistence"]).fit(train[cols])
    return model.predict(part[cols])


def _table(rows, split):
    out = pd.DataFrame(rows, columns=["model", "target", f"{split}_r2", f"{split}_mae"])
    return out.to_string(index=False, float_format=lambda x: f"{x:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", metavar="TRANSFORM_NAME", choices=sorted(TRANSFORMS),
                    help="score TEST for this transformation (run once, after choosing on validation)")
    args = ap.parse_args()

    df = build_features(load_raw())
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    if args.final:
        split, part = "test", test
        combos = [(m, args.final) for m in MODEL_NAMES]
        if args.final != "none":
            combos += [(m, "none") for m in MODEL_NAMES]
    else:
        split, part = "valid", valid
        combos = [(m, t) for t in TRANSFORMS for m in MODEL_NAMES]

    rows = []
    for m, t in combos:
        r2, mae = _metrics(part[TARGET], _fit_predict(m, t, train, part, cols))
        rows.append((m, t, r2, mae))
    r2, mae = _metrics(part[TARGET], _persistence(train, part, cols))
    rows.append(("baseline_persistence", "-", r2, mae))

    print(f"{split.upper()} metrics, cnt scale, n={len(part)}")
    print(_table(rows, split))
    print(f"OK ex4_target_transform: {len(rows)} rows ({split})")


if __name__ == "__main__":
    main()
