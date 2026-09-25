# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân của thành viên TV2 — Trần Nhật Minh.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                              |
| ------------------ | --------------------------------------------------------------------- |
| Họ và tên       | Trần Nhật Minh                                                      |
| MSSV               | 2A202602483                                                           |
| Khóa/Lớp         | K4                                                                    |
| Tên nhóm         | NoName                                                                |
| Vai trò chính    | Data Foundation Owner                                                 |
| Repository         | https://github.com/duongk18FPTU/K4-L3-DAY10-NoName-DataPipeline     |
| Ngày hoàn thành | 2026-09-25                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable     | File/hàm phụ trách                                                       | Input nhận vào                          | Output bàn giao                               | Trạng thái |
| ---------------------- | ------------------------------------------------------------------------- | ---------------------------------------- | --------------------------------------------- | ---------- |
| Ingestion từ Crossref  | `src/ingestion/crossref.py` — `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | Crossref API / JSON snapshot | `data/raw/crossref_records.json` — list `PaperRecord` | Hoàn thành |
| Cleaning & modeling    | `src/ingestion/cleaning.py` — `build_clean_dataframe()`                  | `list[PaperRecord]`, `run_date`          | `pd.DataFrame` với 17 cột chuẩn              | Hoàn thành |
| Corruption simulation  | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()`              | Clean DataFrame                          | Corrupted DataFrame, `corruption_log.json`   | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ    | Kết quả                                          |
| ------------------------------------------------------- | --------------------------------- | ------------------------------------------------- |
| Cung cấp raw snapshot `crossref_records.json`           | TV3, TV4 — dữ liệu test          | TV3 verify được ChromaDB index ngay khi TV2 xong |
| Hỗ trợ TV1 debug idempotent repair                      | TV1 — `corruption_flow.py`       | Xác nhận `load_raw_records()` → `build_clean_dataframe()` tạo lại đúng 24 rows |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện            | File/hàm/artifact liên quan              | Kết quả bàn giao                                   | Cách xác minh                                   |
| --------------------------------- | ----------------------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Parse Crossref JSON payload       | `crossref.py` — `parse_crossref_payload` | 24 `PaperRecord` objects đúng schema               | `load_raw_records()` trả về 24 records không lỗi |
| Build clean DataFrame             | `cleaning.py` — `build_clean_dataframe`  | DataFrame 24 rows × 17 columns, `age_days` đúng    | `papers_clean.csv` — kiểm tra `age_days >= 0`   |
| Inject 6 corruption scenarios     | `corruption.py`                          | `papers_clean_corrupted.csv`, `corruption_log.json` | Quality Gate báo FAIL 4/6 sau corruption         |
| Idempotent repair đảm bảo đúng   | `crossref.py` + `cleaning.py` kết hợp   | Repaired DataFrame = Baseline (24 rows sạch)        | `repaired_metrics["retrieval_hit_rate"] == 1.0` |

**Output cụ thể:** `data/results/corruption_log.json` — ghi lại 6 loại corruption với chính xác các index bị tác động, là bằng chứng audit trail của data lineage.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref API trả về JSON phức tạp với nhiều trường optional, nested, và chứa HTML tags (`<jats:p>`) trong abstract. Cần bóc tách, chuẩn hóa và tạo một schema nhất quán cho các module downstream.

### Cách triển khai

**`parse_crossref_payload()`:** Duyệt qua `payload["message"]["items"]`, với mỗi item:
- DOI → `paper_id` (chuẩn hóa lowercase)
- `title[0]` → normalize whitespace
- `abstract` → `re.sub(r"<[^>]+>", "", ...)` loại bỏ JATS XML tags
- `author[]` → join `given + family`
- Date parsing: ưu tiên `published-print` > `published-online`
- Chỉ giữ record nếu có đủ `paper_id + title + summary`

**`build_clean_dataframe()`:** Nhận `list[PaperRecord]`, tính:
- `age_days = (run_date - published_date).days`
- `authors_joined = ", ".join(authors)`
- `text_for_embedding = "Title: {}\nAuthors: {}\nPublished: {}\nCategories: {}\nSummary: {}"`
- Drop duplicates theo `paper_id`

**`corrupt_clean_dataframe()`:** 6 kịch bản tuần tự:
1. Drop 20% records mới nhất (data loss simulation)
2. Blank summary 3–5 rows (completeness violation)
3. Inject noise vào summary (validity violation)
4. Truncate title → 7 ký tự (validity violation)
5. Lùi ngày 365 ngày + cộng `age_days` (freshness violation)
6. Duplicate 3 rows (uniqueness violation)

### Input, output và contract

