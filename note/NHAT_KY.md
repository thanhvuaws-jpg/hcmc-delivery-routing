# Nhật ký

Mục mới nhất ở trên cùng.

## 30/10/2026 (13:00–13:15) — M2 điểm nóng Getis-Ord Gi*

- `khai_pha/m2_diem_nong.py` → `khai_pha/ket_qua/m2_2026-10-30_0730-0900.csv/.png`.
  - x = 1 − r TB (tầng vàng, đã bỏ đường đóng); lân cận 400 m nhị phân gồm chính nó; Benjamini–Hochberg FDR 5%.
  - 7.192 đoạn (≥ 4 khung dữ liệu), TB 44 lân cận.
  - **Nóng 1.930, lạnh 1.632**, không ý nghĩa 3.630. Nếu dùng |z| > 1,96 trần thì 3.905 → BH bỏ ~340 đoạn báo nhầm.
  - Cụm nóng:
    - lõi Q1/Q3;
    - Q5/Q10/Q11 (3 Tháng 2, Nguyễn Trãi, Trần Hưng Đạo);
    - Lý Thường Kiệt – Hoàng Văn Thụ;
    - Hai Bà Trưng, Điện Biên Phủ, Nguyễn Thị Minh Khai, Nguyễn Đình Chiểu, Hoàng Sa / Trường Sa.
  - Lạnh: Võ Văn Kiệt, trục rìa phía Bắc, Thủ Thiêm.
- **Việc tiếp:**
  1. Chạy `KEO_S3.bat` hằng ngày để thêm dữ liệu (hoặc Claude chạy khi làm).
  2. Tốc độ đường trống mỗi cạnh từ km/h ban đêm (cần vài đêm dữ liệu absolute).
  3. M4 (STL), M5 (lan kẹt, Granger), M6 (mưa/sự cố) cần ≥ 1 tuần.
  4. Chạy lại `mo_hinh/moc_so_sanh.py` khi ≥ 7–14 ngày.
  5. Tắt bộ thu ở máy (GO_HEN_GIO.bat) khi người dùng đồng ý: đã có số so sánh hai nguồn (QĐ-009).
  6. M2 lặp cho cao điểm chiều và nhiều ngày; đối chiếu với 186 điểm ùn tắc của Công an nếu tìm được danh sách.


## 30/10/2026 (12:30–13:00) — M1 mô tả + phát hiện đường đóng ghi 0

- `khai_pha/m1_mo_ta.py` (ngày 30/10, cao điểm 07:30–09:00) → `khai_pha/ket_qua/m1_2026-10-30_*`:
  - hồ sơ giờ (csv + png), bản đồ kẹt (png), top đoạn (csv).
  - Từ 7h: r TB 0,68, **62% chiều dài đường đông** (r < 0,75); đêm 1–5%.
  - Theo nhóm: trunk r ~0,81 (đông 26–35%); primary/secondary ~0,64–0,65 (đông ~70%); tertiary 0,71.
  - Top kẹt sáng 30/10 (sau khi bỏ đường đóng): Bạch Đằng 0,10, Hai Bà Trưng 0,14, Nam Kỳ Khởi Nghĩa 0,16–0,21, Nguyễn Bỉnh Khiêm, Điện Biên Phủ, Võ Thị Sáu, Nguyễn Thị Minh Khai, Phan Đăng Lưu.
  - Bản đồ: lõi Q1/Q3 và Chợ Lớn đỏ, Võ Văn Kiệt xanh — khớp thực tế.
- Phát hiện: đường ĐÓNG TomTom ghi mức 0 (xem CAN_NHO). Đã sửa `vang.py` (r chỉ phần mở + `ty_le_dong`) và M1.
  - Vàng sau sửa: 29/10 151.831 dòng, 30/10 317.195 dòng.


## 30/10/2026 (11:40–12:30) — đoạn đường, tầng vàng, mốc so sánh đầu tiên

- `xu_ly/canh_tinh.py` → `bac/canh_tinh.parquet`: 350.839 cạnh × 32 cột, 575 s, phần lớn là độ trung gian 300 nguồn.
  - Cạnh trung gian cao nhất: Công trường Dân Chủ, Hoàng Văn Thụ.
  - Số làn có ở 16% cạnh, giới hạn tốc độ 5,9%, một chiều 9%.
  - POI trong 300 m: trạm buýt 80% cạnh, trường 64%, chợ 23,5%.
