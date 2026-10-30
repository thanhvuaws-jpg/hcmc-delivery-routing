# Quyết định

Mỗi quyết định ghi: ngày, nội dung, lý do, phương án đã bỏ. Muốn đổi một quyết định cũ thì thêm quyết định mới ghi rõ "thay QĐ-xxx", không xóa mục cũ.

## QĐ-001 — Tách thư mục đồ án và thực tập (29/10/2026)

- **Nội dung:** toàn bộ đồ án chuyên ngành chuyển vào `Copy of Qlnhahang/doanchuyennganh/`. Đề tài thực tập làm trong `Copy of Qlnhahang/thuctaptotnghiep/`, luôn có `note/`.
- **Lý do:** làm đề tài mới mà không lẫn với đồ án, và các phiên sau đọc `note/` là nắm được tiến độ.
- **Giữ ở gốc:** `.claude/` (cấu hình Claude Code dùng chung cho cả hai thư mục).

## QĐ-002 — Làm hoàn toàn trên một máy tính, không thực địa (29/10/2026)

- **Nội dung:** làm tại nhà, 3 tháng, một máy (Ryzen 5 5500U, 16 GB RAM, GTX 1650 4 GB, CUDA chạy được). Không tự quay video, không chạy xe ghi GPS. Mọi dữ liệu lấy qua mạng. Đánh giá bằng "chạy thử ảo" trên dữ liệu quan sát giữ riêng.
- **Lý do:** người dùng chỉ có một máy và không đi thực địa được.
- **Đã bỏ:** video tự quay ở ngã tư (D6), chuyến đi GPS thật (D7).

## QĐ-003 — Dữ liệu lấy được ngay (29/10/2026)

- **Nội dung:** OSM khu trung tâm và thời tiết Open-Meteo đã tải bằng script trong `thu_thap/`, chạy lại được. Dữ liệu nằm ở `du_lieu/`, không đưa lên git.
- **Chưa chốt:** khu vực thử chính thức (đang đề xuất trung tâm TP.HCM cũ) và nguồn camera (chờ cách truy cập chính thức).

## QĐ-004 — Bỏ camera, thay bằng sự cố giao thông TomTom (29/10/2026, người dùng chốt)

- **Nội dung:** bỏ hẳn phần phân tích ảnh camera. Nguồn kẹt xe chính là TomTom Traffic Flow (~4.300 đoạn khu trung tâm, 5 phút/lần). "Tín hiệu báo kẹt sớm" là TomTom Traffic Incidents: kẹt xe, đóng đường, công trình, tai nạn, ngập, có độ trễ (giây) và chiều dài.
- **Lý do:** camera cổng TP.HCM cần cho phép bằng văn bản và bị trình phân quyền chặn khi gọi API nội bộ. Người dùng không xin thêm được. TomTom chỉ cần đăng ký tài khoản miễn phí. Ùn tắc đo bằng tốc độ, không cần đếm xe.
- **Tên đề tài đề xuất:** "Xây dựng hệ thống định tuyến giao thông thông minh cho giao hàng đô thị dựa trên khai phá dữ liệu và học máy trên nền tảng Hybrid Cloud AWS" (bỏ "phân tích hình ảnh camera"). Chờ thầy duyệt.
- **Hybrid:** thu dữ liệu + huấn luyện (GPU) tại máy; phục vụ API/web + lưu trữ dài hạn trên AWS.
- **Đã bỏ:** YOLO đếm xe, câu hỏi "camera giúp dự báo bao nhiêu".

## QĐ-005 — Cách thu và lưu dữ liệu (29/10/2026)

- **Một lượt thu** (`thu_thap/thu_dinh_ky.py`) = kẹt xe + sự cố (mỗi lượt) + dự báo thời tiết (mỗi giờ). Ba phần độc lập, lỗi phần này không mất phần kia.
- **Lưu Parquet**, mỗi lần chụp một tệp nhỏ: `du_lieu/tomtom/chup/YYYY-MM-DD/HHMM.parquet`, `su_co/...`, `thoi_tiet_du_bao/YYYY-MM-DD/HH.parquet`. Hình học đoạn lưu một lần ở `doan.parquet`. Ghi qua tệp tạm rồi đổi tên.
- **Mã đoạn** = băm hình học. Đoạn trùng hình học trong cùng lần chụp thì gộp (trung bình), không đánh số theo thứ tự.
- **Chạy định kỳ** bằng Windows Task Scheduler (5 phút, pythonw, chạy cả khi dùng pin, chạy bù, không chồng lượt). Người dùng tự bật bằng `CAI_HEN_GIO.bat`.
- **Git cục bộ**, `core.hooksPath=.githooks`, pre-commit chặn `.env`, `du_lieu/`, và mọi dòng chứa giá trị trong `.env` (đã thử chặn được 29/10).

## QĐ-006 — Mở rộng bản đồ OSM ra toàn vùng 30 ô TomTom (30/10/2026)

- **Nội dung:** đồ thị xe máy dựng từ `osm_vung_tomtom.json` (10,721–10,838 / 106,607–106,748), thay cho `osm_trung_tam.json` (10,74–10,83 / 106,62–106,73). Tệp cũ giữ nguyên làm bản gốc.
- **Lý do:** 30 ô TomTom phủ rộng hơn bản đồ cũ. Đo lúc 00:52 ngày 30/10: 15,1% điểm đoạn TomTom nằm ngoài bản đồ, bị bỏ phí. Nên làm ngay khi mới có hai ngày dữ liệu, vì dựng lại đồ thị làm đổi chỉ số cạnh, phải ghép lại từ bản thô.
- **Hệ quả:** sau khi dựng lại đồ thị phải chạy `xu_ly/bac_tomtom.py --lam-lai`, `bac_su_co.py`, `bac_kaggle.py`. Mỗi tệp tầng bạc ghi `ma_do_thi` để biết đã ghép theo đồ thị nào.
- **Chưa đổi:** khung hỏi sự cố (Incidents) và danh sách ô TomTom vẫn theo `KHU_VUC` cũ, vì 30 ô đã phủ cả vùng mới.

