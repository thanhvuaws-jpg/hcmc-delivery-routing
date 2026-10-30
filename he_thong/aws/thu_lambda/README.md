# Bộ thu dữ liệu thời gian thực trên AWS

Chạy 24/7 trên AWS, không phụ thuộc máy nhà bật hay tắt. Chỉ lưu bản gốc lên S3; việc giải mã và ghép vào bản đồ do máy làm sau (`thu_thap/mvt.py`, `dinh_tuyen/ghep_tomtom.py`).

```
EventBridge Scheduler (5 phút/lần)
      │
      ▼
Lambda thu-du-lieu-giao-thong (Python 3.13, arm64, 256 MB, ~10 s/lượt)
      │  TomTom: 30 ô Flow relative + 30 ô absolute (km/h, từ 30/10 04:11) + Incidents  ·  Open-Meteo: dự báo (mỗi giờ)
      ▼
S3 thuctap-giaothong-hcm-…/dong/
      tomtom_o/YYYY-MM-DD/HHMM.zip           ~200 KB  (<x>_<y>.pbf relative, absolute/<x>_<y>.pbf km/h)
      tomtom_su_co/YYYY-MM-DD/HHMM.json.gz   ~4 KB
      thoi_tiet_du_bao/YYYY-MM-DD/HH.json.gz
```

## Tài nguyên (vùng ap-southeast-1, Singapore — gần Việt Nam)

| Tài nguyên | Cấu hình | Vì sao |
|---|---|---|
| S3 bucket `thuctap-giaothong-hcm-<6 ký tự ngẫu nhiên>` | Chặn truy cập công khai (mặc định), mã hóa SSE-S3 (mặc định), không versioning | Rẻ nhất, an toàn mặc định |
| IAM role cho Lambda | Quyền ghi log cơ bản + `s3:PutObject` CHỈ vào `arn:aws:s3:::<bucket>/dong/*` | Quyền tối thiểu: lộ hàm cũng không đọc/xóa được dữ liệu |
| Lambda `thu-du-lieu-giao-thong` | Python 3.13, **arm64** (rẻ hơn x86 ~20%), 256 MB, timeout 60 s, **không VPC** (không cần NAT Gateway ~32 USD/tháng). Async: retry = 0, tuổi sự kiện tối đa 5 phút | Không chạy chồng/lặp khi lỗi |
| Biến môi trường | `BUCKET`, `TIEN_TO=dong`, `TOMTOM_KEY` (**người dùng tự dán**) | Không dùng Secrets Manager (0,40 USD/khóa/tháng) |
| CloudWatch Logs | Giữ 14 ngày | Log không phình mãi |
| EventBridge Scheduler `thu-5-phut` | `rate(5 minutes)`, không cửa sổ linh hoạt, retry = 0 | 14 triệu lần gọi/tháng miễn phí |
| AWS Budgets | 2 USD/tháng, email khi thực tế ≥ 80% và dự báo ≥ 100% | Hàng rào tiền (tín dụng đã hết hạn) |

## Chi phí ước tính / tháng

| Mục | Lượng | Tiền |
|---|---|---|
| Lambda | 8.640 lượt × ~10–12 s × 0,25 GB ≈ 26.000 GB-giây | 0 (miễn phí vĩnh viễn 400.000 GB-giây + 1 triệu lượt) |
| EventBridge Scheduler | 8.640 lượt | 0 (miễn phí 14 triệu) |
| S3 lưu trữ | từ 30/10 04:11 zip ~200 KB (thêm ô absolute, QĐ-007) → ~1,7 GB tăng mỗi tháng. Trước đó đo đêm 30/10: zip 83–88 KB, sự cố 3–4 KB, thời tiết 2 KB → ~26 MB/ngày, ~0,8 GB tăng mỗi tháng (ban ngày zip có thể to hơn: tính trần 150 KB → 1,3 GB) | 0,025 USD/GB-tháng: tháng 1 ~0,02, tháng 3 ~0,1 USD |
| S3 PUT | 288 zip + 288 sự cố + 24 thời tiết = 600 lượt/ngày ≈ 18.600/tháng | 0,005 USD/1.000 → ~0,09 USD |
| CloudWatch Logs | vài MB | 0 (5 GB/tháng miễn phí) |
| **Tổng** | | **~0,1–0,2 USD/tháng** (thêm ô absolute chỉ tăng tiền lưu trữ, không tăng lượt ghi) |

Trần tệ nhất của Lambda: Scheduler cố định 5 phút, retry 0, timeout 60 s → dù lượt nào cũng treo tới 60 s thì 8.928 × 60 × 0,25 GB ≈ 134.000 GB-giây/tháng, vẫn dưới 400.000 miễn phí. Không có miễn phí thì cũng chỉ ~1,8 USD.

Dừng bộ thu rồi thì chỉ còn tiền lưu S3 = số GB đã lưu × 0,025 USD/tháng (về 0 khi đã kéo dữ liệu về máy và xóa trên S3).

Hạn mức TomTom: chạy song song với bộ thu ở máy = 17.280 ô/ngày (< 50.000) và 576 lượt sự cố/ngày (< 2.500). Chạy cả hai vài ngày để so, ổn rồi thì tắt bộ thu ở máy (`GO_HEN_GIO.bat`).

## Kiểm thử trước khi lên AWS

`python thu_o_may.py`: chạy đúng hàm Lambda ở máy, thay S3 bằng thư mục tạm. 29/10/2026: ĐẠT (30/30 ô, 3.638 đoạn, 26 sự cố, thời tiết ok, 5,6 s).

## Gói triển khai

`dist/thu_lambda.zip` (3,6 KB, chỉ `lambda_function.py`, không chứa key). Tạo lại:
`python -c "import zipfile; zipfile.ZipFile('dist/thu_lambda.zip','w',zipfile.ZIP_DEFLATED).write('lambda_function.py')"`
