"""
Mốc so sánh cho dự báo kẹt xe 15/30/60 phút trên tầng vàng (du_lieu/vang/).

So 3 cách, cùng một tập kiểm tra chia THEO THỜI GIAN (KE_HOACH_DU_LIEU mục 8):
  giu_nguyen   y(t+h) = r(t)                         — mốc ngây thơ, mô hình nào cũng phải thắng
  tb_1h        y(t+h) = TB r của 1 giờ gần nhất
  gbm          HistGradientBoosting (scikit-learn) học PHẦN THAY ĐỔI y − r từ mọi đặc trưng tầng vàng
Chia: 70% khung thời gian đầu để học, chừa KHOẢNG_HO khung, phần sau để kiểm tra (nhãn 60 phút
của khung học cuối không được rơi vào thời gian kiểm tra).

Thước đo: MAE (điểm %, r × 100) — toàn bộ, ban ngày 6–22h, và khi ĐANG đông/kẹt (r < 0,75);
độ đúng 3 mức thông/đông/kẹt.
Kết quả ghi mo_hinh/ket_qua/moc_<ngày chạy>.json — dữ liệu ít ngày thì số chỉ để kiểm đường ống.

Chạy:  python moc_so_sanh.py
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VANG = os.path.join(GOC, 'du_lieu', 'vang')
RA = os.path.join(GOC, 'mo_hinh', 'ket_qua')
TY_LE_HOC = 0.7
KHOANG_HO = 4                   # 4 khung = 60 phút
NHAN = {'15': 'y_15', '30': 'y_30', '60': 'y_60'}


def muc(r):
    return np.select([r < 0.4, r < 0.75], [0, 1], 2)


def danh_gia(y, du, r_hien_tai, gio):
    e = np.abs(y - du) * 100
    ban_ngay = (gio >= 6) & (gio < 22)
    dong = r_hien_tai < 0.75
    return {'mae': round(float(e.mean()), 3),
            'mae_ban_ngay': round(float(e[ban_ngay].mean()), 3) if ban_ngay.any() else None,
            'mae_dang_dong_ket': round(float(e[dong].mean()), 3) if dong.any() else None,
            'dung_3_muc': round(float((muc(y) == muc(du)).mean()), 4), 'n': int(len(y))}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    d = pd.concat([pd.read_parquet(t) for t in sorted(glob.glob(os.path.join(VANG, '*.parquet')))],
                  ignore_index=True)
    khung = np.sort(d['khung'].unique())
    cat = int(len(khung) * TY_LE_HOC)
    het_hoc, dau_kiem = khung[cat - 1], khung[min(cat + KHOANG_HO, len(khung) - 1)]
    hoc, kiem = d[d['khung'] <= het_hoc], d[d['khung'] >= dau_kiem]
    bo = {'khung', 'doan', *NHAN.values()}
    # Cột chưa có ít nhất 2 giá trị trong phần học (vd r_hom_qua khi chưa đủ 1 ngày) thì bỏ —
    # scikit-learn không chia khoảng được, và cột đó cũng chưa có gì để học.
    bo_vi_trong = [c for c in d.columns if c not in bo and hoc[c].nunique(dropna=True) < 2]
    dac_trung = [c for c in d.columns if c not in bo and c not in bo_vi_trong]
    if bo_vi_trong:
        print('bo cot chua co du lieu de hoc:', bo_vi_trong)
    print(f'{len(d):,} dong, {len(khung)} khung ({khung[0]} -> {khung[-1]})')
    print(f'hoc: {len(hoc):,} dong toi {het_hoc} | kiem: {len(kiem):,} dong tu {dau_kiem} | {len(dac_trung)} dac trung')

    kq = {'tao_luc': time.strftime('%Y-%m-%d %H:%M:%S'), 'hoc_toi': str(het_hoc), 'kiem_tu': str(dau_kiem),
          'so_dong_hoc': len(hoc), 'so_dong_kiem': len(kiem), 'dac_trung': dac_trung, 'ket_qua': {}}
    for h, y in NHAN.items():
        a = hoc[hoc[y].notna() & hoc['r'].notna()]
        b = kiem[kiem[y].notna() & kiem['r'].notna()]
        X = a[dac_trung].copy()
        Xb = b[dac_trung].copy()
        for X_ in (X, Xb):
            X_['loai'] = X_['loai'].cat.codes
        m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=63,
                                          min_samples_leaf=200, l2_regularization=1.0,
                                          categorical_features=[dac_trung.index('loai')], random_state=42)
        m.fit(X.astype(np.float32), (a[y] - a['r']).to_numpy())
        du = np.clip(b['r'].to_numpy() + m.predict(Xb.astype(np.float32)), 0, 1)
        gio = b['khung'].dt.hour.to_numpy()
        yt, r = b[y].to_numpy(), b['r'].to_numpy()
        kq['ket_qua'][h] = {
            'giu_nguyen': danh_gia(yt, r, r, gio),
            'tb_1h': danh_gia(yt, b['r_tb_1h'].fillna(b['r']).to_numpy(), r, gio),
            'gbm': danh_gia(yt, du, r, gio)}
        g = kq['ket_qua'][h]
        print(f'{h:>2} phut | MAE giu nguyen {g["giu_nguyen"]["mae"]:.2f} | TB 1h {g["tb_1h"]["mae"]:.2f} | '
              f'GBM {g["gbm"]["mae"]:.2f}  (ban ngay {g["giu_nguyen"]["mae_ban_ngay"]:.2f} -> {g["gbm"]["mae_ban_ngay"]:.2f}; '
              f'dang dong/ket {g["giu_nguyen"]["mae_dang_dong_ket"]:.2f} -> {g["gbm"]["mae_dang_dong_ket"]:.2f}; '
              f'dung 3 muc {g["giu_nguyen"]["dung_3_muc"]:.1%} -> {g["gbm"]["dung_3_muc"]:.1%})')

    os.makedirs(RA, exist_ok=True)
    tep = os.path.join(RA, f'moc_{time.strftime("%Y-%m-%d_%H%M")}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'-> {tep} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
