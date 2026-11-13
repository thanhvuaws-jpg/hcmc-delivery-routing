"""
Phép thử D11 Kaggle (ĐH Bách Khoa TP.HCM, 07/2020–04/2021) cho dự báo (QĐ-029): có giúp GBM + hồ sơ không?

D11 rất thưa: 2.044/7.394 đoạn có nhãn LOS, trung vị 4 mẫu mỗi đoạn trong 10 tháng, mỗi (đoạn, ô 30 phút) trung vị 1 mẫu
-> không dựng được hồ sơ theo giờ hay tiền huấn luyện. Thử cách duy nhất còn lại: đặc trưng TĨNH mỗi đoạn
  kg_los_tb   mức LOS trung bình (0 = A thông .. 5 = F kẹt) mọi lúc
  kg_los_cd   mức LOS trung bình giờ cao điểm (6–9h, 16–19h)
  kg_n        số mẫu (để mô hình biết số trên dựa vào bao nhiêu mẫu)
chỉ dùng dòng không bị gắn cờ (co = 0: không COVID/Tết, không nhập hàng loạt). Đoạn không có -> NaN.
So với GBM + hồ sơ hiện tại (du_bao_gbm_ls_*.parquet, cùng chia, cùng hạt ngẫu nhiên) ở 30 và 60 phút: toàn bộ và riêng
các đoạn có dữ liệu Kaggle.
Chạy:  python thu_kaggle.py
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

from dac_trung import GOC, BangHoc
from moc_so_sanh import RA, danh_gia, tao_gbm_chung


def dac_trung_kaggle():
    bac = os.path.join(GOC, 'du_lieu', 'bac')
    kc = pd.read_parquet(os.path.join(bac, 'kaggle_canh.parquet'))
    cd = pd.read_parquet(os.path.join(bac, 'canh_doan.parquet'), columns=['chi_so', 'doan'])
    seg = kc.merge(cd, on='chi_so').groupby('segment_id')['doan'].agg(lambda s: s.mode().iat[0])
    los = pd.read_parquet(os.path.join(bac, 'kaggle_los.parquet'))
    los = los[los['co'] == 0].join(seg, on='segment_id').dropna(subset=['doan'])
    gio = los['khung'].dt.hour
    cd_ = los[gio.between(6, 8) | gio.between(16, 18)]
    return pd.DataFrame({'kg_los_tb': los.groupby('doan')['los_so'].mean(),
                         'kg_los_cd': cd_.groupby('doan')['los_so'].mean(),
                         'kg_n': los.groupby('doan').size()}).astype(np.float32)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    kg = dac_trung_kaggle()
    bang = BangHoc()
    d = bang.d
    for c in kg.columns:
        d[c] = d['doan'].map(kg[c]).astype(np.float32)
    bang.kiem = d[d['khung'] >= bang.dau_kiem]
    bang.dat_bo_dau(0.0)
    co_kg = d['kg_n'].notna()
    print(f'{kg.shape[0]} doan co Kaggle (sach); dong co Kaggle: hoc {co_kg[bang.hoc.index].mean():.1%}, '
          f'kiem {co_kg[bang.kiem.index].mean():.1%}; dac trung {len(bang.dac_trung)}', flush=True)
    goc = pd.read_parquet(sorted(glob.glob(os.path.join(RA, 'du_bao_gbm_ls_2026-11-12.parquet')))[0],
                          columns=['khung', 'doan', 'du_30', 'du_60'])
    for h in ('30', '60'):
        y = f'y_{h}'
        a, b = bang.nhan(bang.hoc, y), bang.nhan(bang.kiem, y)
        m = tao_gbm_chung(bang.dac_trung.index('loai'))
        m.fit(bang.X(a, int(h)), (a[y] - a['r']).to_numpy())
        du = np.clip(b['r'].to_numpy() + m.predict(bang.X(b, int(h))), 0, 1)
        x = b[['khung', 'doan', y, 'r', 'kg_n']].assign(du_kg=du).merge(goc, on=['khung', 'doan'])
        gio = x['khung'].dt.hour.to_numpy()
        for ten, mask in (('toan bo', np.ones(len(x), bool)), ('doan co Kaggle', x['kg_n'].notna().to_numpy())):
            g = x[mask]
            k0 = danh_gia(g[y].to_numpy(), g[f'du_{h}'].to_numpy(), g['r'].to_numpy(), gio[mask])
            k1 = danh_gia(g[y].to_numpy(), g['du_kg'].to_numpy(), g['r'].to_numpy(), gio[mask])
            print(f'{h} phut {ten:<15} ({len(g):,} o): MAE {k0["mae"]:.3f} -> co Kaggle {k1["mae"]:.3f} '
                  f'({100 * (k1["mae"] / k0["mae"] - 1):+.2f}%) | F1 ket {k0["f1_ket"]:.3f} -> {k1["f1_ket"]:.3f}', flush=True)
    print(f'({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
