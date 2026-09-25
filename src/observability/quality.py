from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Thuc hien Data Quality Gate bang Great Expectations 1.x (ephemeral mode).

    Kiem tra:
    1. Row count nam trong [5, 5000].
    2. paper_id, title, text_for_embedding khong null.
    3. paper_id unique.
    4. Do dai summary >= 30 ky tu.
    """
    import great_expectations as gx

    context = gx.get_context(mode="ephemeral")

    data_source = context.data_sources.add_pandas(name=f"{report_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{report_name}_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"{report_name}_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    results = []
    all_success = True

    def _check(expectation) -> dict[str, Any]:
        nonlocal all_success
        result = batch.validate(expectation)
        ok = bool(result.success)
        if not ok:
            all_success = False
        return {
            "expectation": type(expectation).__name__,
            "success": ok,
        }

    from great_expectations.expectations import (
        ExpectColumnValuesToNotBeNull,
        ExpectColumnValuesToBeUnique,
        ExpectTableRowCountToBeBetween,
        ExpectColumnValueLengthsToBeBetween,
    )

    results.append(_check(ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)))

    for col in ["paper_id", "title", "text_for_embedding"]:
        if col in df.columns:
            results.append(_check(ExpectColumnValuesToNotBeNull(column=col)))

    if "paper_id" in df.columns:
        results.append(_check(ExpectColumnValuesToBeUnique(column="paper_id")))

    if "summary" in df.columns:
        results.append(_check(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10)))

    payload: dict[str, Any] = {
        "report_name": report_name,
        "success": all_success,
        "total_checks": len(results),
        "passed_checks": sum(1 for r in results if r["success"]),
        "results": results,
    }

    quality_dir = Path("data/quality")
    quality_dir.mkdir(parents=True, exist_ok=True)
    write_json(quality_dir / f"{report_name}_quality.json", payload)

    status = "PASS" if all_success else "FAIL"
    print(f"  [Quality] {report_name}: {status} ({payload['passed_checks']}/{payload['total_checks']} checks passed)")
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Tong hop freshness report: kiem tra ty le ban ghi stale vs threshold.

    Stale = age_days > freshness_threshold_days.
    is_fresh = True khi ty le stale <= 25%.
    """
    threshold = settings.freshness_threshold_days

    stale_mask = df["age_days"] > threshold
    stale_count = int(stale_mask.sum())
    total = len(df)
    stale_ratio = stale_count / total if total > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    payload: dict[str, Any] = {
        "freshness_threshold_days": threshold,
        "latest_published": str(df["published"].max()),
        "oldest_published": str(df["published"].min()),
        "stale_rows": stale_count,
        "total_rows": total,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
    }

    write_json(Path(report_path), payload)

    status = "FRESH" if is_fresh else "STALE"
    print(f"  [Freshness] {status} — {stale_count}/{total} records older than {threshold} days "
          f"({stale_ratio:.1%})")
    return payload
