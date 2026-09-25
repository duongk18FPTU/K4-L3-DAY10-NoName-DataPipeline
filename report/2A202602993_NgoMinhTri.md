# Báo cáo cá nhân — TV3

## 1. Thông tin cá nhân

Ngô Minh Trí — MSSV 2A202602993 — K4 — Nhóm NoName — ngày 2026-09-25.
Vai trò: RAG & Agent Specialist (QA). Repository: bản làm việc K4-L3-DAY10-NoName-DataPipeline; URL bàn giao cần đối chiếu cấu hình remote với nhóm.

## 2. Vai trò và phạm vi

Kiểm tra dữ liệu TV2, build/search/lookup Chroma, so sánh baseline/corrupted/repaired và chuẩn bị demo agent. Module index, embeddings và QA đã có sẵn; không nhận ownership triển khai các module đó.

Deliverables: mở rộng `src/retrieval/agent.py`, `tests/test_tv3_agent.py`, `script/verify_tv3.py`, các artifact xác minh và tài liệu bàn giao. Hỗ trợ TV1 bằng kết quả kiểm tra contract và phát hiện truy vấn tên không tồn tại; hỗ trợ TV4 bằng phát hiện categories rỗng.

## 3. Kết quả theo vai trò

745 kiểm tra tích hợp và 7 unit test thành công. Baseline/repaired có đủ 24 documents. Kiểm tra dimension 384, chuẩn hóa vector, lookup ID/title, search, persistence, rebuild, repair idempotence và cách ly collection. Hai câu demo live có gọi lookup_paper và trả đúng tác giả/ngày; ca không tồn tại chưa xác nhận live. Xem `TV3_HANDOFF.md` và `tv3_agent_demo.json`.

## 4. Kỹ thuật triển khai

Đọc raw PaperRecord qua ingestion của TV2, clean thành DataFrame chứa text_for_embedding, tạo corrupted, repair từ raw ở cùng run_date. Build MiniLM/Chroma thật trong data/tv3, cố định 96 probe từ baseline và dùng lại cho ba trạng thái. Lưu summary, source hash và phiên bản thư viện để đối chiếu. Không ghi đè artifact pipeline chính thức.

Agent giới hạn top_k theo số documents và tối đa 10, kiểm tra câu hỏi rỗng, giới hạn recursion 12, chuẩn hóa text blocks của provider và báo lỗi rõ khi mock không hỗ trợ tool calling. CLI lưu câu trả lời và tên tool sau mỗi câu.

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_tv3*.py' -v
.venv/bin/python script/verify_tv3.py
```

Kết quả và điều kiện cache/model được ghi trong TV3_HANDOFF.md; số liệu tại tv3_verification.json.

## 5. Quyết định kỹ thuật

Có thể chỉ đo output QA hoặc đo riêng semantic retrieval và QA. Chọn đo cả hai vì QA có ưu tiên title chính xác, có thể che việc semantic search chưa tìm đúng paper. Baseline semantic hit@4 = 0.96875 trong khi QA hit@4 = 1.0 chứng minh hai phép đo khác nhau. Bộ probe riêng cho phép kiểm tra TV3 khi phần pipeline/evaluation nhóm chưa được xác minh; không gọi đó là metrics chính thức.

## 6. Blocker và cách xử lý

Model MiniLM chưa có cache khiến bước build chờ tải. Đã tải weight từ nguồn chính thức, kiểm tra checksum và xác minh embedding 384 chiều. Gemini 2.5 Flash trả GoogleModelNotFoundError trong phiên demo; dùng override model gemini-3.8-flash cho tiến trình, không sửa module LLM chung. Hai câu có kết quả thực. Còn hạn chế: newline trong DOI của câu trả lời ngày và chưa có kết quả ca không tồn tại; không tuyên bố demo đầy đủ đã đạt.

## 7. Hiểu luồng end-to-end

1. Crossref → raw PaperRecord → cleaned DataFrame/text_for_embedding → embedding MiniLM → Chroma.
2. Ground-truth IDs kiểm tra truy xuất đúng tài liệu; reference answers hỗ trợ đo chất lượng câu trả lời.
3. Quality kiểm tra cấu trúc, uniqueness, nội dung; freshness kiểm tra tuổi dữ liệu so với SLA.
4. Giữ cùng test set giúp thay đổi chỉ số phản ánh dữ liệu/index thay vì thay câu hỏi.
5. Repair cần phục hồi dữ liệu và metrics, đồng thời kiểm tra chất lượng/freshness chính thức; riêng TV3 đã xác minh dữ liệu và probe về mức baseline.

## 8. Phân tích kết quả

Các số sau là probe TV3 (96 câu), không phải metrics pipeline chính thức.

| Chỉ số | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Semantic hit@4 | 0.96875 | 0.78125 | 0.96875 |
| QA hit@4 | 1 | 0.83333 | 1 |
| Token F1 | 0.75 | 0.55820 | 0.75 |
| F1 với reference không rỗng | 1 | 0.74426 | 1 |
| Summary rỗng | 0 | 4 | 0 |
| Dòng trùng paper | 0 | 3 | 0 |

Judge accuracy/score và quality/freshness chính thức: chưa chạy trong đợt xác minh này.
Corruption loại 4 paper và thêm 3 dòng trùng → 23 dòng nhưng chỉ 20 paper → QA hit giảm còn 0.83333. Repair từ raw → 24 paper và không còn summary rỗng/dòng trùng → probe trở lại baseline. Nhiều lỗi được tiêm cùng lúc nên chưa thể quy toàn bộ suy giảm cho một loại lỗi.

Kết quả ngoài kỳ vọng: baseline F1 chỉ 0.75 vì 24 reference categories rỗng đều nhận điểm 0 theo công thức. 72 reference không rỗng đạt F1 1.0; không tự bổ sung category không có trong nguồn.

## 9. Điều học được và cải thiện

- Số dòng không thay thế kiểm tra số ID duy nhất.
- Chỉ số phụ thuộc coverage của ground truth; cần công bố reference rỗng.
- Exact lookup và semantic search có hành vi khác nhau khi tên tài liệu không tồn tại.

Cải thiện tiếp: phối hợp owner QA thêm xử lý abstention cho exact-title không tồn tại, test đúng/sai title và kiểm tra trích dẫn DOI trong demo live; chạy lại evaluation chính thức khi nhóm tích hợp.

## 10. Xác nhận thành viên

Bản báo cáo dựa trên artifact đã chạy; Trí cần đọc và tự xác nhận mức hiểu trước khi nộp.

- [ ] Tôi đã đối chiếu phần việc và có thể giải thích luồng end-to-end.
- [ ] Tôi đã kiểm tra bằng chứng, giới hạn kết quả và nội dung báo cáo.

Họ tên: Ngô Minh Trí. Ngày tự xác nhận: chưa xác nhận.
