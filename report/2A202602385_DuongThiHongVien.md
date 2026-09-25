# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân của thành viên TV4 — Dương Thị Hồng Viên.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                              |
| ------------------ | --------------------------------------------------------------------- |
| Họ và tên       | Dương Thị Hồng Viên                                                |
| MSSV               | 2A202602385                                                           |
| Khóa/Lớp         | K4                                                                    |
| Tên nhóm         | NoName                                                                |
| Vai trò chính    | Observability & Evaluation Lead                                       |
| Repository         | https://github.com/duongk18FPTU/K4-L3-DAY10-NoName-DataPipeline     |
| Ngày hoàn thành | 2026-09-25                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable     | File/hàm phụ trách                                                      | Input nhận vào                            | Output bàn giao                                              | Trạng thái |
| ---------------------- | ----------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------ | ---------- |
| Data Quality Gate      | `src/observability/quality.py` — `run_data_quality_checks()`           | `pd.DataFrame`, `Settings`, `report_name` | `data/quality/*_quality.json` — GX validation results       | Hoàn thành |
| Freshness SLA          | `src/observability/quality.py` — `build_freshness_report()`            | `pd.DataFrame`, `Settings`, report path   | `data/quality/*_freshness_report.json`                       | Hoàn thành |
| Evaluation Test Set    | `src/evaluation/testset.py` — `build_test_set()`                       | `pd.DataFrame`, output path               | `data/eval/test_set.json` — 10 câu hỏi 4 loại              | Hoàn thành |
| Phase 1 Report         | `src/observability/reporting.py` — `generate_phase1_report()`          | source_summary, metrics, quality, freshness | `data/reports/phase1_report.md`                             | Hoàn thành |
| Corruption Report      | `src/observability/reporting.py` — `generate_corruption_report()`      | 3 bộ metrics + quality + freshness        | `data/reports/corruption_report.md`                          | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ    | Kết quả                                                        |
| ------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------- |
| Verify Quality Gate bắt đúng lỗi trên corrupted data   | TV1 — corruption_flow.py          | Xác nhận GX FAIL 4/6 đúng theo 6 corruption scenarios của TV2 |
| Review format output của testset cho TV1 integrate      | TV1 — evaluate_pipeline()         | Đảm bảo `ground_truth_doc_ids` khớp với `paper_id` trong index |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                    | File/hàm/artifact liên quan                   | Kết quả bàn giao                                     | Cách xác minh                                           |
| ----------------------------------------- | ---------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| GX 1.x Quality Gate — 6 checks           | `quality.py` — `run_data_quality_checks()`    | PASS 6/6 baseline, FAIL 4/6 corrupted, PASS 6/6 repaired | Xem `data/quality/*_quality.json`                   |
| Freshness SLA monitoring                  | `quality.py` — `build_freshness_report()`     | FRESH 0% baseline → FRESH 13% corrupted → FRESH 0% repaired | Xem `data/quality/*_freshness_report.json`         |
| Sinh test set 10 câu hỏi                 | `testset.py` — `build_test_set()`             | `data/eval/test_set.json` — 4 loại câu hỏi            | Xem file JSON, đếm 10 entries                           |
| Báo cáo so sánh 3 trạng thái             | `reporting.py` — `generate_corruption_report` | `data/reports/corruption_report.md` — bảng 3 cột      | Mở file markdown, kiểm tra 3 cột Baseline/Corrupted/Repaired |

**Output cụ thể:** `data/quality/corrupted_quality.json` — `"success": false, "passed_checks": 4, "total_checks": 6` — bằng chứng GX 1.x bắt được data corruption trước khi dữ liệu bẩn vào serving layer.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần một "trạm kiểm soát chất lượng" tự động chặn dữ liệu bẩn vào pipeline, đo tuổi thọ dữ liệu, tạo bộ câu hỏi đánh giá chuẩn, và sinh báo cáo có thể đọc được cho cả kỹ thuật và non-technical stakeholders.

