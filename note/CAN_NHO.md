# Điều cần nhớ

## Ranh giới

- Giờ ghi trong `NHAT_KY.md` phải lấy từ `date` hoặc giờ tệp/AWS — KHÔNG ước chừng (30/10/2026 từng ghi "14:30" khi đồng hồ mới 11:53).

- Đồ án chuyên ngành ở `../doanchuyennganh`, đang tạm gác. Làm thực tập thì không sửa bên đó.
- Bí mật (khóa AWS, mật khẩu, token, IP) không ghi vào tệp nào, kể cả sổ ghi chú này.

## AWS

- **Đang chạy (từ 30/10/2026), vùng ap-southeast-1:**
  - S3 `<S3_BUCKET>` (tên thật nằm trong `.env`, dòng `S3_BUCKET=`; repo GitHub công khai nên không ghi tên ở đây);
  - Lambda `thu-du-lieu-giao-thong`;
  - Scheduler `thu-du-lieu-5-phut` (5 phút);
  - Budgets `thuctap-ngan-sach-thang` (2 USD, email email của người dùng — đã Verified 30/10/2026, 3 cảnh báo).
  - Chi tiết + chi phí: `he_thong/aws/thu_lambda/README.md`.
- Muốn tạm dừng thu trên AWS: EventBridge Scheduler → `thu-du-lieu-5-phut` → Disable. Sửa code: tạo lại `dist/thu_lambda.zip` và Update from .zip.
  - Sửa Lambda thì chạy `thu_o_may.py` cho ĐẠT trước, sau đó xem log lượt kế tiếp. 30/10 04:11 đã làm vậy khi thêm ô absolute.
  - Trong log tìm `o_them_duoc`: chỉ bản mới in ra trường này.
- Kéo dữ liệu S3 về máy: `thu_thap/KEO_S3.bat` (aws s3 sync, profile `thuctap-doc`, chỉ tải tệp mới).
  - **Có tính tiền nhưng gần 0** (bảng giá AWS Price List ap-southeast-1, công bố 15/10/2026, tra 30/10):
    - truyền ra Internet: 100 GB đầu mỗi tháng MIỄN PHÍ (gộp mọi dịch vụ, mọi vùng), sau đó 0,12 USD/GB;
    - GET 0,004 USD / 10.000 lần; LIST/PUT 0,005 USD / 1.000 lần.
  - Bộ thu sinh ~65 MB / ~600 tệp mỗi ngày → kéo về ~2 GB, ~18 nghìn GET/tháng → dưới 0,03 USD/tháng. Phía Lambda ghi lên (~18 nghìn PUT/tháng ≈ 0,09 USD) mới là khoản chính.
  - Nếu sau này đọc S3 nhiều (vd web công khai tải thẳng từ S3) thì tính lại — 100 GB miễn phí dùng chung toàn tài khoản.
  - Cần user IAM CHỈ ĐỌC, do người dùng tự tạo khóa, Claude không cầm khóa.
  - Policy inline cho user đó:
    - `s3:ListBucket` trên `arn:aws:s3:::<S3_BUCKET>`, điều kiện `s3:prefix` like `dong/*`;
    - `s3:GetObject` trên `arn:aws:s3:::<S3_BUCKET>/dong/*`.
  - Rồi chạy `aws configure --profile thuctap-doc` (vùng ap-southeast-1).
  - 30/10/2026 10:34: đã tạo user `thuctap-doc-s3` (không có quyền đăng nhập web, không thuộc nhóm nào) + policy inline `chi-doc-s3-thu-du-lieu` đúng như trên. IAM báo 0 lỗi, mức truy cập "Limited: List, Read".
  - Khóa truy cập do người dùng tự tạo và tự `aws configure`.
  - 30/10/2026: thêm policy inline `chi-doc-log-bo-thu` cho user này: `logs:FilterLogEvents`, `GetLogEvents`, `DescribeLogStreams` trên `arn:aws:logs:ap-southeast-1:*:log-group:/aws/lambda/thu-du-lieu-giao-thong` (+ `:*`). IAM báo 0 lỗi.
    - Dùng cho bảng theo dõi `he_thong/bang_theo_doi/`.
    - Bước bấm "Create policy" bị trình phân quyền của Claude CHẶN ("Permission Grant"). Người dùng tự bấm 30/10 ~12:10, đã chạy.
    - Thao tác CẤP QUYỀN trên AWS (tạo/sửa policy) để người dùng bấm, Claude chỉ điền sẵn.