| Thành phần              | Mô tả                                                                |
| ------------------------ | -------------------------------------------------------------------- |
| Input                    | Crossref JSON hoặc snapshot file; `run_date: datetime` (UTC)        |
| Output                   | `pd.DataFrame` với cột `text_for_embedding`, `age_days`, `summary_chars` |
| Module phụ thuộc        | `core.utils.PaperRecord`, `core.utils.write_json`                   |
| Module sử dụng output   | `retrieval.index.LocalEmbeddingIndex`, `observability.quality`, `evaluation.testset` |
| Điều kiện lỗi xử lý   | Record thiếu DOI/title/abstract → bỏ qua; date parse fail → `None` fallback |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"
python script/run_phase1.py
```

- **Kết quả mong đợi:** `[2/8] Cleaning & normalizing data... → 24 clean rows.`
- **Kết quả thực tế:** ✅ 24 rows, tất cả cột required đều có giá trị, `age_days >= 0`
- **Artifact:** `data/clean/papers_clean.csv`, `data/results/corruption_log.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi corrupt dữ liệu, có thể vá trực tiếp dataframe (patch-in-place) hoặc rebuild từ raw snapshot.
- **Các phương án đã cân nhắc:**
  - (A) Patch corrupted DataFrame → nhanh nhưng không đảm bảo sạch hoàn toàn (có thể còn residual artifacts).
  - (B) Reload raw + rebuild toàn bộ qua `build_clean_dataframe()` → chậm hơn nhưng idempotent.
- **Phương án đã chọn:** (B) — Idempotent rebuild từ raw snapshot.
- **Lý do:** Đảm bảo repaired data = original clean data, không có "residual corruption". Đây là best practice trong data engineering (immutable raw layer).
- **Bằng chứng:** `repaired_metrics.json` — `retrieval_hit_rate = 1.000` và `mean_token_f1 = 0.576` = baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `KeyError: 'message'` khi parse Crossref response — một số API response có cấu trúc khác.
- **Lệnh tái hiện:** Khi response là `{"status": "ok", "message-type": "work-list", "message": {...}}` vs response bị cắt.
- **Nguyên nhân gốc:** Crossref API response lồng nhau sâu, không phải lúc nào cũng có đủ key.
- **Cách xử lý:** Thêm `.get()` defensive coding + validate `if paper_id and title and summary` trước khi append.
- **Xác minh sau sửa:** 24/24 records parse thành công, không có `PaperRecord` bị bỏ qua do lỗi.
- **Điều học được:** Luôn dùng `.get()` thay vì `[]` khi parse API response không có schema cố định.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → Vector Index:** `fetch_source_records()` gọi API → `parse_crossref_payload()` tạo `list[PaperRecord]` → `build_clean_dataframe()` tạo DataFrame → `LocalEmbeddingIndex.build()` encode `text_for_embedding` → ChromaDB lưu vector.

2. **Evaluation set:** Test set dùng `paper_id` làm `ground_truth_doc_ids`. Khi ChromaDB retrieval trả về doc có `paper_id` khớp → hit. `mean_token_f1` so sánh token overlap giữa LLM answer và `ground_truth`.

3. **Quality checks vs Freshness:** Quality checks kiểm tra schema integrity (null, unique, length). Freshness đo thời gian sống của dữ liệu — corruption scenario 5 (lùi ngày) trực tiếp trigger freshness warning.

4. **Cùng test set:** Giữ nguyên test set đảm bảo biến kiểm soát duy nhất là dữ liệu trong index. Nếu thay test set, không biết metric thay đổi do câu hỏi hay data.

5. **Repair thành công:** `data/quality/repaired_quality.json` có `"success": true` VÀ `data/results/repaired_metrics.json` có `retrieval_hit_rate = 1.0` = baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                   |
| -------------------- | -------: | --------: | -------: | ----------------------------------------------------------------------- |
| `retrieval_hit_rate` |    1.000 |     1.000 |    1.000 | Vector embedding đủ robust để ignore noise trong text                   |
| `mean_token_f1`      |    0.576 |     0.550 |    0.576 | Blank summary làm LLM trả lời thiếu thông tin → F1 giảm                |
| `judge_accuracy`     |    0.500 |     0.500 |    0.500 | LLM judge không bị ảnh hưởng nhiều — câu hỏi factual vẫn trả lời được |
| Quality checks       |   6/6 ✅ |    4/6 ❌ |   6/6 ✅ | Blank summary + duplicate → 2 checks fail, đúng như thiết kế            |
| Freshness status     |  FRESH 0% | FRESH 13% |  FRESH 0% | 3/23 records stale sau lùi ngày, dưới ngưỡng 25% nên vẫn FRESH         |

### Kết luận từ số liệu

1. **[Blank summary + truncate title] → [Quality FAIL: null check + length check] → [Token F1: 0.576 → 0.550]** — Data thiếu nội dung làm LLM answer kém chính xác dù retrieval vẫn tìm đúng doc.
2. **[Rebuild từ raw snapshot] → [Quality PASS 6/6, Freshness 0% stale] → [Token F1 = 0.576 = Baseline]** — Idempotent repair chứng minh giá trị của raw lineage preservation.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw snapshot là "nguồn sự thật duy nhất" — không bao giờ overwrite, luôn rebuild từ đó khi cần repair.
2. **Data quality:** Các corruption khác nhau ảnh hưởng các metric khác nhau — blank summary → F1, duplicate → uniqueness check, stale date → freshness.
3. **RAG impact:** Retrieval (hit rate) robust hơn generation (token F1) trước data corruption — embedding còn capture được context từ title ngay cả khi summary trống.

### Nếu có thêm thời gian

Thêm exponential backoff retry cho Crossref API và cache raw response để giảm API calls. Đo cải thiện bằng tỷ lệ thành công khi API rate limit.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Nhật Minh
**Ngày xác nhận:** 2026-09-25
