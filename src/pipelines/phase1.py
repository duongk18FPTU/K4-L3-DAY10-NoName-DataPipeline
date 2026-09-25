from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Baseline pipeline end-to-end (Checkpoint 3).

    Luồng thực thi:
    1. Load settings từ .env.
    2. Fetch live hoặc load offline snapshot raw records (Dual-Mode).
    3. Clean & chuẩn hóa data thành DataFrame.
    4. Lưu clean CSV + JSON.
    5. Build ChromaDB collection 'papers-baseline'.
    6. Tạo hoặc load evaluation test set.
    7. Evaluate pipeline (Hit Rate, Token F1, LLM Judge).
    8. Run Great Expectations quality checks + Freshness SLA.
    9. Sinh báo cáo Markdown phase1_report.md.
    """
    settings = load_settings()
    run_date = now_utc()

    print("=" * 60)
    print("PHASE 1 — BASELINE PIPELINE")
    print("=" * 60)

    # ── Bước 1: Load / fetch raw records ─────────────────────────
    raw_records_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_records_path.exists():
        print("\n[1/8] Fetching live records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"\n[1/8] Loading offline snapshot: {raw_records_path}")
        records = load_raw_records(raw_records_path)
    print(f"      → {len(records)} records loaded.")

    # ── Bước 2: Clean ────────────────────────────────────────────
    print("\n[2/8] Cleaning & normalizing data...")
    df = build_clean_dataframe(records, run_date)
    print(f"      → {len(df)} clean rows.")

    # ── Bước 3: Save clean artifacts ─────────────────────────────
    print("\n[3/8] Saving clean artifacts...")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"      → {settings.paths.clean_csv}")
    print(f"      → {settings.paths.clean_json}")

    # ── Bước 4: Build ChromaDB index ─────────────────────────────
    print("\n[4/8] Building ChromaDB index (papers-baseline)...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"      → Collection '{settings.baseline_collection_name}' ready.")

    # ── Bước 5: Build test set ───────────────────────────────────
    eval_path = settings.paths.eval_testset
    if settings.refresh_test_set or not eval_path.exists():
        print("\n[5/8] Generating evaluation test set...")
        build_test_set(df, eval_path)
    else:
        print(f"\n[5/8] Using existing test set: {eval_path}")

    # ── Bước 6: Evaluate baseline ────────────────────────────────
    print("\n[6/8] Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=eval_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    m = bundle.summary
    print(f"      Hit Rate : {m['retrieval_hit_rate']:.3f}")
    print(f"      Token F1 : {m['mean_token_f1']:.3f}")
    print(f"      Judge Acc: {m['judge_accuracy']:.3f}")

    # ── Bước 7: Quality Gate (GX 1.x) ────────────────────────────
    print("\n[7/8] Running Data Quality Gate (GX 1.x)...")
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    status = "✅ PASSED" if quality.get("success") else "❌ FAILED"
    print(f"      → Quality Gate: {status}")

    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    fresh_status = "✅ FRESH" if freshness.get("is_fresh") else "⚠️  STALE"
    print(f"      → Freshness   : {fresh_status}  "
          f"(stale={freshness['stale_rows']}/{freshness['total_rows']} rows)")

    # ── Bước 8: Generate Markdown report ─────────────────────────
    print("\n[8/8] Generating Phase 1 Markdown report...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "records_loaded": len(records),
        "clean_rows": len(df),
        "run_date": run_date.isoformat(),
        "embedding_model": settings.embedding_model,
        "collection": settings.baseline_collection_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"      → {settings.paths.baseline_report}")

    print("\n" + "=" * 60)
    print("✅  Phase 1 complete!")
    print(f"    Artifacts in: {settings.paths.clean_csv.parent.parent}")
    print("=" * 60)

