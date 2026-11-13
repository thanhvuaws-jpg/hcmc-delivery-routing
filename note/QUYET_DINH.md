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
- **Tên đề tài đề xuất:** "Xây dựng hệ thống định tuyến giao thông thông minh cho giao hàng đô thị dựa trên khai phá dữ liệu và học máy trên nền tảng Hybrid Cloud AWS" (bỏ "phân tích hình ảnh camera"). Chờ thầy duyệt. → **Đã thay bằng tên chốt ở QĐ-019 (31/10/2026).**
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

## QĐ-011 — Định tuyến 3 phương án theo thời điểm (30/10/2026)

- **Mô hình tốc độ** (`dinh_tuyen/mo_hinh_toc_do.py`): v(cạnh, giờ) = v_trống(cạnh) × r(cạnh, giờ).
  - v_trống: đo thật (`xu_ly/toc_do_canh.py`); không có thì trung vị loại đường, rồi bảng đoán `TOC_DO`.
  - r: TB điều hòa các lần chụp của CẠNH trong giờ đó (≥ 3 lần); không đủ thì r loại đường × giờ; hẻm/service lấy residential.
  - **Giờ chưa có dữ liệu KHÔNG coi là đường trống**: lấy TB các giờ cùng nhóm (6–21h / đêm), in cảnh báo.
  - Giờ xuất phát cách lần chụp mới nhất ≤ 30 phút: 30 phút đầu chuyến dùng r đo thật.
  - Lần chụp mới nhất: cạnh đóng hết → CẤM; đóng một phần → thời gian × (1 + phần đóng).
- **3 phương án** (`dinh_tuyen/ba_phuong_an.py`):
  - ngắn nhất (mét);
  - nhanh nhất (giây, thời gian phụ thuộc GIỜ XE TỚI cạnh);
  - tối ưu = thời gian × (1 + 0,5 × max(0; 0,75 − r)/0,75) + phạt ngập (mưa ≥ 5 mm/h: 600 s/cạnh dễ ngập do mưa; 1–5: 180 s; triều cường bật tay: 600 s).
  - Cả 3 cấm đường đóng, giữ luật một chiều / cấm rẽ / cấm xe máy. Kết quả chấm lại bằng cùng thước đo thời gian (không phạt).
- **Tăng tốc A\*:** danh sách kề tính sẵn, mét phẳng × 0,995 (cận dưới), cận v_max trong 3 giờ tới, bảng giây/cạnh theo giờ dạng list, **ALT 8 mốc** (cận dưới = thời gian đường trống, hợp lệ vì r ≤ 1).
  - Kết quả: 3h 41.921 → 1.801 nút; 8h 58.537 → 21.734 nút.
  - Kiểm: có/không ALT cùng chi phí 20/20.
- **Kiểm** (`dinh_tuyen/kiem_tra_tuan7.py`, ĐẠT):
  - 90 cặp × (3h, 8h): 0 lỗi luật, 0 cạnh đóng; 3 tuyến TB 0,15 / 0,41 s, chậm nhất 1,53 s (< 2 s).
  - 8h: nhanh nhất tiết kiệm TB 4,5 phút (17,8%), tối đa 15,4 phút, nhanh hơn ở 97% cặp. Cạnh kẹt nặng 12,0 → 9,3 (tối ưu).
  - Mưa to: 14/14 cặp né được, hoặc không thể né hợp lý (cầu Bà Tàng: cấm hẳn cạnh ngập thì không còn đường).
- **Giới hạn ghi rõ:**
  - số "tiết kiệm" là theo MÔ HÌNH tốc độ, chưa chấm bằng tốc độ thật quan sát sau đó (tuần 10);
  - giờ 12–18 hiện đang ước lượng (dữ liệu từ 29/10 19:00);
  - chưa có phạt rẽ trái qua trục lớn.
- **Đã bỏ:**
  - tốc độ cố định theo loại đường: không thấy kẹt từng đoạn, tối ưu không né đúng chỗ;
  - coi giờ thiếu dữ liệu là đường trống: sai cao điểm chiều.

## QĐ-012 — Chấm tuyến bằng tốc độ thật + dự phòng 30% cho cạnh không có số đo (30/10/2026)

- **Cách chấm** (`danh_gia/cham_tuyen_that.py`, không dùng dữ liệu tương lai):
  - 90 cặp điểm × 7 giờ xuất phát (06:30–15:30) ngày 30/10 = 630 chuyến.
  - Bộ định tuyến chỉ biết lần chụp mới nhất ≤ giờ xuất phát.
  - Chấm bằng r ĐO THẬT ở khung 5 phút lúc xe tới từng cạnh. Cạnh không đo dùng hồ sơ (`--khat-khe`: hồ sơ × 0,7).
  - So 4 phương án: A ngắn nhất, B bản đồ thường (đường trống, không biết đóng), C nhanh nhất theo hiện tại, D tối ưu.
- **Lần 1** (tối ưu chỉ phạt kẹt):
  - bình thường: D nhanh hơn A 20,7%, không chậm hơn ở 92% chuyến;
  - khắt khe: 13,2%, chỉ **77%** — KHÔNG ĐẠT (tuyến hay luồn hẻm mà hẻm không có số đo).
- **Nội dung:** phương án tối ưu cộng 30% thời gian cho cạnh chưa từng có số đo TomTom (`RUI_RO_KHONG_DO`, `MoHinhTocDo.co_so_do`).
- **Lần 2** (sau QĐ):
  - bình thường: D nhanh hơn A **19,4%**, không chậm hơn **91%**;
  - khắt khe: **16,1%**, **89%** → ĐẠT tiêu chí kế hoạch (≥ 80%, ≥ 5%) trong cả 2 kịch bản.
  - C nhanh hơn B (bản đồ thường) 22,0% / 13,4%.
  - Đi vào đường đóng: A 27, B 23, C 0–3, D 3–7. C/D chỉ vào đường BẮT ĐẦU đóng sau lúc xuất phát; chạy thật cần tính lại tuyến giữa đường.
  - Dự đoán giờ đến (C): sai TB 0,6 phút (3%); khắt khe 3,1 phút (16%), gần như luôn đoán sớm.
- **Giới hạn:**
  - mới 1 ngày (thứ Sáu);
  - 36% chiều dài tuyến C chấm bằng hồ sơ ước lượng, không phải số đo;
  - hồ sơ cho cạnh không đo dựng cùng ngày.
  - Chạy lại khi có nhiều ngày, nhất là cuối tuần / mưa.
- **Đánh đổi** (kiem_tra_tuan7 sau QĐ, vẫn ĐẠT): số cạnh kẹt nặng trên tuyến tối ưu 9,3 → 11,8. Tuyến bám đường chính có số đo (dù kẹt) thay vì luồn hẻm chưa rõ tốc độ: chấp nhận được vì thời gian thật vẫn tốt hơn và ổn định hơn.
- **Đã bỏ:** coi tốc độ hẻm ước lượng là chắc chắn (lần 1 — thua kịch bản khắt khe).

## QĐ-013 — Tính lại tuyến giữa đường mỗi lần chụp mới, chỉ đổi khi đỡ ≥ 60 s (30/10/2026)

- **Vì sao:** QĐ-012 cho thấy C/D vẫn đi vào 3–7 cạnh BẮT ĐẦU đóng sau lúc xuất phát. Bộ định tuyến chỉ nhìn lúc đi thì không né được.
- **Nội dung:**
  - `tim_duong.BanDo.tim(di_tu=(nút trước, nút hiện tại))`: tìm từ trạng thái (nút, đường đang đi) → luật cấm rẽ áp ngay ở nút đầu, không quay đầu về nút vừa rời.
  - `DinhTuyen.tim(di_tu=...)` và `DinhTuyen.chi_phi_tuyen()` (chi phí một tuyến cho sẵn, CÙNG thước đo với `tim`).
  - Mỗi lần chụp mới (5 phút), ở nút giao xe đang đứng: tính tuyến tối ưu với tình trạng mới nhất. ĐỔI khi tuyến cũ đi qua đường đang đóng, hoặc tuyến mới rẻ hơn ≥ `NGUONG_DOI_S` = 60 s chi phí.
  - Lý do 60 s — vì NGƯỜI LÁI, không phải vì chính xác hơn (đo 30/10, bình thường, 630 chuyến):

    | ngưỡng | lần đổi tuyến | tổng tiết kiệm so với D | mỗi lần đổi | E nhanh hơn D (tổng) | chuyến E chậm hơn D > 1 phút |
    |---|---|---|---|---|---|
    | 0 s | 1.227 (1,95/chuyến, tối đa 6; 60% chuyến đổi ≥ 2 lần) | 234 phút | 0,19 phút | 2,21% | 1 |
    | **60 s** | **147 (0,23/chuyến, tối đa 2)** | **172 phút** | **1,17 phút** | **1,63%** | **0** |
    | 120 s | 50 (0,08/chuyến) | 94 phút | 1,87 phút | 0,89% | 0 |

    Ngưỡng 0 NHANH NHẤT tính tổng (lúc đầu mình tưởng đổi liên tục sẽ thiệt — số đo cho thấy không phải), nhưng bắt người lái rẽ khác gần như mỗi 5 phút để đỡ ~11 giây. 60 s giữ 74% phần tiết kiệm với 1/8 số lần đổi. Cả 3 ngưỡng đều 0 lần vào đường đóng (đổi vì đường đóng không cần ngưỡng).
- **Kiểm:**
  - `kiem_tra_tuan7.py` (vẫn ĐẠT): tình trạng không đổi → tính lại từ 1/3 và 2/3 chuyến cho đúng chi phí phần còn lại (nguyên lý Bellman) 20/20; tuyến ghép 0 lỗi luật, 0 lần quay đầu tại chỗ.
  - Trong bộ chấm: chuyến không đổi tuyến lần nào cho phút trùng khít D (502/502; khắt khe 486/486).
- **Kết quả** (`danh_gia/cham_tuyen_that.py`, phương án E, 630 chuyến ngày 30/10):

  | | bình thường | khắt khe |
  |---|---|---|
  | tính lại TB / chuyến | 2,8 | 3,2 |
  | chuyến có đổi tuyến | 128 (20%) | 144 (23%) |
  | trên chuyến có đổi: D → E | 23,1 → 21,7 phút (−6%) | 25,3 → 24,2 phút (−4%) |
  | E nhanh hơn / chậm hơn D (chuyến có đổi) | 92% / 5% | 80% / 17% |
  | toàn bộ: E nhanh hơn D | 1,6% | 1,3% |
  | E không chậm hơn A (ngắn nhất) | 92% | 90% (D: 89%) |
  | vào đường đang đóng: D → E | 3 → **0** | 7 → **3** |

  - 3 lần còn lại (khắt khe) đều là chuyến đi từ Ngã sáu Cộng Hòa: lúc tính lại, tuyến cũ qua đường đóng mà KHÔNG còn đường tránh từ vị trí xe (bộ đếm `ket_dong_E` = 3/3; C cũng dính đúng chỗ đó).
  - Khắt khe: 17% chuyến đổi tuyến bị thiệt — tuyến mới hay luồn hẻm mà kịch bản này coi hẻm chậm hơn ước lượng 30%. Vẫn có lợi tổng thể.
- **Đã bỏ:**
  - tính lại theo giờ cố định (mỗi phút…): tình trạng chỉ đổi khi có lần chụp mới, tính thêm là phí;
  - ngưỡng 0 (đổi ngay khi rẻ hơn): nhanh hơn 0,6 điểm % nhưng đổi tuyến gấp 8 lần (bảng trên);
  - ngưỡng 120 s: bỏ lỡ gần nửa phần tiết kiệm.
  - Muốn đổi ngưỡng: `cham_tuyen_that.py --nguong=N` để đo lại.

## QĐ-014 — Bộ chuẩn METR-LA / PEMS-BAY theo đúng giao thức DCRNN, tự dựng đồ thị (30/10/2026)

- **Vì sao:** dữ liệu TP.HCM mới ~1 ngày, chưa đủ để học sâu. Cần chứng minh đường ống (chia, chuẩn hoá, thước đo) và mã mô hình ĐÚNG trên dữ liệu có số công bố, rồi mới tin số trên dữ liệu thật.
- **Nguồn:** `metr-la.h5`, `pems-bay.h5` từ Google Drive chính thức của tác giả DCRNN; `distances_*.csv`, `graph_sensor_*` từ repo DCRNN (MIT). Lưu `du_lieu/metr_la/` (không lên git, không phát tán lại).
- **Giao thức** (`mo_hinh/chuan_metr_la.py`) — giữ nguyên như bài báo để số so được:
  - 5 phút/bước; vào 12 bước → ra 12 bước; mẫu cửa sổ chia theo thời gian 70 / 10 / 20 (đúng `generate_training_data.py`);
  - z-score theo phần học (kể cả số 0, như mã gốc); tốc độ 0 = thiếu → loại khỏi MAE/RMSE/MAPE và khỏi hàm mất mát;
  - báo cáo bước 3 / 6 / 12 = 15 / 30 / 60 phút.