- `xu_ly/doan_duong.py` → `bac/doan.parquet`, `bac/canh_doan.parquet`.
  - Lần 1 tính mọi nút giao: 177.212 đoạn, trung vị 38 m — vụn vì hẻm.
  - Lần 2 đường chính chỉ cắt ở giao đường chính / đổi tên: **158.147 đoạn**; đường chính 8.463 đoạn (1.472 km, trung vị 110 m).
  - Đoạn có TomTom ~7.200–7.400. Độ lệch mức kẹt giữa các cạnh trong cùng đoạn: TB 2,55, p95 16 điểm.
- `xu_ly/vang.py` → `du_lieu/vang/YYYY-MM-DD.parquet`, `_mo_ta.json`: đoạn × 15 phút, 45 cột (xem đầu tệp).
  - 29/10: 152.069 dòng, 30/10: 317.901 dòng; 7.390 đoạn.
  - Kiểm: y_15 = r(t+15) và y_60 = r(t+60) đúng ở 461.505 dòng; r_tru_1 = r(t−15) đúng; không rò rỉ.
  - Thời tiết lấy bản DỰ BÁO phát hành trước t (merge_asof).
- `mo_hinh/moc_so_sanh.py` → `mo_hinh/ket_qua/moc_*.json`.
  - Học 70% thời gian đầu, chừa 1 giờ, kiểm phần sau.
  - Mốc giữ nguyên trên toàn bộ 2 ngày: MAE 15/30/60 phút = 5,27 / 7,00 / 8,70 điểm. Đêm < 1,5; ngày ~8; lúc kẹt 10,6.
  - **GBM lần đầu THUA mốc** (tập kiểm 7–11h sáng 30/10): 15 phút 8,41 vs 7,91; 60 phút 12,66 vs 10,83.
    - Lý do: phần học toàn ban đêm (18:45 → 05:45); chưa có r_hom_qua / r_tuan_truoc; 7 cột lịch bị bỏ vì chưa đổi giá trị.
    - **KHÔNG trích số này vào báo cáo.** Chạy lại khi có ≥ 7–14 ngày.
  - scikit-learn HistGradientBoosting; máy chưa có lightgbm/xgboost (pip từng bị chặn — nếu cần thì người dùng tự cài).
- `thu_thap/KEO_S3.bat` giờ chạy: sync → bac_tomtom → bac_su_co → bac_thoi_tiet → vang.


## 30/10/2026 (11:00–11:40) — tầng bạc thời tiết, điểm giao hàng, điểm ngập, đặc trưng tĩnh

- `xu_ly/bac_thoi_tiet.py` →
  - `bac/thoi_tiet_gio.parquet` (298.860 dòng). Lưu trữ tới 24/10; giờ sau đó lấy bản dự báo phát hành SAU giờ đó (`du_bao_sau`).
  - `bac/thoi_tiet_du_bao.parquet` (18 giờ phát hành; `truoc_h` −23..47).
  - **Hở 25–28/10** (lưu trữ chưa có, dự báo chưa thu): không ảnh hưởng TomTom (bắt đầu 29/10). Vài ngày nữa chạy lại `tai_thoi_tiet.py` là đầy.
- `xu_ly/bac_zenodo.py` → `bac/zenodo_bai_toan.parquet` (56 bài × 1.001 dòng), `bac/zenodo_diem.parquet`.
  - Kho (Bưu cục Q10) bắt nút cách 10 m.
  - 68% toạ độ khách nằm trong bản đồ (≤ 100 m tới nút): bán kính của họ 10 km, bản đồ mình ~7 km.
- **D8 điểm ngập:**
  - Infographic PC08 (Tiền Phong 06/10/2026) chép ra `thu_thap/chep_tay/ngap_pc08_2026-10-06.csv`: 83 mưa + 39 triều, có README nguồn.
  - `xu_ly/bac_ngap.py` ghép theo tên đường OSM:
    - giao lộ / đoạn giữa hai nút giao / quanh mốc;
    - cả tuyến CHỈ khi dòng ghi đúng "Đường X.";
    - nút giao đường đôi cho phép cách ≤ 60 m.
  - Kết quả: **30 điểm ghép được** (13 mưa, 17 triều) → 2.127 cạnh.
  - Còn lại: 41 tên không có trong bản đồ (ngoài vùng), 17 đường giao ngoài vùng, 16 Bình Dương/Vũng Tàu, 11 có chi tiết mà không định vị được, 6 địa danh, 1 tên chung chung.
  - Lần chạy đầu đánh "cả tuyến" cho mọi dòng có tên đường → gắn nhầm (vd Lê Văn Lương "đoạn qua xã Nhà Bè" thành cả Lê Văn Lương ở Q7). Đã siết.
