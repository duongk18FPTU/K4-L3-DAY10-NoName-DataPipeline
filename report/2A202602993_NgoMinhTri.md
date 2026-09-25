# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân của thành viên TV3 — Ngô Minh Trí.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                              |
| ------------------ | --------------------------------------------------------------------- |
| Họ và tên       | Ngô Minh Trí                                                        |
| MSSV               | 2A202602993                                                           |
| Khóa/Lớp         | K4                                                                    |
| Tên nhóm         | NoName                                                                |
| Vai trò chính    | RAG & Agent Specialist                                                |
| Repository         | https://github.com/duongk18FPTU/K4-L3-DAY10-NoName-DataPipeline     |
| Ngày hoàn thành | 2026-09-25                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable        | File/hàm phụ trách                                                  | Input nhận vào                             | Output bàn giao                                          | Trạng thái |
| ------------------------- | -------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------- | ---------- |
| Retrieval verification    | `script/verify_tv3.py`, `script/test_tv3_retrieval.py`             | Clean DataFrame từ TV2                      | `report/tv3_verification.json`, `report/TV3_results.json` | Hoàn thành |
| Agent demo extension      | `src/retrieval/agent.py` — `build_agent()`, `answer_question()`    | ChromaDB index, LLM config                  | Agent trả lời câu hỏi end-to-end                          | Hoàn thành |
| Test suite                | `tests/test_tv3_agent.py`                                           | Agent instance                              | Test cases pass                                           | Hoàn thành |
| Handoff documentation     | `report/TV3_HANDOFF.md`                                             | Kết quả verification                        | Tài liệu bàn giao cho TV1 tích hợp                        | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                     | Thành viên/module được hỗ trợ | Kết quả                                                     |
| ---------------------------------------------- | ------------------------------ | ------------------------------------------------------------ |
| Verify clean data format phù hợp ChromaDB      | TV2 — cleaning.py              | Xác nhận `text_for_embedding` đúng format, 24 docs nạp OK  |
| Cung cấp preflight report cho TV1 tích hợp     | TV1 — phase1.py                | `tv3_preflight.json` xác nhận index hoạt động trước khi TV1 chạy |
| Debug collection name conflict trong ChromaDB  | TV1 — corruption_flow.py       | Phát hiện 3 collection cần tên khác nhau để tránh conflict  |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                  | File/hàm/artifact liên quan          | Kết quả bàn giao                                       | Cách xác minh                                        |
| ---------------------------------------- | ------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------- |
| Test ChromaDB index baseline             | `LocalEmbeddingIndex.build()`        | Collection `papers-tv3-test` — 24 documents indexed     | `tv3_verification.json` — `documents_indexed: 24`   |
| Verify retrieval accuracy                | `script/test_tv3_retrieval.py`       | `TV3_results.json` — hit rate, response time            | Hit rate = 1.000 trên 10 queries test                |
| Mở rộng và test Agent                   | `src/retrieval/agent.py`             | Agent trả lời coherent với context từ ChromaDB          | `tv3_agent_demo.json` — 3 demo Q&A                  |
| Đo embedding performance                | `script/verify_tv3.py`              | Embedding time, index build time được ghi lại           | Log trong `tv3_preflight.json`                       |

**Output cụ thể:** `report/tv3_verification.json` — xác minh độc lập ChromaDB hoạt động đúng trước khi TV1 chạy full pipeline; là "green light" để TV1 bắt đầu integration.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module `retrieval/` đã được implement sẵn. TV3 cần đảm bảo: (1) data từ TV2 đúng format để nạp vào ChromaDB, (2) index hoạt động đúng trước khi TV1 chạy full pipeline, (3) agent trả lời coherent.

### Cách triển khai

**Verification workflow (`verify_tv3.py`):**
1. Load clean DataFrame từ `data/clean/papers_clean.json`.
2. Gọi `LocalEmbeddingIndex.build(df, settings)` với collection name `papers-tv3-test` (riêng biệt, không conflict với pipeline chính).
3. Thực hiện 5 test queries với similarity search.
4. Đo response time, kiểm tra retrieved doc_ids có trong DataFrame.
5. Ghi kết quả ra `tv3_verification.json` và `tv3_preflight.json`.

**Agent extension (`agent.py`):**
- `build_agent()`: Khởi tạo chain kết nối ChromaDB retriever + LLM provider.
- `answer_question()`: Nhận câu hỏi → retrieve top-k docs → format context → LLM generate answer.
- Thêm error handling khi LLM không available (mock response fallback).

**Test suite (`test_tv3_agent.py`):**
- Test `build_agent()` với mock settings.
- Test `answer_question()` với câu hỏi mẫu.
- Test edge case: câu hỏi không có context phù hợp.

### Input, output và contract

| Thành phần              | Mô tả                                                             |
| ------------------------ | ----------------------------------------------------------------- |
| Input                    | `pd.DataFrame` với cột `text_for_embedding`, `paper_id`; `Settings` object |
| Output                   | ChromaDB collection với documents indexed; Agent trả về `str` answer |
| Module phụ thuộc        | `ingestion.cleaning` (TV2), `core.config`                        |
| Module sử dụng output   | `pipelines.phase1` (TV1), `pipelines.corruption_flow` (TV1)      |
| Điều kiện lỗi xử lý   | Empty collection → raise ValueError; LLM timeout → mock fallback |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"
python script/verify_tv3.py
python script/test_tv3_retrieval.py
```

- **Kết quả mong đợi:** 24 docs indexed, hit rate = 1.000 trên test queries.
- **Kết quả thực tế:** ✅ `tv3_verification.json` — `"documents_indexed": 24`, hit rate = 1.0
- **Artifact:** `report/tv3_verification.json`, `report/TV3_results.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi test ChromaDB, nên dùng chung collection `papers-baseline` hay tạo collection riêng?
- **Các phương án đã cân nhắc:**
  - (A) Dùng chung `papers-baseline` — tiện nhưng có thể conflict khi TV1 cũng build index cùng lúc.
  - (B) Tạo collection riêng `papers-tv3-test` — độc lập, không ảnh hưởng pipeline chính.