- **Đồ thị:** KHÔNG mở `adj_mx*.pkl` của repo (pickle tải về có thể chạy mã). Dựng lại từ khoảng cách: W = exp(−(d/σ)²), bỏ W < 0,1.
- **Kiểm đường ống (khớp bài báo):**
  - HA (trung bình cùng giờ cùng thứ, như `eval_baseline_methods.py`): METR-LA 4,15 / 7,77 / 12,9% (bài báo 4,16 / 7,80 / 13,0%); PEMS-BAY 2,88 / 5,59 / 6,8% (trùng).
  - Số cạnh đồ thị (bỏ đường chéo): 1.515 / 2.369 = đúng bảng 1 bài Graph WaveNet.
  - Mốc "giữ nguyên số đo cuối" (METR-LA): 3,71 / 4,61 / 6,14 MAE — mô hình học sâu phải thắng xa mốc này.
- **Mô hình** (`mo_hinh/hoc_sau.py`): GRU dùng chung mọi nút (không không gian, cùng loại FC-LSTM) và Graph WaveNet đúng siêu tham số bài báo. Mục tiêu: Graph WaveNet gần 2,69 / 3,07 / 3,53 MAE (bài báo, Titan Xp); GRU nằm giữa FC-LSTM và Graph WaveNet → khoảng cách GRU ↔ GWN = đóng góp của thông tin không gian.
- **Dừng sớm** sau 20 vòng không tốt hơn (bài báo chạy đủ 100 vòng): chỉ để đỡ giờ máy (GTX 1650 ~110 s/vòng); ghi rõ khi báo cáo.
- **Kết quả** (30/10, tập kiểm tra METR-LA, MAE / RMSE / MAPE ở 15 | 30 | 60 phút):

  | mô hình | 15 phút | 30 phút | 60 phút | TB 12 bước |
  |---|---|---|---|---|
  | **Graph WaveNet (của mình)** — 69 vòng, tốt nhất vòng 49, 127 phút | **2,69 / 5,18 / 7,0%** | **3,06 / 6,18 / 8,5%** | **3,48 / 7,20 / 10,1%** | 3,02 / 6,11 / 8,32% |
  | Graph WaveNet (bài báo) | 2,69 / 5,15 / 6,9% | 3,07 / 6,22 / 8,4% | 3,53 / 7,37 / 10,0% | 3,04 / 6,09 / 8,23% (bảng 3) |
  | **GRU dùng chung nút (của mình)** — 100 vòng, 47 phút | 3,00 / 5,91 / 8,0% | 3,61 / 7,30 / 10,2% | 4,48 / 9,00 / 13,7% | 3,60 / 7,32 / 10,26% |
  | FC-LSTM (bài báo DCRNN) | 3,44 / 6,30 / 9,6% | 3,77 / 7,23 / 10,9% | 4,37 / 8,69 / 13,2% | |
  | giữ nguyên số đo cuối (của mình) | 3,71 | 4,61 | 6,14 | |

  - Graph WaveNet **tái lập đúng bài báo** (lệch ≤ 0,05 MAE, 60 phút còn tốt hơn) → mã mô hình + đường ống tin được.
  - Đóng góp của thông tin KHÔNG GIAN (GRU → GWN): MAE giảm 10% / 15% / 22% ở 15 / 30 / 60 phút — dự báo càng xa càng cần biết đường lân cận. Đây là lý do khi chạy trên TP.HCM phải đưa đồ thị đoạn đường vào, không dự báo từng đoạn riêng lẻ.
  - GRU vẫn đang cải thiện ở vòng 100 (tốt nhất vòng 92) — có thể chạy dài hơn; không ảnh hưởng kết luận.
- **Đã bỏ:**
  - dùng thẳng `adj_mx.pkl` (rủi ro chạy mã lạ; tự dựng lại cho ra đúng số cạnh công bố);
  - thư viện có sẵn (torch_geometric_temporal…): thêm phụ thuộc nặng, khó soát giao thức; tự viết ~100 dòng, đọc được từng bước.

## QĐ-015 — Học sâu trên TP.HCM: tầng vàng 15 phút, đồ thị đoạn nối tiếp THƯA, chia y như moc_so_sanh (30/10/2026)

- **Nội dung** (`mo_hinh/hoc_sau_hcm.py`, dùng lại mô hình của `hoc_sau.py`):
  - Nút = đoạn đường có dữ liệu TomTom (7.413); giá trị r; thiếu = NaN. Vào 3 kênh: r chuẩn hoá (thiếu → 0), cờ "có số đo", giờ trong ngày.
  - Đồ thị: đoạn i → j khi j bắt đầu ở nút cuối của i (13.080 cặp) + vòng tự thân; P_xuôi, P_ngược.
  - Vào 8 khung (2 giờ) → ra 4 khung; Graph WaveNet 3 khối (vùng nhìn 10).
  - Chia + thước đo GIỐNG `moc_so_sanh.py` (import thẳng `TY_LE_HOC`, `KHOANG_HO`, `danh_gia`) → so thẳng với giữ nguyên / TB 1h / GBM trên CÙNG từng ô. Đã kiểm: số ô và MAE "giữ nguyên" trùng khít.
  - 10% cuối phần học làm kiểm định để dừng sớm (không dùng cập nhật trọng số — GBM thì học hết, mô hình học sâu chịu thiệt chút).
- **Vì sao đồ thị THƯA, bỏ ma trận tự học:** N = 7,4 nghìn → ma trận N × N 54 triệu ô, nhân đặc ~138 GFLOP mỗi tầng, không vừa GTX 1650 4 GB. Nhân thưa (`hoc_sau.lan_truyen`) cho cùng kết quả. Bài báo (bảng 3): bỏ ma trận tự học chỉ kém 3,08 so với 3,04 MAE.
- **Kết quả lần đầu** (30/10 22:4x; 112 khung 29/10 18:45 → 30/10 22:30; học 71 mẫu, kiểm tra 30 khung tối thứ Sáu 15:15–22:30), MAE điểm %:

  | | 15 phút | 30 phút | 60 phút |
  |---|---|---|---|
  | giữ nguyên | 7,85 | 9,97 | 11,51 |
  | TB 1h | 8,49 | 9,63 | 11,08 |
  | GBM (`moc_so_sanh`) | 7,59 | 9,36 | **10,53** |
  | GRU (không đồ thị) | 8,08 | 9,71 | 11,05 |
  | **Graph WaveNet** (dừng vòng 62, 8,5 phút) | **7,46** | **9,14** | 10,77 |

  - Đồ thị lại giúp rõ (GRU → GWN: −8% / −6% / −3%), cùng chiều với METR-LA.
  - **CHƯA KẾT LUẬN**: 1,5 ngày, chỉ 71 mẫu học, 1 buổi tối để kiểm tra; chưa có "hôm qua / tuần trước" (GBM sẽ có khi đủ ngày). Chạy lại khi ≥ 7–14 ngày.
- **Đã bỏ:**
  - làm theo cạnh 5 phút (~28 nghìn cạnh): không so được với GBM (tầng vàng 15 phút), lại nặng gấp 4 lần;
  - mỗi đoạn một mô hình riêng: mất thông tin lân cận (bằng chứng: GRU kém GWN).

## QĐ-016 — Tìm theo cạnh, phạt rẽ trái qua trục lớn 30 s, tuyến thay thế bằng phương pháp phạt (30–31/10/2026)

- **Trạng thái A\* = (nút, nút vừa rời)**, thay cho (nút, đường đang đi):
  - Trạng thái cũ gộp hai chiều xe tới cùng một nút trên đường hai chiều → sai khi chi phí phụ thuộc hướng tới (rẽ trái; cả luật "không quay đầu" vốn có).
  - Kiểm: chi phí 270/270 tuyến (90 cặp × 3 phương án, 8h, chưa bật phạt) TRÙNG KHÍT trước/sau → không đổi kết quả cũ, chỉ đúng hơn về mô hình.
  - Giá: số trạng thái ~gấp đôi → tuyến 8h chậm nhất 1,46 → 2,3–2,8 s (vượt 2 s).
- **Cận ALT theo cửa sổ giờ** (`DinhTuyen._alt_cho`), để kéo thời gian lại:
  - trọng số = thời gian qua cạnh ở tốc độ LỚN NHẤT trong 3 giờ từ giờ xuất phát; bảng riêng cho phương án tối ưu nhân thêm hệ số phạt NHỎ NHẤT. Vẫn là cận dưới hợp lệ (kiểm ALT có/không: 20/20 cùng chi phí);
  - dựng ~0,7 s, nhớ theo (giờ, có số đo hiện tại), xóa khi `dat_tinh_trang`;
  - kết quả: trạng thái phương án tối ưu TB 178 nghìn (tuyến nặng nhất) → 11 nghìn TB; 3 phương án chậm nhất **1,23 s**.
  - Thử 16 / 24 mốc: gần như không đỡ thêm (14,4 → 13,3 nghìn trạng thái) → giữ 8.
  - `BanDo.tim` dùng thẳng (không ALT, như kiem_tra_tuan1) chậm hơn: 59 → ~130 ms TB; đường chạy thật dùng `DinhTuyen` nên không ảnh hưởng.
- **Phạt rẽ trái** (`PHAT_RE_TRAI_S` = 30 s, chỉ phương án tối ưu, cộng vào CHI PHÍ không vào giờ tới dự kiến):
  - rẽ trái = đổi hướng ≥ 30° sang trái (toạ độ phẳng) tại nút giao có trục lớn (trunk/primary/secondary, ≥ 3 nút kề; 9.718 nút). Xe chạy bên phải → rẽ trái phải cắt dòng xe ngược chiều / dòng trục lớn.
  - 30 s là GIẢ ĐỊNH (chưa có số đo trễ rẽ ở TP.HCM): cỡ trễ kiểm soát ở nút có đèn mức phục vụ C (20–35 s/xe, HCM 2010). Đổi được qua hằng số.
  - Thử 0 / 15 / 30 / 60 s (90 cặp, 8h, thời gian theo mô hình — KHÔNG gồm thời gian chờ rẽ vì dữ liệu không đo):

    | phạt | rẽ trái TB/tuyến | thời gian chạy | tuyến đổi |
    |---|---|---|---|
    | 0 s | 3,52 (ngắn nhất: 2,84) | gốc | – |
    | 15 s | 2,62 | +0,2% | 47/90 |
    | **30 s** | **1,86 (−47%)** | **+1,3%** (tối đa +3 phút) | 64/90 |
    | 60 s | 1,26 | +3,0% | 73/90 |

  - Không phạt thì tuyến tối ưu rẽ trái qua trục lớn NHIỀU hơn cả tuyến ngắn nhất. 30 s: bớt 1,66 lần rẽ/tuyến với ~14 s chạy thêm → mỗi lần rẽ bỏ được chỉ tốn ~8 s, ít hơn nhiều mọi mức trễ rẽ hợp lý.
  - **Chấm tốc độ thật** (`cham_tuyen_that.py --phat-re-trai=0` so với mặc định, CÙNG dữ liệu 30/10, 630 chuyến). Bộ chấm chỉ tính thời gian CHẠY; trễ rẽ trái thật không đo được nên thử cộng CÙNG một mức trễ giả định cho MỌI tuyến (A, D chịu như nhau — không vòng vo):

    | trễ thật mỗi lần rẽ trái | D phạt 0: nhanh hơn A / không chậm hơn A | D phạt 30 s | D phạt 30 so với phạt 0 |
    |---|---|---|---|
    | 0 s (chỉ thời gian chạy) | 19,4% / 91% | 18,3% / **84%** | +1,4% |
    | 15 s | 18,1% / 89% | 18,7% / 88% | −0,8% |
    | 30 s | 16,9% / 86% | 19,2% / 92% | −2,7% |
    | 45 s | 15,8% / 84% | 19,6% / 93% | −4,5% |

    - Rẽ trái TB/chuyến: A 2,87, C 3,49, D 3,41 → **1,95** khi phạt.
    - Phạt có lợi khi trễ thật > ~10 s mỗi lần rẽ trái qua trục lớn (nút có đèn gần như chắc chắn hơn mức này).
    - Nếu chỉ tính thời gian chạy (trường hợp xấu nhất cho phạt) vẫn ĐẠT tiêu chí kế hoạch (84% ≥ 80%, 18,3% ≥ 5%), nhưng 06:30 / 07:30 xuống 74% / 78% — ghi rõ khi báo cáo.
    - Tính lại giữa đường (E) với phạt 30 s: đổi tuyến 20% chuyến, chuyến có đổi 23,2 → 21,7 phút, vào đường đóng 0; tự kiểm 501/501.
