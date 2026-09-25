# Bàn giao TV3 — Ngô Minh Trí

Ngày: 2026-09-25. Phạm vi: QA retrieval/index và demo agent theo PHAN_CONG.md.

## Kết quả đã xác minh

- 745 kiểm tra tích hợp thành công; MiniLM thật, vector 384 chiều, Chroma thật.
- 7 unit test agent thành công.
- Baseline/repaired: 24 documents; corrupted: 23 dòng nhưng chỉ 20 paper duy nhất (4 paper bị loại, 3 dòng trùng).
- Kiểm tra lookup, search, persistence, rebuild không tăng số documents, repair lặp lại không đổi và collection không ảnh hưởng lẫn nhau.
- Dùng cùng 96 câu hỏi (24 paper × 4 loại) cho cả ba trạng thái. Đây là probe TV3, không phải evaluation set hoặc metrics chính thức của TV4/TV1.

| Chỉ số probe | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Semantic hit@4 | 0.96875 | 0.78125 | 0.96875 |
| QA hit@4 | 1.00000 | 0.83333 | 1.00000 |
| Token F1, 96 câu | 0.75000 | 0.55820 | 0.75000 |
| Token F1, 72 reference không rỗng | 1.00000 | 0.74426 | 1.00000 |

Bằng chứng: `report/tv3_preflight.json`, `report/tv3_verification.json`.
Toàn bộ 24 paper thiếu categories nên 24 reference loại categories rỗng; công thức F1 cho điểm 0. Không diễn giải F1 baseline 0.75 thành 25% câu trả lời sai nội dung.

## Chạy lại

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_tv3*.py' -v
.venv/bin/python script/verify_tv3.py
```

Lần đầu cần mạng để tải MiniLM. Trên máy đã chạy, cache nằm ở `../.cache/huggingface`; dùng `HF_HOME=../.cache/huggingface HF_HUB_OFFLINE=1` trước lệnh verify để tái sử dụng. Có thể truyền `--run-date` bằng timestamp trong verification JSON để cố định thời gian. Database và chi tiết probe nằm trong `data/tv3/`, được ignore khỏi Git.

Demo sau khi build index:

```bash
LLM_MODEL=gemini-3.8-flash .venv/bin/python -m retrieval.agent \
  --manifest data/tv3/embeddings/papers_embeddings.json \
  --question "Who authored the paper 'Reliable retrieval-augmented feature generation with large language model reasoning'? Include its paper_id."
```

Cần cấu hình provider Gemini và API key cục bộ. Phiên thử model gemini-2.5-flash trả GoogleModelNotFoundError; override model chỉ cho tiến trình demo. Hai câu live đã lưu bằng chứng trả đúng tác giả/ngày và gọi lookup_paper. Câu hỏi paper không tồn tại chưa có kết quả lưu nên chưa xác nhận demo từ chối thành công. DOI trong câu trả lời ngày bị model chèn newline; cần kiểm tra trích dẫn trước khi trình diễn. Chi tiết hai câu: `report/tv3_agent_demo.json`.

## Vấn đề bàn giao

- TV1: `answer_question()` có thể trả tác giả paper gần nhất khi tên được hỏi không tồn tại. `lookup()` trả None đúng; cần xử lý ở tầng QA theo quyền sở hữu nhóm. Agent đã được hướng dẫn exact lookup, nhưng chưa có bằng chứng live cho ca không tồn tại.
- TV4: xử lý/reference thiếu categories minh bạch khi tạo evaluation set.
- Chưa chạy LLM judge, Ragas, quality/freshness chính thức hoặc pipeline chính thức trong đợt xác minh TV3. Không dùng số probe để thay thế các metrics này.
- FakeListChatModel không hỗ trợ tool calling; agent báo lỗi rõ khi provider mock. Dùng QA offline để kiểm tra không cần API.
- TV1 cập nhật TEAM: Ngô Minh Trí / 2A202602993 / TV3 RAG & Agent QA / báo cáo `report/2A202602993_NgoMinhTri.md`.