- 30/10/2026 ~11:00: người dùng đã tự xóa user cũ `user_thanhvu` (Admin, khóa chưa từng dùng). IAM giờ chỉ còn `thuctap-doc-s3`. Nhóm `admin_thanhvu` còn lại nhưng rỗng. Root ĐÃ có MFA (IAM Dashboard: "Root user has MFA").
- TOMTOM_KEY nằm trong biến môi trường Lambda — người dùng tự dán. Claude không nhập khóa vào web.
- Giao diện Lambda (10/2026) là "Create Event Function". Menu Runtime dễ chọn nhầm (đã từng ra Python 3.15 Preview) → gõ tìm "Python 3.13" rồi chọn, chụp lại kiểm.
- Tín dụng AWS trong tài khoản (158 USD còn lại) đã **HẾT HẠN 20/10/2026** (ảnh chụp trang Credits ngày 29/10: cả 4 khoản ghi Expired). Mọi tài nguyên bật lên đều tính tiền thật. Phải có AWS Budgets trước khi tạo bất cứ thứ gì.
- 30/10/2026: đã xóa bản sao lưu RDS cũ `testdtb-snapshot` (us-east-1). Đây là nguồn duy nhất của phí 0,05 USD/tháng; sau khi xóa, tài khoản không còn bản sao lưu RDS nào. Thấy phí lạ thì xem Bills → theo dịch vụ + vùng trước, đừng đoán.
- Xóa dữ liệu vĩnh viễn trên AWS (snapshot, bucket, object…) do người dùng tự bấm; Claude chỉ tìm, giải thích và kiểm lại sau khi xóa.
- Thư xác minh email của AWS Budgets hay rơi vào Spam Gmail (link bị khóa) → bấm "Not spam" trước rồi mới Verify.
- Người dùng đang đăng nhập bằng root: nên làm việc bằng user IAM có MFA.
- Tránh: NAT Gateway, RDS/OpenSearch bật suốt, GPU thuê. Huấn luyện ở máy nhà.

## Dữ liệu camera (cổng giaothong.hochiminhcity.gov.vn)

- Đơn vị: Sở Xây dựng TP.HCM; camera do Trung tâm quản lý hầm sông Sài Gòn quản lý.
- Điều khoản (`/TermOfUse`, mục 4): chỉ cho xem/tải/in để dùng cá nhân, phi thương mại, không sao chép/xuất bản/dùng lại. Dùng khác phải có cho phép bằng văn bản.
- 29/10/2026: người dùng báo đã gọi điện xin và được chấp nhận. **Cần email xác nhận** để đưa vào báo cáo.
- Kỹ thuật (xem tay trên bản đồ): mỗi camera có mã 24 ký tự hex, ảnh tự làm mới mỗi 5 giây; khu trung tâm có rất nhiều camera; có lớp "Tình trạng giao thông" (nhanh/chậm).
- 29/10/2026: trình phân quyền tự động của Claude Code **chặn** việc gọi thẳng vào API nội bộ của cổng ("Website Access Circumvention"). Không tìm cách lách. Muốn thu tự động thì cần: (a) bên cổng cấp cách truy cập chính thức, hoặc (b) người dùng tự quyết định cho phép trong phiên làm việc.

## Đồ thị đường (OSM)

- 3.666 đường loại footway đang bị loại khỏi đồ thị xe máy. Một số hẻm ở TP.HCM có thể bị vẽ nhầm là footway → có thể bỏ sót đường tắt. Cần soát mẫu trước khi kết luận "hệ thống tìm được đường hẻm".
- Ở TP.HCM rất nhiều luật cấm rẽ ghi `except=motorcycle` (794 luật): xe máy được rẽ. Không được áp các luật này cho xe máy.
- Luật cấm theo giờ (`restriction:conditional`, 50 luật áp cho xe máy) lưu ở `theo_gio` trong pickle, chưa áp. Định tuyến theo thời điểm (tuần 7) phải đọc.
- Tốc độ trong đồ thị hiện là tốc độ "đường trống" theo loại đường, chưa phải dữ liệu thật. Đường "nhanh nhất" ở tuần 1 chỉ để thử thuật toán.

