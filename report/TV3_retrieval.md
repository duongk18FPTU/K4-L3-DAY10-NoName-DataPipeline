# TV3 — Kiểm thử RAG và ChromaDB

## Phạm vi

Kiểm thử các module retrieval có sẵn bằng MiniLM và ChromaDB thật. Không thay đổi các module của TV1, TV2, TV4. Ba file TV4 (`quality.py`, `reporting.py`, `testset.py`) vẫn là khung TODO tại thời điểm kiểm tra, không có implementation TV4 cần xóa.

Đối chiếu README mục 6, CHECKPOINTS CP2 và RUBRIC mục 4: dùng đúng `sentence-transformers/all-MiniLM-L6-v2`, collection `papers-baseline`, đủ 24 tài liệu của snapshot, metadata truy vấn và Chroma persist. Script kiểm tra vector 384 chiều, hữu hạn, chuẩn hóa; nội dung/metadata đã lưu khớp đầu vào; build lại cùng collection không nhân đôi dữ liệu. Dùng `--expected-documents N` khi nhóm đổi snapshot có số tài liệu khác.

Đây là kiểm thử riêng TV3. Thư mục `data/tv3/` phục vụ kiểm chứng an toàn. Các artifact nộp bài ở `data/chroma/`, `data/results/`, `data/reports/` theo README vẫn phải do pipeline TV1 sinh ra. Không dùng kết quả smoke test thay thế `baseline_metrics.json` hoặc báo cáo GX của TV4.

## Chạy kiểm thử

```powershell
uv run python script/test_tv3_retrieval.py
```

Script dùng snapshot `data/raw/crossref_records.json` và gọi cleaning/corruption của TV2. Mỗi lần chạy tạo thư mục riêng trong `data/tv3/<run-id>/`, gồm CSV sạch, database Chroma, manifest, corruption log, câu trả lời chi tiết và `results.json`. Không ghi đè collection của pipeline chung.

Kiểm tra: schema đầu vào retrieval, DOI duy nhất, metadata không null, số document bằng số dòng, load lại index, lookup theo DOI/tiêu đề và lookup không tồn tại. Chạy semantic search trực tiếp theo tiêu đề và QA bốn dạng câu hỏi cho mọi paper trong baseline; dùng cùng câu hỏi cho corrupted/repaired. Repair đọc lại raw và so sánh DataFrame tại cùng thời điểm tính age_days.

Thời gian index đầu tiên có thể bao gồm tải/nạp model. Title-search Hit Rate@4 chỉ đo truy vấn theo tiêu đề, không đại diện mọi truy vấn ngữ nghĩa. QA có cơ chế exact-title lookup; QA exact match không phải Token F1 hoặc LLM Judge. Bộ smoke test này không thay thế bộ test RAG của TV4. Không ép chỉ số corrupted phải giảm.

`report/TV3_results.json` lưu kết quả mới nhất sau khi tất cả kiểm tra bắt buộc pass, kèm SHA-256 raw để truy vết nguồn dữ liệu. `index_seconds` và `rebuild_seconds` tách thời gian lần đầu với lần model đã có cache. Giữ cấu hình MiniLM/top-k của repo để so sánh công bằng; chưa có benchmark đủ rộng để kết luận tối ưu chất lượng trên mọi câu hỏi.

## Demo Agent (tùy chọn, gọi LLM)

Cấu hình provider và thông tin truy cập trong `.env`, sau đó chạy:

```powershell
uv run python script/test_tv3_retrieval.py --agent-question "Find papers about retrieval augmented generation and cite their DOI."
```

Nếu không truyền tùy chọn này, script không gọi LLM. Chưa xác nhận demo Agent live.

Điểm cần phối hợp trước nghiệm thu RUBRIC mục 5: router hiện dùng tên `gemini` (rubric ghi `google`); nhánh `mock` dùng `FakeListChatModel`, chưa chứng minh hỗ trợ tool calling với `create_agent`. Không ghi nhận mock/live Agent đạt chỉ từ kiểm thử QA. TV3 cần demo provider đã cấu hình; nếu muốn mở rộng router ngoài file sở hữu `agent.py`, thống nhất với nhóm trước.

## Bàn giao

Các file đóng góp: `script/test_tv3_retrieval.py`, `data/tv3/.gitignore`, báo cáo này. Điền MSSV/họ tên và đổi tên báo cáo theo quy định nhóm trước khi nộp.

## Kết quả thực chạy

Lệnh `.venv\Scripts\python.exe script/test_tv3_retrieval.py` hoàn tất với exit code 0, PASS. Evidence mới nhất: `report/TV3_results.json`, chi tiết tại `data/tv3/6ae8fce6b6c04af18b729651dfe860b9/results.json`.

| Chỉ số | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Documents | 24 | 23 | 24 |
| Thời gian build (giây) | 8.245 | 1.172 | 1.291 |
| Thời gian rebuild (giây) | 1.197 | 1.329 | 1.470 |
| Vector / metadata / rebuild | Pass | Pass | Pass |
| Title-search Hit Rate@4 | 95.83% | 79.17% | 95.83% |
| QA exact match (96 câu) | 100% | 77.08% | 100% |
| Count / reload / lookup | Pass | Pass | Pass |

Dữ liệu sửa chữa khớp baseline; hai chỉ số tìm kiếm và QA phục hồi. Semantic search baseline chưa đạt 100% dù QA đạt 100%, do QA có exact-title lookup. Chưa chạy GX, pipeline tích hợp hoặc Agent live; những kết quả đó không nằm trong PASS trên.