- **Phương án đã chọn:** (B) — Collection riêng biệt cho verification.
- **Lý do:** Đảm bảo TV3 test không làm hỏng state của pipeline chính; TV1 có thể build collection chính thức sau khi TV3 verify xong.
- **Bằng chứng:** Pipeline TV1 chạy không bị ảnh hưởng, `papers-baseline` collection sạch khi TV1 build.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `ValueError: Collection papers-baseline already exists` khi chạy `verify_tv3.py` lần 2.
- **Lệnh tái hiện:** Chạy `python script/verify_tv3.py` lần 2 trên cùng ChromaDB instance.
- **Nguyên nhân gốc:** ChromaDB không auto-overwrite collection — cần delete hoặc dùng tên khác.
- **Cách xử lý:** Đổi sang collection name `papers-tv3-test`; TV1 dùng tên chính thức `papers-baseline`.
- **Xác minh sau sửa:** `verify_tv3.py` chạy idempotent nhiều lần không báo lỗi.
- **Điều học được:** ChromaDB collection management cần xử lý cẩn thận trong stateful environments; luôn dùng tên riêng biệt cho test vs production collections.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → Vector Index:** TV2 parse Crossref → `build_clean_dataframe()` tạo `text_for_embedding` → `LocalEmbeddingIndex.build()` encode bằng `all-MiniLM-L6-v2` (384 dims) → ChromaDB lưu vectors kèm metadata `paper_id`.

2. **Evaluation set:** TV4's `build_test_set()` tạo 10 câu hỏi có `ground_truth_doc_ids`. `evaluate_pipeline()` ChromaDB search → so sánh retrieved `paper_id` với `ground_truth_doc_ids` → `retrieval_hit_rate`. LLM answer → token overlap → `mean_token_f1`.

3. **Quality checks vs Freshness:** Quality (GX 1.x) = data integrity tại thời điểm hiện tại (null, format, uniqueness). Freshness = tuổi thọ data — `age_days > 180` → stale. Corruption scenario 5 lùi ngày tác động freshness nhưng không fail quality format checks.

4. **Cùng test set:** Fixed test set = controlled experiment — chỉ data trong index thay đổi, câu hỏi giữ nguyên. Đảm bảo metric thay đổi chỉ phản ánh data quality, không phải question difficulty.

5. **Repair thành công:** `data/quality/repaired_quality.json` — `"success": true` (6/6) VÀ `data/results/repaired_metrics.json` — `retrieval_hit_rate = 1.000`, `mean_token_f1 = 0.576` = baseline values.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                          |
| -------------------- | -------: | --------: | -------: | ------------------------------------------------------------------------------ |
| `retrieval_hit_rate` |    1.000 |     1.000 |    1.000 | Vector similarity robust — noise text không làm mất khả năng tìm kiếm         |
| `mean_token_f1`      |    0.576 |     0.550 |    0.576 | Blank summary → LLM answer thiếu detail → F1 giảm 2.6%; repair hoàn toàn     |
| `judge_accuracy`     |    0.500 |     0.500 |    0.500 | Factual questions (date, authors) vẫn answered đúng dù summary corrupt         |
| Quality checks       |   6/6 ✅ |    4/6 ❌ |   6/6 ✅ | Blank summary → fail length check; duplicate → fail uniqueness. Đúng kỳ vọng  |
| Freshness status     |  FRESH 0% | FRESH 13% |  FRESH 0% | 13% stale < 25% threshold → FRESH; repair clear hoàn toàn                     |

### Kết luận từ số liệu

1. **[Blank summary + duplicate rows] → [Quality FAIL: length + uniqueness checks] → [Token F1: 0.576 → 0.550]** — ChromaDB retrieve đúng doc nhờ title embedding nhưng LLM không có summary để generate đầy đủ.
2. **[Rebuild từ raw snapshot] → [Quality PASS 6/6, Freshness 0% stale] → [Token F1 = 0.576 = Baseline]** — Idempotent repair from raw lineage fully restores pipeline quality — đây là proof of concept quan trọng nhất của bài lab.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Embedding quality phụ thuộc text quality — `text_for_embedding` cần cả title, authors, summary để đầy đủ ngữ nghĩa; mất summary → F1 giảm dù retrieval vẫn đúng.
2. **Data quality:** Retrieval (vector similarity) robust hơn generation (LLM) trước data corruption — đây là điểm yếu của RAG pipeline cần monitor riêng ở tầng generation.
3. **RAG design:** 3 ChromaDB collections riêng biệt (baseline/corrupted/repaired) là thiết kế đúng cho A/B comparison — tránh data leakage giữa các trạng thái.

### Nếu có thêm thời gian

Thêm Ragas framework để đánh giá `answer_relevance` và `context_precision` — metrics phong phú hơn judge_accuracy đơn giản. Đo cải thiện bằng correlation giữa Ragas scores và Quality Gate results.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Minh Trí
**Ngày xác nhận:** 2026-09-25