- **Tuyến thay thế** (`DinhTuyen.tuyen_thay_the`) — phương pháp phạt (kiểu Bader và cs. 2011): tìm tốt nhất → nhân ×1,5 chi phí cạnh đã dùng → tìm lại; nhận khi chi phí thật ≤ 1,25 × tốt nhất và trùng ≤ 70% chiều dài với mọi tuyến đã nhận (tiêu chí "kéo dãn có giới hạn / chia sẻ có giới hạn" của Abraham và cs. 2010, chặt hơn mức 80% của họ).
  - kiem_tra_tuan7 (8h): ≥ 2 tuyến ở 99% cặp, đủ 3 tuyến 78%; chi phí tuyến thay thế TB ×1,10; trùng TB 15%; 0 vi phạm / lỗi luật / đường đóng.
  - Thời gian (dùng lại tuyến đầu từ `tim()`): TB 0,58 s, chậm nhất 2,06 s → API trả 3 phương án trước, tuyến thay thế gọi riêng.
- **Đã bỏ:**
  - Yen k-shortest: ra các tuyến chỉ khác nhau vài cạnh;
  - phạt rẽ trái theo (nút, đường) cũ: gộp hướng tới → phạt sai chiều;
  - phạt rẽ trái cả phương án nhanh nhất: "nhanh nhất" giữ đúng nghĩa thời gian chạy đo được.

## QĐ-017 — API chạy trên VPS sẵn có của người dùng THAY EC2; mọi phần AWS khác giữ nguyên (31/10/2026)

- **Người dùng quyết định** ("t có vps mà lo j cần j ec2"; rồi nói rõ: "thay vì thuê ec2 thì thay bằng vps thôi mà có bảo ko dùng aws"). CHỈ thay mục "API trên EC2 nhỏ hoặc ECS" của tuần 9.
- **Kiến trúc:**
  - AWS (giữ nguyên): Lambda + Scheduler 5 phút → S3; Athena; **web bản đồ trên S3 + CloudFront (HTTPS)**; CloudWatch cảnh báo; Budgets.
  - VPS: chỉ API (FastAPI) trong container RIÊNG, đọc dữ liệu mới nhất từ S3 bằng khóa IAM chỉ-đọc (tải ra ~2 GB/tháng, trong 100 GB miễn phí). Web trên CloudFront gọi API này (CORS, HTTPS).
  - Máy nhà: huấn luyện (GPU), đưa trọng số lên VPS.
  - Kiến trúc lai: AWS + VPS + máy nhà.
- **Cần trên VPS:** bộ định tuyến đo 31/10: ~1,0 GB RAM, khởi động 20 s (nạp một lần) → để trống ~1,5 GB cho API. Lúc triển khai kiểm `free -h`; thiếu thì thêm swap hoặc thu nhỏ vùng bản đồ.
- **Ràng buộc** (VPS đang chạy Royal POS của đồ án):
  - không đụng container / CSDL của đồ án;
  - đi qua Caddy + Cloudflare sẵn có bằng tên miền con, không mở cổng mới (tường lửa DOCKER-USER chỉ nhận Cloudflare);
  - sửa cấu hình Caddy thì hỏi người dùng trước;
  - IP VPS, khóa S3 chỉ ở `.env` trên VPS, KHÔNG lên git;
  - API có mật khẩu (TomTom gói Evaluation không cho phát tán công khai); web tĩnh trên CloudFront không chứa dữ liệu TomTom, chỉ lấy qua API.
- **Đã bỏ:** EC2 / ECS (~10–15 USD/tháng nếu bật suốt; tín dụng AWS đã hết hạn). Các dịch vụ AWS khác KHÔNG bỏ.

## QĐ-018 — Sản phẩm: API → web demo cơ bản → app Android thiết kế riêng trên Figma; train khi đủ dữ liệu (31/10/2026)

- **Người dùng quyết định** (31/10 ~00:20): "app sẽ thiết kế ui ux như đồ án ko phải bê bên đồ án qua nha mà thiết kế 1 kiểu khác nhưng trên figma á; web demo thì làm giao diện cơ bản để test chức năng đc r; ... nào thu thập đủ dữ liệu để train thì bắt đầu tiếp".
- **Thứ tự:**
  1. API chung (FastAPI) — web và app cùng dùng: `/tuyen` (3 phương án + tuyến thay thế, giờ đi, mưa), `/tinh-lai` (xe đang chạy, QĐ-013), `/tinh-trang`, `/du-bao` (15/30/60 phút), `/ngap`.
  2. **Web demo giao diện CƠ BẢN** — chỉ để test chức năng: bản đồ Leaflet, chọn điểm, giờ đi, mưa to, 3 tuyến + bảng so sánh, tuyến thay thế, lớp kẹt / dự báo / ngập, chế độ "xe ảo chạy lại tốc độ thật" để xem đổi tuyến giữa đường. Không cần đầu tư thẩm mỹ.
  3. **App Android (Kotlin)** — UI/UX THIẾT KẾ KỸ trên Figma như cách làm ở đồ án (tự thiết kế toàn bộ, không dùng kiểu mặc định, người dùng duyệt bản Figma rồi mới code), nhưng **phong cách KHÁC hẳn đồ án** — không bê bộ Sơn Son / Royal POS sang. Bản đồ MapLibre/osmdroid (không cần khóa Google Maps); GPS thật, đi theo tuyến, báo đổi tuyến giữa đường.
- **Train / test mô hình khi đủ dữ liệu** (không cần thu đủ 3 tháng mới train) — dữ liệu bắt đầu 29/10/2026 19:00:
  - ~05–06/11 (7 ngày): train thật lần 1 (GBM + Graph WaveNet); có đặc trưng "hôm qua", chưa có "tuần trước"; kiểm tra 1–2 ngày cuối.
  - ~12–13/11 (14 ngày): lần chính — có "tuần trước", học ~10 ngày, kiểm tra 3–4 ngày gồm cả cuối tuần.
  - Tuần 5–6 kế hoạch (30/11–13/12): ~5 tuần dữ liệu → kết quả cho báo cáo + ablation sự cố / thời tiết.
  - VẪN THU tiếp tới cuối kỳ (~0,2–0,3 USD/tháng): mỗi tuần train lại; 1–2 tuần cuối GIỮ RIÊNG (không học) cho chạy thử ảo tuần 11.
  - Tháng 11 cuối mùa mưa TP.HCM: mưa còn — cần cho M6 (mưa làm kẹt thêm bao nhiêu); sang 12–1 ít mưa.
- **Trong lúc chờ dữ liệu:** làm API + web demo, khai phá M5 / M8 / M9, kiểm tay 30 đoạn ghép.

## QĐ-019 — Chốt tên đề tài (31/10/2026, người dùng nhờ chốt: "chot ten de tai cho t cai")

- **Tiếng Việt:** Xây dựng hệ thống định tuyến giao hàng xe máy tại TP.HCM ứng dụng học sâu dự báo ùn tắc và AWS
- **Tiếng Anh:** Building a Motorbike Delivery Routing System for Ho Chi Minh City Using Deep Learning Congestion Forecasting and AWS
- Bản dài trước (~36 chữ) người dùng nhờ rút ngắn cùng ngày: "Xây dựng hệ thống định tuyến giao hàng xe máy tại TP.HCM dựa trên khai phá dữ liệu giao thông thời gian thực và dự báo ùn tắc bằng học sâu, kết hợp điện toán đám mây AWS". "Khai phá dữ liệu", "thời gian thực" chuyển xuống phần mô tả / tóm tắt đề tài.
- Phương án ngắn khác đã đưa: "...ứng dụng khai phá dữ liệu và học sâu" (bỏ AWS); "Định tuyến giao hàng xe máy tại TP.HCM dựa trên dự báo ùn tắc bằng học sâu, kết hợp AWS".
- **Vì sao:** nói đúng những gì đã / sẽ làm — "hệ thống" (API + web + app, QĐ-018), "xe máy" + "TP.HCM" (đồ thị xe máy, luật cấm rẽ, rẽ trái), "khai phá dữ liệu" (M1–M9, giữ chữ từ tên cũ đã gửi thầy), "thời gian thực" (TomTom 5 phút), "dự báo ùn tắc bằng học sâu" (Graph WaveNet đã tái lập bài báo), "kết hợp AWS" (Lambda, S3, Athena, CloudFront — API ở VPS theo QĐ-017 nên không ghi "trên nền tảng AWS").
- **Đã bỏ:**
  - "Hybrid Cloud" — dễ bị hỏi vặn; tính lai (AWS + VPS + máy nhà) giải thích trong báo cáo;
  - "thông minh" — chung chung;
  - "trên đồ thị" — chi tiết kỹ thuật, để trong báo cáo cho tên đỡ dài.
- **Thầy đã đồng ý** (người dùng báo 07/11/2026: "thầy bảo ok rồi đề tài có độ phức tạp rất tốt và có thể yên tâm làm"). Thầy sửa tên thì ghi QĐ mới.

## QĐ-020 — Đưa hồ sơ lịch sử vào mô hình dự báo; kết quả train thật lần 1 (06/11/2026)

- **Dữ liệu:** 775 khung, 29/10 18:45 → 06/11 20:15, 7.463 đoạn, 176/176 phép kiểm đạt. Học tới 04/11 10:00, kiểm tra từ 04/11 11:15 (229 khung, ~1,6 triệu ô mỗi tầm, mọi mô hình chấm trùng từng ô).
- **Vì sao thêm hồ sơ:** GBM thắng "giữ nguyên" nhưng thua trung bình lịch sử ở 60 phút (7,64 so với 7,33) vì không biết nhịp bình thường của từng đoạn.
- **Nội dung** (`mo_hinh/ho_so_lich_su.py`): H[khung, đoạn] = TB r cùng loại ngày (thường / cuối tuần) và ô 15 phút, chỉ từ phần học, loại chính khung đó (chống rò nhãn).
  - GBM (`gbm_ls`): thêm `r_ls_dich`, `ls_tru_r`, `lech_ls`.
  - Học sâu (`--ho-so`): thêm kênh độ lệch, học phần chênh so với hồ sơ ở giờ đích.
- **Kết quả** (MAE điểm %, tập kiểm tra):

  | mô hình | 15 phút | 30 phút | 60 phút |
  |---|---|---|---|
  | giữ nguyên | 6,49 | 8,31 | 9,78 |
  | TB 1 giờ | 7,22 | 8,28 | 9,78 |
  | trung bình lịch sử | 7,34 | 7,33 | 7,33 |
  | GRU | 6,19 | 7,51 | 8,61 |
  | Graph WaveNet | 6,16 | 7,39 | 8,36 |
  | GBM | 5,99 | 7,05 | 7,64 |
  | Graph WaveNet + hồ sơ | 6,24 | 6,70 | 6,73 |
  | **GBM + hồ sơ** | **5,72** | **6,47** | **6,64** |

  - **Tiêu chí thấp hơn lịch sử ≥ 10%:** GBM + hồ sơ 22,1% / 11,7% / **9,3%** → đạt ở 15, 30 phút, **chưa đạt ở 60 phút**. Graph WaveNet + hồ sơ 15,0% / 8,6% / 8,2%.
  - Hồ sơ giúp GBM giảm 4,5% / 8,2% / 13,1%; giúp Graph WaveNet −1,3% (kém đi) / 9,3% / 19,5%.
  - GBM + hồ sơ: RMSE 8,83 / 9,85 / 10,09; ban ngày 6,89 / 7,76 / 7,99; đúng 3 mức 86,2% / 84,6% / 84,3%; F1 mức kẹt 0,651 / 0,599 / 0,580 (giữ nguyên 0,638 / 0,544 / 0,481).
  - Ổn định theo ngày (GBM + hồ sơ, 04/11 · 05/11 · 06/11): 15 phút 6,67 · 5,42 · 5,47; 60 phút 7,57 · 6,27 · 6,50. 04/11 chỉ tính từ 11:15 nên không có đêm dễ đoán, 06/11 tới 20:15.
