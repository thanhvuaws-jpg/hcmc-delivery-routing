# Định tuyến giao hàng đô thị thông minh — TP.HCM

Đề tài thực tập tốt nghiệp. Hệ thống dự báo ùn tắc trên các tuyến đường và gợi ý tuyến đi cho shipper xe máy:
- **ngắn nhất**,
- **nhanh nhất**,
- **tối ưu**: tính kẹt xe, sự cố, thời tiết/ngập và luật giao thông.

Hệ thống chạy theo mô hình hybrid: thu dữ liệu và huấn luyện tại máy, phục vụ trên AWS.

> Trước khi làm gì, đọc `note/` (bắt đầu từ `note/README.md`). Quy tắc chung ở `CLAUDE.md`.

## Dữ liệu (tất cả lấy qua mạng, không cần xin phép)

| Nguồn | Nội dung | Script |
|---|---|---|
| OpenStreetMap | Mạng đường + luật (một chiều, cấm xe máy, cấm rẽ, cấm theo giờ) | `thu_thap/tai_osm.py` |
| TomTom Traffic Flow | Mức kẹt (tốc độ hiện tại / tốc độ đường trống) của ~4.300 đoạn đường khu trung tâm, 5 phút/lần | `thu_thap/thu_dinh_ky.py` |
| TomTom Traffic Incidents | Sự cố đang diễn ra: kẹt xe, đóng đường, công trình, tai nạn, ngập | `thu_thap/thu_dinh_ky.py` |
| Open-Meteo | Thời tiết theo giờ từ 2020 + dự báo 48 giờ, lưu mỗi giờ | `thu_thap/tai_thoi_tiet.py`, `thu_thap/du_bao_thoi_tiet.py` |
| Bộ thu AWS (Lambda) | Cùng TomTom Flow (thêm km/h) + Incidents + dự báo, 24/7 lên S3 | `he_thong/aws/thu_lambda/`, kéo về: `thu_thap/KEO_S3.bat` |
| OSM POI | Trường, chợ, bệnh viện, TTTM, trạm buýt | `thu_thap/tai_osm.py poi` |
| Kaggle (ĐH Bách Khoa) | Tốc độ + nhãn LOS 2020–21 | `thu_thap/tai_kaggle.py` |
| Zenodo HCM_1000 | 56 bài toán giao hàng có khung giờ (điểm đi–đến thật) | `thu_thap/tai_tep.py` |
| CSGT PC08 | 122 điểm nguy cơ ngập (chép từ infographic) | `thu_thap/chep_tay/` |

Ghi nguồn khi dùng: "© OpenStreetMap contributors", "Traffic data © TomTom", "Weather data by Open-Meteo.com".

## Cài đặt

1. Python 3.13 + các gói trong `requirements.txt`.
2. Tạo `.env` ở thư mục này với dòng `TOMTOM_KEY=...`. Không đưa lên git, không gửi qua chat.
3. Tải dữ liệu nền:
   ```
   python thu_thap/tai_osm.py
   python thu_thap/tai_thoi_tiet.py
   ```
4. Thu dữ liệu tự động: bấm đúp `thu_thap/CAI_HEN_GIO.bat` một lần (Windows Task Scheduler, 5 phút/lần). Tắt bằng `GO_HEN_GIO.bat`. Nhật ký ở `du_lieu/nhat_ky/`.
5. Dựng đồ thị và thử tìm đường:
   ```
   python dinh_tuyen/do_thi.py
   python dinh_tuyen/kiem_tra_tuan1.py
   ```

## Cấu trúc

```
thu_thap/     tải và thu dữ liệu (OSM, TomTom, thời tiết), bộ đọc ô vector mvt.py, chep_tay/
dinh_tuyen/   đồ thị xe máy có luật + tìm đường (A* có luật cấm rẽ) + ghép TomTom vào cạnh
xu_ly/        tầng bạc (bac_*.py, lich, canh_tinh, doan_duong) và tầng vàng (vang.py)
khai_pha/     khai phá dữ liệu M1–M9 (m1_mo_ta.py, m2_diem_nong.py…), kết quả ở ket_qua/
mo_hinh/      dự báo ùn tắc: mốc so sánh + mô hình (moc_so_sanh.py), kết quả ở ket_qua/
kiem_thu/     test đơn vị (pytest) + kiem_du_lieu.py (bất biến trên dữ liệu thật)
he_thong/     aws/thu_lambda (bộ thu AWS), bang_theo_doi (ứng dụng theo dõi 2 bộ thu); API + web (tuần 8–9)
danh_gia/     đánh giá offline + chạy thử ảo (tuần 10–11)
du_lieu/      dữ liệu — KHÔNG đưa lên git (đồng: tomtom/, s3/, thoi_tiet*/… ; bac/ ; vang/)
note/         sổ ghi chú: kế hoạch, quyết định, nhật ký, điều cần nhớ
```