## TomTom

- Key ở `thuctaptotnghiep/.env` (`TOMTOM_KEY=`). Không bao giờ in key ra màn hình hay nhật ký. Khi in lỗi HTTP phải che `key=`.
- Hạn mức Evaluation: 2.500 lượt gọi thường/ngày (Flow Segment, Incidents…) + 50.000 ô bản đồ/ngày. Một lần chụp khu trung tâm = 30 ô → 5 phút/lần = 8.640 ô/ngày.
- traffic_level ở kiểu `relative` = tốc độ hiện tại / tốc độ đường trống. Thang chia: <0,4 kẹt; 0,4–0,75 đông; ≥0,75 thông.
- Incidents API không nhận `language=vi-VN` (400): dùng en-GB. Tên đường (from/to) vẫn là tiếng Việt.
- Hai chiều của một con đường = hai đoạn vẽ ngược thứ tự điểm (mã khác nhau). Khoảng 8% đoạn ngắn trùng hình học trong cùng lần chụp → gộp lấy trung bình.
- **Đoạn TomTom KHÔNG phải đơn vị cố định**: TomTom cắt đoạn theo chỗ mức kẹt thay đổi. Chuỗi thời gian phải gắn vào cạnh đồ thị (`tomtom/canh/`), không gắn vào mã đoạn TomTom.
- (Đã xử lý 30/10/2026, QĐ-006) Ô TomTom từng rộng hơn bản đồ OSM: 20% mẫu rơi ra ngoài. Bản đồ mới phủ cả vùng ô, ghép được 95,8% mẫu (lượt 05:02).
- Overpass (OSM) rất hay quá tải: 30/10 lúc 04:00–05:00 mọi máy chủ trả 502/504 hoặc hết giờ chờ, tải 16 ô mất 59 phút. `tai_osm.py` đã lưu từng ô để tải tiếp; cứ để chạy nền, đừng chạy lại từ đầu.
- Dựng lại đồ thị (`do_thi.py`) là chỉ số cạnh đổi → phải chạy `BoGhep.dung()` và ghép lại `tomtom/canh/` từ `tomtom/tho/`.
- TomTom gần như không có dữ liệu ở hẻm/residential: đường nhỏ phải dùng tốc độ ước lượng (theo loại đường × khung giờ), ghi rõ trong báo cáo.
- (Từ 30/10/2026 15:52 bộ thu ở máy ĐÃ TẮT — người dùng bấm Dừng thu; chỉ còn AWS. Bật lại: nút Bắt đầu thu trên bảng theo dõi.) Bộ thu ở máy chỉ chạy khi máy bật và đã đăng nhập. Máy ngủ/tắt = khoảng trống trong dữ liệu. Khi phân tích phải đánh dấu khoảng trống, không nội suy bừa.

- **Đường ĐÓNG ≠ kẹt xe.** TomTom ghi mức 0 kèm `road_closure` cho đường đang đóng. Ngày 30/10: 8.798 ô mức 0 có cờ đóng, 4.089 ô mức 0 không có cờ.
  - 3 "đoạn kẹt nhất" ban đầu của M1 (Cách Mạng Tháng Tám, Tố Hữu, Tân Kỳ Tân Quý, r = 0 suốt 90 phút) hóa ra là đường đóng.
  - Từ QĐ-010, bộ ghép tách mẫu đóng/mở: `muc` chỉ từ phần mở, `phu_dong` = phần đóng. Cạnh `phu = 0` (đóng hết) thì `muc` vô nghĩa. M1 vẫn bỏ mọi cạnh có phần đóng.
  - Khi tìm đường thì cạnh đóng phải cấm, không chỉ "chậm".