- **Giới hạn, chưa kết luận:**
  - mới một tuần: học 5,6 ngày, kiểm tra 2,4 ngày toàn ngày thường, chưa có mưa ≥ 5 mm/h, chưa có đặc trưng "tuần trước";
  - mốc lịch sử chỉ tra đúng thứ ở 45% dòng, còn lại lùi về loại ngày; thêm tuần thì mốc này tốt lên;
  - GBM có 41 đặc trưng (sự cố, thời tiết, lân cận…), Graph WaveNet chỉ 5 kênh → chưa phải so công bằng; Graph WaveNet thua GBM chưa nói được học sâu kém hơn;
  - GWN so với GRU chỉ hơn 0,5% / 1,6% / 2,9%, thấp hơn nhiều mức 10–22% trên METR-LA (488 mẫu học, đồ thị thưa, bỏ ma trận tự học); chưa chạy GRU + hồ sơ;
  - dừng sớm của học sâu dựa trên 54 khung kiểm định, phần lớn là đêm (kiểm định 5,10 so với kiểm tra 6,24–6,73). Đã sửa: từ lần sau ít nhất 96 khung.
- **Lần chính ~12–13/11:** train lại đủ 4 mô hình + GRU có hồ sơ; thêm sự cố / thời tiết vào Graph WaveNet để so công bằng; ablation sự cố / thời tiết.
- **Đã bỏ:** tính hồ sơ không loại chính khung (rò nhãn); dùng hẳn đúng thứ khi mới một tuần (mỗi thứ chỉ 1 ngày, trùng chính nhãn).

## QĐ-021 — Kết quả khai phá đợt 1 (M3, M5, M8, M9) và phép thử "có đoán mò không" (07/11/2026)

Dữ liệu tới 07/11 00:15. Script ở `khai_pha/`, `mo_hinh/kiem_doan_mo.py`; bảng + hình ở `ket_qua/` (không lên git).

- **Phép thử đoán mò** (`kiem_doan_mo.py`, cùng tập kiểm tra, học trên mẫu 800 nghìn dòng; 15 | 30 | 60 phút):

  | cách | MAE | đúng 3 mức | F1 mức kẹt | đúng hướng khi đổi ≥ 15 điểm |
  |---|---|---|---|---|
  | đoán mò: luôn đoán TB | 20,25 · 20,25 · 20,26 | ~51% | 0,000 | 72–75% |
  | đoán mò: bốc ngẫu nhiên | 25,1 | ~46% | ~0,06 | 60–61% |
  | giữ nguyên | 6,48 · 8,34 · 9,89 | 83,8 · 79,4 · 75,9% | 0,636 · 0,542 · 0,478 | 0% |
  | học trên nhãn XÁO TRỘN | 6,48 · 8,34 · 9,89 | 83,8 · 79,4 · 75,8% | 0,637 · 0,542 · 0,478 | 46–49% |
  | **mô hình thật** (GBM + hồ sơ) | **5,71 · 6,46 · 6,63** | **86,3 · 84,7 · 84,4%** | **0,649 · 0,601 · 0,581** | **87 · 91 · 93%** |

  - Nhãn xáo trộn → tụt về đúng mức "giữ nguyên": cách chấm không tự tạo ra điểm, phần hơn của mô hình thật là học được thật.
  - Đoán mò về hướng KHÔNG phải 50%: đường đổi mạnh thường là đang quay về mức thường, nên đoán TB đã đúng 72–75%. Phải so 87–93% với mức này.
  - Học 800 nghìn dòng ra gần y như 3,9 triệu dòng (5,71 so với 5,72): số không phụ thuộc mẫu.
  - Chưa chứng minh được: tuần sau còn đúng không, mưa to thì sao. Cần chạy lại nhiều tuần.
- **M3 — nhóm đường** (6 ngày thường, 7.176 đoạn):
  - Theo mức, 3 nhóm, ổn định (ARI 0,84, silhouette 0,33): thông thoáng 28,5% km (kẹt TB ban ngày 11%), vừa 42,5% (31%), nặng 29% (50%). Cả ba đều đỉnh 17:30.
  - Theo dạng, 2 nhóm nhưng ranh giới MỜ (silhouette 0,18, ARI 0,61): hai đỉnh sáng + chiều 38% km, nặng về chiều 62%. Không có nhóm chỉ kẹt sáng như dự kiến.
  - Bỏ DTW: nó kéo đỉnh sáng khớp đỉnh chiều, ngược mục đích.
- **M5 — kẹt lan** (5 phút, cặp cùng tuyến ≤ 4 km, phần dư sau khi trừ nhịp ngày):
  - **KHÔNG đo được tốc độ lan.** Đỉnh tương quan ở độ trễ ~0 mọi khoảng cách; độ dốc +0,10 phút/km (trừ biến động chung +0,24, CI +0,11..+0,46) tương đương > 250 km/h, không phải tốc độ vật lý → lấy mẫu 5 phút quá thưa để thấy, không nên ghi là "tốc độ lan".
  - Biến động CHUNG toàn mạng chiếm phần lớn: tương quan ở 3,5–4 km 0,38 → 0,08 sau khi trừ. Còn lại chỉ mạnh trong ~1 km (0,50 ở < 0,5 km; 0,20 ở 0,5–1 km; 0,14 ở 1–2 km).
  - Granger sau khi trừ (3.000 cặp 0,5–2 km): chỉ thượng nguồn báo trước 18,4%, chỉ hạ nguồn 12,0%, cả hai 23,5%, không chiều nào 46%. Không có chiều áp đảo.
  - Dùng được: lân cận chỉ cần tầm ~1 km; nên thêm đặc trưng **trạng thái chung toàn mạng** cho mô hình ở lần train chính.
- **M8 — đối chiếu Index 2025** (7 ngày 31/10–06/11, cân theo chiều dài): mức kẹt 24 giờ 38–45%, 6–22 giờ 53–63% (Index 46,9%, nằm giữa); chiều 17–19h 15,6–16,0 km/h (Index 14,8); 10 km ban ngày 28–30 phút (Index 31,9). Tốc độ cao hơn 5–14%: khác vùng, khác cách cân, ô tô 2025. Số Index lấy từ note 29/10, trang TP.HCM không mở lại được 07/11.
- **M9 — tuyến ngắn nhất dính kẹt** (500 tuyến giữa điểm giao hàng thật, TB 7,1 km; 69% chiều dài có số đo; 2.367 lần chụp):

  | ngày thường | ≥ 200 m kẹt nặng | ≥ 1 km kẹt nặng | % dài đông | thời gian so với đường trống |
  |---|---|---|---|---|
  | 17h | 89% | 56% | 83% | +147% |
  | 7–8h | 74–77% | 34% | 71% | +101..104% |
  | 13h | 54% | 13% | 62% | +71% |
  | 1–4h | ~1–2% | 0% | 1–2% | +1–2% |

  - Cuối tuần nhẹ hơn hẳn: đỉnh 39% (≥ 200 m), 10% (≥ 1 km) lúc 18h; mới một cuối tuần trọn.
  - ~5–6% tuyến ngắn nhất đi qua đường đang đóng, gần như mọi giờ (đóng dài ngày).
  - Chỉ tính trên phần có số đo; thời gian +147% là trên phần đó.

## QĐ-022 — Web demo: ảnh nền HOT, chỉ chạy ở máy (07/11/2026)

- **Ảnh nền:** HOT (`{s}.tile.openstreetmap.fr/hot`), dữ liệu OpenStreetMap, màu nhạt nên lớp kẹt xe và các tuyến nổi rõ. Đã so tận mắt tại trung tâm TP.HCM với OSM Pháp (quá nhiều chữ), OSM Đức (đường hồng lẫn với màu kẹt), Esri (không phải dữ liệu OSM mà đồ thị đang dùng).
- **Đã bỏ:** `tile.openstreetmap.org` (máy này không kết nối được, chưa rõ do đâu); CARTO (trả ảnh "API KEY REQUIRED").
- **Dự phòng:** lỗi từ 3 ảnh trở lên thì tự vẽ đường chính từ `/api/hinh-doan`.
- **Còn phải làm trước khi mở công khai:** HOT là máy chủ cộng đồng, chưa đọc điều khoản dùng, có thể không hợp lưu lượng lớn. API chưa có mật khẩu, vì vậy chỉ nghe 127.0.0.1 (TomTom gói Evaluation).
- **Chưa sửa, phạt ngập:** `PHAT_NGAP_S` = 180 s (mưa ≥ 1 mm/h) và 600 s (mưa ≥ 5 mm/h, triều) là số đặt tay, chưa đo, và tính cho MỖI CẠNH nên đường chia càng nhỏ phạt càng nặng: Ung Văn Khiêm 33 cạnh ở 3 mm/h = 99 phút phạt, tuyến tối ưu đi vòng từ 4,2 lên 7,8 phút. Nên đổi sang phạt theo điểm ngập hoặc theo mét. "Dự kiến" cũng chưa tính chậm vì ngập. Số đánh giá tuyến không bị ảnh hưởng vì `cham_tuyen_that.py` chạy không mưa.

## QĐ-023 — Chấm tuyến 8 ngày trên điểm giao hàng thật: đạt, kèm các điểm yếu (07/11/2026)

90 cặp điểm giao hàng thật (Zenodo, hạt 42) × 10 giờ xuất phát × 8 ngày (30/10–06/11) = 7.200 chuyến. Chấm bằng tốc độ TomTom đo sau lúc xuất phát; bộ định tuyến chỉ biết số đo tới lúc đi, CHƯA dùng dự báo. Script `cham_tuyen_that.py`, `tong_hop_cham.py`, `do_ben_cham.py`. Bộ 10 địa danh đang chạy, kết quả ghi sau.

| so sánh | nhanh hơn | CI 95% (theo cặp điểm) | cặp nhanh hơn |
|---|---|---|---|
| D tối ưu so với A ngắn nhất | 11,4% (23,2 → 20,5 phút) | 8,8 .. 14,7 | 94% |
| D, bỏ hẳn phạt đường đóng | 9,6% | 8,2 .. 11,1 | |
| E tính lại giữa đường so với A | 12,6% | 9,9 .. 15,9 | 94% |
| D so với B bản đồ thường | 11,1% | 8,6 .. 14,7 | 96% |
| C nhanh nhất so với B | 13,4% | 10,9 .. 16,9 | 100% |
| E so với D | 1,3% | 1,1 .. 1,6 | 91% |

- **Tiêu chí kế hoạch** (không chậm hơn ≥ 80%, nhanh hơn ≥ 5%): gộp 84,1%, đạt 7/8 ngày, 18/20 khung giờ.
- **Không đạt:** Chủ nhật 01/11 (79,2%; E đạt 81,8%, chưa rõ vì sao thấp hơn thứ Bảy 88%, mới có một Chủ nhật); 06:30 ngày thường (70%) và cuối tuần (78%).
- **06:30:** C đạt 95% ở khung này. D = C + phạt kẹt + phạt rẽ trái, nên phần tụt là giá của các mức phạt đó, không phải số đo sai. Khi chậm, D chậm TB 0,8 phút.
- **Đánh đổi của D:** dài hơn A 9,6% (7,53 so với 6,87 km), rẽ trái qua trục lớn ít hơn 35% (2,13 so với 3,29). Chậm hơn A ở 15,9% chuyến: trung vi 0,5 phút, p90 1,8 phút.
- **Độ bền 1, cạnh không đo:** chiếm 30,3% thời gian của A, 30,7% của D, nên đổi hệ số 0,7–2,0 thì số % gần như không đổi (11,3–11,6%). Nhưng tỉ lệ không chậm hơn thì nhạy: 87% ở 0,85; 81% ở 1,15; 77% ở 1,3; 66% ở 2,0. Nghĩa là nếu đường nhỏ thực tế nhanh hơn hồ sơ khoảng 30% thì tiêu chí 80% KHÔNG còn đạt.
- **Độ bền 2, phạt đường đóng:** phạt 300 s tính cho MỖI CẠNH, là số đặt tay. A dính ở 3,8% chuyến (270 chuyến, chỉ thuộc 4/90 cặp), TB 2,58 cạnh. Hai chuyến D chậm hơn A 50 phút (01/11 19:30) là do 10 cạnh × 5 phút, E tránh được, không phải chậm thật; bỏ các chuyến D dính đường đóng thì chậm nhất 8,6 phút. Báo cáo phải ghi số 9,6% bên cạnh 11,4%.
- **Giới hạn chưa kiểm được:** TomTom chỉ cho một tốc độ chung mỗi đoạn, không tách riêng xe máy, nên chênh lệch khi kẹt có thể khác với xe máy thật; thời gian chờ đèn và chờ rẽ trái không nằm trong số phút; 8 ngày chỉ có 1 thứ Bảy, 1 Chủ nhật; bootstrap theo cặp điểm chưa tính độ phụ thuộc giữa các ngày. Cách kiểm trực tiếp nhất: chạy thử vài chuyến thật có GPS điện thoại.
- **Việc tiếp:** đổi phạt đường đóng từ theo cạnh sang theo lần gặp rồi chấm lại ở lần train chính (không sửa `cham_tuyen_that.py` khi bộ địa danh đang chạy: mỗi ngày là một tiến trình mới, sẽ đọc mã mới giữa chừng); chấm lại khi đủ nhiều cuối tuần hơn.

