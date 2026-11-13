"""
So GBM + hồ sơ với một mô hình học sâu đã train, trên CÙNG các ô của phần kiểm tra (QĐ-026, QĐ-027):
  1. so lại MAE từng mô hình — phải trùng số của lần train (moc_so_sanh.py, hoc_sau_hcm.py), lệch là có lỗi;
  2. TRUNG BÌNH hai dự báo, trọng số 0,5 CHỌN TRƯỚC (không dò trên tập kiểm tra — dò ở đây là nhìn đáp án);
  3. bootstrap theo khối (ngày, giờ) cho chênh MAE và F1 mức kẹt giữa hai mô hình: chênh có vượt nhiễu không.
     Khối (ngày, giờ) vì các ô cùng giờ cùng ngày sai cùng chiều (mưa, sự kiện); bootstrap từng ô sẽ cho khoảng
     tin cậy hẹp giả. Các giờ trong cùng một ngày vẫn còn phụ thuộc nhau -> khoảng thật có thể rộng hơn.

Cũng ghi dự báo GBM + hồ sơ của phần kiểm tra ra parquet để chấm tuyến dùng (danh_gia/cham_tuyen_that.py --du-bao).

Chạy:  python so_sanh_du_bao.py [ten_hoc_sau] [--lam-lai]
       ten_hoc_sau mặc định gwn_ho_so_them_che; cần hoc_sau/hcm_<ten>_<ngày>_du_bao.parquet
       (python hoc_sau_hcm.py ... --chi-du-bao). --lam-lai: train lại GBM dù đã có tệp dự báo.
Ra:    mo_hinh/ket_qua/du_bao_gbm_ls_<ngày cuối dữ liệu>.parquet, so_sanh_du_bao_<ngày>_<ten>.json
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from dac_trung import NHAN, BangHoc
from moc_so_sanh import RA, danh_gia, mae_theo_ngay, tao_gbm_chung

TRONG_SO_HOC_SAU = 0.5
SO_LAN_BOOT = 2000
NGUONG_KET = 0.4                # muc(): r < 0,4 là kẹt


def du_bao_gbm(tep, lam_lai):
    """Dự báo GBM + hồ sơ cho MỌI ô phần kiểm tra có r (kể cả ô chưa có nhãn — chấm tuyến cần), kèm nhãn."""
    if os.path.exists(tep) and not lam_lai:
        return pd.read_parquet(tep)
    bang = BangHoc()
    hoc, kiem = bang.hoc, bang.kiem
    b = kiem[kiem['r'].notna()]
    ra = pd.DataFrame({'khung': b['khung'].to_numpy(), 'doan': b['doan'].to_numpy(), 'r': b['r'].to_numpy()})
    for h, y in NHAN.items():
        t = time.time()
        a = bang.nhan(hoc, y)
        m = tao_gbm_chung(bang.dac_trung.index('loai'))       # đúng như gbm_ls của moc_so_sanh (random_state 42)
        m.fit(bang.X(a, int(h)), (a[y] - a['r']).to_numpy())
        ra[f'du_{h}'] = np.clip(b['r'].to_numpy() + m.predict(bang.X(b, int(h))), 0, 1).astype(np.float32)
        ra[y] = b[y].to_numpy()
        print(f'GBM + ho so {h} phut: {time.time() - t:.0f}s', flush=True)
    ra.to_parquet(tep, index=False)
    return ra


def khoi_dem(khoi, y, du):
    """Theo khối: Σ|sai|, số ô, TP, FP, FN của mức kẹt — đủ để tính lại MAE và F1 kẹt cho mọi mẫu bootstrap."""
    kt, kd = y < NGUONG_KET, du < NGUONG_KET
    return np.stack([np.bincount(khoi, w, minlength=khoi.max() + 1) for w in
                     (np.abs(y - du) * 100, np.ones_like(y), (kt & kd).astype(float), (~kt & kd).astype(float),
                      (kt & ~kd).astype(float))])


def chi_so(tong):
    """tong (5, ...) -> MAE, F1 kẹt."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return tong[0] / tong[1], 2 * tong[2] / (2 * tong[2] + tong[3] + tong[4])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    thong_so = [a for a in sys.argv[1:] if not a.startswith('--')]
    ten = thong_so[0] if thong_so else 'gwn_ho_so_them_che'
    tep_hs = sorted(glob.glob(os.path.join(RA, 'hoc_sau', f'hcm_{ten}_*_du_bao.parquet')))
    if not tep_hs:
        sys.exit(f'chua co du bao cua {ten}: chay hoc_sau_hcm.py ... --chi-du-bao')
    tep_hs = tep_hs[-1]
    ngay = os.path.basename(tep_hs)[len(f'hcm_{ten}_'):][:10]
    g = du_bao_gbm(os.path.join(RA, f'du_bao_gbm_ls_{ngay}.parquet'), '--lam-lai' in sys.argv)
    s = pd.read_parquet(tep_hs, columns=['khung', 'doan', 'du_15', 'du_30', 'du_60'])
    d = g.merge(s, on=['khung', 'doan'], suffixes=('_gbm', '_hs'))
    print(f'{len(g):,} o GBM, {len(s):,} o hoc sau, chung {len(d):,}; hoc sau: {os.path.basename(tep_hs)}')

    rng = np.random.default_rng(42)
    kq = {'hoc_sau': ten, 'trong_so_hoc_sau': TRONG_SO_HOC_SAU, 'so_lan_boot': SO_LAN_BOOT, 'ket_qua': {}}
    for h, y in NHAN.items():
        m = d[y].notna()
        x = d[m]
        yt, r = x[y].to_numpy(np.float64), x['r'].to_numpy(np.float64)
        du = {'gbm_ls': x[f'du_{h}_gbm'].to_numpy(np.float64), ten: x[f'du_{h}_hs'].to_numpy(np.float64)}
        du['trung_binh'] = (1 - TRONG_SO_HOC_SAU) * du['gbm_ls'] + TRONG_SO_HOC_SAU * du[ten]
        gio = x['khung'].dt.hour.to_numpy()
        ngay_o = x['khung'].dt.strftime('%Y-%m-%d').to_numpy()
        kq_h = {k: danh_gia(yt, v, r, gio) for k, v in du.items()}
        kq_h['mae_theo_ngay'] = {k: mae_theo_ngay(yt, v, ngay_o) for k, v in du.items()}

        # Bootstrap theo khối (ngày, giờ).
        khoi = pd.factorize(x['khung'].dt.strftime('%Y-%m-%d %H'))[0]
        nk = khoi.max() + 1
        dem = {k: khoi_dem(khoi, yt, v) for k, v in du.items()}
        chon = rng.integers(0, nk, size=(SO_LAN_BOOT, nk))
        w = np.zeros((SO_LAN_BOOT, nk))
        np.add.at(w, (np.repeat(np.arange(SO_LAN_BOOT), nk), chon.ravel()), 1)
        mau = {k: chi_so(c @ w.T) for k, c in dem.items()}          # (MAE, F1) mỗi cái (SO_LAN_BOOT,)
        boot = {}
        for k in (ten, 'trung_binh'):
            for j, cs in enumerate(('mae', 'f1_ket')):
                chenh = mau[k][j] - mau['gbm_ls'][j]
                diem = chi_so(dem[k].sum(1))[j] - chi_so(dem['gbm_ls'].sum(1))[j]
                boot[f'{k}_tru_gbm_{cs}'] = {'diem': round(float(diem), 4),
                                             'ci95': [round(float(np.percentile(chenh, 2.5)), 4),
                                                      round(float(np.percentile(chenh, 97.5)), 4)],
                                             'ty_le_duong': round(float((chenh > 0).mean()), 4)}
        kq_h['bootstrap'] = boot
        kq_h['so_khoi'] = int(nk)
        kq['ket_qua'][h] = kq_h
        print(f'\n{h} phut ({len(x):,} o, {nk} khoi ngay x gio):')
        for k in du:
            v = kq_h[k]
            print(f'  {k:<20} MAE {v["mae"]:.3f} | RMSE {v["rmse"]:.3f} | F1 ket {v["f1_ket"]:.4f} | '
                  f'theo ngay {kq_h["mae_theo_ngay"][k]}')
        for k, v in boot.items():
            print(f'  {k:<32} {v["diem"]:+.4f}  CI95 [{v["ci95"][0]:+.4f}, {v["ci95"][1]:+.4f}]  '
                  f'P(>0) {v["ty_le_duong"]:.3f}')

    tep = os.path.join(RA, f'so_sanh_du_bao_{ngay}_{ten}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'\n-> {tep} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
