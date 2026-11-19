# Bikeshare demand: forecasting daily rides without leaking the target

## Results

Split by date: train 2011 (348 days), validation H1 2012 (182), test H2 2012 (184). All numbers are rides per day (MAE) and R². "Before" is the starter pipeline; "after" adds my feature `hum_x_temp = hum * temp` (via /new-feature). "After" rows match `reports/metrics.json`, produced by `make all`.

| Model | Pipeline | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6493 | 829.9 | 0.5835 | 946.6 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.2129 | 1292.6 | -0.5867 | 2034.4 |

Negative R² and losing to the baseline are different things here. Gradient boosting is negative on test and still beats the mean baseline comfortably (-0.5867 vs -2.1441). Ridge is positive but only narrowly beats persistence on R² (0.5835 vs 0.5099) and loses to it on MAE (946.6 vs 840.1).

Audit: `python agent/audit.py . --out reports/audit.jsonl` (run with `AUDIT_MODEL=sonnet`) flagged 0 of 1 repos: leakage none, temporal_ok true, baseline_reported true, reproducible true, confidence high. Its two findings are notes, not violations (only hgb sets a `random_state`, and a confirmation that lags use a gap-free calendar with `shift(1)` before rolling), and neither changes a number.

## Headline finding

A model given `casual` and `registered` scores test R² = 1.000000, which is the signature of leakage: `casual + registered == cnt` on every row (least-squares residual 8.56e-12), so the model only learns addition. With those columns excluded and a split by date, the mean baseline scores test R² -2.1441 because ridership grew about 65% from 2011 to 2012. Persistence ("yesterday again") scores 0.5099 (MAE 840.1), ridge 0.5835 (MAE 946.6), and gradient boosting -0.5867 (MAE 2034.4): ridge is only about 0.07 R² ahead of persistence and behind it on MAE, and gradient boosting fails because a tree cannot predict above the largest value it saw in training (the 2011 maximum, 6,043 rides) while more than half of the test days are above it. My feature `hum_x_temp` moved validation R² by +0.002 for ridge and -0.006 for gradient boosting, both below the 0.01 noise floor on 182 days, so I kept it in the code but do not claim it as an improvement.

## Exercise 4: target transformation

Goal: find a target transformation that lets the tree compete, then decide whether it is defensible. All selection used the validation set; the test set was scored once, after choosing, and not rerun. The code is in `src/ex4_target_transform.py` on the branch `exercise4-target-transform` (not merged, so the committed `reports/metrics.json` is the untransformed pipeline).

Validation (n = 182), predictions always scored back on the original `cnt` scale:

| Model | Target | Valid R² | Valid MAE |
|---|---|---|---|
| hgb | none | 0.213 | 1292.6 |
| hgb | log1p(cnt) | 0.145 | 1350.3 |
| hgb | cnt / cnt_roll_7 (ratio_roll7) | 0.736 | 683.4 |
| hgb | cnt - cnt_lag_7 | 0.501 | 953.6 |
| hgb | cnt - cnt_lag_1 | 0.609 | 825.7 |
| ridge | none | 0.649 | 829.9 |
| baseline_persistence | - | 0.451 | 900.6 |
| control: predict cnt_roll_7 unchanged | - | 0.5945 | 823.9 |

I chose hgb with the ratio target (prediction = ratio x cnt_roll_7). `cnt_roll_7` is built with `shift(1)`, so it is known at prediction time. The control row matters: predicting the 7-day mean unchanged already scores 0.5945, so most of the 0.736 is the anchor and the tree adds about +0.14 R² over it.

Test, scored once (n = 184): hgb ratio_roll7 R² 0.604 / MAE 868.1; ridge 0.584 / 946.6; persistence 0.510 / 840.1; untransformed hgb -0.587 / 2034.4.

Verdict: the transformation is defensible as a forecast relative to a recent level, and it rescues the tree (from -0.587 to 0.604). It is not a win. It is only 0.02 R² above ridge, it still loses to persistence on MAE, and the validation lead (0.736 vs 0.649) shrank on test after I picked the best of 10 model-and-target combinations on 182 days. I would claim only that a tree can compete once the target is anchored to recent demand.

