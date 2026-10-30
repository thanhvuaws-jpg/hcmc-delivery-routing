"""
Tốc độ THẬT cho định tuyến, từ tầng bạc TomTom (km/h kiểu absolute + tỉ lệ relative).

1. Tốc độ đường trống từng cạnh: mỗi lần chụp có cả km/h (v) và tỉ lệ r = v / v_trống, nên
   v_trống ≈ v / r. Chỉ lấy lần chụp đường gần trống (r ≥ R_TRONG) — chia cho r nhỏ phóng đại
   sai số làm tròn 5 km/h của TomTom. Lấy trung vị theo cạnh, cần ≥ TOI_THIEU lần.
2. Hồ sơ theo loại đường × giờ trong ngày: km/h TB ĐIỀU HÒA (đúng cho thời gian đi) và r, trọng số
   chiều dài. Dùng làm
   tốc độ mặc định cho cạnh TomTom không đo (hẻm, residential) và cho giờ chưa có dữ liệu.
3. So với bảng tốc độ đoán trong dinh_tuyen/do_thi.py (TOC_DO): sai bao nhiêu.

Đầu ra:
  du_lieu/bac/toc_do_canh.parquet     chi_so, v_trong (km/h), n_lan, v_trong_loai (trung vị cùng loại)
  du_lieu/bac/toc_do_ho_so.parquet    loai, gio, v_tb (km/h), r_tb, km_quan_sat
Chạy:  python toc_do_canh.py
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
R_TRONG = 0.85
TOI_THIEU = 6


V_TOI_THIEU = 3.0       # km/h: xe đứng yên trong hàng kẹt vẫn nhích — tránh thời gian vô hạn


def tb_dieu_hoa(v, dai):
    """Tốc độ TB đúng cho THỜI GIAN đi: tổng quãng đường / tổng thời gian (TB điều hòa có trọng số
    chiều dài). Trung vị/TB cộng của km/h làm tròn 5 của TomTom thì ra số tròn và lệch thời gian."""
    v = np.maximum(v, V_TOI_THIEU)
    return float(dai.sum() / (dai / v).sum())


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from do_thi import TOC_DO
    canh = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['chi_so', 'loai', 'dai'])
    phan = []
    for tep in sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet'))):
        s = pd.read_parquet(tep, columns=['khung', 'chi_so', 'muc', 'toc_do', 'phu'])
        phan.append(s[(s['phu'] > 0) & s['toc_do'].notna()])
    s = pd.concat(phan, ignore_index=True)
    s['toc_do'] = s['toc_do'].astype(float)
    s['r'] = s['muc'] / 100
    s = s.merge(canh, on='chi_so')
    print(f'{len(s):,} quan sat co km/h, {s["chi_so"].nunique():,} canh, '
          f'{s["khung"].min()} -> {s["khung"].max()}')

    # 1. Tốc độ đường trống theo cạnh.
    trong = s[(s['r'] >= R_TRONG) & (s['toc_do'] > 0)].copy()
    trong['v_trong'] = trong['toc_do'] / trong['r']
    g = trong.groupby('chi_so')['v_trong'].agg(v_trong='median', n_lan='size')
    g = g[g['n_lan'] >= TOI_THIEU].join(canh.set_index('chi_so')['loai'])
    g['v_trong_loai'] = g.groupby('loai')['v_trong'].transform('median')
    g.reset_index().astype({'chi_so': np.int32, 'v_trong': np.float32, 'v_trong_loai': np.float32}).to_parquet(
        os.path.join(BAC, 'toc_do_canh.parquet'), index=False)

    # 2. Hồ sơ loại đường × giờ (trọng số chiều dài).
    s['gio'] = s['khung'].dt.hour
    hs = s.groupby(['loai', 'gio']).apply(lambda x: pd.Series({
        'v_tb': tb_dieu_hoa(x['toc_do'].to_numpy(), x['dai'].to_numpy()),
        'r_tb': np.average(x['r'], weights=x['dai']),
        'km_quan_sat': x['dai'].sum() / 1000}), include_groups=False).reset_index()
    hs.to_parquet(os.path.join(BAC, 'toc_do_ho_so.parquet'), index=False)

    # 3. So với bảng đoán.
    print(f'Toc do duong trong (r >= {R_TRONG}, >= {TOI_THIEU} lan): {len(g):,} canh')
    print(f'  {"loai":<15}{"so canh":>8}{"do (km/h)":>11}{"doan (km/h)":>12}{"lech":>8}')
    for loai, x in g.groupby('loai'):
        if len(x) < 30 or loai not in TOC_DO:
            continue
        do = x['v_trong'].median()
        print(f'  {loai:<15}{len(x):>8,}{do:>11.1f}{TOC_DO[loai]:>12}{100 * (TOC_DO[loai] - do) / do:>+7.0f}%')
    chinh = hs[hs['loai'].isin(['primary', 'secondary', 'tertiary', 'residential'])]
    print('Toc do TB theo gio (km/h), cac loai chinh:')
    print(chinh.pivot(index='gio', columns='loai', values='v_tb').round(1).to_string())


if __name__ == '__main__':
    main()
