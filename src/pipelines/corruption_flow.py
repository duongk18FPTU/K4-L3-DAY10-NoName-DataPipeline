from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corruption → Evaluate → Repair → Evaluate → Compare (Checkpoint 4-5).

    Luồng thực thi:
    1. Load settings + baseline clean dataset.
    2. Tiêm 6 kịch bản lỗi vào clean DataFrame (corruption).
    3. Lưu corrupted artifacts (CSV, JSON).
    4. Build ChromaDB collection 'papers-corrupted' + đánh giá suy giảm.
    5. Run Quality Gate trên corrupted data → phải báo FAILED.
    6. Repair idempotent từ raw snapshot → rebuild clean DataFrame.
    7. Build ChromaDB collection 'papers-repaired' + đánh giá phục hồi.
    8. Run Quality Gate trên repaired data → phải báo PASSED.
    9. Sinh báo cáo đối chiếu 3 trạng thái: Baseline vs Corrupted vs Repaired.
    """
    settings = load_settings()
    run_date = now_utc()

    print("=" * 60)
    print("PHASE 2 — CORRUPTION → REPAIR → COMPARISON")
    print("=" * 60)

    # ── Bước 1: Load baseline clean data ─────────────────────────
    print("\n[1/9] Loading baseline clean dataset...")
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Baseline clean JSON not found: {settings.paths.clean_json}\n"
            "Run 'python script/run_phase1.py' first."
        )
    df_clean = pd.read_json(settings.paths.clean_json)
    baseline_metrics = None
    if settings.paths.baseline_metrics.exists():
        from core.utils import read_json
        baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"      → {len(df_clean)} clean rows loaded.")

    # ── Bước 2: Corrupt ──────────────────────────────────────────
    print("\n[2/9] Injecting 6 data corruption scenarios...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    print(f"      → {len(df_corrupted)} rows after corruption.")
    print(f"      → Log: {settings.paths.corruption_log}")

    # ── Bước 3: Save corrupted artifacts ─────────────────────────
    print("\n[3/9] Saving corrupted artifacts...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    print(f"      → {settings.paths.corrupted_clean_csv}")

    # ── Bước 4: Build corrupted index + evaluate ─────────────────
    print("\n[4/9] Building ChromaDB index (papers-corrupted)...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print(f"      → Collection '{settings.corrupted_collection_name}' ready.")

    print("\n[5/9] Evaluating CORRUPTED pipeline...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    cm = corrupted_bundle.summary
    print(f"      Hit Rate : {cm['retrieval_hit_rate']:.3f}  ← expect degraded")
    print(f"      Token F1 : {cm['mean_token_f1']:.3f}")
    print(f"      Judge Acc: {cm['judge_accuracy']:.3f}")

    # ── Bước 5: Quality Gate on corrupted data ───────────────────
    print("\n[6/9] Running Quality Gate on CORRUPTED data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, report_name="corrupted")
    c_status = "✅ PASSED" if corrupted_quality.get("success") else "❌ FAILED (expected!)"
    print(f"      → Quality Gate: {c_status}")

    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.corrupted_quality_report.parent / "corrupted_freshness_report.json"
    )
    fresh_status = "✅ FRESH" if corrupted_freshness.get("is_fresh") else "⚠️  STALE (expected!)"
    print(f"      → Freshness   : {fresh_status}")

    # ── Bước 6: Idempotent Repair từ raw snapshot ────────────────
    print("\n[7/9] Repairing from raw snapshot (Idempotent Repair)...")
    if not settings.paths.raw_records_json.exists():
        raise FileNotFoundError(
            f"Raw records snapshot not found: {settings.paths.raw_records_json}\n"
            "Cannot perform repair without raw lineage."
        )
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    print(f"      → {len(df_repaired)} rows after repair.")
    print(f"      → {settings.paths.repaired_clean_csv}")

    # ── Bước 7: Build repaired index + evaluate ──────────────────
    print("\n[8/9] Building ChromaDB index (papers-repaired)...")
    repaired_index = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    print(f"      → Collection '{settings.repaired_collection_name}' ready.")

    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    rm = repaired_bundle.summary
    print(f"      Hit Rate : {rm['retrieval_hit_rate']:.3f}  ← expect recovery")
    print(f"      Token F1 : {rm['mean_token_f1']:.3f}")
    print(f"      Judge Acc: {rm['judge_accuracy']:.3f}")

    # ── Bước 8: Quality Gate on repaired data ────────────────────
    repaired_quality = run_data_quality_checks(df_repaired, settings, report_name="repaired")
    r_status = "✅ PASSED" if repaired_quality.get("success") else "❌ FAILED"
    print(f"      → Quality Gate: {r_status}")

    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.freshness_report
    )
    print(f"      → Freshness   : {'✅ FRESH' if repaired_freshness.get('is_fresh') else '⚠️  STALE'}")

    # ── Bước 9: Generate 3-column comparison report ───────────────
    print("\n[9/9] Generating 3-state comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics or {},
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"      → {settings.paths.comparison_report}")

    # ── Tóm tắt so sánh 3 trạng thái ────────────────────────────
    print("\n" + "=" * 60)
    print("📊  3-STATE COMPARISON SUMMARY")
    print("=" * 60)
    b_hit = baseline_metrics.get("retrieval_hit_rate", "N/A") if baseline_metrics else "N/A"
    b_f1  = baseline_metrics.get("mean_token_f1", "N/A") if baseline_metrics else "N/A"
    fmt   = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)

    print(f"{'Metric':<22} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 55)
    print(f"{'Hit Rate':<22} {fmt(b_hit):>10} {cm['retrieval_hit_rate']:>10.3f} {rm['retrieval_hit_rate']:>10.3f}")
    print(f"{'Token F1':<22} {fmt(b_f1):>10} {cm['mean_token_f1']:>10.3f} {rm['mean_token_f1']:>10.3f}")
    print(f"{'Judge Accuracy':<22} {'N/A':>10} {cm['judge_accuracy']:>10.3f} {rm['judge_accuracy']:>10.3f}")
    print("=" * 60)
    print("✅  Phase 2 complete!")
    print(f"    Report: {settings.paths.comparison_report}")
    print("=" * 60)

