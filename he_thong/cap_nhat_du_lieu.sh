#!/bin/bash
# Kéo dữ liệu mới từ S3, dựng lại bạc + vàng, kiểm, rồi dự báo ngoài mẫu tới khung mới nhất cho lớp dự báo của API / web
# và tính lại hồ sơ tốc độ của API (QĐ-029). Chạy bằng Git Bash từ bất kỳ đâu:  bash he_thong/cap_nhat_du_lieu.sh
#  - Chỉ TẢI tệp mới / khác từ S3, không xóa gì ở máy, không ghi gì lên S3 (profile chỉ đọc thuctap-doc).
#  - Tên bucket đọc từ .env (dòng S3_BUCKET=...), không ghi ở đây vì repo công khai.
#  - Đừng chạy khi đang chấm tuyến (danh_gia/): các script đó đọc tầng bạc giữa chừng.
set -e
export MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/.."
B=$(grep -E '^S3_BUCKET=' .env | cut -d= -f2 | tr -d '\r')
[ -n "$B" ] || { echo "LOI: chua co S3_BUCKET trong .env"; exit 1; }
echo "== keo S3 $(date +%T)"; aws s3 sync "s3://$B/dong" du_lieu/s3/dong --profile thuctap-doc --region ap-southeast-1 --only-show-errors
for s in bac_tomtom bac_su_co bac_thoi_tiet vang; do echo "== $s $(date +%T)"; python xu_ly/$s.py; done
echo "== kiem_du_lieu $(date +%T)"; python kiem_thu/kiem_du_lieu.py | grep -vE '^\s+\[DAT\]' || true
echo "== pytest $(date +%T)"; python -m pytest -q kiem_thu 2>&1 | tail -1
echo "== du bao ngoai mau $(date +%T)"; (cd mo_hinh && python du_bao_moi.py)
echo "== ho so API $(date +%T)"; python he_thong/api/may_chu.py --dung-ho-so
echo "== xong $(date +%T)"