- **Bộ 10 địa danh** (chọn tay, gần trung tâm, 7.056 chuyến; bộ điểm giao hàng thật ở trên mới là số chính):
  - D so với A 16,6% (CI 14,4 .. 18,8; 19,4 → 16,2 phút), E so với A 17,6% (15,4 .. 19,8), D so với B 15,7% (13,5 .. 18,0), C so với B 18,3% (16,2 .. 20,5), E so với D 1,2% (1,0 .. 1,4). Không chậm hơn 85,4%. Đạt 7/8 ngày, 16/20 khung giờ.
  - Không đạt: lại đúng Chủ nhật 01/11 (77,4%, E 80,3%); 06:30 ngày thường (68%), cuối tuần 06:30 (76%), 12:00 (79%), 14:00 (76%). Hai bộ điểm cùng cho thấy: Chủ nhật và sáng sớm là chỗ yếu; 06:30 cuối tuần D gần bằng bản đồ thường (−0,1%).
  - Thiếu 144 chuyến (2%), TẤT CẢ đi tới Lăng Cha Cả, 02–06/11: nút đích bị đường đóng bao quanh ở một số giờ nên không tìm được đường và chuyến bị bỏ khỏi mọi phương án. Vì thế nhóm này tự loại khỏi phép so.
  - D dính đường đóng 34 chuyến, 30 chuyến trong đó tới Lăng Cha Cả, E cũng không tránh được (đường đóng ngay sát đích). Ba chuyến D chậm 24–29 phút hôm 05/11 14:00 là do 7 cạnh × 5 phút; bỏ các chuyến này thì chậm nhất 8,2 phút.
  - Cạnh không đo: D 28% thời gian, A 20%, ngược với bộ giao hàng thật (gần bằng nhau). Hệ số 0,7 → 14,1%; 2,0 → 20,2%. Muốn D bằng A thì đường nhỏ phải chậm hơn hồ sơ 6,65 lần. Phạt đường đóng 0 → 16,0%.
  - 16,6% cao hơn 11,4% nhưng chưa đo vì sao. Có thể do điểm chọn tay gần trung tâm, và hệ số `RUI_RO_KHONG_DO` từng được chỉnh trên bộ địa danh này (30/10). Không báo 16,6% làm số chính.

## QĐ-025 — Chạy kiểm trước lần train chính (11/11/2026): mốc 60 phút đã đạt, sự cố và thời tiết chưa giúp

Dữ liệu tới 11/11 17:00 (1.242 khung 15 phút). Học tới 07/11 19:45, kiểm tra từ 07/11 21:00. Đây là lần chạy kiểm mã sau khi tách `BangHoc` và thêm đặc trưng trạng thái chung, CHƯA phải lần train chính.

| MAE (điểm %) | 15 phút | 30 phút | 60 phút |
|---|---|---|---|
| giữ nguyên | 6,06 | 7,79 | 9,24 |
| lịch sử | 7,89 | 7,83 | 7,72 |
| GBM | 5,65 | 6,68 | 7,24 |
| **GBM + hồ sơ** | **5,38** | **6,10** | **6,34** |
| thấp hơn lịch sử | 31,8% | 22,1% | **17,8%** |

- **Tiêu chí ≥ 10% nay đạt cả 3 mốc** (06/11: 60 phút mới 9,3%). Mốc lịch sử gần như cũ (7,72 so với 7,33), còn mô hình giảm từ 6,64 xuống 6,34, nên phần hơn là thật chứ không phải do tập kiểm tra dễ hơn. Tập kiểm tra đã khác 06/11, nên phải so lại ở lần train chính.
- **Phép thử đoán mò** (lặp lại 07/11):
  - mô hình 5,39 / 6,13 / 6,36;
  - nhãn xáo trộn tụt về đúng mức giữ nguyên (6,08 / 7,79 / 9,24);
  - đúng hướng khi đường đổi mạnh 87,6 / 90,8 / 93,2%, so với đoán TB 73,6–76,8%.
- **Ablation, câu hỏi 3** (bỏ nhóm thì MAE đổi bao nhiêu; tập sự cố đọc trên `co_du_lieu_su_co`, 55% ô kiểm tra):

  | bỏ nhóm | 15 phút | 30 phút | 60 phút |
  |---|---|---|---|
  | hồ sơ | +0,251 | +0,550 | +0,885 |
  | trạng thái chung (M5) | +0,050 | +0,069 | +0,115 |
  | sự cố (trên ô có dữ liệu sự cố) | +0,001 | +0,004 | −0,002 |
  | thời tiết | −0,002 | −0,005 | −0,020 |
  | lân cận | +0,002 | +0,001 | −0,000 |

  - Hồ sơ đóng góp nhiều nhất. Trạng thái chung toàn mạng có ích thật, đúng như M5 gợi ý.
  - **Sự cố gần như bằng 0.** Có thể vì 16.216/16.325 sự cố (99,3%) là loại "kẹt xe" do TomTom suy ra từ chính tốc độ, nên trùng thông tin với r.
  - **Thời tiết hơi làm xấu đi**, vì chưa có trận mưa to nào (ô có mưa dự báo ≥ 1 mm chỉ 2,7%).
  - Báo cáo phải nói thẳng như vậy. Lần train cuối khi có mưa to và nhiều tuần hơn thì đo lại.
- Hệ quả: khoảng mất sự cố 09–11/11 gần như không làm giảm độ chính xác dự báo.
- Graph WaveNet `--ho-so --them-kenh` chạy thử 1 vòng với kênh mới: mã chạy được (11 kênh vào = 5 kênh gốc + 6 kênh thêm, GPU 1,65 GB, 89 s/vòng). Số của 1 vòng không có ý nghĩa, đã xóa tệp kết quả.

## QĐ-024 — Web demo có chế độ dẫn đường bằng xe ảo; bản đồ vector MapLibre (07/11/2026, người dùng: "thêm thử đi")

Bổ sung QĐ-018: web vẫn là giao diện cơ bản để test, nay test luôn cả cách dẫn đường trước khi vẽ app. Bản thật có GPS vẫn nằm trong app.

- **Vì sao xe ảo, chưa GPS:** máy tính không di chuyển, GPS thật chỉ có nghĩa trên điện thoại. Xe ảo chạy lại theo số đo TomTom đã thu nên kiểm được chỉ dẫn, quay bản đồ và đổi tuyến giữa đường trên dữ liệu thật. Phần chỉ dẫn và tính lại ở API nên app dùng lại được.
- **Tách rõ biết và chưa biết:** xe DI CHUYỂN theo tốc độ đo thật ở lúc tới từng cạnh (`giay`). Giờ đến và màu tuyến chỉ dùng `du_kien`, `r_biet` tính từ lần chụp hiện tại, cập nhật mỗi lần chụp mới. Không dùng số đo tương lai cho những gì hiện lên cho người lái. Hết số đo thì xe chạy tiếp bằng số cuối và có ghi rõ trên màn hình.
- **Đổi tuyến:** cùng luật phương án E (QĐ-013): ở nút đầu tiên sau mốc lần chụp mới, đổi khi đỡ ≥ 60 s chi phí hoặc tuyến cũ qua đường vừa đóng. Đối chiếu với chấm tuyến: z77 01/11 19:30 22,0 phút; z20 05/11 17:00 39,7 phút, 3 lần đổi; khớp hết.
- **Bản đồ:** MapLibre GL + OpenFreeMap (vector, không cần khóa). Đã bỏ Leaflet vì không quay được; ảnh nền chữ sẽ quay ngược khi đi hướng nam, nên vector mới giữ chữ thẳng. HOT giữ làm dự phòng, sau đó tới đường chính từ `/api/hinh-doan`. Chưa đọc điều khoản OpenFreeMap và HOT, phải đọc trước khi mở công khai. MapLibre có bản Android nên app dùng được cùng cách.
- **Chỉ dẫn (`chi_dan.py`):** nguyên tắc là chỉ báo khi người lái phải quyết định. Quy tắc ghi ở đầu tệp; ngưỡng 20° / 45° / 150° là chọn tay rồi xem trên tuyến thật, chưa kiểm hàng loạt với thực địa.
- **Độ phức tạp tuyến** (`do_phuc_tap_tuyen.py`, 85/90 cặp điểm thật; 5 cặp ngoài khung `VUNG` của API dù vẫn nằm trong `trong_vung` theo khoảng cách tới nút):

  | 05/11 | km | phút thực tế | số chỉ dẫn TB | mỗi km | % đi trong hẻm hoặc đường không tên |
  |---|---|---|---|---|---|
  | 17:30 ngắn nhất | 6,9 | 30,1 | 17,7 | 2,7 | 13,5 |
  | 17:30 nhanh nhất | 7,5 | 25,8 | 25,6 | 3,6 | 23,1 |
  | 17:30 tối ưu | 7,9 | 26,5 | 22,5 | 3,0 | 18,3 |
  | 10:00 ngắn nhất | 6,9 | 24,0 | 17,7 | 2,7 | 13,5 |
  | 10:00 tối ưu | 7,6 | 21,5 | 19,7 | 2,8 | 15,2 |

  Giờ cao điểm tối ưu nhiều hơn ngắn nhất 27% chỉ dẫn và ít hơn nhanh nhất 12%, nên chưa cần thêm phạt mỗi lần rẽ. Bốn tuyến chọn tay trước đó cho thấy chênh tới 2–4 lần: không đại diện, đừng trích. Có tuyến riêng lẻ vẫn tới 51 chỉ dẫn; muốn biết người lái có theo nổi không thì phải chạy thử thật.
- **Chưa làm:** GPS thật, phát hiện lệch tuyến, giọng nói; bắt đầu từ bảng "tuyến khác"; API chưa có mật khẩu nên vẫn chỉ nghe 127.0.0.1.

## QĐ-026 — Kết quả lần train chính (12–13/11/2026): GBM + hồ sơ tốt nhất; học sâu + hồ sơ đạt tiêu chí, bắt kẹt 30–60 phút tốt hơn; kênh sự cố hỏng khi mất dữ liệu, che lúc học thì sửa được

Dữ liệu 29/10 18:45 → 12/11 22:30 (1.360 khung, 7.485 đoạn). Học tới 08/11 16:15 (học sâu: 855 mẫu học, 96 kiểm định, 405 kiểm tra). Kiểm tra 08/11 17:30 → 12/11 22:30, tức tối Chủ nhật 08/11 cộng thứ Hai tới thứ Năm. Lần đầu có đặc trưng "tuần trước"; mốc lịch sử tra đúng thứ ở 100% dòng (06/11 chỉ 45%). Log: `mo_hinh/ket_qua/chay_train_chinh_2026-11-12.log`.

| MAE (điểm %) | 15 phút | 30 phút | 60 phút | thấp hơn lịch sử |
|---|---|---|---|---|
| giữ nguyên | 6,28 | 8,11 | 9,65 | |
| TB 1 giờ | 7,11 | 8,20 | 9,75 | |
| lịch sử | 7,77 | 7,76 | 7,76 | |
| GRU | 6,01 | 7,28 | 8,38 | 22,7 / 6,2 / −8,0% |
| Graph WaveNet | 5,93 | 7,13 | 8,16 | 23,7 / 8,1 / −5,2% |
| GBM | 5,75 | 6,79 | 7,36 | 26,0 / 12,5 / 5,2% |
| Graph WaveNet + hồ sơ + thêm kênh | 6,17 | 6,72 | 6,80 | 20,6 / 13,4 / 12,4% |
| Graph WaveNet + hồ sơ + thêm kênh + che sự cố (chạy 13/11) | 5,79 | 6,25 | 6,30 | 25,4 / 19,5 / 18,7% |
| Graph WaveNet + hồ sơ | 5,83 | 6,31 | 6,39 | 25,0 / 18,7 / 17,7% |
| GRU + hồ sơ | 5,79 | 6,36 | 6,34 | 25,5 / 18,0 / 18,3% |
| **GBM + hồ sơ** | **5,48** | **6,16** | **6,29** | **29,5 / 20,6 / 18,8%** |

