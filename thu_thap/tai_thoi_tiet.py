"""
Tải lịch sử thời tiết theo GIỜ cho nhiều điểm trong TP.HCM.

Nguồn: Open-Meteo Historical Weather API (archive-api.open-meteo.com), giấy phép
CC BY 4.0, miễn phí cho dùng phi thương mại. Ghi nguồn "Weather data by Open-Meteo.com".

Vì sao nhiều điểm: mưa ở TP.HCM rất cục bộ — quận này mưa to, quận kế bên khô.
Lưu ý độ phân giải: dữ liệu lưu trữ (ERA5 và các mô hình tái phân tích) là lưới vài
km tới ~25 km, nên các điểm gần nhau có thể ra cùng số liệu. Đủ để làm đặc trưng
"trời đang mưa / mưa to" cho mô hình, không đủ để nói mưa ở từng con đường.

Chạy:   python tai_thoi_tiet.py                      (2020-01-01 tới 6 ngày trước — phủ cả giai đoạn Kaggle 2020–21)
        python tai_thoi_tiet.py 2024-01-01 2024-12-31
Kết quả: ../du_lieu/thoi_tiet/<diem>.csv
"""
import csv
import datetime as dt
import os
import sys
import time

import requests

THU_MUC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'du_lieu', 'thoi_tiet')
API = 'https://archive-api.open-meteo.com/v1/archive'

DIEM = {
    'ben_thanh':   (10.7725, 106.6980),
    'cong_hoa':    (10.8010, 106.6530),
    'hang_xanh':   (10.8010, 106.7110),
    'nga_sau_cho_lon': (10.7560, 106.6590),
    'nguyen_van_linh_q7': (10.7290, 106.7210),
}

BIEN = ['temperature_2m', 'relative_humidity_2m', 'precipitation', 'rain',
        'weather_code', 'cloud_cover', 'wind_speed_10m']


def tai_mot_diem(ten, vi_do, kinh_do, tu, den):
    r = requests.get(API, params={
        'latitude': vi_do, 'longitude': kinh_do,
        'start_date': tu, 'end_date': den,
        'hourly': ','.join(BIEN),
        'timezone': 'Asia/Ho_Chi_Minh',
    }, timeout=120)
    r.raise_for_status()
    gio = r.json()['hourly']
    os.makedirs(THU_MUC, exist_ok=True)
    tep = os.path.join(THU_MUC, f'{ten}.csv')
    with open(tep, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['thoi_gian'] + BIEN)
        for i, t in enumerate(gio['time']):
            w.writerow([t] + [gio[b][i] for b in BIEN])
    so_gio_mua = sum(1 for x in gio['precipitation'] if x and x >= 0.5)
    print(f'  {ten:<20} {len(gio["time"]):>6,} gio | {so_gio_mua:,} gio co mua >= 0.5mm -> {tep}')


if __name__ == '__main__':
    homnay = dt.date.today()
    tu = sys.argv[1] if len(sys.argv) > 2 else '2020-01-01'
    den = sys.argv[2] if len(sys.argv) > 2 else str(homnay - dt.timedelta(days=6))
    print(f'Tai thoi tiet theo gio {tu} -> {den}')
    for ten, (a, b) in DIEM.items():
        tai_mot_diem(ten, a, b, tu, den)
        time.sleep(1)   # lịch sự với API miễn phí
