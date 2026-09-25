from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.utils import normalize_whitespace, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject realistic data corruption patterns into a clean dataframe."""
    corrupted = df.copy()
    output_path = Path(output_log_path)
    log: list[dict] = []

    if corrupted.empty:
        write_json(output_path, log)
        return corrupted

    corrupted = corrupted.reset_index(drop=True)

    latest_drop_count = min(len(corrupted) - 1, max(1, int(len(corrupted) * 0.2)))
    latest_index = corrupted.sort_values("published", ascending=False).head(latest_drop_count).index.tolist()
    corrupted = corrupted.drop(index=latest_index).reset_index(drop=True)
    log.append({"action": "drop_latest_records", "count": len(latest_index), "indices": latest_index})

    blank_count = min(len(corrupted), max(3, min(5, len(corrupted) // 5)))
    blank_idx = corrupted.sample(n=blank_count, random_state=42).index.tolist()
    corrupted.loc[blank_idx, "summary"] = ""
    log.append({"action": "blank_summary", "count": len(blank_idx), "indices": blank_idx})

    noise_count = max(1, min(4, len(corrupted) // 6))
    noise_candidates = corrupted.index.difference(blank_idx)
    noise_idx = noise_candidates.to_series().sample(n=min(noise_count, len(noise_candidates)), random_state=7).tolist()
    for idx in noise_idx:
        current = str(corrupted.at[idx, "summary"] or "")
        corrupted.at[idx, "summary"] = f"@#$%NOISE@#$% {current} @#$%NOISE@#$%"
    log.append({"action": "inject_noise", "count": len(noise_idx), "indices": noise_idx})

    title_idx = corrupted.sample(n=max(1, min(3, len(corrupted) // 8)), random_state=11).index.tolist()
    for idx in title_idx:
        original = str(corrupted.at[idx, "title"] or "")
        corrupted.at[idx, "title"] = original[:7]
    log.append({"action": "truncate_title", "count": len(title_idx), "indices": title_idx})

    stale_idx = corrupted.sample(n=max(1, min(4, len(corrupted) // 6)), random_state=13).index.tolist()
    for idx in stale_idx:
        published = pd.to_datetime(corrupted.at[idx, "published"], errors="coerce")
        if pd.notna(published):
            corrupted.at[idx, "published"] = (published - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
            corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
    log.append({"action": "stale_date", "count": len(stale_idx), "indices": stale_idx})

    dup_count = min(3, len(corrupted))
    dup_idx = corrupted.sample(n=dup_count, random_state=17).index.tolist()
    duplicate_rows = corrupted.loc[dup_idx].copy()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    log.append({"action": "duplicate_rows", "count": len(dup_idx), "indices": dup_idx})

    for col in ["authors", "categories"]:
        if col in corrupted.columns:
            corrupted[col] = corrupted[col].apply(lambda x: x if isinstance(x, list) else [x] if x else [])

    if "text_for_embedding" not in corrupted.columns:
        corrupted["text_for_embedding"] = ""

    def rebuild_text(row: pd.Series) -> str:
        title = normalize_whitespace(str(row.get("title") or ""))
        authors = row.get("authors") or []
        categories = row.get("categories") or []
        published = str(row.get("published") or "")
        authors_joined = ", ".join(str(a) for a in authors if str(a).strip())
        categories_joined = ", ".join(str(c) for c in categories if str(c).strip())
        summary = normalize_whitespace(str(row.get("summary") or ""))
        return (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

    corrupted["text_for_embedding"] = corrupted.apply(rebuild_text, axis=1)
    corrupted["summary_chars"] = corrupted["summary"].str.len()
    write_json(output_path, log)
    return corrupted
