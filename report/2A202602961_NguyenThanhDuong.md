# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân của thành viên TV1 — Nguyễn Thanh Dương.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                       |
| ------------------ | ------------------------------------------------------------------------------ |
| Họ và tên       | Nguyễn Thanh Dương                                                           |
| MSSV               | 2A202602961                                                                    |
| Khóa/Lớp         | K4                                                                             |
| Tên nhóm         | NoName                                                                         |
| Vai trò chính    | Pipeline Lead & Integrator (Trưởng nhóm)                                    |
| Repository         | https://github.com/duongk18FPTU/K4-L3-DAY10-NoName-DataPipeline              |
| Ngày hoàn thành | 2026-09-25                                                                     |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable        | File/hàm phụ trách                          | Input nhận vào                                   | Output bàn giao                                   | Trạng thái    |
| ------------------------- | -------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- | ------------- |
| Baseline Pipeline         | `src/pipelines/phase1.py` — `main()`       | Settings, raw records, các module TV2/TV3/TV4      | `data/reports/phase1_report.md`, metrics, CSV/JSON | Hoàn thành    |
| Corruption & Repair Flow  | `src/pipelines/corruption_flow.py` — `main()` | Baseline clean dataset, corruption module TV2   | `data/reports/corruption_report.md`, 3 bộ metrics  | Hoàn thành    |
| Team Documentation        | `docs/TEAM.md`, `PHAN_CONG.md`             | Thông tin nhóm, phân công vai trò                  | File markdown hoàn chỉnh                           | Hoàn thành    |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ          | Kết quả                                                                              |
| ------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------- |
| Implement TV4 modules (quality.py, testset.py, reporting.py) khi TV4 chưa xong | TV4 — Dương Thị Hồng Viên | Pipeline chạy thông, phase1 & corruption flow hoàn tất 100% |
| Pull & merge code của TV2, TV3 vào main                | TV2 — Trần Nhật Minh, TV3 — Ngô Minh Trí | Tích hợp thành công, không conflict |
| Fix lỗi Unicode encoding khi chạy trên Windows terminal | Toàn pipeline                          | Thêm `PYTHONIOENCODING=utf-8`, pipeline chạy ổn định |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện              | File/hàm/artifact liên quan                        | Kết quả bàn giao                              | Cách xác minh                              |
| ------------------------------------ | ---------------------------------------------------- | --------------------------------------------- | ------------------------------------------ |
| Orchestrate 8 bước baseline pipeline | `src/pipelines/phase1.py`                          | `data/reports/phase1_report.md`               | `python script/run_phase1.py` → exit 0    |
| Orchestrate 9 bước corruption flow   | `src/pipelines/corruption_flow.py`                 | `data/reports/corruption_report.md`           | `python script/run_corruption_flow.py` → exit 0 |
| Build ChromaDB index baseline        | `retrieval/index.py` — `LocalEmbeddingIndex.build` | Collection `papers-baseline` (24 docs)         | Hit Rate = 1.000                           |
| Điều phối Quality Gate               | `observability/quality.py`                         | `data/quality/baseline_quality.json` — PASS 6/6 | Xem JSON artifact                        |

**Output cụ thể:** `data/reports/corruption_report.md` — bảng so sánh 3 cột xác nhận pipeline hoạt động đúng chu trình: Baseline (PASS) → Corrupted (FAIL) → Repaired (PASS).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

TV1 đóng vai "nhạc trưởng": các module của TV2, TV3, TV4 là các "nhạc cụ" riêng lẻ — phase1.py và corruption_flow.py là bản nhạc điều phối chúng chạy đúng thứ tự và truyền đúng artifact cho nhau.

### Cách triển khai

**phase1.py** theo mô hình pipeline tuyến tính 8 bước:
1. Load settings (offline fallback nếu không có API).
2. Fetch hoặc load raw records từ snapshot.
3. Build clean DataFrame qua `build_clean_dataframe()`.
4. Lưu CSV + JSON ra `data/clean/`.
5. Build ChromaDB index `papers-baseline` qua `LocalEmbeddingIndex.build()`.
6. Sinh 10 câu hỏi evaluation qua `build_test_set()`.
7. Đánh giá RAG baseline qua `evaluate_pipeline()`.
8. Chạy Quality Gate (GX 1.x) + Freshness SLA + sinh báo cáo markdown.

**corruption_flow.py** theo mô hình 9 bước, thêm 3 trạng thái song song (Baseline ← từ pha 1 / Corrupted / Repaired) rồi so sánh cuối cùng.

Thiết kế **Idempotent Repair**: bước sửa chữa không vá dữ liệu bẩn mà load lại từ `raw_records.json` và chạy lại clean hoàn toàn — đảm bảo kết quả repaired = baseline.

### Input, output và contract

| Thành phần              | Mô tả                                                                    |
| ------------------------ | ------------------------------------------------------------------------ |
| Input                    | `Settings` object, `data/raw/crossref_records.json`, module functions từ TV2/TV3/TV4 |
| Output                   | 2 file markdown report, 6 JSON metrics files, 3 bộ CSV/JSON clean data  |
| Module phụ thuộc        | `ingestion.*`, `retrieval.*`, `evaluation.*`, `observability.*`          |
| Điều kiện lỗi xử lý | FileNotFoundError nếu thiếu raw snapshot; NotImplementedError nếu TV khác chưa implement |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Exit code 0, in ra bảng 3-STATE COMPARISON SUMMARY.
- **Kết quả thực tế:** ✅ Cả 2 script chạy thành công, 21 artifact được sinh ra.
- **Artifact:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi TV4 chưa implement xong các module, pipeline bị block hoàn toàn.
- **Các phương án đã cân nhắc:**
  - (A) Chờ TV4 implement — rủi ro time block, bài lab không chạy được.
  - (B) TV1 implement luôn module của TV4 theo đúng pseudo-code trong PHAN_CONG.md.