### Cách triển khai

**`run_data_quality_checks()` — GX 1.x Ephemeral Mode:**
```python
context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name=f"{report_name}_source")
data_asset = data_source.add_dataframe_asset(...)
batch_def = data_asset.add_batch_definition_whole_dataframe(...)
batch = batch_def.get_batch(batch_parameters={"dataframe": df})
```
6 Expectations: `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull` (3 cols), `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`.

**`build_freshness_report()`:**
- `stale_mask = df["age_days"] > threshold` (threshold = 180 days)
- `is_fresh = stale_ratio <= 0.25` (≤ 25% stale)

**`build_test_set()`:** Chọn 5 papers có summary dài nhất → sinh 10 câu hỏi xoay vòng qua 4 loại (summary, authors, date, categories).

**`generate_corruption_report()`:** Markdown 3-column table so sánh Baseline | Corrupted | Repaired với metrics, quality status, freshness status.

### Input, output và contract

| Thành phần              | Mô tả                                                                   |
| ------------------------ | ----------------------------------------------------------------------- |
| Input                    | `pd.DataFrame` với cột `age_days`, `paper_id`, `summary`, `text_for_embedding` |
| Output                   | JSON quality reports, Markdown reports, test_set.json                   |
| Module phụ thuộc        | `ingestion.cleaning` (TV2) — cần `age_days`, `summary_chars` đã tính   |
| Module sử dụng output   | `pipelines.phase1`, `pipelines.corruption_flow` (TV1)                   |
| Điều kiện lỗi xử lý   | DataFrame rỗng → Quality FAIL ngay (row count check); age_days missing → KeyError |

### Cách xác minh

```bash
# Kiểm tra quality reports
cat data/quality/baseline_quality.json
cat data/quality/corrupted_quality.json

# Kiểm tra test set
cat data/eval/test_set.json
```

