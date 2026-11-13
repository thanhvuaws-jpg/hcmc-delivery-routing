"""
Vá điểm yếu dự báo 60 phút (QĐ-032): thử đổi ĐÍCH HỌC và HÀM MẤT MÁT của GBM + hồ sơ, chọn trong phần học rồi chấm MỘT lần.

  V0  bình phương, học y − r                (như moc_so_sanh / du_bao_moi hiện tại)
  V1  tuyệt đối,   học y − r
  V2  bình phương, học y − H(giờ đích)      (H: hồ sơ ngày thường / cuối tuần; ô chưa có hồ sơ -> r)
  V3  tuyệt đối,   học y − H(giờ đích)

Bước 1 CHỌN: học tới MOC_CHON (05/11 16:15; hồ sơ, tình trạng chung cũng chỉ tới đó), kiểm định trên các khung sau đó mà nhãn
  còn ≤ HET_HOC (08/11 16:15) — không chạm tập kiểm tra. Mỗi tầm: biến thể MAE kiểm định thấp nhất, không thấp hơn V0 ≥ 1% thì V0.
Bước 2 CHẤM: học tới HET_HOC như lần train chính, ô có nhãn ≤ CUOI_CU (12/11 22:30). V0 phải ra đúng số sau khi sửa sự cố
  (5,475 / 6,167 / 6,292 — QĐ-029 mục 5). Báo V0 và biến thể chọn: MAE, so với lịch sử theo thứ / hồ sơ, từng ngày, F1 kẹt.

Chạy:  python thu_dich_mat_mat.py          (~1 giờ; cần ~6 GB RAM trống)
Ra:    mo_hinh/ket_qua/thu_dich_mat_mat_<ngày giờ>.json
"""
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from dac_trung import GOC, NHAN, BangHoc
from moc_so_sanh import LichSu, danh_gia, mae_theo_ngay

RA = os.path.join(GOC, 'mo_hinh', 'ket_qua')
MOC_CHON = '2026-11-05 16:15'
HET_HOC = '2026-11-08 16:15'             # mốc cắt lần train chính (du_bao_moi.HET_HOC)
CUOI_CU = pd.Timestamp('2026-11-12 22:30')
V0_DA_BAO = {'15': 5.475, '30': 6.167, '60': 6.292}
BIEN_THE = {'V0': ('squared_error', 'r'), 'V1': ('absolute_error', 'r'),
            'V2': ('squared_error', 'ho_so'), 'V3': ('absolute_error', 'ho_so')}
NGUONG_CHON = 0.01


def tao_gbm(loss, cot_loai):
    # Như moc_so_sanh.tao_gbm_chung, chỉ thêm loss.
    return HistGradientBoostingRegressor(loss=loss, max_iter=400, learning_rate=0.05, max_leaf_nodes=63, min_samples_leaf=200,
                                         l2_regularization=1.0, categorical_features=[cot_loai], random_state=42)


def du_bao_cac_bien_the(bang, h, a, b, ten_cac):
    """Học trên dòng a, dự báo dòng b cho các biến thể; trả {tên: r dự báo}, cùng gốc hồ sơ của b."""
    y = NHAN[h]
    Xa, Xb = bang.X(a, int(h)), bang.X(b, int(h))
    goc = {'r': (a['r'].to_numpy(), b['r'].to_numpy())}
    goc['ho_so'] = tuple(np.where(np.isnan(X['r_ls_dich'].to_numpy()), d['r'].to_numpy(), X['r_ls_dich'].to_numpy())
                         for X, d in ((Xa, a), (Xb, b)))
    ra = {}
    for ten in ten_cac:
        loss, g = BIEN_THE[ten]
        t = time.time()
        m = tao_gbm(loss, bang.dac_trung.index('loai'))
        m.fit(Xa, a[y].to_numpy() - goc[g][0])
        ra[ten] = np.clip(goc[g][1] + m.predict(Xb), 0, 1)
        print(f'  {h} phut {ten} ({loss}, goc {g}): {m.n_iter_} vong, {time.time() - t:.0f}s', flush=True)
        del m
    return ra, goc['ho_so'][1]


