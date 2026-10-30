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