## Exercise 5: ridge vs persistence

On test, ridge is better than “yesterday again” on R² (0.5835 vs 0.5099, about +0.07) but is worse for MAE (946.6 vs 840.1 rides, about 13% worse). Since R² squares errors and MAE does not, ridge avoids some large misses while being further off on a typical day. On validation it is better for both (R² 0.6493 vs 0.4507; MAE 829.9 vs 900.6), so the evidence depends on the period. Predicting the 7-day mean unchanged scores validation R² 0.5945 and MAE 823.9, within 0.06 R² of ridge and slightly better on MAE. I would not deploy ridge based on this evidence, it adds a fitted model, a refit schedule and a feature pipeline for a 0.07 R² gain that disappears on MAE. It would be worth deploying only if large misses cost much more than typical ones.

## Attribution

Models: Claude Code on hosted Claude models through my Claude Pro account. My `.claude/settings.local.json` selects `sonnet`, and a `/context` check in one session showed Fable 5.2, so I used more than one model and cannot say exactly which step ran on which; the teammate audit session was, as best I recall, Claude Opus. `agent/audit.py` ran with `AUDIT_MODEL=sonnet`. Hosted models do not publish a parameter size. The Claude chat help was Claude Sonnet 5.5.

I started on the local `qwen3.5:9b` model through Ollama, as the handout specifies, and switched: `make model` failed because the model needs 7.1 GiB and my 8 GB laptop had 4.8 GiB free. All Claude Code work after that, and the audit script, used a hosted Claude model through my Claude Pro account (set in `.claude/settings.local.json`; `AUDIT_MODEL=sonnet` for `agent/audit.py`). I also used a Claude chat session (claude.ai, Sonnet 5.5) throughout to walk me through the assignment and to draft commands, the text of `.claude/skills/seed-fault/SKILL.md`, my `CLAUDE.md` additions, the scripts that assembled `docs/SEEDED_FAULTS.md` and `docs/AUDIT.md`, wording for several `docs/DECISIONS.md` lines, and a first draft of the Exercise 5 paragraph, which I rewrote in my own words and whose numbers I checked against `reports/metrics.json`. I ran every command, checked outputs against my own terminal output, and edited the text before committing.

Agent-generated (Claude Code, run by me):
- `hum_x_temp` in `src/features.py` and its test `test_hum_x_temp_is_same_day_product`
- `test_every_raw_column_is_classified`, `test_encode_weather_rejects_unknown_labels` and `test_load_raw_rejects_modified_csv` in `tests/test_contract.py`
- `REDUNDANT_COLS`, `FEATURE_INPUT_COLS` and `EXPECTED_RAW_SHA256_PREFIX` in `src/config.py`, and `check_raw_hash` in `src/ingest.py`
- the three seeded-fault edits and their fixes in `src/features.py`
- `src/ex4_target_transform.py`
- the `/leakage-auditor` report in `docs/AUDIT.md`, and the `agent/audit.py` run in `reports/audit.jsonl`

My decisions, each traced to a line in `docs/DECISIONS.md`:
- Treating `cnt_2d_bfr` as unverified rather than leakage, after checking the agent's claims against pandas (Step 2 line).
- Keeping `hum_x_temp` in the code but not claiming it as an improvement (hum_x_temp line).
- Classifying raw columns against fixed sets, not `feature_columns()`, and adding `REDUNDANT_COLS` (unclassified-column line).
- Choosing a sha256 check over a Stop hook, a PreToolUse hook or `chmod` for the fourth fault (fault 4 line).
- Choosing `ratio_roll7` on validation only, scoring test once, and judging it defensible but not a win (Exercise 4 line).
- Not deploying ridge over a naive rule, because its R² lead disappears on MAE (Exercise 5 line).
- The scope and wording of `CLAUDE.md` and the `/seed-fault` skill (CLAUDE.md and skill lines).
- Whether the answer is believable: ridge's lead over persistence is thin, and that caveat goes in this report.