- `xu_ly/canh_tinh.py` → `bac/canh_tinh.parquet`: thẻ OSM (số làn, giới hạn tốc độ, cầu/hầm), bậc nút, POI trong 300 m + khoảng cách, điểm thời tiết, độ trung gian (300 nguồn). Đang chạy.
- Nguồn đã tìm mà chưa dùng:
  - 186 điểm nguy cơ ùn tắc (Công an TP.HCM, 30/10/2025): danh sách đầy đủ không có trong bài.
  - 34 "rốn ngập" Sở Xây dựng (25/06/2026): đa số ngoài vùng, PC08 mới hơn.


## 30/10/2026 (10:30–11:00) — khóa chỉ-đọc S3, kéo dữ liệu AWS, đo nhiễu hai nguồn

- IAM:
  - Tạo user `thuctap-doc-s3` + policy inline `chi-doc-s3-thu-du-lieu` (0 lỗi IAM).
  - Người dùng tự tạo khóa; Claude mở sẵn cửa sổ `aws configure --profile thuctap-doc`, điền sẵn vùng + json, không chạm vào khóa.
  - Kiểm quyền: `sts` ra đúng user. Liệt kê gốc bucket và liệt kê mọi bucket đều AccessDenied. Chỉ đọc được `dong/`.
- `aws s3 sync` (8 s): 132 zip kẹt xe (21 MB), 132 sự cố, 11 dự báo thời tiết. Không thiếu lượt nào từ 23:57.
- Tầng bạc dựng lại với hai nguồn:
  - 30/10 có 132 khung (131 AWS); toc_do có ở 61% dòng (chỉ AWS từ 04:11);
  - sự cố: 1.485 mã.
- Nhiễu hai nguồn → QĐ-009 (sàn Hampel 15 điểm).
- Giờ cao điểm sáng thứ Sáu 30/10:
  - 7–10h: tỉ lệ TB 66–67%, 11–12% cạnh kẹt (< 40%), TB 21 km/h;
  - đêm: 97–99%, ~30 km/h.
- Người dùng tự xóa user cũ `user_thanhvu` (Admin, khóa chưa từng dùng). Claude kiểm lại: "Users deleted", IAM còn 1 user `thuctap-doc-s3`, profile vẫn chạy. Root đã có MFA.


## 30/10/2026 (01:00–04:20) — tăng tốc ghép, tầng bạc, thêm nguồn

**Đã xong (có số kiểm):**
- `dinh_tuyen/ghep_tomtom.py` viết lại bằng numpy: 19 s → 0,7 s/lần chụp; song song 6 tiến trình ~0,15 s/lần chụp.
  - Kết quả trùng bản cũ: `kiem_tra_ghep_nhanh.py` ĐẠT trên 3 lần chụp (0 cạnh lệch).
  - Chỉ mục mới ghi atomic, có `ma_do_thi`. Bộ thu ở máy dùng bản mới từ lượt 01:02, không lỗi.
- `xu_ly/lich.py` → `du_lieu/bac/lich.parquet` (D14), 2020–2027:
  - âm lịch thuật toán Hồ Ngọc Đức, kiểm 8/8 ngày Tết + 7/7 Giỗ Tổ;
  - ngày nghỉ chính thức 2020–21 và 11/2026–02/2027 (24/11/2026 nghỉ đúng 1 ngày theo đề xuất BNV, chưa thấy quyết định cuối);
  - giai đoạn COVID có cột tin cậy;
  - cờ `di_hoc` theo QĐ 5067/QĐ-UBND năm học 2026–27.
- `thu_thap/tai_thoi_tiet.py`: thời tiết giờ từ **01/01/2020** (59.736 giờ × 5 điểm), phủ cả giai đoạn Kaggle.
- `xu_ly/bac_tomtom.py` → `du_lieu/bac/tomtom_canh/YYYY-MM-DD.parquet`:
  - mỗi khung 5 phút một lần chụp, ưu tiên AWS;
  - cột muc, toc_do (km/h), phu, dong_duong, co, nguon; cờ L4/L7/L8;
  - kèm `khoang_trong.parquet`, `chat_luong_ngay.parquet`.
  - Kết quả: 29/10 có 59 khung, L4 5,9%; 30/10 tới 04:15 có 52 khung, L4 1,6%; 0 khoảng trống.
  - Chỉ 11% cạnh đồ thị có TomTom: hẻm/residential không có, đúng như đã biết.