| F1 mức kẹt | 15 phút | 30 phút | 60 phút |
|---|---|---|---|
| giữ nguyên | 0,625 | 0,529 | 0,460 |
| GBM + hồ sơ | 0,641 | 0,591 | 0,573 |
| GRU + hồ sơ | **0,644** | **0,617** | 0,601 |
| Graph WaveNet + hồ sơ | 0,638 | 0,608 | **0,604** |
| Graph WaveNet + hồ sơ + thêm kênh + che sự cố | 0,637 | 0,605 | 0,601 |

- **Tiêu chí ≥ 10% đạt cả 3 mốc** với GBM + hồ sơ, GRU + hồ sơ và Graph WaveNet + hồ sơ (thấp nhất 17,7%). So với 06/11, MAE của GBM + hồ sơ giảm 4,2 / 4,8 / 5,3% và Graph WaveNet + hồ sơ giảm 6,6 / 5,8 / 5,1%. Tập kiểm tra đã khác nên chỉ so tương đối.
- **GBM + hồ sơ có MAE và RMSE thấp nhất** (RMSE 8,63 / 9,59 / 9,77; học sâu + hồ sơ 9,25–10,16). Học sâu + hồ sơ kém GBM 5,7–6,4% ở 15 phút, 0,8–3,2% ở 30 và 60 phút.
- **Nhưng học sâu + hồ sơ bắt mức kẹt 30–60 phút tốt hơn**: F1 kẹt 0,601–0,617 so với 0,573–0,591 của GBM. Chưa kiểm ý nghĩa thống kê (cần bootstrap theo ngày, giờ), nên chưa được báo là "hơn".
- **Thông tin không gian giúp rất ít.** Graph WaveNet so với GRU: không hồ sơ thấp hơn 1,3 / 2,1 / 2,6%; có hồ sơ −0,7 / +0,8 / −0,8%, coi như bằng nhau. Trên METR-LA là 10 / 15 / 22%. Cùng chiều với ablation GBM (lân cận ≈ 0) và M5 (tương quan giữa các đoạn xa chủ yếu là biến động chung). Giả thuyết chưa kiểm: khung 15 phút quá thô, ảnh hưởng của đường lân cận lan tới trong chưa tới 15 phút nên đã nằm sẵn trong r(t); thêm vào đó đồ thị thưa và đã bỏ ma trận tự học.
- **Học sâu đạt tốt nhất rất sớm**: vòng 7 (GRU + hồ sơ), 15 (Graph WaveNet + hồ sơ), 17 (thêm kênh); không hồ sơ thì vòng 31–54. Giả thuyết: 855 mẫu học là quá ít. Sẽ kiểm bằng đường cong học (học với 50 / 70 / 100% số ngày).
- **Thêm kênh làm Graph WaveNet kém đi 5,8 / 6,5 / 6,4%, và phần kém dồn hết vào ngày mất sự cố** (MAE 60 phút):

  | | 08/11 tối CN | 09/11 | 10/11 (mất cả ngày) | 11/11 (mất tới 16:45) | 12/11 |
  |---|---|---|---|---|---|
  | Graph WaveNet + hồ sơ | 8,73 | 6,26 | 6,17 | 6,14 | 6,36 |
  | + thêm kênh | 7,73 | 6,21 | **7,26** | **7,06** | 6,40 |
  | + thêm kênh + che sự cố | 7,70 | 6,20 | **6,14** | **6,14** | 6,36 |
  | (GBM + hồ sơ để so) | 7,29 | 6,21 | 6,15 | 6,15 | 6,41 |

  - Nguyên nhân: khoảng mất 09/11 23:30 → 11/11 16:45 nằm trọn trong phần kiểm tra. Lúc học, kênh "có dữ liệu sự cố" luôn bằng 1, nên mạng chưa từng gặp cảnh thiếu dữ liệu và đoán lệch khi gặp.
  - Ngày có dữ liệu thì hai bản ngang nhau; tối Chủ nhật bản thêm kênh còn tốt hơn 11%.
  - GBM không bị ảnh hưởng (ablation sự cố ≈ 0 cả trên ô có dữ liệu sự cố).
  - Sửa: cờ `--che-su-co` trong `hoc_sau_hcm.py` (khi học, che kênh sự cố ở 20% mẫu như lúc mất thật). **Hệ thống thật cũng cần cách này**, vì TomTom có thể lỗi lại.
  - **Kết quả che (13/11 03:56 → 05:17, 81 phút, tốt nhất ở vòng 30, dừng sớm vòng 50):** 5,79 / 6,25 / 6,30.
    - Hai ngày mất sự cố về 6,14 / 6,14 (60 phút), bằng bản không thêm kênh. Ngày có dữ liệu giữ nguyên. Tối Chủ nhật vẫn giữ lợi thế của thêm kênh (7,70 so với 8,73).
    - Là mô hình học sâu tốt nhất cả 3 mốc. So với GBM + hồ sơ: kém 5,7% ở 15 phút, 1,4% ở 30 phút, **0,1% ở 60 phút (coi như hòa)**. Ở 60 phút thắng GBM 4 ngày thường, thua tối Chủ nhật (7,70 so với 7,29).
    - F1 kẹt 0,637 / 0,605 / 0,601, vẫn trên GBM ở 30–60 phút.
    - **Giới hạn phải ghi trong báo cáo:** cách sửa này nghĩ ra SAU khi nhìn MAE theo ngày của tập kiểm tra, nên số trên tập kiểm tra hơi lạc quan. Bù lại, tỷ lệ 20% chọn trước, không dò; cơ chế giải thích được và phần cải thiện nằm đúng chỗ dự đoán (ngày mất). Mới chạy 1 hạt giống ngẫu nhiên; chênh 0,1% với GBM nằm trong nhiễu. Lần train cuối (2–3 tháng) phải bật `--che-su-co` ngay từ đầu, khi đó mới là kiểm tra sạch.
- **Phép thử đoán mò: đạt.**
  - Mô hình 5,47 / 6,16 / 6,30.
  - Nhãn xáo trộn tụt về đúng mức giữ nguyên (6,29 / 8,11 / 9,64).
  - Đúng hướng khi đường đổi mạnh 87,9 / 91,5 / 93,7%, so với đoán theo trung bình 72,6–76,0%.
- **Ablation GBM + hồ sơ** (bỏ nhóm thì MAE đổi bao nhiêu, 15 / 30 / 60 phút):

  | bỏ nhóm | 15 phút | 30 phút | 60 phút | ghi chú |
  |---|---|---|---|---|
  | hồ sơ | +0,274 | +0,645 | +1,091 | lớn hơn 11/11 (+0,25 / +0,55 / +0,885) |
  | trạng thái chung | +0,012 | +0,019 | +0,015 | nhỏ hơn 11/11 (+0,05 / +0,07 / +0,115); trên ô đổi mạnh bỏ đi lại tốt hơn 0,17–0,21 |
  | sự cố | −0,002 | +0,002 | 0,000 | trên ô có sự cố +0,029 ở 15 phút |
  | thời tiết | +0,003 | +0,003 | 0,000 | trên ô có mưa bỏ đi lại tốt hơn 0,007–0,021 |
  | lân cận | +0,001 | −0,002 | +0,001 | |

  - Ngoài hồ sơ, các nhóm còn lại gần như không giúp với dữ liệu hiện có.
  - Trạng thái chung từng có ích ở lần chạy kiểm 11/11 nay nhỏ lại. Một lần chia dữ liệu chưa đủ để kết luận nó có ích.
- **Điểm yếu là tối Chủ nhật 08/11.**
  - GBM + hồ sơ 6,55 / 7,34 / 7,29, so với ngày thường 5,33–5,53 / 6,01–6,23 / 6,15–6,41.
  - Học sâu + hồ sơ còn kém bản không hồ sơ (Graph WaveNet 60 phút: 8,73 so với 7,73). Hồ sơ cuối tuần buổi tối mới có 3 tối (31/10, 01/11, 07/11).
  - Tập kiểm tra chỉ có một tối cuối tuần, nên chưa đo được cuối tuần cho ra hồn.
- **Đề xuất:** nối GBM + hồ sơ vào định tuyến trước, vì MAE thấp nhất ở 15–30 phút, chạy CPU và không hỏng khi mất sự cố. Mô hình học sâu đem so khi chấm tuyến là Graph WaveNet + hồ sơ + thêm kênh + che sự cố (thay cho bản không che). **Người dùng duyệt 13/11 ("ok làm đi") → QĐ-027.**
- **Việc tiếp:** chuyển sang QĐ-027.

## QĐ-027 — Gộp hai mô hình, kiểm ý nghĩa thống kê, nối dự báo vào định tuyến, đường cong học (13/11/2026, người dùng: "ok làm đi")

Người dùng duyệt đề xuất cuối QĐ-026 và việc tiếp. Cùng tập kiểm tra như QĐ-026 (08/11 17:30 → 12/11 22:30).

### 1. So GBM + hồ sơ với Graph WaveNet che sự cố trên cùng ô; trung bình hai mô hình; bootstrap

- Mã: `hoc_sau_hcm.py --chi-du-bao` (nạp `.pt` đã train, chấm lại, ghi `_du_bao.parquet`); `mo_hinh/so_sanh_du_bao.py` (train lại GBM + hồ sơ, ghi `ket_qua/du_bao_gbm_ls_2026-11-12.parquet`, so, bootstrap). Log `mo_hinh/ket_qua/so_sanh_du_bao_2026-11-13.log`.
- Tái lập: GBM + hồ sơ 5,477 / 6,162 / 6,295 và Graph WaveNet 5,791 / 6,251 / 6,303, **trùng từng số** với lần train (cả MAE theo ngày). 2.907.799 ô có r(t), hai bên khớp 100%.
- **Trung bình 0,5 / 0,5** (trọng số chọn trước, không dò trên tập kiểm tra):

  | MAE (điểm %) | 15 phút | 30 phút | 60 phút |
  |---|---|---|---|
  | GBM + hồ sơ | **5,477** | 6,162 | 6,295 |
  | Graph WaveNet che sự cố | 5,791 | 6,251 | 6,303 |
  | trung bình | 5,556 | **6,141** | **6,243** |
  | F1 kẹt: GBM / Graph WaveNet / trung bình | 0,641 / 0,637 / 0,643 | 0,591 / 0,605 / 0,602 | 0,573 / 0,601 / 0,591 |

  Trung bình tốt hơn GBM 0,3% ở 30 phút, 0,8% ở 60 phút, nhưng kém 1,4% ở 15 phút. Lợi quá nhỏ so với việc phải chạy thêm GPU khi phục vụ, nên **chưa dùng**. Lần train cuối sẽ chọn trọng số trên tập kiểm định, không chọn trên tập kiểm tra.
- **Bootstrap theo khối (ngày, giờ)**, 2.000 lần, 101–102 khối; chênh = Graph WaveNet − GBM:

  | | 15 phút | 30 phút | 60 phút |
  |---|---|---|---|
  | chênh MAE | +0,31 [+0,27; +0,35] | +0,09 [+0,04; +0,13] | +0,01 [−0,05; +0,07] |
  | chênh F1 kẹt | −0,004 [−0,007; −0,000] | **+0,015 [+0,011; +0,019]** | **+0,027 [+0,022; +0,035]** |

  - **Học sâu bắt kẹt 30–60 phút tốt hơn GBM, vượt nhiễu** theo phép thử này (QĐ-026 mới ghi "chưa kiểm"). MAE: GBM tốt hơn ở 15–30 phút, 60 phút hòa.
  - Giới hạn: khối (ngày, giờ) chưa tính phụ thuộc giữa các giờ trong cùng một ngày, nên khoảng thật có thể rộng hơn. Tập kiểm tra chỉ có 4 ngày thường và một tối Chủ nhật. Cách che sự cố nghĩ ra sau khi nhìn tập kiểm tra (QĐ-026).

### 2. Nối dự báo vào định tuyến

