# Phase 1 — Baseline Pipeline Report

> Generated: 2026-09-25 16:39:33

---

## 1. Data Source

| Field | Value |
|:---|:---|
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| records_loaded | 24 |
| clean_rows | 24 |
| run_date | 2026-09-25T09:39:04.837199+00:00 |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| collection | papers-baseline |

---

## 2. RAG Evaluation Metrics

| Metric | Value |
|:---|:---|
| samples | 10 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 0.5764 |
| judge_accuracy | 0.5000 |
| mean_judge_score | 3 |
| ragas | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

---

## 3. Data Quality Gate

**Result: ✅ PASS** (6/6 checks passed)

| Check | Result |
|:---|:---|
| ExpectTableRowCountToBeBetween | ✅ |
| ExpectColumnValuesToNotBeNull | ✅ |
| ExpectColumnValuesToNotBeNull | ✅ |
| ExpectColumnValuesToNotBeNull | ✅ |
| ExpectColumnValuesToBeUnique | ✅ |
| ExpectColumnValueLengthsToBeBetween | ✅ |

---

## 4. Freshness SLA

**Status: ✅ FRESH**

| Field | Value |
|:---|:---|
| Threshold | 180 days |
| Latest Published | 2026-09-13 |
| Oldest Published | 2026-04-06 |
| Stale Records | 0/24 (0.0%) |