## QĐ-007 — Bộ thu AWS lấy thêm ô kiểu `absolute` (km/h) (30/10/2026)

- **Nội dung:** Lambda lấy thêm 30 ô `absolute` mỗi lượt, cùng zip: `absolute/<x>_<y>.pbf`. Ô relative giữ tên cũ ở gốc zip. Triển khai lúc 04:09 ngày 30/10; bản cũ cất ở scratchpad.
- **Lý do:** relative chỉ cho tỉ lệ so với đường trống. absolute cho tốc độ thật (km/h, bước 5 km/h; đo 04:07: 0–75 km/h). Có km/h mới tính được thời gian đi qua từng cạnh cho "đường nhanh nhất", và suy ra tốc độ đường trống mỗi cạnh = trung vị absolute ÷ relative ban đêm.
- **Chi phí:** không thêm lần ghi S3 (chung zip). S3 tăng ~0,8 GB/tháng (~0,02 USD). Lambda ~9,5 s/lượt, vẫn miễn phí. Hạn mức TomTom 34.560/50.000 ô/ngày khi bộ ở máy còn chạy; tắt bộ ở máy thì còn 17.280.
- **Không làm ở bộ thu máy:** bộ đó sắp tắt (sau 2–3 ngày so song song).

## QĐ-008 — Tầng bạc (30/10/2026)

- **Một khung 5 phút = một lần chụp.** Ưu tiên AWS (24/7, giờ đều), thiếu thì lấy bản ở máy. Khung có cả hai thì đo chênh lệch → "nhiễu nguồn" trong `chat_luong_ngay`.
- **Gắn cờ, không xóa.** Cờ bitmask `co`: bit (n−1) = Ln trong `KE_HOACH_DU_LIEU.md`. TomTom dùng L4 (Hampel ±30 phút, ngưỡng max(3·1,4826·MAD, 10 điểm %)), L7 (phủ < 30% cạnh), L8 (COVID/quanh Tết). Khoảng trống L6 để bảng riêng.
- **Ngưỡng sàn Hampel 10 điểm là tạm.** Ngày 29/10 có 5,9% dòng bị gắn L4, độ lệch trung vị 22 điểm. Khi có dữ liệu hai nguồn trùng khung, đặt lại sàn = phân vị 95 của |AWS − máy| (nhiễu đo thật).
- **Kaggle D11:** `period` trong train.csv là giờ UTC (bằng chứng: khớp giờ UTC của báo cáo tốc độ 42%, giờ VN 0,3%). Tầng bạc đã đổi sang giờ VN.

## QĐ-009 — Ngưỡng sàn Hampel = 15 điểm, theo nhiễu đo thật (30/10/2026, thay phần "tạm" của QĐ-008)

- **Đo:** 44 cặp khung (mỗi 15 phút, 23:55 → 10:50) mà bộ thu AWS và bộ thu ở máy cùng chụp, cách nhau ~1 phút; 1,45 triệu cặp (cạnh, khung).
  - |AWS − máy|: p50 0, p90 3, p95 7, p99 23 điểm.
  - Theo giờ, p95 ban đêm ~0, **ban ngày 6–10h là 13–14 điểm**.
  - Trùng cạnh 98,7%; lệch trung bình cả ngày 1,3 điểm.
- **Nội dung:** `HAMPEL_SAN` 10 → 15 điểm (≥ p95 ban ngày). Dưới mức đó là dao động bình thường của nguồn, không gọi là bất thường.
- **Kết quả:** L4 ngày 29/10 giảm 5,8% → 4,6%; ngày 30/10 3,6% → 2,9%.
- **Đã bỏ:** ngưỡng theo giờ (phức tạp hơn mà chưa cần); giữ 10 điểm (gắn cờ nhầm dao động bình thường ban ngày).

## QĐ-010 — Tách phần đường ĐÓNG khỏi mức kẹt ngay ở bộ ghép (30/10/2026)

- **Nội dung:**
  - `BoGhep.ghep` trả [tổng mức × mét phần MỞ, mét mở, mét đóng].
  - `bang_canh` có thêm `dong_m`; `muc` chỉ tính từ phần mở.
  - Tầng bạc thêm cột `phu_dong` (% chiều dài thuộc đoạn đóng); `phu` giờ chỉ là phần mở.
  - Tầng vàng lấy trọng số dài × phu (mở), `ty_le_dong` từ `phu_dong`. Hampel bỏ qua cạnh chỉ có phần đóng.
- **Lý do:**
  - TomTom ghi mức 0 cho đoạn `road_closure`; đó không phải kẹt.
  - Ngày 30/10, 32% cạnh có cờ đóng thật ra chỉ đóng MỘT PHẦN. Mức bị trộn số 0 nên kéo xuống (TB 12, max 67).
  - Bản trước (bỏ cả cạnh có cờ đóng ở tầng vàng) làm mất phần mở còn đo được.
- **Kiểm:**
  - test `test_phan_dong_tach_khoi_muc`: nửa đóng + nửa mở mức 0,8 → cạnh 80, không phải 40.
  - `kiem_tra_ghep_nhanh.py` ĐẠT (bản tham chiếu từng điểm sửa cùng ngữ nghĩa).
  - `kiem_du_lieu.py` 50/50.
- **Đã bỏ:** gắn cờ ở cạnh rồi lọc ở tầng vàng (mất dữ liệu phần mở); để nguyên (mô hình học "kẹt cứng" trên đường đóng).
