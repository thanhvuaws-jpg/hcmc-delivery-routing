"""
Lưu bản DỰ BÁO thời tiết theo giờ (48 giờ tới) cho 5 điểm TP.HCM, mỗi giờ một lần.

Vì sao lưu dự báo chứ không chỉ lưu thời tiết đã xảy ra: lúc chạy thật, mô hình chỉ
biết DỰ BÁO mưa chứ không biết trước trời sẽ mưa thật hay không. Huấn luyện bằng
thời tiết thật mà chạy bằng dự báo thì mô hình được học trên dữ liệu "quá đẹp".
Lưu dự báo đúng như lúc phát hành để sau này huấn luyện công bằng.

Nguồn: Open-Meteo Forecast API (CC BY 4.0, phi thương mại, không cần khóa).
Lưu: du_lieu/thoi_tiet_du_bao/YYYY-MM-DD/HH.parquet
"""
import datetime as dt
import os

import requests

from tai_thoi_tiet import DIEM

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
THU_MUC = os.path.join(GOC, 'du_lieu', 'thoi_tiet_du_bao')
API = 'https://api.open-meteo.com/v1/forecast'
BIEN = ['precipitation', 'precipitation_probability', 'rain', 'showers', 'temperature_2m',
        'relative_humidity_2m', 'weather_code', 'cloud_cover', 'wind_speed_10m']


def tep_cua_gio(luc):
    return os.path.join(THU_MUC, f'{luc:%Y-%m-%d}', f'{luc:%H}.parquet')


def thu(luc):
    """Trả về số dòng đã lưu, hoặc None nếu giờ này đã có bản dự báo."""
    import pandas as pd
    tep = tep_cua_gio(luc)
    if os.path.exists(tep):
        return None
    ten = list(DIEM)
    r = requests.get(API, params={
        'latitude': ','.join(str(DIEM[t][0]) for t in ten),
        'longitude': ','.join(str(DIEM[t][1]) for t in ten),
        'hourly': ','.join(BIEN), 'forecast_days': 2, 'timezone': 'Asia/Ho_Chi_Minh',
    }, timeout=60)
    r.raise_for_status()
    js = r.json()
    js = js if isinstance(js, list) else [js]       # nhiều điểm -> danh sách, mỗi điểm một mục
    hang = []
    phat_hanh = pd.Timestamp(luc.replace(tzinfo=None))
    for diem, k in zip(ten, js):
        gio = k['hourly']
        for i, t in enumerate(gio['time']):
            hang.append({'phat_hanh': phat_hanh, 'diem': diem, 'thoi_gian': pd.Timestamp(t),
                         **{b: gio[b][i] for b in BIEN}})
    df = pd.DataFrame(hang)
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    df.to_parquet(tep + '.tam', index=False)
    os.replace(tep + '.tam', tep)
    return len(df)


if __name__ == '__main__':
    print(thu(dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))))
