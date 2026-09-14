# Synthetic JEE Knowledge Tracing Benchmark & Cross-World Robustness Report

See full detailed report in [`docs/synthetic-jee-kt-benchmark-report.md`](../../docs/synthetic-jee-kt-benchmark-report.md).

## Summary Table (5 Seeds, 140 Students, 35,000 Interactions)

| Model | AUC | Log Loss | RMSE | Brier Score | BKT State Recovery MAE | BKT State Recovery r |
|---|---|---|---|---|---|---|
| **baseline** | 0.5572 ± 0.0087 | 2.6225 ± 0.0431 | 0.5670 ± 0.0040 | 0.3215 ± 0.0045 | n/a (predictive only) | n/a |
| **bkt_default** | 0.5770 ± 0.0076 | 0.6899 ± 0.0051 | 0.4963 ± 0.0025 | 0.2464 ± 0.0025 | 0.3179 ± 0.0107 | 0.4722 ± 0.0266 |
| **bkt_fit** | 0.6522 ± 0.0079 | 0.6582 ± 0.0040 | 0.4824 ± 0.0020 | 0.2327 ± 0.0019 | 0.2148 ± 0.0073 | 0.6525 ± 0.0226 |
| **pfa** | 0.6621 ± 0.0047 | 0.6524 ± 0.0026 | 0.4797 ± 0.0013 | 0.2301 ± 0.0012 | n/a (predictive only) | n/a |
| **lkt** | **0.6707 ± 0.0072** | **0.6488 ± 0.0045** | **0.4778 ± 0.0021** | **0.2283 ± 0.0020** | n/a (predictive only) | n/a |

## Cross-World Stress Test 1: Standard (A+B+C) -> Stress (D+E)

| Model | Within-World AUC | Cross-World AUC | Generalization Gap (Delta AUC) |
|---|---|---|---|
| **baseline** | 0.5272 | 0.5280 | -0.0008 |
| **bkt_default** | 0.5654 | 0.5448 | +0.0206 |
| **bkt_fit** | 0.6447 | 0.6274 | +0.0173 |
| **pfa** | 0.6456 | 0.6232 | +0.0224 |
| **lkt** | **0.6604** | **0.6283** | **+0.0321** |

## Ablation Suite (Protocol §5)

### Ablation A: Core-Variable-Only vs. Core+Extended-Variable Generation
- **Core Worlds (A, B, C):** LKT (0.6633) > PFA (0.6497) > BKT Fit (0.6483) > BKT Default (0.5742) > Baseline (0.5303)
- **Extended Worlds (D, E, F):** LKT (0.6456) > PFA (0.6362) > BKT Fit (0.6234) > BKT Default (0.5651) > Baseline (0.5575)
- *Finding:* Rankings invariant; extended behavioral noise introduces ~1-2.5% AUC reduction across parametric models.

### Ablation B: Single-Concept vs. Multi-Concept Items
- **Single-Concept Items:** LKT (0.6597) > PFA (0.6505) > BKT Fit (0.6468) > BKT Default (0.5724)
- **Multi-Concept Items:** LKT (0.6274) > PFA (0.6225) > BKT Fit (0.6077) > BKT Default (0.5659)
- *Finding:* PFA compensatory summation outperforms BKT-fit (+0.0148) and BKT-default (+0.0566) on multi-concept questions.

### Ablation C: Fixed-Default BKT vs. EM-Fitted BKT
- **BKT Default (Fixed):** AUC 0.5732, State Recovery MAE 0.3144, State Recovery r 0.4557
- **BKT Fit (EM):** AUC 0.6411 (+0.0679), State Recovery MAE 0.2241 (-29% error), State Recovery r 0.6018