- `xu_ly/bac_su_co.py` → `su_co_khung/`, `su_co.parquet`: 564 sự cố.
  - 542 kẹt xe: kéo dài TB 37 phút, trễ TB 266 s, ghép cạnh 96%.
  - 22 đóng đường dài ngày (Trường Chinh, Cộng Hòa từ 22/09): ghép 77%.
- `xu_ly/bac_kaggle.py` → `kaggle_toc_do`, `kaggle_los`, `kaggle_canh` (D11).
  - Phát hiện `period` là giờ UTC (xem CAN_NHO).
  - Ghép trên đồ thị cũ: 2.361 đúng cạnh + 1.340 đường đi + 2.960 hình học + 3.366 không ghép được (đa số ngoài vùng).
- **Bộ thu AWS thêm ô `absolute` (km/h)** (QĐ-007):
  - `thu_o_may.py` ĐẠT trước; triển khai 04:09;
  - lượt 04:11 trên AWS: 30+30 ô, 0 lỗi, 199 KB, 11,5 s.
  - Thử bộ đọc tầng bạc trên zip mới: 98,9% cạnh có km/h, tốc độ đường trống suy ra trung vị 30 km/h.
- `thu_thap/KEO_S3.bat`: kéo S3 về rồi dựng tầng bạc. Cần profile `thuctap-doc` chỉ-đọc, người dùng tự tạo khóa (cách làm ở CAN_NHO).
- `thu_thap/tai_osm.py`:
  - tải theo ô 4×4, mỗi ô lưu ngay vào `ban_do/o_tam/`, chạy lại thì tải tiếp;
  - thêm `python tai_osm.py poi` (trường, chợ, bệnh viện, TTTM, trạm buýt).

**05:01–05:05 — xong phần bản đồ mới (QĐ-006):**
- OSM vùng ô TomTom tải xong: 16/16 ô, 59 phút vì Overpass quá tải. 204.684 nút, 58.414 đường, 1.123 luật cấm rẽ → `osm_vung_tomtom.json` (28,5 MB).
- Đồ thị mới: 170.259 nút, 350.839 cạnh, 8.937 km (cũ: 122.543 / 252.455 / 5.968 km); 94 luật cấm + 11 luật "chỉ được". `ma_do_thi` = be3e6a760eb6.
  - `kiem_tra_tuan1.py`: 90/90 tuyến, 0 lỗi luật, TB 71 ms/tuyến.
  - `kiem_tra_ghep_nhanh.py`: ĐẠT.
  - Ghép TomTom: **95,8% mẫu** (cũ 80%), 33.229 cạnh có dữ liệu mỗi lần chụp (cũ 28.251). Bộ thu ở máy tự dùng đồ thị mới từ lượt 05:02.
- Tầng bạc dựng lại toàn bộ theo đồ thị mới:
  - TomTom: 29/10 có 59 khung, 30/10 tới 05:00 có 61 khung, 0 khoảng trống;
  - sự cố: 568, ghép kẹt xe 97%;
  - Kaggle: 2.557 đúng cạnh + 1.425 đường đi + 3.204 hình học; 75,8% báo cáo tốc độ, 69,1% nhãn LOS nằm trên đoạn ghép được.
- POI (D16): `osm_poi_vung_tomtom.json`, 4.608 điểm (2.099 trạm buýt, 686 trường, 136 chợ, 112 bệnh viện, 121 ĐH/CĐ, 44 TTTM…).

**Còn dở:** (kéo S3 đã xong lúc 10:40, xem mục trên)
- Đặt lại sàn Hampel bằng nhiễu hai nguồn khi đã kéo được S3 (QĐ-008).

## 30/10/2026 — soát tiền AWS, xóa bản sao lưu RDS cũ

- Hóa đơn 10/2026: 0,05 USD là RDS Backup Storage (0,559 GB-tháng) ở us-east-1, được tín dụng Free Tier trừ hết nên thực trả 0,00 USD. Glue, KMS, S3 đều 0 USD.
- Nguồn: bản sao lưu thủ công `testdtb-snapshot`:
  - MySQL 8.0.42, 634 MiB;
  - lấy từ CSDL thử `testdtb` (tạo 26/10/2025, chụp 28/10/2025, CSDL gốc đã xóa từ trước);
  - không liên quan thực tập hay đồ án.