- Kiểu ô `absolute` (km/h) làm tròn bước 5 km/h; tối 30/10 04:07 thấy 0–75 km/h. Tốc độ đường trống suy ra = km/h ÷ tỉ lệ relative: trung vị 30, p10 25, p90 40 km/h.
- Bộ ghép kiểu cũ (từng điểm, Python) mất 19 s/lần chụp; bản numpy 0,7 s, kết quả trùng (`dinh_tuyen/kiem_tra_ghep_nhanh.py`).
  - Dữ liệu từ parquet là `numpy.float32` nên `isinstance(x, float)` = False. Bộ ghép cũ bỏ hết đoạn vì vậy. Phải đổi `float()` trước, `doan_tu_tho` đã làm.
- Hampel trên pandas rolling mất 22 s/ngày. Bản sắp xếp cửa sổ numpy (`trung_vi_truot`) mất 0,8 s, kết quả trùng.

## Kiểm thử (từ 30/10/2026)

- `python -m pytest kiem_thu -q`: 34 test đơn vị trên dữ liệu giả có đáp án tính tay (ghép, Hampel, âm lịch, tên đường…). Sửa hàm xử lý nào thì chạy lại.
- `python kiem_thu/kiem_du_lieu.py`: 50 bất biến trên dữ liệu THẬT mọi tầng. Chạy sau mỗi lần dựng lại bạc/vàng.
  - Lần đầu bắt được 2 lỗi thật: gộp đoạn ghi đè 3 đoạn; đường đóng một phần bị trộn mức 0.
- Sửa mã có dấu `\` thì dùng công cụ Edit, KHÔNG dùng heredoc Python trong Git Bash.
  - 30/10 dính BA lần:
    - dấu nối dòng (gạch ngược + xuống dòng) thành hai ký tự gạch ngược + n, hỏng `kiem_tra_ghep_nhanh.py`;
    - chính dòng ghi chú này cũng bị cắt;
    - `ba_phuong_an.py` (he_so).
  - Quy tắc: trong mã dùng ngoặc tròn để xuống dòng, KHÔNG dùng gạch ngược nối dòng. Mọi sửa có `\` thì dùng Edit.
  - Soát nhanh: `python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('**/*.py', recursive=True) if 'du_lieu' not in f]"`.

## Bộ dữ liệu Kaggle TP.HCM (D11)

- **Cột `period` của train.csv là GIỜ UTC, ngày cũng là ngày UTC**, giống `updated_at` của segment_status.
  - Bằng chứng: khớp giờ UTC của báo cáo cùng đoạn cùng ngày ở 42% dòng, khớp giờ VN chỉ 0,3%.
  - Đổi sang giờ VN thì đỉnh LOS rơi vào 6–8h và 18h.
- Tốc độ = 1 km/h chiếm 23% báo cáo (nghi giá trị mặc định, cờ bit 8). Có giây nhận 1.263 báo cáo (nhập hàng loạt, L3 gắn 40% báo cáo).

- CC0, nhóm ĐH Bách Khoa TP.HCM, cập nhật lần cuối 20/05/2021. Dữ liệu có thể rơi vào thời kỳ **COVID** (giãn cách 04/2020, phong tỏa 07–09/2021). Phải xem ngày và loại các giai đoạn đó trước khi học, nếu không mô hình học nhầm "đường vắng bất thường".
- Đơn vị là đoạn đường của họ (segments/nodes riêng) và mức LOS theo 30 phút, khác TomTom (tỉ lệ tốc độ, 5 phút). Muốn kết hợp phải ghép đoạn của họ vào cạnh đồ thị (như ghép TomTom), rồi quy về cùng thang.
- Định nghĩa "kẹt xe" chính thức TP.HCM (báo Tuổi Trẻ dẫn báo cáo thành phố): xe di chuyển dưới 5 km/h liên tục hơn 30 phút, hàng xe dài ít nhất 200 m. Nên nêu trong báo cáo khi định nghĩa nhãn.

## Trình phân quyền tự động của Claude Code (đã chặn 29/10/2026)

- Gọi thẳng API nội bộ của cổng camera ("Website Access Circumvention").
- `pip install` gói từ PyPI ("Untrusted Code Integration") → tự viết phần nhỏ, hoặc người dùng tự cài.
- Tạo tác vụ hẹn giờ Windows ("Unauthorized Persistence") → người dùng tự bấm `CAI_HEN_GIO.bat`.
- Không tìm cách lách. Giải thích cho người dùng và để họ quyết.

## Công cụ

