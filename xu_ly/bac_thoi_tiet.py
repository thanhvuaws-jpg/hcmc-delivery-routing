"""
Tầng bạc thời tiết (D2 lưu trữ + D3 dự báo) cho 5 điểm TP.HCM.

Đầu vào (tầng đồng):
  du_lieu/thoi_tiet/<diem>.csv                         lưu trữ theo giờ (Open-Meteo archive,
                                                        từ 01/2020, chậm ~6 ngày so với hôm nay)
  du_lieu/thoi_tiet_du_bao/YYYY-MM-DD/HH.parquet       dự báo 48 giờ, bộ thu ở máy (mỗi giờ)
  du_lieu/s3/dong/thoi_tiet_du_bao/YYYY-MM-DD/HH.json.gz  cùng thứ đó, bộ thu AWS

Đầu ra:
  du_lieu/bac/thoi_tiet_gio.parquet
      thoi_gian, diem, + biến thời tiết; nguon = 'luu_tru' (đã xảy ra, từ archive) hoặc
      'du_bao_sau' (giờ archive chưa có: lấy bản dự báo phát hành SAU giờ đó gần nhất —
      tức ước lượng của mô hình cho giờ đã qua). Dùng để PHÂN TÍCH (mưa làm kẹt bao nhiêu).
  du_lieu/bac/thoi_tiet_du_bao.parquet
      phat_hanh (đầu giờ phát hành), diem, thoi_gian, truoc_h (thoi_gian − phat_hanh, giờ;
      âm = giờ đã qua lúc phát hành), + biến, nguon. Dùng làm ĐẶC TRƯNG cho mô hình: lúc dự báo
      kẹt xe ở thời điểm t chỉ được dùng bản phát hành trước t (KE_HOACH_DU_LIEU mục 8).

Một giờ phát hành có cả bản AWS và bản máy thì giữ AWS (như tầng bạc TomTom).

Chạy:  python bac_thoi_tiet.py
"""
import glob
import gzip
import json
import os
import sys

import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
LUU_TRU = os.path.join(GOC, 'du_lieu', 'thoi_tiet')
DU_BAO_MAY = os.path.join(GOC, 'du_lieu', 'thoi_tiet_du_bao')
DU_BAO_AWS = os.path.join(GOC, 'du_lieu', 's3', 'dong', 'thoi_tiet_du_bao')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
BIEN = ['precipitation', 'precipitation_probability', 'rain', 'showers', 'temperature_2m',
        'relative_humidity_2m', 'weather_code', 'cloud_cover', 'wind_speed_10m']


def luu_tru():
    phan = []
    for tep in sorted(glob.glob(os.path.join(LUU_TRU, '*.csv'))):
        d = pd.read_csv(tep, parse_dates=['thoi_gian'])
        d.insert(1, 'diem', os.path.basename(tep)[:-4])
        phan.append(d)
    d = pd.concat(phan, ignore_index=True)
    return d.dropna(subset=['precipitation'])          # giờ cuối có thể chưa có số


def du_bao():
    phan = []
    for tep in glob.glob(os.path.join(DU_BAO_MAY, '*', '*.parquet')):
        d = pd.read_parquet(tep)
        d['nguon'] = 'may'
        phan.append(d)
    for tep in glob.glob(os.path.join(DU_BAO_AWS, '*', '*.json.gz')):
        with gzip.open(tep, 'rt', encoding='utf-8') as f:
            goi = json.load(f)
        ph = pd.Timestamp(goi['phat_hanh']).tz_localize(None)
        tra_ve = goi['tra_ve'] if isinstance(goi['tra_ve'], list) else [goi['tra_ve']]
        for diem, k in zip(goi['diem'], tra_ve):
            gio = k['hourly']
            d = pd.DataFrame({'thoi_gian': pd.to_datetime(gio['time']), **{b: gio[b] for b in BIEN}})
            d.insert(0, 'diem', diem)
            d.insert(0, 'phat_hanh', ph)
            d['nguon'] = 'aws'
            phan.append(d)
    d = pd.concat(phan, ignore_index=True)
    d['phat_hanh'] = d['phat_hanh'].dt.floor('h')
    # Cùng giờ phát hành có cả hai nguồn: giữ AWS.
    d = d.sort_values('nguon').drop_duplicates(['phat_hanh', 'diem', 'thoi_gian'], keep='first')
    d['truoc_h'] = ((d['thoi_gian'] - d['phat_hanh']).dt.total_seconds() // 3600).astype('int16')
    d['nguon'] = pd.Categorical(d['nguon'], categories=['aws', 'may'])
    return d.sort_values(['phat_hanh', 'diem', 'thoi_gian'], ignore_index=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(BAC, exist_ok=True)
    lt = luu_tru()
    db = du_bao()
    db.to_parquet(os.path.join(BAC, 'thoi_tiet_du_bao.parquet'), index=False)

    # Giờ chưa có trong lưu trữ: lấy bản phát hành sau giờ đó (truoc_h <= 0) gần nhất.
    het_luu_tru = lt['thoi_gian'].max()
    sau = db[(db['truoc_h'] <= 0) & (db['thoi_gian'] > het_luu_tru)]
    sau = sau.sort_values('phat_hanh').drop_duplicates(['diem', 'thoi_gian'], keep='first')
    cot = ['thoi_gian', 'diem'] + [b for b in BIEN if b in lt.columns]
    gio = pd.concat([lt[cot].assign(nguon='luu_tru'), sau[cot].assign(nguon='du_bao_sau')], ignore_index=True)
    gio = gio.sort_values(['thoi_gian', 'diem'], ignore_index=True)
    gio['nguon'] = pd.Categorical(gio['nguon'], categories=['luu_tru', 'du_bao_sau'])
    gio.to_parquet(os.path.join(BAC, 'thoi_tiet_gio.parquet'), index=False)

    print(f'luu tru: {len(lt):,} dong, {lt["thoi_gian"].min()} -> {het_luu_tru}')
    print(f'du bao: {db["phat_hanh"].nunique()} gio phat hanh ({db.drop_duplicates("phat_hanh")["nguon"].value_counts().to_dict()}), '
          f'{len(db):,} dong, truoc_h {db["truoc_h"].min()}..{db["truoc_h"].max()}')
    print(f'thoi_tiet_gio: {len(gio):,} dong, den {gio["thoi_gian"].max()} '
          f'(du_bao_sau: {int((gio["nguon"] == "du_bao_sau").sum())} dong)')
    mua = gio[gio['precipitation'] >= 0.5]
    print(f'gio co mua >= 0.5 mm (moi diem TB): {len(mua) / gio["diem"].nunique():,.0f} / '
          f'{len(gio) / gio["diem"].nunique():,.0f} gio')


if __name__ == '__main__':
    main()
