# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
2026-11-19: Plan-mode exploration of data/raw/bike_daily.csv. Agent's claims all verified by pandas: 728 rows x 18 columns, 2011-01-03 to 2012-12-31, 2011-03-10 missing, weather GOOD/MISTY/BAD = 463/245/20, casual+registered==cnt on every row, cnt_2d_bfr is a correct 2-day lag except 3 rows (2011-01-03, 2011-01-04, 2011-03-12) whose source days are absent. Agent errors found: none. Treated cnt_2d_bfr as unverified, not leakage.