- Cài gói Python từ PyPI bằng pip có thể bị trình phân quyền chặn. Ưu tiên tự viết phần nhỏ (như `mvt.py`), hoặc nhờ người dùng thêm quyền. (30/10/2026 ~17:46: `pip install gdown tables` chạy được.)
- **Không mở pickle tải từ ngoài về** (`.pkl`, `torch.load(weights_only=False)` tệp lạ): mở pickle = chạy mã trong tệp. Bộ METR-LA: bỏ `adj_mx*.pkl` của repo DCRNN, dựng lại ma trận kề từ `distances_*.csv` (khớp số cạnh công bố 1.515 / 2.369). Tệp `.h5` của pandas cũng có thể chứa pickle (cột kiểu object) → soát bằng `tables.open_file` + `walk_nodes` trước (METR-LA/PEMS-BAY chỉ có mảng số/chuỗi).
- Lệnh `python -c` in tên địa điểm tiếng Việt ra màn hình → `UnicodeEncodeError` cp1252. Đặt `PYTHONIOENCODING=utf-8` trước lệnh (các script chính đã tự `sys.stdout.reconfigure(encoding='utf-8')`).
- **Đo rồi mới kết luận** (30/10, QĐ-013): tưởng "đổi tuyến liên tục (ngưỡng 0) thì thiệt vì nhiễu" — đo ra ngưỡng 0 lại NHANH NHẤT; lý do giữ 60 s là vì người lái. Lý do ghi trong QĐ phải khớp số đo, không phải trực giác.
- Định tuyến (31/10, QĐ-016):
  - Chi phí phụ thuộc HƯỚNG TỚI nút (rẽ trái, quay đầu) thì trạng thái A* phải chứa nút trước. Đổi mô hình chi phí kiểu này thì so chi phí cũ / mới trên 270 tuyến trước khi tin.
  - A* viết bằng Python chậm theo SỐ TRẠNG THÁI: muốn nhanh thì làm cận dưới chặt hơn (ALT theo giờ), đừng thêm mốc (16–24 mốc gần như không đỡ).
  - Bộ chấm tốc độ thật KHÔNG tính trễ ở nút giao (đèn, rẽ trái) → mọi phạt nút giao luôn trông "thiệt" khi chỉ chấm thời gian chạy; phải thử thêm kịch bản trễ giả định cộng ĐỀU cho mọi tuyến.
- `distances_bay_2017.csv` KHÔNG có dòng tiêu đề, `distances_la_2012.csv` có — đọc kiểu `header=None` rồi bỏ dòng "from" nếu có.
- Google Drive (thư mục chia sẻ của tác giả bài báo): `gdown.download_folder(id=..., skip_download=True)` để xem mã tệp, rồi `gdown.download(id=...)`.
- GPU máy nhà: GTX 1650 4 GB, PyTorch 2.6 cu124. Graph WaveNet trên METR-LA ~116 s/vòng (bài báo: 54 s trên Titan Xp) → 100 vòng ≈ 3 giờ: chạy nền, có điểm dừng mỗi vòng (`hoc_sau.py --tiep` khi máy ngủ giữa chừng).

- Overpass (OpenStreetMap) trả 504 khi tải cả khu trung tâm một lần → `tai_osm.py` chia 2×2 ô + máy chủ dự phòng.
- Thời tiết lưu trữ Open-Meteo lưới thô: 5 điểm trong thành phố chỉ ra 3 chuỗi khác nhau.

## Bài học mang sang từ đồ án chuyên ngành

- Kiểm thử ghi dữ liệu chỉ chạy trên bản sao, không bao giờ trên dữ liệu thật (đồ án từng mất dữ liệu ngày 22/09/2026 vì một bộ kiểm chạy nhầm CSDL thật).
- Không mở cổng CSDL ra Internet (đồ án từng bị bot xóa sạch CSDL). Quản trị CSDL qua đường hầm SSH hoặc mạng riêng.
- Trên Windows, mã có dấu gạch ngược (`\`) thì viết bằng tệp, không qua heredoc của Git Bash (heredoc làm mất dấu `\`).
- Trợ lý khác (Kiro, Antigravity) có thể cùng sửa dự án: luôn kiểm lại, đừng tin câu "đã test".
