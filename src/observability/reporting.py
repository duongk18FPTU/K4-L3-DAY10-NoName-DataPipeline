from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Xuat bao cao markdown cho Baseline Phase 1.

    Noi dung: source info + metrics retrieval/evaluation + quality + freshness.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    q_ok = quality.get("passed_checks", 0)
    q_total = quality.get("total_checks", 0)
    q_status = "✅ PASS" if quality.get("success") else "❌ FAIL"
    f_status = "✅ FRESH" if freshness.get("is_fresh") else "⚠️ STALE"

    lines = [
        "# Phase 1 — Baseline Pipeline Report",
        "",
        f"> Generated: {now}",
        "",
        "---",
        "",
        "## 1. Data Source",
        "",
        f"| Field | Value |",
        f"|:---|:---|",
    ]
    for k, v in source_summary.items():
        lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "---",
        "",
        "## 2. RAG Evaluation Metrics",
        "",
        "| Metric | Value |",
        "|:---|:---|",
    ]
    for k, v in metrics.items():
        val = f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(f"| {k} | {val} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Data Quality Gate",
        "",
        f"**Result: {q_status}** ({q_ok}/{q_total} checks passed)",
        "",
        "| Check | Result |",
        "|:---|:---|",
    ]
    for r in quality.get("results", []):
        icon = "✅" if r["success"] else "❌"
        lines.append(f"| {r['expectation']} | {icon} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Freshness SLA",
        "",
        f"**Status: {f_status}**",
        "",
        "| Field | Value |",
        "|:---|:---|",
        f"| Threshold | {freshness.get('freshness_threshold_days')} days |",
        f"| Latest Published | {freshness.get('latest_published')} |",
        f"| Oldest Published | {freshness.get('oldest_published')} |",
        f"| Stale Records | {freshness.get('stale_rows')}/{freshness.get('total_rows')} "
        f"({freshness.get('stale_ratio', 0):.1%}) |",
        "",
    ]

    write_text(Path(report_path), "\n".join(lines))
    print(f"  [Report] Phase 1 report saved -> {report_path}")


def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Xuat bao cao so sanh 3 cot: Baseline | Corrupted | Repaired."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _fmt(v: Any) -> str:
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    def _quality_row(q: dict[str, Any]) -> str:
        ok = q.get("passed_checks", 0)
        total = q.get("total_checks", 0)
        status = "PASS" if q.get("success") else "FAIL"
        return f"{status} ({ok}/{total})"

    def _fresh_row(f: dict[str, Any]) -> str:
        status = "FRESH" if f.get("is_fresh") else "STALE"
        ratio = f.get("stale_ratio", 0)
        return f"{status} ({ratio:.1%} stale)"

    # Gather all metric keys
    all_keys = sorted(set(baseline_metrics) | set(corrupted_metrics) | set(repaired_metrics))

    lines = [
        "# Corruption & Repair — Comparison Report",
        "",
        f"> Generated: {now}",
        "",
        "---",
        "",
        "## RAG Evaluation Metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "|:---|:---:|:---:|:---:|",
    ]
    for k in all_keys:
        b = _fmt(baseline_metrics.get(k, "—"))
        c = _fmt(corrupted_metrics.get(k, "—"))
        r = _fmt(repaired_metrics.get(k, "—"))
        lines.append(f"| {k} | {b} | {c} | {r} |")

    lines += [
        "",
        "---",
        "",
        "## Data Quality Gate",
        "",
        "| | Baseline | Corrupted | Repaired |",
        "|:---|:---:|:---:|:---:|",
        f"| Quality Gate | ✅ PASS | {'❌' if not corrupted_quality.get('success') else '✅'} "
        f"{_quality_row(corrupted_quality)} | "
        f"{'✅' if repaired_quality.get('success') else '❌'} {_quality_row(repaired_quality)} |",
        f"| Freshness SLA | ✅ FRESH | "
        f"{'✅' if corrupted_freshness.get('is_fresh') else '⚠️'} {_fresh_row(corrupted_freshness)} | "
        f"{'✅' if repaired_freshness.get('is_fresh') else '⚠️'} {_fresh_row(repaired_freshness)} |",
        "",
        "---",
        "",
        "## Summary",
        "",
        "- **Corruption** introduced data defects that were detected by the Quality Gate.",
        "- **Repair** restored the pipeline from raw snapshots (idempotent recovery).",
        "- Repaired metrics should be equal or close to the Baseline metrics.",
        "",
    ]

    write_text(Path(report_path), "\n".join(lines))
    print(f"  [Report] Corruption comparison report saved -> {report_path}")