- Đã kiểm: không còn bản sao lưu tự động hay bản giữ lại ở us-east-1; vùng ap-southeast-1 không có bản sao lưu RDS. Trang EC2 Snapshots không mở được trong tiện ích Chrome, nhưng hóa đơn không có dòng EC2/EBS.
- Người dùng TỰ bấm xóa (Claude không xóa dữ liệu vĩnh viễn thay người dùng). Claude kiểm lại: "Successfully deleted snapshot testdtb-snapshot", Manual snapshots (0).
- Email Budgets `email của người dùng`:
  - lúc đầu **Pending**: thư xác minh nằm trong Spam của Gmail nên link bị khóa;
  - người dùng bấm "Not spam" rồi "Verify email";
  - Claude kiểm lại: **Verified**, 3 cảnh báo đang bật.

## 30/10/2026 (00:05) — bộ thu trên AWS CHẠY THẬT

- Người dùng tự dán TOMTOM_KEY vào biến môi trường Lambda; Claude bấm Save giúp (không nhập khóa).
- Gọi thử Lambda trên AWS: 30/30 ô, 0 lỗi, 100 KB, 23 sự cố, 7,5 s.
- EventBridge Scheduler `thu-du-lieu-5-phut`:
  - `rate(5 minutes)`, cửa sổ linh hoạt Off, không retry, không DLQ, trạng thái Enabled (tạo 00:00:53);
  - role tự tạo `Amazon_EventBridge_Scheduler_LAMBDA_1d17b91213`.
- Log group `/aws/lambda/thu-du-lieu-giao-thong`: giữ 2 tuần.
- Kiểm S3: lượt hẹn giờ đầu 00:01 → `dong/tomtom_o/2026-10-30/0001.zip` (88,1 KB); đủ 3 tiền tố tomtom_o / tomtom_su_co / thoi_tiet_du_bao.
- Hai bộ thu (máy + AWS) chạy song song. Hạn mức TomTom đủ: 17.280 ô + 576 lượt sự cố/ngày.
- Việc tiếp:
  - (1) script kéo dữ liệu S3 về máy — cần người dùng tạo user IAM chỉ-đọc + access key, tự cấu hình `aws configure`;
  - (2) so 2–3 ngày giữa hai bộ thu rồi tắt bộ thu ở máy;
  - (3) xử lý tầng bạc theo `KE_HOACH_DU_LIEU.md`.

## 29/10/2026 (23:30) — tạo tài nguyên AWS (người dùng duyệt "làm đi")

Thao tác bằng Claude in Chrome, tài khoản đang đăng nhập bằng root. Vùng ap-southeast-1 (Singapore).

- S3 `<S3_BUCKET>`: chặn công khai, ACL tắt, SSE-S3, không versioning.
- Lambda `thu-du-lieu-giao-thong`:
  - Python 3.13, arm64, 256 MB, timeout 60 s, không VPC, không Function URL.
  - Code = `dist/thu_lambda.zip`.
  - Async: retry 0, tuổi sự kiện tối đa 5 phút.
  - Biến môi trường: BUCKET, TIEN_TO=dong.
- IAM role `thu-du-lieu-giao-thong-role-g5skf5c0`: log cơ bản (AWS tự tạo) + inline policy `chi-ghi-s3-thu-du-lieu` (chỉ s3:PutObject vào `<bucket>/dong/*`; IAM báo 0 lỗi).
- AWS Budgets `thuctap-ngan-sach-thang`: 2 USD/tháng, báo email khi thực tế 85% / 100% và dự báo 100%.
  - Email người dùng cho: email của người dùng. Phải bấm link xác minh trong email (quy định mới từ 30/09/2026).
  - Budgets chỉ theo dõi + email là miễn phí.
  - Tài khoản còn 2 budget cũ (75 và 25 USD).
- CHƯA làm:
  - người dùng tự dán TOMTOM_KEY;
  - gọi thử Lambda;
  - EventBridge Scheduler 5 phút;
  - đặt log giữ 14 ngày (log group tạo ở lần gọi đầu).

## 29/10/2026 (23:00) — kiểm tra bộ thu + chuẩn bị bộ thu trên AWS