- Mã:
  - `ba_phuong_an.DinhTuyen.dat_du_bao(r_khe, moc_s)`: r mỗi cạnh theo khe thời gian KỂ TỪ LÚC XUẤT PHÁT; thời gian và phạt kẹt theo r của khe xe tới cạnh.
  - Cận ALT và v_max lấy r lớn nhất qua các khe, nên vẫn là cận dưới.
  - `dinh_tuyen/kiem_tra_du_bao.py` ĐẠT:
    - không bật dự báo thì trùng bản cũ 18/18;
    - mọi khe bằng tình trạng lúc đi thì trùng chế độ giữ nguyên 18/18;
    - có / không ALT cùng chi phí 18/18 (2 cặp tới Lăng Cha Cả không có đường ở cả hai vì đường đóng 10/11);
    - mốc khe đúng.
- `cham_tuyen_that.py --du-bao=gbm_ls` thêm 3 phương án:
  - F: nhanh nhất theo dự báo;
  - G: tối ưu theo dự báo;
  - H: tối ưu khi BIẾT TRƯỚC r thật từng khe (trần của mọi bộ dự báo, không làm được ngoài đời).
  - Chỉ chấm 4 ngày thường 09–12/11, vì chúng nằm trọn trong phần kiểm tra của GBM. Dự báo lấy ở khung 15 phút vừa xong (lúc đi − 15 phút).
- **Bản đầu sai cách đem dự báo xuống cạnh** ("cong": r lần chụp lúc đi + (dự báo − r của đoạn ở khung vừa xong)). Chấm 09/11:
  - F CHẬM hơn C 0,47%; G ≈ D (+0,03%); H nhanh hơn D 2,34%.
  - Đoán giờ đến: F sai 0,87 phút, C sai 0,79 phút.
  - F đổi tuyến so với C ở 64% chuyến: nhanh hơn 19%, chậm hơn 33%.
  - Tệp `cham_tuyen_2026-11-09_zenodo_dubao-gbm_ls-cong.csv`, log `chay_du_bao_gbm_ls-cong.log`.
- **Tìm nguyên nhân bằng `danh_gia/kiem_du_bao_canh.py` trên tối 08/11.** Ngày này thuộc phần kiểm tra nhưng KHÔNG nằm trong 4 ngày chấm, nên chọn cách mà không nhìn ngày đem chấm. Sai thời gian qua cạnh tương đối, trọng số chiều dài:

  | khe sau lúc đi | giữ nguyên lần chụp | cong | mức dự báo của đoạn | nửa |
  |---|---|---|---|---|
  | 0–15 phút | **10,1%** | 11,8% | 14,8% | 10,4% |
  | 15–30 | 19,9% | 19,8% | **15,7%** | 19,1% |
  | 30–45 | 22,0% | 20,7% | **15,7%** | 20,4% |
  | 45–60 | 23,0% | 20,9% | **15,7%** | 20,7% |

  - Lần chụp lúc đi (vd 06:30) đã nằm TRONG khe 0, còn GBM chỉ thấy khung 06:15–06:25. Vì vậy 15 phút đầu giữ nguyên thắng.
  - Từ phút 15 trở đi, lần chụp 5 phút của một cạnh rất nhiễu. Cộng phần thay đổi vào đó gần như không giúp; mức dự báo của đoạn (trung bình nhiều cạnh, kéo về hồ sơ) đúng hơn 21–32%.
  - Nếu canh lúc đi = lần chụp cuối của khung (τ = f + 10 phút), thì mức dự báo thắng cả khe đầu (14,7% so với 16,0%).
- **Cách dùng ("muc", mặc định):** khe 0–15 phút giữ lần chụp lúc đi; từ phút 15 dùng dự báo 30 / 45 / 60 phút của đoạn chứa cạnh; cạnh không thuộc đoạn có dự báo giữ như C/D. Bản đầu vẫn chạy lại được bằng `--cach-du-bao=cong`.
- **Kết quả 4 ngày** (09–12/11, 90 cặp điểm giao hàng thật × 10 giờ = 3.600 chuyến). Log `danh_gia/ket_qua/chay_du_bao_gbm_ls.log`, tổng hợp `tong_hop_du_bao_gbm_ls.json`. CI 95% bootstrap theo cặp điểm:

  | so sánh (tổng thời gian thật) | nhanh hơn | CI 95% | chuyến nhanh hơn / chậm hơn |
  |---|---|---|---|
  | F nhanh nhất theo dự báo so với C (giữ nguyên) | 0,13% | −0,03 .. 0,28 | 18% / 13% |
  | **G tối ưu theo dự báo so với D** | **0,15%** | **−0,06 .. 0,36** | 18% / 16% |
  | H biết trước r thật so với D (trần) | 2,28% | 1,96 .. 2,58 | 48% / 15% |
  | E tính lại giữa đường mỗi lần chụp mới so với D | 1,48% | 1,23 .. 1,73 | 21% / 3% |
  | G so với A ngắn nhất | 11,87% | 9,40 .. 14,88 | G không chậm hơn A ở 85,1% chuyến (D 84,8%) |

  - Theo ngày, G so với D: +0,49 / −0,38 / +0,13 / +0,36%; H: 2,34 / 2,19 / 2,17 / 2,42%. Theo giờ, G so với D từ −0,55% (18:00) tới +0,68% (06:30).
  - Phần trần dự báo lấy được: 6,5% (CI −3 .. 15%).
  - Giờ đến đoán: C sai TB 0,77 phút (3,2%), F 0,78 phút (3,2%), không hơn.
- **Kết luận: với chuyến xuất phát NGAY (TB 21 phút), dự báo 15–60 phút KHÔNG làm tuyến nhanh hơn một cách đo được.** CI chứa 0, nên không được báo là "dự báo giúp định tuyến".
  - Trần chỉ 2,3%: ngay cả biết trước hoàn toàn tương lai, tuyến cũng chỉ nhanh hơn chừng đó.
  - E (tính lại giữa đường bằng lần chụp mới) đã lấy được 1,48%, tức 65% trần, mà không cần dự báo.
- **Không phải vì dự báo sai ở mức cạnh** (kiểm thêm để GIẢI THÍCH, không dùng để chỉnh lại; `kiem_du_bao_canh.py` 06:30–19:30 trên 09/11 và 11/11):
  - Sai thời gian qua cạnh, mức dự báo so với giữ nguyên: 18,1–18,3% so với 22,4–22,6% ở khe 15–30 phút; 18,3–18,5% so với 25,4–25,7% ở khe 30–45 phút.
  - 15 phút đầu giữ nguyên vẫn thắng (10,7–10,9% so với 16,9%).
  - Lý do còn lại: chuyến TB 21 phút nên phần lớn thời gian nằm ở 15 phút đầu, nơi dự báo không giúp. Thêm nữa, sai số chung cho mọi tuyến không làm đổi lựa chọn tuyến.
- Bản đầu ("cong", chỉ 09/11): G so với D +0,03%, F so với C −0,47%. Ghi lại để thấy cách đem dự báo xuống cạnh quan trọng thế nào.
- **Ý nghĩa cho đề tài** (chưa chốt, chờ người dùng):
  - Dự báo có ích ở chỗ "giữ nguyên" yếu, tức tầm 30–60 phút (MAE 6,2–6,3 so với 8,1–9,6): chuyến hẹn đi sau 30–60 phút, ước giờ giao cho đơn đặt trước, cảnh báo kẹt sắp tới.
  - Đề xuất phép chấm tiếp: lập tuyến lúc p cho chuyến đi lúc p + 30. So 3 cách: giữ nguyên lần chụp lúc p, hồ sơ giờ, dự báo. Đo cả thời gian thật lẫn sai giờ đến.
  - Với chuyến đi ngay: cách có lợi đo được là tính lại giữa đường (E).

### 3. Đường cong học (bỏ ngày cũ nhất, giữ ngày gần tập kiểm tra; hồ sơ cũng chỉ từ phần còn lại)

- Mã: `ho_so(..., dau)`, `BangHoc.dat_bo_dau()`, `mo_hinh/duong_cong_hoc.py` (GBM), `hoc_sau_hcm.py --bo-dau=X`. Có test mới `test_ho_so_bo_ngay_dau`; tổng 67/67 test qua.
- **GRU + hồ sơ** (log `mo_hinh/ket_qua/duong_cong_hoc_gru_2026-11-13.log`):

  | phần học | từ | mẫu học | MAE 15 / 30 / 60 | 60 phút ngày thường 09–12/11 | F1 kẹt 30 / 60 |
  |---|---|---|---|---|---|
  | 50% (4,9 ngày) | 03/11 17:30 | 380 | 6,28 / 6,80 / 6,84 | 6,53–6,74 | 0,601 / 0,597 |
  | 75% (7,4 ngày) | 01/11 06:00 | 618 | 5,92 / 6,36 / 6,38 | 6,23–6,47 | 0,604 / 0,599 |
  | 100% (9,9 ngày) | 29/10 18:45 | 855 | 5,79 / 6,36 / 6,34 | 6,12–6,38 | 0,617 / 0,601 |

  - Từ 50% lên 75%: MAE giảm 6–7%. Từ 75% lên 100%: giảm 2,2 / 0 / 0,6% (ngày thường 1–1,7%). **Thêm ngày vẫn giúp nhưng chậm dần.**
  - Phần lớn lợi ích nhiều khả năng đến từ hồ sơ có thêm ngày cùng loại. Giả thuyết "855 mẫu quá ít cho học sâu" (QĐ-026) chỉ đúng một phần.
  - Tối Chủ nhật 08/11 (60 phút): 9,97 → 7,58 → 8,29, không đều. Phần học 50% chỉ có một cuối tuần, nên bớt ngày và bớt cuối tuần lẫn vào nhau.
  - Mới một hạt giống ngẫu nhiên; vòng tốt nhất 19 / 36 / 7 rất khác nhau, nên số lẻ dưới 1% là nhiễu.
- **GBM + hồ sơ** (`duong_cong_hoc.py`, log `mo_hinh/ket_qua/duong_cong_hoc_gbm_ls_2026-11-13.log`; lượt 100% trùng đúng 5,477 / 6,162 / 6,295):

  | phần học | dòng học | MAE 15 / 30 / 60 | thấp hơn lịch sử (cùng phần học) | 60 phút ngày thường | F1 kẹt 30 / 60 |
  |---|---|---|---|---|---|
  | 50% (4,9 ngày) | 3,44 tr | 5,572 / 6,356 / 6,650 | 24,8 / 14,2 / 10,1% | 6,40–6,72 | 0,571 / 0,539 |
  | 75% (7,4 ngày) | 5,16 tr | 5,495 / 6,180 / 6,331 | 29,6 / 20,8 / 18,8% | 6,21–6,43 | 0,592 / 0,576 |
  | 100% (9,9 ngày) | 6,87 tr | 5,477 / 6,162 / 6,295 | 29,5 / 20,6 / 18,8% | 6,15–6,41 | 0,591 / 0,573 |

  - Từ 50% lên 75%: MAE giảm 1,4 / 2,8 / 4,8%. Từ 75% lên 100%: chỉ giảm 0,3 / 0,3 / 0,6%. **GBM gần bão hòa theo số ngày** với bộ đặc trưng hiện tại. GRU chậm lại tương tự (0–2%).
- **Ý nghĩa cho lần train cuối (2–3 tháng):**
  - Đừng chờ MAE giảm nhiều nhờ thêm ngày thường.
  - Lợi ích chờ được: đủ cuối tuần (hiện chỉ 2 trong phần học); có hồ sơ theo TỪNG thứ thay vì chỉ ngày thường / cuối tuần; có thể gặp mưa to; có tập kiểm tra sạch (bật `--che-su-co` từ đầu, chọn trọng số gộp trên kiểm định).
  - Muốn MAE giảm thêm thì phải có thông tin mới (đặc trưng, nguồn), không phải thêm ngày.
- Giới hạn: bỏ ngày cũ cũng bỏ bớt cuối tuần; mới một lần chia; GBM có `random_state` cố định, nên khác nhau dưới 0,5% có thể là nhiễu do chọn phần học.

### 4. Tóm tắt và việc tiếp

- Đạt / có số:
  - học sâu bắt kẹt 30–60 phút tốt hơn GBM, vượt nhiễu;
  - gộp hai mô hình lợi rất ít;
  - dự báo KHÔNG làm tuyến đi ngay nhanh hơn đo được (trần 2,3%, tính lại giữa đường lấy 1,5%);
  - thêm ngày giúp chậm dần.
