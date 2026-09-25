# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `NoName`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-NoName-DataPipeline`

---

## 1. Danh Sách Thành Viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Thanh Dương | 2A202602961 | `26ai.duongnt6@vinuni.edu.vn` | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/2A202602961_NguyenThanhDuong.md` |
| 2 | Trần Nhật Minh | 2A202602483 | `26ai.minhtn3@vinuni.edu.vn` | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data) | `report/2A202602483_TranNhatMinh.md` |
| 3 | Ngô Minh Trí | 2A202602993 | `26ai.trinm2@vinuni.edu.vn` | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | `report/2A202602993_NgoMinhTri.md` |
| 4 | Dương Thị Hồng Viên | 2A202602385 | `26ai.viendth@vinuni.edu.vn` | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602385_DuongThiHongVien.md` |

*(Phân công chi tiết theo vai trò tham khảo tại file `docs/CHECKPOINTS.md` và `PHAN_CONG.md`)*.

---

## 2. Báo Cáo Đóng Góp Cá Nhân

### 2.1. Nguyễn Thanh Dương - 2A202602961 (TV1)
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline (Pipeline Integrator).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và quản lý trạng thái luồng dữ liệu đa tầng (Baseline - Corrupted - Repaired).

### 2.2. Trần Nhật Minh - 2A202602483 (TV2)
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu (Data Foundation Owner).
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thiết lập các kịch bản cấy độc dữ liệu trong `src/ingestion/corruption.py` và cơ chế phục hồi idempotent từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### 2.3. Ngô Minh Trí - 2A202602993 (TV3)
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding (RAG Specialist).
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng và kiểm thử QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### 2.4. Dương Thị Hồng Viên - 2A202602385 (TV4)
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation (Observability & Evaluation Lead).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