- Bộ thu ở máy: 48 lượt liên tục 19:07–22:57, không khoảng trống, 0 lỗi; tác vụ đang chạy lúc 23:02.
- Người dùng nhắc lại nguyên tắc: lõi dữ liệu + khai phá + ML/DL trước, UI sau; dữ liệu mới nhất ưu tiên; ghi hết vào note → `KE_HOACH_DU_LIEU.md` mục 0 + bộ nhớ dài hạn.
- Bộ thu AWS `he_thong/aws/thu_lambda/`:
  - Chỉ lưu bản gốc lên S3; chỉ thư viện chuẩn + boto3.
  - Chạy song song 5 luồng: 30 ô trong 3,9 s.
  - Bản gốc một lượt ~104 KB (zip pbf 100 KB + sự cố gzip 4 KB).
  - TomTom trả nén brotli nếu client nhận → Lambda xin gzip.
  - `thu_o_may.py` (S3 giả): ĐẠT — 30/30 ô, 3.638 đoạn, 26 sự cố, thời tiết ok, 5,6 s.
  - Gói 3,6 KB, không chứa key. Phương án + chi phí trong README (~0,2–0,3 USD/tháng).
- Chờ người dùng duyệt danh sách tài nguyên AWS + email nhận cảnh báo Budgets. Người dùng phải tự dán TOMTOM_KEY vào biến môi trường Lambda.

## 29/10/2026 (khuya) — tải dữ liệu mở + kế hoạch dữ liệu

- Khóa Kaggle có trong `.env`. Tải D11 bằng `thu_thap/tai_kaggle.py` (REST API, không cần gói kaggle): 5 bảng, 8,4 MB nén.
- Tìm rộng (GitHub, Zenodo, Figshare, Mendeley, Kaggle, báo chí):
  - D13 Zenodo HCM_1000 V2: tải bằng `thu_thap/tai_tep.py`, MD5 khớp, 802 tệp.
  - D8 điểm ngập: 122 điểm (CSGT, 10/2026) nằm trong 2 ảnh infographic của Tuổi Trẻ → chép tay tuần 4.
  - Bỏ qua: PathFinding_HCM (repo đã gỡ, dùng lại D11); bài báo "HCMC-Traffic Extension" (dữ liệu = D11); Grab-Posisi (Singapore/Jakarta); HealthyAir (không khí); XMap (thương mại).
- Khảo sát D11:
  - 90.938 báo cáo, 07/2020–04/2021, không trùng phong tỏa 2021.
  - Bất thường: 7h có 31.576 báo cáo; tốc độ tới 200 km/h; tháng lệch.
  - 2.425 đoạn khớp đúng cạnh theo mã nút OSM.
- Viết `note/KE_HOACH_DU_LIEU.md` (3 tầng đồng/bạc/vàng, chuẩn hóa, cờ L1–L8, 4 cách bù thiếu, khai phá M1–M9, đặc trưng, chia theo thời gian).

## 29/10/2026 (tối muộn) — tìm dữ liệu có sẵn để kết hợp

- Người dùng lo không kịp. Đánh giá thật: đang VƯỢT kế hoạch (tuần 1–3 gần xong ngay tuần 0).
- Tìm trên mạng:
  - D11: Kaggle "Traffic Flow data in Ho Chi Minh City" — CC0, ĐH Bách Khoa TP.HCM, 38,5 MB, LOS theo 30 phút, cập nhật 05/2021 → chờ người dùng tải.
  - D12: TomTom Traffic Index TP.HCM 2025 để đối chiếu.
  - Cổng dữ liệu mở data.hochiminhcity.gov.vn: chưa thấy bộ điểm ngập công bố.
  - XMap: dữ liệu tốc độ Việt Nam thương mại, có mẫu thử nhưng phải đăng ký → bỏ qua.

## 29/10/2026 (19:10) — hẹn giờ chạy + ghép TomTom vào đồ thị (tuần 3 làm sớm)

- Người dùng đã bấm `CAI_HEN_GIO.bat`. Tác vụ `\ThucTapTotNghiep\ThuDuLieuGiaoThong` tự chạy 19:02 (kết quả 0), 5 phút/lần.
- Phát hiện: mã đoạn theo băm hình học KHÔNG ổn định. TomTom cắt đoạn theo chỗ mức kẹt đổi, nên 28% đoạn có hình học mới sau 5 phút → bỏ cách lưu `chup/` + `doan.parquet` (chỉ còn vài lượt 18:57–19:07 ở định dạng cũ).
- `dinh_tuyen/ghep_tomtom.py`:
  - lấy mẫu 10 m dọc đoạn TomTom → cạnh đồ thị gần nhất trong 15 m, lệch hướng ≤ 35° ("full" nhận cả hai chiều);
  - bảng cạnh cố định `du_lieu/do_thi/canh.parquet`.