def buoc_chon():
    bang = BangHoc(het_hoc=MOC_CHON)
    print(f'CHON: hoc {bang.dau_hoc} -> {bang.het_hoc}; kiem dinh tu {bang.dau_kiem}, nhan <= {HET_HOC}', flush=True)
    chon, bang_kq = {}, {}
    for h, y in NHAN.items():
        a = bang.nhan(bang.hoc, y)
        b = bang.nhan(bang.kiem, y)
        b = b[b['khung'] + pd.Timedelta(minutes=int(h)) <= pd.Timestamp(HET_HOC)]
        du, _ = du_bao_cac_bien_the(bang, h, a, b, list(BIEN_THE))
        yt = b[y].to_numpy()
        mae = {k: float(np.abs(yt - v).mean() * 100) for k, v in du.items()}
        tot = min(mae, key=mae.get)
        chon[h] = tot if mae[tot] <= (1 - NGUONG_CHON) * mae['V0'] else 'V0'
        bang_kq[h] = {'n': int(len(b)), 'mae': mae}
        print(f'{h:>2} phut kiem dinh ({len(b):,} o): ' + ', '.join(f'{k} {v:.3f}' for k, v in mae.items())
              + f' -> chon {chon[h]}', flush=True)
        del a, b, du
        gc.collect()
    del bang
    gc.collect()
    return chon, bang_kq


def buoc_cham(chon):
    bang = BangHoc(het_hoc=HET_HOC)
    print(f'\nCHAM: hoc {bang.dau_hoc} -> {bang.het_hoc}; kiem tu {bang.dau_kiem}, nhan <= {CUOI_CU}', flush=True)
    lich_su = LichSu(bang.hoc)
    kq = {}
    for h, y in NHAN.items():
        a = bang.nhan(bang.hoc, y)
        b = bang.nhan(bang.kiem, y)
        b = b[b['khung'] + pd.Timedelta(minutes=int(h)) <= CUOI_CU]
        ten_cac = list(dict.fromkeys(['V0', chon[h]]))
        du, hs = du_bao_cac_bien_the(bang, h, a, b, ten_cac)
        yt, r = b[y].to_numpy(), b['r'].to_numpy()
        gio = b['khung'].dt.hour.to_numpy()
        ngay = b['khung'].dt.strftime('%Y-%m-%d').to_numpy()
        ls, _ = lich_su.du_bao(b, int(h))
        g = {'n': int(len(b)), 'lich_su': danh_gia(yt, ls, r, gio), 'ho_so': danh_gia(yt, hs, r, gio),
             'theo_ngay': {'lich_su': mae_theo_ngay(yt, ls, ngay), 'ho_so': mae_theo_ngay(yt, hs, ngay)}}
        for ten, v in du.items():
            g[ten] = danh_gia(yt, v, r, gio)
            g['theo_ngay'][ten] = mae_theo_ngay(yt, v, ngay)
        kq[h] = g
        lech_v0 = abs(g['V0']['mae'] - V0_DA_BAO[h])
        print(f'{h:>2} phut ({len(b):,} o): lich su {g["lich_su"]["mae"]:.3f} | ho so {g["ho_so"]["mae"]:.3f} | V0 {g["V0"]["mae"]:.3f}'
              f' (da bao {V0_DA_BAO[h]}, lech {lech_v0:.3f}{" <- KHONG KHOP" if lech_v0 > 0.002 else ""})', flush=True)
        for ten in du:
            x = g[ten]
            print(f'    {ten}: MAE {x["mae"]:.3f} | thap hon lich su {100 * (1 - x["mae"] / g["lich_su"]["mae"]):.1f}% | '
                  f'thap hon ho so {100 * (1 - x["mae"] / g["ho_so"]["mae"]):.1f}% | F1 ket {x["f1_ket"]:.3f} | '
                  f'theo ngay {g["theo_ngay"][ten]}', flush=True)
        print(f'    ho so theo ngay {g["theo_ngay"]["ho_so"]} | F1 ket ho so {g["ho_so"]["f1_ket"]:.3f}', flush=True)
        del a, b, du
        gc.collect()
    return kq


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    chon, kiem_dinh = buoc_chon()
    print(f'\nCHON (dang ky truoc, QD-032): {chon}', flush=True)
    cham = buoc_cham(chon)
    os.makedirs(RA, exist_ok=True)
    tep = os.path.join(RA, f'thu_dich_mat_mat_{time.strftime("%Y-%m-%d_%H%M")}.json')
    json.dump({'moc_chon': MOC_CHON, 'het_hoc': HET_HOC, 'cuoi': str(CUOI_CU), 'chon': chon, 'kiem_dinh': kiem_dinh,
               'cham': cham}, open(tep, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'-> {tep} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
