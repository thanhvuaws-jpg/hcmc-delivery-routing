"""
Dự báo theo ĐOẠN (15 phút) đem xuống từng CẠNH cho bộ định tuyến thì đúng tới đâu? (QĐ-027)

Chấm lần đầu 09/11 (cham_tuyen_that.py --du-bao=gbm_ls): F chậm hơn C 0,47%, giờ đến đoán kém hơn — dù dự báo đoạn
đúng hơn giữ nguyên 13–24%. Script này đo thẳng ở mức cạnh: với mỗi lúc đi τ, so r dự báo từng khe sau τ với r THẬT
(TB điều hòa các lần chụp trong khe), trên cạnh có số đo lúc τ, thuộc đoạn có dự báo, có số đo trong khe.

Cách đem xuống cạnh (r_τ = lần chụp mới nhất của cạnh, r_f = r của đoạn ở khung 15 phút vừa xong):
  giu      r_τ                                   (C/D đang dùng)
  cong     r_τ + (dự báo − r_f)                  (bản đầu của F/G)
  muc      dự báo của đoạn                        (bỏ chi tiết từng cạnh)
  nua      r_τ + 0,5 × (dự báo − r_f)
Hai cách canh giờ:
  τ = f + 15 phút  (như chấm tuyến: lần chụp τ thuộc khung SAU, GBM chưa thấy -> lệch 5 phút thông tin)
  τ = f + 10 phút  (lần chụp τ là lần cuối của khung f: GBM và giữ nguyên cùng biết như nhau; khe dự báo lùi 5 phút)
Thước đo, trọng số chiều dài: MAE r (điểm %) và sai thời gian tương đối Σ dài·|1/r_dự − 1/r_thật| / Σ dài/r_thật.

Mặc định chạy tối 08/11 (thuộc tập kiểm tra nhưng KHÔNG nằm trong 4 ngày chấm tuyến 09–12/11) để chọn cách mà
không nhìn ngày đem chấm.
Chạy:  python kiem_du_bao_canh.py [2026-11-08] [17:45] [22:00]
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

from cham_tuyen_that import GOC, nap_du_bao, nap_quan_sat


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    ngay, tu, den = (a + ['2026-11-08', '17:45', '22:00'][len(a):])[:3]
    khung, R, _, _ = nap_quan_sat(ngay, '00:00', '23:59')
    du_bao, tep = nap_du_bao('gbm_ls', ngay)
    canh = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'canh_doan.parquet'), columns=['chi_so', 'doan'])
    doan_cua = canh.sort_values('chi_so')['doan'].to_numpy()
    dai = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['dai'])['dai'].to_numpy()
    print(f'{ngay} {tu}-{den}; {os.path.basename(tep)}')
    tong = {}
    for lech_phut in (15, 10):
        for f in pd.date_range(f'{ngay} {tu}', f'{ngay} {den}', freq='15min') - pd.Timedelta(minutes=15):
            x = du_bao[du_bao['khung'] == f]
            tau = f + pd.Timedelta(minutes=lech_phut)
            k = np.flatnonzero(khung <= tau)
            if x.empty or not len(k) or khung[k[-1]] != tau:
                continue
            r_tau = R[k[-1]]
            r_f = np.full(int(doan_cua.max()) + 1, np.nan, np.float32)
            r_f[x['doan'].to_numpy()] = x['r'].to_numpy()
            r_f = r_f[doan_cua]
            for j, p in enumerate(('du_15', 'du_30', 'du_45', 'du_60')):
                # Khung đích của du_p bắt đầu ở f + p; khe tính từ đó (với τ = f + 15 trùng khe j của chấm tuyến).
                a_, b_ = f + pd.Timedelta(minutes=15 * (j + 1)), f + pd.Timedelta(minutes=15 * (j + 2))
                kk = np.flatnonzero((khung >= a_) & (khung < b_))
                if not len(kk):
                    continue
                with np.errstate(divide='ignore', invalid='ignore'), warnings.catch_warnings():
                    warnings.simplefilter('ignore', RuntimeWarning)
                    that = 1 / np.nanmean(1 / R[kk], axis=0)
                du = np.full(int(doan_cua.max()) + 1, np.nan, np.float32)
                du[x['doan'].to_numpy()] = x[p].to_numpy()
                du = du[doan_cua]
                m = ~np.isnan(r_tau) & ~np.isnan(du) & ~np.isnan(that) & ~np.isnan(r_f)
                cach = {'giu': r_tau, 'cong': r_tau + (du - r_f), 'muc': du, 'nua': r_tau + 0.5 * (du - r_f)}
                w = dai[m]
                for ten, v in cach.items():
                    v = np.clip(v[m], 0.1, 1)
                    t = tong.setdefault((lech_phut, p, ten), np.zeros(4))
                    t += [(w * np.abs(v - that[m]) * 100).sum(), w.sum(),
                          (w * np.abs(1 / v - 1 / that[m])).sum(), (w / that[m]).sum()]
    for lech_phut in (15, 10):
        print(f'\ntau = f + {lech_phut} phut  (MAE r diem % | sai thoi gian tuong doi %)')
        for p in ('du_15', 'du_30', 'du_45', 'du_60'):
            o = []
            for ten in ('giu', 'cong', 'muc', 'nua'):
                t = tong.get((lech_phut, p, ten))
                if t is not None:
                    o.append(f'{ten} {t[0] / t[1]:.2f} | {100 * t[2] / t[3]:.2f}')
            print(f'  {p}: ' + '   '.join(o))


if __name__ == '__main__':
    main()
