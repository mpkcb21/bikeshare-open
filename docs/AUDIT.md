# Audit of a teammate's repo (Exercise 3)

Repo audited: https://github.com/karsan377/agentic-programming (HEAD 5e6398c, two commits: the unmodified starter and "Rewrite src/train.py from spec").
How: I cloned it outside my own repo, read its diff against the starter (only src/train.py changed), then ran Claude Code from my own repo with `--add-dir` pointing at the clone, auto mode off, and asked it to run the leakage-auditor subagent read-only.
Model: Claude Opus, selected in Claude Code (from memory, not re-checked)

## Subagent report (verbatim)

```text
All five checks pass, and I found nothing that changes a number or invalidates a conclusion. I wrote and modified no files. I ran the pipeline functions in memory only, with bytecode writing off, and did not run any make target. Repo: /Users/madhavpudukottaikrishnaraj/teammate-audit/agentic-programming, HEAD 5e6398c.

1. Target leakage: pass. feature_columns (src/features.py:81-84) excludes everything in FORBIDDEN. The 14 features it returns are temp, atemp, hum, windspeed, dayofweek, is_weekend, is_holiday, is_workday, month_sin, month_cos, weather_severity, cnt_lag_1, cnt_lag_7 and cnt_roll_7. None contains casual, registered, cnt, cnt_2d_bfr or a time index. The three lag features are built only from cnt shifted by 1 or more (src/features.py:74-76).
2. Temporal ordering: pass.
   - cnt_roll_7 does .shift(1) before .rolling (src/features.py:76).
   - temporal_split (src/train.py:45-51) splits by dteday. I got 348 train, 182 valid and 184 test rows.
   - The StandardScaler sits inside the pipeline and is fit only on train in evaluate (src/train.py:56). No imputer or encoder is fitted. The weather encoding is a fixed dict.
   - The mean baseline is fit on train only.
3. Calendar gaps: pass. build_features calls reindex_to_calendar before any shift (src/features.py:54). The reindexed grid has 729 days against 728 raw rows, so only the 2011-03-10 gap exists.
4. Silent row loss: pass.
   - encode_weather raises on unmapped labels (src/features.py:27-30). The raw data has 0 NaNs.
   - Features drop from 728 to 714 rows, a loss of 14. That is the 7 warm-up days plus the 7 rows after the 2011-03-10 gap, which equals the expected loss.
   - tests/test_contract.py::test_only_expected_rows_are_dropped bounds this loss. The dropna() at src/features.py:78 carries no assertion in the code itself. The test covers it, so this is not a finding.
5. Baselines: pass. MODELS (src/train.py:37-42) includes baseline_mean and baseline_persistence, and both are scored by the same evaluate call as the models. Persistence predicts cnt_lag_1, which is yesterday's true count on the gap-free index. I ran all four models on the data. The mean baseline is negative on both splits and HGB is negative on test, which the repo treats as findings, not bugs.

┌─────────────┬──────────┬───────────┬─────────┬──────────┐
│    Model    │ Valid R2 │ Valid MAE │ Test R2 │ Test MAE │
├─────────────┼──────────┼───────────┼─────────┼──────────┤
│ mean        │ -0.932   │ 2002      │ -2.144  │ 2848     │
├─────────────┼──────────┼───────────┼─────────┼──────────┤
│ persistence │ 0.451    │ 901       │ 0.510   │ 840      │
├─────────────┼──────────┼───────────┼─────────┼──────────┤
│ ridge       │ 0.648    │ 833       │ 0.583   │ 947      │
├─────────────┼──────────┼───────────┼─────────┼──────────┤
│ hgb         │ 0.166    │ 1341      │ -0.618  │ 2057     │
└─────────────┴──────────┴───────────┴─────────┴──────────┘

Persistence has the best MAE on test (840 against ridge's 947), though ridge has the higher test R2 (0.583 against 0.510). HGB loses to persistence on both splits. If the write-up claims ridge beats persistence, say it does so on R2 only, not on test MAE.
```

The subagent said it had not re-run its own numbers.

## My verdict

I agree with the subagent: no leakage, a correct temporal split, and both baselines reported. I did not rely on its word alone:

- `git diff --stat 9b1e487 HEAD` in the clone shows one changed file, src/train.py. Their features.py, config.py, tests and .claude hooks are the unmodified starter, so the leakage checks (1, 3, 4) describe the starter's code, which I had already audited in my own repo. Their raw CSV sha256 starts with a6bed1577f6e4de5.
- I read the train.py diff: it fits on train only, scores valid and test, and has no tuning loop.
- I ran their suite from my venv: 14 passed. I also ran `python -m src.train` and got the same table as the subagent to four decimals (ridge 0.6475 valid / 0.5833 test; persistence 0.4507 / 0.5099; mean -0.9318 / -2.1441; hgb 0.1659 / -0.6179).

Things the subagent did not flag, none of them leakage:

- hgb now uses the library default max_iter instead of the starter's max_iter=300, so its numbers differ from the starter's (0.2185 / -0.4975).
- metrics.json no longer records n_features, features, n_train, n_valid or n_test.
- The check that raised when cnt_lag_1 was missing from the persistence baseline was removed.
- train.py calls load_raw() and build_features() directly instead of reading features.parquet, so it skips the make features stage.
- Their suite is still the starter's 14 tests, with no new test for the rewrite.

Agreed caveat: ridge beats persistence on R2 (0.583 vs 0.510) but not on test MAE (947 vs 840), so a write-up should not say ridge simply beats persistence.
