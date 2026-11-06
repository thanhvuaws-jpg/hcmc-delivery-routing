"""
Mô hình dự báo có thật sự học được gì hay chỉ đoán mò? Ba phép thử trên CÙNG tập kiểm tra của moc_so_sanh.py.

  1. Đoán mò thật: luôn đoán r trung bình phần học; bốc ngẫu nhiên một giá trị r của phần học.
  2. Học trên nhãn XÁO TRỘN: cùng mô hình, cùng đặc trưng, nhưng nhãn học bị hoán vị ngẫu nhiên nên mọi quan hệ
     giữa đặc trưng và nhãn bị phá. Nếu đường ống tốt thì mô hình này KHÔNG được giỏi hơn "giữ nguyên"; nếu vẫn
     giỏi, nghĩa là điểm số đến từ cách chấm chứ không từ điều mô hình học được.
  3. Đoán đúng HƯỚNG khi đường đổi mạnh (|y − r| ≥ NGUONG_DOI điểm trong tầm dự báo): đây là lúc "giữ nguyên"
     vô dụng và là lúc cần mô hình nhất. Đoán mò thì khoảng 50%.

Học trên mẫu MAU_HOC dòng cho nhanh (số MAE có thể kém hơn chút so với moc_so_sanh.py, vốn học toàn bộ).
Không phát hiện được rò rỉ nhãn trong đặc trưng — phần đó kiểm riêng ở kiem_thu/test_moc_so_sanh.py và chia theo
thời gian có khoảng hở.

Chạy:  python kiem_doan_mo.py
Ra:    mo_hinh/ket_qua/kiem_doan_mo_<ngày cuối của dữ liệu>.json (không lên git — từ dữ liệu TomTom)
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from ho_so_lich_su import ho_so
from moc_so_sanh import KHOANG_HO, NHAN, TY_LE_HOC, VANG, RA, danh_gia, muc

MAU_HOC = 800_000
NGUONG_DOI = 0.15


def huong_dung(y, du, r):
    """Trong các ô đổi mạnh: tỉ lệ dự báo đi đúng hướng thay đổi thật so với r hiện tại."""
    doi = np.abs(y - r) >= NGUONG_DOI
    return float((np.sign(du[doi] - r[doi]) == np.sign(y[doi] - r[doi])).mean()), int(doi.sum())


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    d = pd.concat([pd.read_parquet(t) for t in sorted(glob.glob(os.path.join(VANG, '*.parquet')))], ignore_index=True)
    khung = np.sort(d['khung'].unique())
    cat = int(len(khung) * TY_LE_HOC)
    het_hoc, dau_kiem = khung[cat - 1], khung[min(cat + KHOANG_HO, len(khung) - 1)]
    hoc, kiem = d[d['khung'] <= het_hoc], d[d['khung'] >= dau_kiem]
    bo = {'khung', 'doan', *NHAN.values()}
    dac_trung = [c for c in d.columns if c not in bo and hoc[c].nunique(dropna=True) >= 2]
    doan = np.sort(d['doan'].unique())
    fi, ni = np.searchsorted(khung, d['khung'].to_numpy()), np.searchsorted(doan, d['doan'].to_numpy())
    R = np.full((len(khung), len(doan)), np.nan, dtype=np.float32)
    R[fi, ni] = d['r'].to_numpy()
    H = ho_so(R, pd.DatetimeIndex(khung), cat)
    del R
    print(f'{len(khung)} khung -> {khung[-1]}; hoc toi {het_hoc}, kiem tu {dau_kiem}', flush=True)
    rng = np.random.default_rng(42)
    r_hoc = hoc['r'].dropna().to_numpy()
    tb_hoc = float(r_hoc.mean())
    kq = {}

    def dac_trung_day_du(dong, buoc):
        X = dong[dac_trung].copy()
        X['loai'] = X['loai'].cat.codes
        vt = dong.index.to_numpy()
        dich = fi[vt] + buoc
        h_dich = np.where(dich < len(khung), H[np.minimum(dich, len(khung) - 1), ni[vt]], np.nan)
        X['r_ls_dich'] = h_dich
        X['ls_tru_r'] = h_dich - dong['r'].to_numpy()
        X['lech_ls'] = dong['r'].to_numpy() - H[fi[vt], ni[vt]]
        return X.astype(np.float32)

    for h, y_cot in NHAN.items():
        a = hoc[hoc[y_cot].notna() & hoc['r'].notna()]
        a = a.iloc[rng.choice(len(a), min(MAU_HOC, len(a)), replace=False)]
        b = kiem[kiem[y_cot].notna() & kiem['r'].notna()]
        X, Xb = dac_trung_day_du(a, int(h) // 15), dac_trung_day_du(b, int(h) // 15)
        dich_y = (a[y_cot] - a['r']).to_numpy()
        y, r, gio = b[y_cot].to_numpy(), b['r'].to_numpy(), b['khung'].dt.hour.to_numpy()

        def mo_hinh(nhan):
            m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=63, min_samples_leaf=200,
                                              l2_regularization=1.0, categorical_features=[dac_trung.index('loai')],
                                              random_state=42)
            return np.clip(r + m.fit(X, nhan).predict(Xb), 0, 1)

        cach = {'doan_mo_tb': np.full(len(y), tb_hoc), 'doan_mo_boc': rng.choice(r_hoc, len(y)), 'giu_nguyen': r,
                'hoc_nhan_xao': mo_hinh(rng.permutation(dich_y)), 'mo_hinh_that': mo_hinh(dich_y)}
        kq[h] = {}
        print(f'\n{h} phut ({len(y):,} o; doi manh {int((np.abs(y - r) >= NGUONG_DOI).sum()):,} o)')
        for ten, du in cach.items():
            g = danh_gia(y, du, r, gio)
            kq[h][ten] = {**g, 'huong_dung_khi_doi_manh': huong_dung(y, du, r)[0]}
            print(f'  {ten:<14} MAE {g["mae"]:6.2f} | dung 3 muc {g["dung_3_muc"]:6.1%} | F1 ket {g["f1_ket"]:.3f} | '
                  f'dung huong khi doi manh {kq[h][ten]["huong_dung_khi_doi_manh"]:6.1%}', flush=True)
    ngay = pd.Timestamp(khung[-1])
    with open(os.path.join(RA, f'kiem_doan_mo_{ngay:%Y-%m-%d}.json'), 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'({(time.time() - t0) / 60:.1f} phut)')


if __name__ == '__main__':
    main()