- **Phương án đã chọn:** (B) — Implement TV4's modules, commit riêng với message rõ ràng.
- **Lý do:** Tránh block toàn nhóm; code TV4 đã có pseudo-code chi tiết sẵn trong PHAN_CONG.md nên implement nhanh và đúng spec.
- **Bằng chứng:** Commit `fa34a6b` — quality gate PASS 6/6 lần đầu chạy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`
- **Lệnh tái hiện:** `python script/run_phase1.py` trên Windows terminal (CP1252 encoding)
- **Nguyên nhân gốc:** Python trên Windows mặc định dùng CP1252 cho stdout; các ký tự Unicode như `→`, `✅`, `📊` không nằm trong bảng mã này.
- **Cách xử lý:** Thêm `$env:PYTHONIOENCODING="utf-8"` trước khi chạy.
- **Xác minh sau sửa:** `$env:PYTHONIOENCODING="utf-8"; python script/run_phase1.py` → exit 0, in đúng toàn bộ ký tự.
- **Điều học được:** Luôn set `PYTHONIOENCODING=utf-8` trong CI/CD environment cho dự án đa nền tảng.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → Vector Index:** Crossref API trả về JSON → `parse_crossref_payload()` bóc tách thành `PaperRecord` → `build_clean_dataframe()` normalize + tính `age_days` + tạo `text_for_embedding` → `LocalEmbeddingIndex.build()` encode văn bản bằng `all-MiniLM-L6-v2` và nạp vào ChromaDB collection.

2. **Evaluation set:** `build_test_set()` sinh 10 câu hỏi có `ground_truth` và `ground_truth_doc_ids = [paper_id]`. `evaluate_pipeline()` dùng ChromaDB search → so sánh retrieved doc_ids với ground_truth_doc_ids → tính `retrieval_hit_rate`; dùng LLM judge → tính `judge_accuracy`.

3. **Quality checks vs Freshness:** Quality checks (GX 1.x) kiểm tra tính toàn vẹn cấu trúc dữ liệu (null, unique, length). Freshness monitoring kiểm tra tính thời gian — `age_days > threshold` → SLA stale ratio. Hai cơ chế bổ sung nhau: một cái đo "đúng" (completeness/validity), một cái đo "mới" (timeliness).

4. **Cùng test set:** Dùng cùng `test_set.json` cho 3 trạng thái đảm bảo so sánh công bằng — chỉ có dữ liệu trong index thay đổi, không phải câu hỏi. Nếu thay test set thì không thể biết metric thay đổi do data hay do câu hỏi khác.

5. **Repair thành công khi:** `repaired_quality["success"] == True` (6/6 GX checks pass) VÀ `repaired_metrics["retrieval_hit_rate"]` ≈ `baseline_metrics["retrieval_hit_rate"]`. Artifact xác minh: `data/quality/repaired_quality.json` và `data/results/repaired_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                               |
| -------------------- | -------: | --------: | -------: | ------------------------------------------------------------------- |
| `retrieval_hit_rate` |    1.000 |     1.000 |    1.000 | ChromaDB vẫn tìm được doc ngay cả khi summary bị xáo trộn nhẹ     |
| `mean_token_f1`      |    0.576 |     0.550 |    0.576 | F1 giảm 2.6% khi data bẩn, phục hồi hoàn toàn sau repair          |
| `judge_accuracy`     |    0.500 |     0.500 |    0.500 | LLM judge ổn định; corruption ảnh hưởng ít đến câu trả lời cuối   |
| Quality checks       |   6/6 ✅ |    4/6 ❌ |   6/6 ✅ | GX bắt được lỗi null summary + duplicate paper_id sau corruption   |
| Freshness status     |  FRESH 0% |  FRESH 13% |  FRESH 0% | Stale tăng do corruption lùi ngày, repair khôi phục hoàn toàn     |

### Kết luận từ số liệu

1. **[Blank summary + truncate title] → [Quality FAIL: summary length check + null check] → [Token F1 giảm 0.026]** — Dữ liệu thiếu summary khiến embedding kém chất lượng, trả lời không đầy đủ.
2. **[Idempotent Repair từ raw snapshot] → [Quality PASS 6/6, Freshness 0% stale] → [Token F1 = 0.576 = Baseline]** — Repair hoàn toàn bằng cách rebuild từ nguồn, không patch dữ liệu bẩn.

**Kết quả khác kỳ vọng:** `retrieval_hit_rate` không giảm khi corrupt (vẫn 1.000). Giả thuyết: ChromaDB vector similarity đủ mạnh để tìm đúng document ngay cả khi text embedding bị noise nhẹ. Kiểm tra: xem `corrupted_answers.json` — retrieved doc_ids vẫn đúng 10/10.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline design:** Idempotent pipeline (luôn rebuild từ raw) quan trọng hơn incremental patch — đảm bảo reproducibility và tránh "silent corruption accumulation".
2. **Data observability:** Great Expectations 1.x API thay đổi hoàn toàn so với 0.x — `get_context(mode="ephemeral")` + `add_pandas()` là pattern mới cần nắm.
3. **Data → RAG impact:** Không phải mọi corruption đều ảnh hưởng đến retrieval hit rate; blank summary ảnh hưởng Token F1 nhiều hơn retrieval accuracy vì embedding vẫn capture được context từ title.

### Nếu có thêm thời gian

Thêm alert notification khi Quality Gate FAIL — ví dụ gửi Slack webhook với tóm tắt kết quả. Đo cải thiện bằng cách so sánh MTTR (Mean Time To Repair) trước và sau khi có alert.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thanh Dương
**Ngày xác nhận:** 2026-09-25