- Việc tiếp, chờ người dùng chọn:
  1. chấm "lập tuyến trước 30 phút" (chỗ dự báo có lợi thế lớn nhất so với giữ nguyên);
  2. E + dự báo (tính lại giữa đường có dùng dự báo);
  3. đưa dự báo vào API / web (giờ đến dự kiến theo dự báo, cảnh báo kẹt 30–60 phút tới);
  4. phạt đường đóng theo lần gặp (việc cũ từ QĐ-023).
- **Người dùng (13/11): "làm hết đi"** → QĐ-028.

## QĐ-028 — Chấm tuyến lập trước 30 phút; lớp dự báo trên API / web (13/11/2026, người dùng: "làm hết đi")

### 1. Chấm tuyến lập trước 30 phút

- Vì sao: QĐ-027 cho thấy với chuyến đi ngay, dự báo không giúp. Chỗ "giữ nguyên" yếu nhất là 30–60 phút tới (MAE 8,1–9,6 so với GBM 6,2–6,3), tức chuyến lên tuyến trước lúc đi: đơn hẹn giao, điều phối xếp chuyến.
- Mã `danh_gia/cham_tuyen_dat_truoc.py`:
  - Lập lúc p cho chuyến xuất phát lúc τ = p + 30 phút; chỉ biết dữ liệu tới p.
  - So 5 cách biết r theo khe kể từ τ:
    - `giu`: lần chụp lúc p;
    - `ls`: hồ sơ của đoạn theo (ngày thường / cuối tuần, ô 15 phút), CHỈ từ phần học;
    - `gbm_ls`, `gwn_ho_so_them_che`: dự báo tầm 45 và 60 phút cho 2 khe đầu, quá tầm thì như `ls`;
    - `that`: biết trước, làm trần.
  - Mỗi cách tính tuyến nhanh nhất (n_) và tối ưu (t_). Mốc: A (ngắn nhất), N (tối ưu lập ngay lúc đi).
  - Ghi cả giờ đến DỰ KIẾN lúc lập.
  - Tổng hợp `tong_hop_dat_truoc.py`, có CI theo cặp điểm.
- Tự kiểm: N trùng phut_D của lần chấm đi ngay 90/90, chạy thử 09/11 17:00.
- Chạy 4 ngày 09–12/11 (13:13 →), 2 ngày song song. Log `danh_gia/ket_qua/chay_dat_truoc30_{a,b}.log`.
- **Kết quả 4 ngày** (13:13 → 14:13, 3.600 chuyến; tự kiểm N = D 900/900 cả 4 ngày). Tổng hợp `danh_gia/ket_qua/tong_hop_dat_truoc30.json`, CI 95% theo cặp điểm.
  - Thời gian thật của tuyến tối ưu, nhanh hơn `giu`:

    | cách biết | nhanh hơn | CI 95% |
    |---|---|---|
    | ls (hồ sơ) | 1,79% | 1,22 .. 2,33 |
    | gbm_ls | 1,60% | 1,05 .. 2,10 |
    | gwn_ho_so_them_che | 1,75% | 1,21 .. 2,27 |
    | that (trần) | 5,64% | 5,15 .. 6,13 |
    | N (lập ngay lúc đi) | 3,53% | 3,17 .. 3,88 |

    So với `ls`: gbm −0,20% (CI −0,38 .. −0,02, tức hơi KÉM), gwn −0,04% (CI −0,13 .. +0,07, ngang).
  - Sai giờ đến dự kiến lúc lập, tuyến nhanh nhất:

    | cách biết | sai TB | lệch TB (âm = hứa sớm) | p90 |
    |---|---|---|---|
    | giu | 1,93 phút (8,3%) | −1,49 | 4,58 |
    | ls | 1,38 phút (5,9%) | −1,19 | 3,34 |
    | gbm_ls | 1,45 (6,2%) | −1,28 | 3,52 |
    | gwn | 1,43 (6,1%) | −1,28 | 3,34 |
    | that | 0,46 (2,1%) | −0,09 | 0,98 |

    gbm − ls: +0,07 phút (CI +0,03 .. +0,11); gwn − ls: +0,05 (CI +0,04 .. +0,06). Cả hai hơi kém hồ sơ.
- **Kết luận:**
  - Lập trước 30 phút thì dự báo (cả GBM lẫn học sâu) thắng "giữ nguyên" rõ ràng: thời gian 1,6–1,8%, giờ đến sai ít hơn 25% (0,48–0,50 phút).
  - Nhưng **không hơn hồ sơ lịch sử ngày thường / cuối tuần**. Hồ sơ đã lấy gần hết phần lợi; trần còn 3,9% chưa ai lấy được.
- **Vì sao dự báo chỉ ngang hồ sơ** (kiểm để GIẢI THÍCH, `kiem_du_bao_canh_ls.py` và tính lại trên ô):
  - Ở mức ô, mốc "lịch sử" của tiêu chí (theo TỪNG THỨ, `LichSu` của `moc_so_sanh`) yếu, vì mỗi thứ trong phần học mới có 1–2 ngày. Hồ sơ ngày thường / cuối tuần (H, chỉ phần học) mạnh hơn nhiều:

    | MAE ô (điểm %) | 15 phút | 30 phút | 60 phút |
    |---|---|---|---|
    | lịch sử theo thứ (mốc tiêu chí) | 7,77 | 7,76 | 7,76 |
    | hồ sơ ngày thường / cuối tuần | 6,57 | 6,56 | 6,52 |
    | GBM + hồ sơ | 5,48 | 6,16 | 6,29 |
    | Graph WaveNet che sự cố | 5,78 | 6,24 | 6,30 |
    | giữ nguyên | 6,28 | 8,11 | 9,64 |

    GBM thấp hơn hồ sơ ngày thường / cuối tuần chỉ **16,7 / 6,0 / 3,5%**, so với 29,5 / 20,6 / 18,8% khi so với mốc tiêu chí.
    - Đã đưa mốc này vào `moc_so_sanh.py` (`ho_so`). Chạy lại 14:21 → 14:46 (`moc_2026-11-13_1446.json`), khớp đúng các số trên.
    - **Theo ngày:** ngày thường 09–12/11 ở 60 phút GBM 6,15–6,41 so với hồ sơ 6,16–6,37, tức NGANG. Ở 30 phút hơn 1–2,5%; ở 15 phút hơn ~13%. Lợi thế chung ở 60 phút gần như chỉ đến từ tối Chủ nhật 08/11, lúc hồ sơ cuối tuần còn quá ít mẫu (MAE 10,3–11,6).
    - F1 kẹt của hồ sơ: 0,591 / 0,591 / 0,594. GBM 0,641 / 0,591 / 0,573 (60 phút KÉM hồ sơ); Graph WaveNet 0,637 / 0,605 / 0,601 (chỉ hơn hồ sơ 0,007–0,014).
    - Nghĩa là: giá trị của dự báo nằm chủ yếu ở 15–30 phút tới. Ở 60 phút, mô hình hội tụ về hồ sơ lịch sử, đúng như thường gặp ở dự báo giao thông tầm xa.
  - Ở mức cạnh (ban ngày 09/11, 11/11, khe 45–60 phút), ls, GBM và Graph WaveNet gần như bằng nhau: MAE r 8,2–8,3; sai thời gian 18,2–18,7%. Sai trong nội bộ đoạn (cạnh khác đoạn) lớn hơn hẳn phần dự báo cải thiện.
  - Mọi cách (trừ biết trước) đều đoán lạc quan: ở mức cạnh nghĩ nhanh hơn thật 7–10% (GBM −9,1 .. −9,8%, ls −6,8 .. −7,6%); giờ đến hứa sớm 1,2–1,5 phút.
    - Nguyên nhân có thể: lấy TB r của đoạn thay cho TB thời gian (TB điều hòa); bộ định tuyến chọn đúng những cạnh bị đoán nhanh hơn thật.
    - Chưa sửa, vì sửa (hiệu chỉnh lệch) phải chọn hệ số trên dữ liệu ngoài 4 ngày chấm.
- **Rủi ro cho tiêu chí ≥ 10% ở lần train cuối (mức nghiêm trọng: trung bình – cao):**
  - Khi có nhiều tuần, mốc lịch sử theo thứ sẽ mạnh lên, có thể gần bằng hoặc hơn hồ sơ ngày thường / cuối tuần. Khi đó GBM ở 60 phút có thể chỉ còn hơn khoảng 3–6%, tức KHÔNG đạt 10%.
  - Hiện vẫn đạt đúng như tiêu chí đã đặt từ trước, nhưng báo cáo PHẢI ghi thêm mốc hồ sơ ngày thường / cuối tuần cho trung thực.
  - Việc tiếp: mỗi lần train lại thì tính cả hai mốc; thêm hồ sơ theo từng thứ làm đặc trưng khi đủ ≥ 3 tuần mỗi thứ; thử hiệu chỉnh lệch lạc quan.

### 2. Lớp dự báo trên API / web

- `GET /api/du-bao?luc=&tam=15|30|45|60` (`dich_vu.du_bao`): r dự báo GBM + hồ sơ từng đoạn chính cho khung f + tam.
  - f = khung 15 phút vừa ĐỦ lúc lần chụp gần luc (f + 10 phút ≤ lần chụp), nên chỉ dùng dữ liệu có tới lúc đó.
  - Chỉ có ở khoảng ngoài mẫu (phần kiểm tra của mô hình); ngoài khoảng đó báo lỗi rõ ràng.
  - `/api/thong-tin` trả thêm `khoang_du_bao`.
- Web: ô "Kẹt xe theo: bây giờ / dự báo 15 / 30 / 60 phút tới" thay ô "gắn sau lần train chính".
- Giới hạn:
  - Dự báo đọc từ tệp đã tính sẵn (`mo_hinh/ket_qua/du_bao_gbm_ls_*.parquet`, không lên git). Chưa có dự báo "bây giờ" cho dữ liệu mới.
  - Muốn có thì phải lưu mô hình rồi chạy trên khung vàng mới nhất sau mỗi lần dựng lại; chưa làm.
  - Máy không có tệp này (vd khi đưa API lên VPS): lớp dự báo báo "chưa có" và mọi phần khác vẫn chạy; kiểm ở mục web bên dưới.
- Kiểm trên trình duyệt (13/11, `preview thuc-tap-web`):
  - 10/11 08:00, tầm 30: dùng khung 07:45, dự báo cho 08:15–08:30, 5.731 đoạn.
  - 01/11 (ngoài khoảng): báo "Chua co du bao…".
  - Tầm sai (20): lỗi 400.
  - Quay về "bây giờ" vẫn vẽ đúng.
  - Không có lỗi phía máy chủ.

### 3. Đề tài trả lời được gì (sau QĐ-026 → QĐ-028) và việc còn lại

- Các tiêu chí đặt từ 29/10 đều ĐẠT:
  - dự báo thấp hơn mốc lịch sử theo thứ 29,5 / 20,6 / 18,8%;
  - tuyến tối ưu nhanh hơn ngắn nhất 11,9% và không chậm hơn ở 85% chuyến;
  - trả tuyến dưới 2 giây.
- Câu trả lời trung thực về "dự báo giúp định tuyến thế nào":
  1. Chuyến đi ngay: không giúp đo được. Trần 2,3%; tính lại giữa đường lấy 1,5%.
  2. Chuyến lập trước 30 phút: thắng giữ nguyên (1,6–1,8% thời gian, giờ đến sai ít hơn 25%), nhưng ngang hồ sơ lịch sử.
  3. Học sâu bắt kẹt 30–60 phút tốt hơn GBM, vượt nhiễu (QĐ-027).
  4. Ở 45–60 phút, phần dự báo được gần như đã nằm trong hồ sơ. Đây là giới hạn của dữ liệu đo ở khung 15 phút, chứ không phải do thiếu ngày (đường cong học phẳng).
- Bỏ qua "E + dự báo" (tính lại giữa đường có dùng dự báo): đi ngay thì dự báo ≈ 0, còn tầm xa thì dự báo ≈ hồ sơ, nên khó hơn E được. Ghi lại để không làm lại.
- Việc còn lại:
  - mốc hồ sơ ngày thường / cuối tuần vào `moc_so_sanh.py` (báo cả hai mốc);
  - hiệu chỉnh lệch lạc quan (chọn hệ số ngoài ngày chấm);
  - hồ sơ theo từng thứ khi đủ tuần;
  - thử D11 Kaggle 2020–21 cho hồ sơ dài hạn;
  - phạt đường đóng theo lần gặp (QĐ-023);
  - dự báo "bây giờ" cho dữ liệu mới (lưu mô hình).
