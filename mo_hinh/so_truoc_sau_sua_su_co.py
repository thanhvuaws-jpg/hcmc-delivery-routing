"""
So dự báo TRƯỚC và SAU khi sửa lỗi rò rỉ ở đặc trưng sự cố (QĐ-029 mục 5), trên ĐÚNG CÙNG các ô (khung, đoạn) có nhãn.

Trước: hình học "dài nhất cả đời sự cố" cho mọi khung (biết trước hàng kẹt sẽ dài tới đâu).
Sau:   hình học của đúng lần ghi ở khung đó.
Cả hai cùng mốc cắt học 08/11 16:15, cùng tập kiểm tra từ 08/11 17:30. Tệp cũ cất ở ket_qua/cu_truoc_sua_su_co/ (GBM)
và hoc_sau/hcm_gwn_ho_so_them_che_2026-11-12_du_bao.parquet (Graph WaveNet che sự cố, dữ liệu tới 12/11 22:30).
Nhãn y lấy từ tệp GBM (r không đổi khi sửa, nên nhãn hai bên như nhau).

Nếu rò rỉ đã giúp mô hình thì MAE SAU phải TĂNG, nhất là từ 11/11 17:00 (lúc sự cố có dữ liệu lại).
Chỉ so các ô có giờ đích ≤ 12/11 22:30 (khung cuối dữ liệu của tệp Graph WaveNet cũ) = đúng tập ô đã báo số ở
QĐ-026/027. Các khung cuối của tệp cũ bị lỗi "thiếu hồ sơ ở giờ đích" (QĐ-029 mục 6), không liên quan rò rỉ.
Chạy:  python so_truoc_sau_sua_su_co.py
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

RA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ket_qua')
HS = os.path.join(RA, 'hoc_sau')
MOC_SU_CO = pd.Timestamp('2026-11-11 17:00')
CUOI_CU = pd.Timestamp('2026-11-12 22:30')      # khung cuối dữ liệu của lần train chính
TAM = ('15', '30', '60')


def nap(tep, ten, nhan=False):
    cot = ['khung', 'doan'] + [f'du_{h}' for h in TAM] + ([f'y_{h}' for h in TAM] if nhan else [])
    d = pd.read_parquet(tep, columns=cot)
    return d.rename(columns={f'du_{h}': f'{ten}_{h}' for h in TAM})


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    moi = sorted(glob.glob(os.path.join(RA, 'du_bao_gbm_ls_*.parquet')))[-1]
    gwn_moi = sorted(glob.glob(os.path.join(HS, 'hcm_gwn_ho_so_them_che_cat11081615_*_du_bao.parquet')))[-1]
    x = (nap(os.path.join(RA, 'cu_truoc_sua_su_co', 'du_bao_gbm_ls_2026-11-13.parquet'), 'gbm_cu', nhan=True)
         .merge(nap(moi, 'gbm_moi'), on=['khung', 'doan'])
         .merge(nap(os.path.join(HS, 'hcm_gwn_ho_so_them_che_2026-11-12_du_bao.parquet'), 'gwn_cu'), on=['khung', 'doan'])
         .merge(nap(gwn_moi, 'gwn_moi'), on=['khung', 'doan']))
    print(f'GBM moi: {os.path.basename(moi)} | GWN moi: {os.path.basename(gwn_moi)}')
    print(f'{len(x):,} o chung 4 tep, khung {x["khung"].min()} -> {x["khung"].max()}')
    ngay = x['khung'].dt.strftime('%m-%d')
    sau_moc = x['khung'] >= MOC_SU_CO
    for h in TAM:
        y = x[f'y_{h}']
        co = y.notna() & (x['khung'] + pd.Timedelta(minutes=int(h)) <= CUOI_CU)
        doi = (x[f'gbm_cu_{h}'] - x[f'gbm_moi_{h}']).abs() > 1e-6
        print(f'\n--- {h} phut ({co.sum():,} o co nhan; GBM doi du bao o {(doi & co).sum():,} o) ---')
        nhom = [('toan bo', co), ('truoc 11/11 17:00', co & ~sau_moc), ('tu 11/11 17:00', co & sau_moc),
                ('o GBM doi du bao', co & doi)] + [(f'ngay {n}', co & (ngay == n)) for n in sorted(ngay.unique())]
        print(f'{"nhom":<20}{"so o":>11} | {"GBM truoc":>9} {"sau":>7} {"chenh":>7} | {"GWN truoc":>9} {"sau":>7} {"chenh":>7}')
        for ten, m in nhom:
            if m.sum() == 0:
                continue
            k = {c: float(np.mean(np.abs(y[m] - x.loc[m, f'{c}_{h}']))) * 100 for c in ('gbm_cu', 'gbm_moi', 'gwn_cu', 'gwn_moi')}
            print(f'{ten:<20}{int(m.sum()):>11,} | {k["gbm_cu"]:>9.3f} {k["gbm_moi"]:>7.3f} {k["gbm_moi"] - k["gbm_cu"]:>+7.3f}'
                  f' | {k["gwn_cu"]:>9.3f} {k["gwn_moi"]:>7.3f} {k["gwn_moi"] - k["gwn_cu"]:>+7.3f}')


if __name__ == '__main__':
    main()