- `dinh_tuyen/kiem_tra_ghep.py` trên một lượt chụp thật:
  - ghép 10 giây;
  - 22,4% mẫu TomTom nằm NGOÀI khu vực bản đồ (ô TomTom rộng hơn);
  - **trong khu vực ghép được 96,1%** (mọi loại đường TomTom ≥ 90%);
  - % chiều dài cạnh có dữ liệu: trunk 95%, primary 85%, secondary 86%, tertiary 50%, residential/hẻm gần 0 (TomTom không có dữ liệu ở đường nhỏ).
  - Hình `dinh_tuyen/ket_qua/tuan3_ket_xe.png`: 19:05 khu trung tâm đỏ (kẹt), hợp lý.
- Bộ thu lưu mới:
  - `tomtom/tho/` (bản thô có hình học) + `tomtom/canh/` (theo cạnh cố định), zstd mức 19;
  - ~250 KB/lượt ≈ 70 MB/ngày ≈ 6,3 GB/3 tháng; một lượt ~31 giây.
- Còn của tuần 3: kiểm tay 30 đoạn ghép ngẫu nhiên; ghép sự cố vào cạnh.

## 29/10/2026 (khuya) — bỏ camera, dựng bộ thu + khung dự án

- Người dùng chốt: bỏ camera, thêm sự cố TomTom (QĐ-004).
- Bộ thu hoàn chỉnh (QĐ-005):
  - `thu_thap/thu_dinh_ky.py` gọi `thu_tomtom.py` (luu_chup, lay_su_co/luu_su_co) và `du_bao_thoi_tiet.py`.
  - Chạy tay lúc 18:57: 4.339 đoạn (đã gộp đoạn trùng), 186 sự cố (169 kẹt xe, 17 đóng đường), 240 dòng dự báo.
  - Sự cố có tên đường tiếng Việt, độ trễ, chiều dài. Ví dụ: Công Trường Mê Linh → Lý Chính Thắng 2,4 km, trễ 28 phút.
  - Tham số `language=vi-VN` bị TomTom từ chối → dùng en-GB (mô tả tiếng Anh, tên đường vẫn tiếng Việt).
- Tạo tác vụ hẹn giờ Windows bị trình phân quyền chặn ("Unauthorized Persistence") → viết `thu_thap/CAI_HEN_GIO.bat` để người dùng tự bấm đúp.
- Khung dự án: `README.md`, `requirements.txt`, git cục bộ (nhánh main, chưa commit, chưa remote), `.githooks/` chặn bí mật (đã thử: chặn được tệp chứa key).
- Kế hoạch: tuần 3 đổi thành ghép dữ liệu TomTom vào đồ thị (map matching); câu hỏi 3 đổi thành "sự cố + thời tiết giúp bao nhiêu".

## 29/10/2026 (đêm, tiếp) — TomTom chạy được

- Người dùng có key TomTom (gói Evaluation miễn phí, có Traffic API). Key nằm trong `.env`, không in ra.
- Lệnh `pip install mapbox-vector-tile` bị trình phân quyền chặn ("Untrusted Code Integration") → tự viết `thu_thap/mvt.py` (đọc MVT bằng Python thuần, không gói ngoài).
- `thu_thap/thu_tomtom.py thu-thu`, chụp lúc 18:46 (cao điểm chiều):
  - 30 ô ở mức phóng 14, 0 lỗi, 19,6 giây.
  - **4.866 đoạn có dữ liệu, tổng 1.605 km đường**, gồm cả đường nội khu nhỏ.
  - Mức kẹt: 879 đoạn kẹt (<0,4), 2.776 đông (0,4–0,75), 1.211 thông.
  - Thuộc tính TomTom trả về: road_type, traffic_level (0..1 = tốc độ hiện tại / tốc độ đường trống), traffic_road_coverage (one_side/full), road_closure.
  - Kiểm chứng km/h: Điện Biên Phủ 31/41 km/h, CMT8 31/41, Nguyễn Thị Minh Khai 12/30 km/h; độ tin cậy 0,98–0,998.
- Kết luận: TomTom đủ làm nguồn kẹt xe chính. Camera thành phần bổ trợ, không bắt buộc.
- Tiếp theo: lệnh `chup` lưu Parquet + hẹn giờ 5 phút/lần (chờ người dùng đồng ý tạo tác vụ Windows).