- **Kết quả mong đợi:** baseline PASS, corrupted FAIL, repaired PASS.
- **Kết quả thực tế:** ✅ Đúng như thiết kế — bằng chứng tại `data/quality/`.
- **Artifact:** `data/quality/*_quality.json`, `data/reports/phase1_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** GX 1.x thay đổi API hoàn toàn so với phiên bản 0.x được dùng nhiều trong tutorial cũ.
- **Các phương án đã cân nhắc:**
  - (A) Dùng GX 0.x API (`DataContext`, `get_batch()` cũ) — nhiều tutorial hơn nhưng deprecated.
  - (B) Dùng GX 1.x API (`get_context(mode="ephemeral")`, `add_pandas()`) — API mới, ít tài liệu hơn.
- **Phương án đã chọn:** (B) — GX 1.x theo yêu cầu bài lab.
- **Lý do:** Bài lab yêu cầu GX 1.x; ephemeral mode không cần file system setup, phù hợp CI/CD.
- **Bằng chứng:** Quality Gate chạy thành công 3 lần (baseline, corrupted, repaired) với đúng kết quả mong đợi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Import `from great_expectations.expectations import ExpectColumnValueLengthsToBeBetween` thất bại — `ImportError`.
- **Lệnh tái hiện:** `python -c "from great_expectations.expectations import ExpectColumnValueLengthsToBeBetween"`
- **Nguyên nhân gốc:** GX 1.x đổi tên và vị trí import của một số Expectations so với 0.x.
- **Cách xử lý:** Kiểm tra GX 1.x release notes, tìm đúng import path, test từng Expectation riêng.
- **Xác minh sau sửa:** `run_data_quality_checks()` chạy 6 checks thành công, `baseline_quality.json` có 6 results.
- **Điều học được:** Luôn pin version trong `requirements.txt` và đọc changelog khi upgrade major version.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → Vector Index:** TV2 parse Crossref → clean DataFrame có `text_for_embedding` → TV3/TV1 embed qua `all-MiniLM-L6-v2` → ChromaDB lưu vectors. TV4 không tham gia bước này nhưng cần output (DataFrame) để chạy Quality Gate.

2. **Evaluation set:** `build_test_set()` của TV4 tạo 10 câu hỏi với `ground_truth` và `ground_truth_doc_ids`. `evaluate_pipeline()` của TV1 dùng test set này → ChromaDB retrieve → LLM answer → tính hit_rate, token_f1, judge_accuracy.

3. **Quality checks vs Freshness:** Quality = "data đúng chưa?" (schema, completeness, uniqueness). Freshness = "data còn mới không?" (age_days vs threshold). Corruption scenario 5 (lùi ngày) tác động freshness; scenario 2+3 (blank/noise summary) tác động quality.

4. **Cùng test set:** Giữ nguyên test set cho 3 trạng thái để isolate variable — chỉ data trong index thay đổi. Nếu thay test set thì không biết metric thay đổi do câu hỏi khó hơn hay do data xấu hơn.

5. **Repair thành công khi:** `repaired_quality.json` có `"success": true` (6/6) VÀ `repaired_metrics.json` có `retrieval_hit_rate = 1.0` và `mean_token_f1 = 0.576` = baseline values.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                  |
| -------------------- | -------: | --------: | -------: | -------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |    1.000 |     1.000 |    1.000 | Vector embedding robust trước noise text — ChromaDB vẫn tìm đúng doc                  |
| `mean_token_f1`      |    0.576 |     0.550 |    0.576 | Summary bị xóa → LLM answer thiếu chi tiết → F1 giảm; repair khôi phục hoàn toàn     |
| `judge_accuracy`     |    0.500 |     0.500 |    0.500 | LLM judge ổn định — câu hỏi factual (date, authors) vẫn được trả lời đúng             |
| Quality checks       |   6/6 ✅ |    4/6 ❌ |   6/6 ✅ | Blank summary → fail length check; duplicate rows → fail uniqueness. Đúng kỳ vọng    |
| Freshness status     |  FRESH 0% | FRESH 13% |  FRESH 0% | 3/23 records stale (13%) < 25% threshold → vẫn FRESH nhưng tăng rõ ràng               |

### Kết luận từ số liệu

1. **[Blank summary + duplicate rows] → [Quality FAIL: length check + uniqueness check] → [Token F1: 0.576 → 0.550]** — Data bẩn bị GX bắt ngay; tác động đến answer quality dù retrieval không giảm.
2. **[Idempotent repair từ raw snapshot] → [Quality PASS 6/6, Freshness 0% stale] → [Token F1 = 0.576 = Baseline]** — Repair hoàn toàn — cả data quality lẫn model performance đều về baseline.

**Kết quả khác kỳ vọng:** Freshness vẫn "FRESH" sau corruption (13% < 25% threshold). Kỳ vọng ban đầu là sẽ STALE. Giả thuyết: corruption chỉ lùi 3–4 records (sample với random_state=13), chiếm 13% < ngưỡng 25%.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** GX 1.x ephemeral mode là cách đúng để integrate quality checks vào pipeline không cần persistent context — phù hợp CI/CD.
2. **Data quality:** Freshness threshold cần được calibrate theo business context — 25% stale có thể là acceptable cho research data nhưng không acceptable cho financial data.
3. **RAG impact:** Quality Gate bắt được data issues trước khi ảnh hưởng đến users — đây là giá trị cốt lõi của observability layer trong production RAG systems.

### Nếu có thêm thời gian

Thêm GX Expectation cho `age_days >= 0` (invalid future dates) và `summary_chars > 100` (quality threshold). Đo cải thiện bằng tỷ lệ "false negative" — data bẩn lọt qua mà không bị bắt.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Dương Thị Hồng Viên
**Ngày xác nhận:** 2026-09-25
