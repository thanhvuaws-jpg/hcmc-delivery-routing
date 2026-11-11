"""
Ablation — sự cố và thời tiết giúp dự báo tốt hơn bao nhiêu? (câu hỏi 3 của đề tài, KE_HOACH tuần 6)

Cùng mô hình GBM + hồ sơ (moc_so_sanh.gbm_ls), cùng mẫu học, cùng tập kiểm tra; mỗi lần bỏ một nhóm đặc trưng
(dac_trung.NHOM) rồi đo MAE tăng bao nhiêu. Tăng nhiều = nhóm đó đóng góp nhiều; tăng ≈ 0 = bỏ đi cũng vậy.

Sự cố và mưa chỉ xảy ra ở một phần nhỏ dữ liệu nên MAE toàn bộ gần như không đổi dù chúng có ích đúng lúc cần. Vì
vậy đo thêm trên đúng các ô liên quan:
  co_du_lieu_su_co  khung có lần chụp sự cố (đọc đóng góp nhóm sự cố trên tập này, khung thiếu là NaN);
  co_su_co   đoạn đang có sự cố ở khung t;
  co_mua     dự báo mưa giờ kế ≥ 1 mm ở khung t;
  doi_manh   đường thực sự đổi ≥ 15 điểm trong tầm dự báo (lúc khó nhất).
MAE theo từng ngày kiểm tra để xem chênh lệch có lặp lại ngày nào cũng vậy không, hay chỉ do một ngày.

Chạy:  python ablation.py
Ra:    mo_hinh/ket_qua/ablation_<ngày cuối của dữ liệu>.json (không lên git — từ dữ liệu TomTom)
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from dac_trung import NHAN, NHOM, BangHoc
from moc_so_sanh import RA, mae_theo_ngay, tao_gbm_chung

MAU_HOC = 800_000
BIEN_THE = {'du': (), 'bo_su_co': ('su_co',), 'bo_thoi_tiet': ('thoi_tiet',), 'bo_su_co_thoi_tiet': ('su_co', 'thoi_tiet'),
            'bo_lan_can': ('lan_can',), 'bo_ho_so': ('ho_so',), 'bo_chung': ('chung',)}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bang = BangHoc()
    print(f'{len(bang.khung)} khung -> {bang.khung[-1]}; hoc toi {bang.het_hoc}, kiem tu {bang.dau_kiem}', flush=True)
    rng = np.random.default_rng(42)
    kq = {}
    for h, y_cot in NHAN.items():
        a, b = bang.nhan(bang.hoc, y_cot), bang.nhan(bang.kiem, y_cot)
        a = a.iloc[rng.choice(len(a), min(MAU_HOC, len(a)), replace=False)]
        X, Xb = bang.X(a, int(h)), bang.X(b, int(h))
        dich_y = (a[y_cot] - a['r']).to_numpy()
        y, r = b[y_cot].to_numpy(), b['r'].to_numpy()
        ngay = b['khung'].dt.strftime('%Y-%m-%d').to_numpy()
        # co_du_lieu_su_co: khung CÓ lần chụp sự cố (vang.py ghi NaN cho khung thiếu, vd 09/11 23:30 → 11/11 16:45
        # TomTom từ chối vì hết credit). Đóng góp của nhóm sự cố phải đọc trên tập này, không trên toan_bo.
        tap = {'toan_bo': np.ones(len(y), bool), 'ban_ngay': ((b['khung'].dt.hour >= 6) & (b['khung'].dt.hour < 22)).to_numpy(),
               'co_du_lieu_su_co': b['su_co'].notna().to_numpy(),
               'co_su_co': (b['su_co'] > 0).to_numpy(), 'co_mua': (b['mua_db_1'] >= 1).to_numpy(), 'doi_manh': np.abs(y - r) >= 0.15}
        print(f'\n{h} phut: {len(y):,} o; ' + ', '.join(f'{k} {v.mean():.1%}' for k, v in tap.items() if k != 'toan_bo'), flush=True)
        kq[h] = {'ty_le_tap': {k: float(v.mean()) for k, v in tap.items()}}
        goc = None
        for ten, nhom in BIEN_THE.items():
            bo = {c for n in nhom for c in NHOM[n]}
            giu = [c for c in X.columns if c not in bo]
            cot_loai = giu.index('loai')
            du = np.clip(r + tao_gbm_chung(cot_loai).fit(X[giu], dich_y).predict(Xb[giu]), 0, 1)
            e = np.abs(y - du) * 100
            mae = {k: float(e[v].mean()) if v.any() else None for k, v in tap.items()}
            if goc is None:
                goc = (mae, e)
            theo_ngay = mae_theo_ngay(y, du, ngay)
            kq[h][ten] = {'mae': mae, 'theo_ngay': theo_ngay}
            print(f'  {ten:<20}' + ' | '.join(f'{k} {v:6.3f} ({v - goc[0][k]:+.3f})' for k, v in mae.items() if v is not None), flush=True)
    with open(os.path.join(RA, f'ablation_{pd.Timestamp(bang.khung[-1]):%Y-%m-%d}.json'), 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'({(time.time() - t0) / 60:.1f} phut)')


if __name__ == '__main__':
    main()