## 29/10/2026 (đêm) — bắt đầu tuần 1: đồ thị xe máy + tìm đường

- `dinh_tuyen/do_thi.py`: đồ thị xe máy từ OSM, dựng trong 4 giây.
  - 122.543 nút, 252.455 cạnh có hướng, 36.707 đường. 97% số nút nằm trong thành phần liên thông mạnh lớn nhất.
  - Áp luật: một chiều, cấm xe máy, bỏ cao tốc, 83 luật cấm rẽ + 6 luật "chỉ được đi". 794 luật cấm rẽ ghi "trừ xe máy" → không áp. 50 luật cấm theo giờ lưu riêng để tuần 7 áp. 45 luật có "via" là cả con đường thì chưa xử lý.
- `dinh_tuyen/tim_duong.py`: A* với trạng thái (nút, đường đang đi) để áp luật cấm rẽ; không quay đầu giữa đường.
- `dinh_tuyen/kiem_tra_tuan1.py` trên 10 địa điểm × 90 cặp:
  - Tìm được 90/90 cặp, **0 lỗi luật**.
  - Trung bình 79 ms/tuyến, chậm nhất 271 ms.
  - Luật cấm rẽ không đổi tuyến nào trong 90 cặp: phần lớn luật trong khu vực có "trừ xe máy".
- **Số liệu cho phần "vấn đề" của báo cáo:** 85/90 cặp, đường ngắn nhất khi bỏ luật phải đi NGƯỢC CHIỀU ít nhất một đoạn. Đi đúng luật dài hơn trung bình 5,5%, nhiều nhất 25,1%.
- Hình `dinh_tuyen/ket_qua/tuan1_tuyen.png` (nền = mạng đường từ đồ thị). Bản đồ HTML `tuan1_ban_do.html` không có ảnh nền trong khung xem trước của Claude (máy chủ ảnh OSM từ chối), tuyến vẫn vẽ đúng.
- Còn lại của tuần 1: đề cương 3–5 trang.

## 29/10/2026 (tối)

- Người dùng: làm tại nhà, 3 tháng, một máy, không đi thực địa (QĐ-002). Phát hiện tín dụng AWS đã hết hạn 20/10/2026.
- Kiểm máy: đủ sức (GTX 1650 + CUDA, 16 GB RAM). Ổ C còn ~44 GB, D ~33 GB.
- Đã tải:
  - `du_lieu/thoi_tiet/` — 5 điểm × 33.408 giờ (01/2023 → 23/10/2026).
  - `du_lieu/ban_do/osm_trung_tam.json` — 20,7 MB: 41.828 đường, 144.567 nút, 992 luật cấm rẽ, 4.825 đường một chiều, 375 đường cấm xe máy.
- Viết `note/KE_HOACH.md` (13 tuần), đã sửa theo QĐ-002.
- Camera: đọc điều khoản cổng; người dùng báo đã gọi xin được chấp nhận. Xem tay được cách cổng phát ảnh. Bước gọi thẳng API nội bộ bị trình phân quyền chặn, dừng lại chờ người dùng quyết (xem `CAN_NHO.md`).
- Còn dở: dựng đồ thị xe máy từ OSM (tuần 1); TomTom (chờ khóa API); camera (chờ cách truy cập).

## 29/10/2026 (tiếp)

- Người dùng trình bày ý tưởng gộp + tên đề tài dự kiến (ghi ở `Y_TUONG.md`, Nguồn 2).
- Đã kiểm chứng: cổng camera giao thông TP.HCM, chính sách AWS Free Tier mới.
- Đã góp ý (phạm vi, dữ liệu, cách đánh giá, lý do hybrid). Chờ người dùng trả lời 3 câu hỏi còn mở rồi mới chốt QĐ cho đề tài.

## 29/10/2026

- Tạo `thuctaptotnghiep/` và sổ `note/` (README, CAN_NHO, QUYET_DINH, NHAT_KY, Y_TUONG).
- Chuyển toàn bộ đồ án chuyên ngành vào `doanchuyennganh/` (QĐ-001). Đã sửa các chỗ trỏ đường dẫn cũ: hook chặn bí mật của 3 repo git, `.claude/launch.json`, lối tắt "Royal – Điều hành máy chủ" trên Desktop.
- Còn dở: người dùng sẽ trình bày ý tưởng đề tài (AWS + dữ liệu thật), đã gửi kèm một đoạn chat với ChatGPT để đọc.
