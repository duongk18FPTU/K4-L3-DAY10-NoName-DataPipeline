# Corruption & Repair — Comparison Report

> Generated: 2026-09-25 16:41:36

---

## RAG Evaluation Metrics

| Metric | Baseline | Corrupted | Repaired |
|:---|:---:|:---:|:---:|
| judge_accuracy | 0.5000 | 0.5000 | 0.5000 |
| mean_judge_score | 3 | 3 | 3 |
| mean_token_f1 | 0.5764 | 0.5499 | 0.5764 |
| ragas | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |
| retrieval_hit_rate | 1.0000 | 1.0000 | 1.0000 |
| samples | 10 | 10 | 10 |

---

## Data Quality Gate

| | Baseline | Corrupted | Repaired |
|:---|:---:|:---:|:---:|
| Quality Gate | ✅ PASS | ❌ FAIL (4/6) | ✅ PASS (6/6) |
| Freshness SLA | ✅ FRESH | ✅ FRESH (13.0% stale) | ✅ FRESH (0.0% stale) |

---

## Summary

- **Corruption** introduced data defects that were detected by the Quality Gate.
- **Repair** restored the pipeline from raw snapshots (idempotent recovery).
- Repaired metrics should be equal or close to the Baseline metrics.
