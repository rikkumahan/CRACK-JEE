# Synthetic JEE Knowledge Tracing Benchmark & Cross-World Robustness Report

See full detailed report in [`docs/synthetic-jee-kt-benchmark-report.md`](../../docs/synthetic-jee-kt-benchmark-report.md).

## Summary Table (5 Seeds, 140 Students, 14,000 Interactions)

| Model | AUC | Log Loss | RMSE | Brier Score | BKT State Recovery MAE | BKT State Recovery r |
|---|---|---|---|---|---|---|
| **baseline** | 0.5289 ± 0.0083 | 2.9252 ± 0.0427 | 0.5739 ± 0.0029 | 0.3294 ± 0.0034 | n/a (predictive only) | n/a |
| **bkt_default** | 0.5300 ± 0.0103 | 0.6764 ± 0.0080 | 0.4912 ± 0.0037 | 0.2413 ± 0.0037 | 0.3302 ± 0.0165 | 0.3174 ± 0.0270 |
| **bkt_fit** | 0.6165 ± 0.0131 | 0.6635 ± 0.0070 | 0.4848 ± 0.0033 | 0.2350 ± 0.0032 | 0.2808 ± 0.0126 | 0.4054 ± 0.0276 |
| **pfa** | 0.6334 ± 0.0125 | 0.6560 ± 0.0077 | 0.4814 ± 0.0037 | 0.2317 ± 0.0035 | n/a (predictive only) | n/a |
| **lkt** | **0.6409 ± 0.0125** | **0.6533 ± 0.0076** | **0.4799 ± 0.0037** | **0.2303 ± 0.0035** | n/a (predictive only) | n/a |

## Cross-World Stress Test 1: Standard (A+B+C) -> Stress (D+E)

| Model | Within-World AUC | Cross-World AUC | Generalization Gap (Delta AUC) |
|---|---|---|---|
| **baseline** | 0.5463 | 0.5049 | +0.0414 |
| **bkt_default** | 0.5373 | 0.5150 | +0.0223 |
| **bkt_fit** | 0.6391 | 0.6022 | +0.0369 |
| **pfa** | 0.6504 | 0.6236 | +0.0268 |
| **lkt** | **0.6527** | **0.6324** | **+0.0203** |
