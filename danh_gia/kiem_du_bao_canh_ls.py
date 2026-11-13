"""
Vì sao lập tuyến trước 30 phút (QĐ-028) dự báo chỉ NGANG hồ sơ lịch sử, dù ở mức ô (đoạn × khung) GBM thấp hơn lịch sử
19% MAE? Đo ở mức CẠNH, khe xe tới = 45 và 60 phút sau khung vừa xong f (đúng 2 khe đầu của chuyến lập trước 30 phút):
  ls     hồ sơ của đoạn (ngày thường / cuối tuần × ô 15 phút, chỉ phần học) — cách `ls` của cham_tuyen_dat_truoc.py
  gbm    dự báo GBM + hồ sơ của đoạn          gwn    dự báo Graph WaveNet che sự cố của đoạn
Thước đo trọng số chiều dài, trên cạnh có số đo trong khe: MAE r (điểm %), sai thời gian tương đối, và LỆCH thời gian
(Σ dài·(1/r_dự − 1/r_thật) / Σ dài/r_thật; âm = đoán nhanh hơn thật).
Chỉ để GIẢI THÍCH kết quả đã chấm, không dùng để chọn lại cách.
Chạy:  python kiem_du_bao_canh_ls.py 2026-11-09 [06:00] [19:00]
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

from cham_tuyen_dat_truoc import ho_so_doan
from cham_tuyen_that import GOC, nap_du_bao, nap_quan_sat


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    ngay, tu, den = (a + ['2026-11-09', '06:00', '19:00'][len(a):])[:3]
    khung, R, _, _ = nap_quan_sat(ngay, '00:00', '23:59')
    doan_cua = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'canh_doan.parquet'),
                               columns=['chi_so', 'doan']).sort_values('chi_so')['doan'].to_numpy()
    so = int(doan_cua.max()) + 1
    dai = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['dai'])['dai'].to_numpy()
    P, _ = ho_so_doan(so)
    db = {t: nap_du_bao(t, ngay)[0].set_index('khung') for t in ('gbm_ls', 'gwn_ho_so_them_che')}
    tong = {}
    for p in pd.date_range(f'{ngay} {tu}', f'{ngay} {den}', freq='15min'):
        f = p - pd.Timedelta(minutes=15)
        if any(f not in d.index for d in db.values()):
            continue
        for tam in (45, 60):
            a_, b_ = f + pd.Timedelta(minutes=tam), f + pd.Timedelta(minutes=tam + 15)
            kk = np.flatnonzero((khung >= a_) & (khung < b_))
            if not len(kk):
                continue
            with np.errstate(divide='ignore', invalid='ignore'), warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                that = 1 / np.nanmean(1 / R[kk], axis=0)
            cach = {'ls': P[int(a_.dayofweek >= 5), a_.hour * 4 + a_.minute // 15][doan_cua]}
            for ten, d in db.items():
                x = d.loc[[f]]
                v = np.full(so, np.nan, np.float32)
                v[x['doan'].to_numpy()] = x[f'du_{tam}'].to_numpy()
                cach[ten[:3]] = v[doan_cua]
            m = ~np.isnan(that) & np.all([~np.isnan(v) for v in cach.values()], axis=0)
            w, th = dai[m], that[m]
            for ten, v in cach.items():
                v = np.clip(v[m], 0.1, 1)
                t = tong.setdefault((tam, ten), np.zeros(5))
                t += [(w * np.abs(v - th) * 100).sum(), w.sum(), (w * np.abs(1 / v - 1 / th)).sum(),
                      (w * (1 / v - 1 / th)).sum(), (w / th).sum()]
    print(f'{ngay} {tu}-{den} (lap luc p, f = p - 15): MAE r | sai thoi gian | lech thoi gian (am = doan nhanh hon)')
    for tam in (45, 60):
        print(f'  tam {tam}: ' + '   '.join(
            f'{ten} {t[0] / t[1]:.2f} | {100 * t[2] / t[4]:.2f}% | {100 * t[3] / t[4]:+.2f}%'
            for ten in ('ls', 'gbm', 'gwn') for t in [tong[(tam, ten)]]))


if __name__ == '__main__':
    main()
