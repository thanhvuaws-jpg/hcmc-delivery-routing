"""
Tổng hợp chấm tuyến LẬP TRƯỚC (cham_tuyen_dat_truoc.py, QĐ-028) qua các ngày, CI 95% bootstrap theo cặp điểm:
  - thời gian thật của tuyến tối ưu (t_) theo từng cách biết so với giu (giữ nguyên lúc lập) và ls (hồ sơ lịch sử);
  - sai giờ đến dự kiến lúc lập của tuyến nhanh nhất (n_) và tối ưu (t_): TB |dự kiến − thật|, lệch TB (âm = hứa sớm);
  - N (lập ngay lúc đi) và that (biết trước) làm mốc trên.
Chạy:  python tong_hop_dat_truoc.py [30]
Ra:    danh_gia/ket_qua/tong_hop_dat_truoc<TRUOC>.json
"""
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')
SO_LAN = 2000


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    truoc = sys.argv[1] if len(sys.argv) > 1 else '30'
    mau = re.compile(rf'dat_truoc{truoc}_(\d{{4}}-\d\d-\d\d)\.csv$')
    bang = [pd.read_csv(t).assign(ngay=mau.search(t).group(1))
            for t in sorted(glob.glob(os.path.join(RA, f'dat_truoc{truoc}_*.csv'))) if mau.search(t)]
    kq = pd.concat(bang, ignore_index=True)
    cach = [c[len('phut_t_'):] for c in kq.columns if c.startswith('phut_t_')]
    cot = [f'phut_{p}_{c}' for c in cach for p in 'nt'] + ['phut_A', 'phut_N']
    kq = kq.dropna(subset=cot)
    print(f'{len(kq)} chuyen, ngay {sorted(kq["ngay"].unique())}, cach biet {cach}')
    nhom = [g.index.to_numpy() for _, g in kq.groupby(['di', 'den'])]
    rng = np.random.default_rng(42)
    chon = [np.concatenate([nhom[i] for i in rng.integers(0, len(nhom), len(nhom))]) for _ in range(SO_LAN)]

    def ci(ham):
        v = np.array([ham(kq.loc[c]) for c in chon])
        return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]

    def tk(g, cham, nhanh):
        return 100 * (1 - g[nhanh].sum() / g[cham].sum())

    def sai(g, k):
        return (g[f'du_doan_{k}'] - g[f'phut_{k}']).abs().mean()

    tom = {'so_chuyen': len(kq), 'truoc_phut': int(truoc)}
    for goc in ('giu', 'ls'):
        for c in [*cach, 'N']:
            if c == goc:
                continue
            a, b = f'phut_t_{goc}', ('phut_N' if c == 'N' else f'phut_t_{c}')
            tom[f'thoi_gian_{c}_so_{goc}'] = {'phan_tram': round(tk(kq, a, b), 3), 'ci95': ci(lambda g: tk(g, a, b)),
                                              'nhanh_hon': round(float((kq[b] < kq[a] - 0.05).mean()), 4),
                                              'cham_hon': round(float((kq[b] > kq[a] + 0.05).mean()), 4)}
    for p in 'nt':
        for c in cach:
            k = f'{p}_{c}'
            s = kq[f'du_doan_{k}'] - kq[f'phut_{k}']
            tom[f'gio_den_{k}'] = {'sai_tb_phut': round(float(s.abs().mean()), 3),
                                   'sai_tb_phan_tram': round(float(100 * (s.abs() / kq[f'phut_{k}']).mean()), 2),
                                   'lech_tb_phut': round(float(s.mean()), 3), 'p90': round(float(s.abs().quantile(0.9)), 3),
                                   'ci95_sai_tb': ci(lambda g, k=k: sai(g, k))}
        for c in cach:
            for goc in ('giu', 'ls'):
                if c in (goc, 'giu') or (goc == 'ls' and c == 'ls'):
                    continue
                k, g0 = f'{p}_{c}', f'{p}_{goc}'
                tom[f'gio_den_{k}_tru_{g0}'] = {'chenh_sai_tb_phut': round(float(sai(kq, k) - sai(kq, g0)), 3),
                                                'ci95': ci(lambda g, k=k, g0=g0: sai(g, k) - sai(g, g0))}
    tom['theo_gio'] = {h: {**{f'sai_n_{c}': round(float(sai(g, f'n_{c}')), 3) for c in cach},
                           **{f't_{c}_so_giu': round(tk(g, 'phut_t_giu', f'phut_t_{c}'), 2) for c in cach if c != 'giu'}}
                       for h, g in kq.groupby('gio')}
    tom['theo_ngay'] = {n: {f'sai_n_{c}': round(float(sai(g, f'n_{c}')), 3) for c in cach}
                        for n, g in kq.groupby('ngay')}
    tom['phut_tb'] = {c: round(float(kq[c].mean()), 3) for c in cot}
    for k, v in tom.items():
        print(f'{k}: {v}')
    tep = os.path.join(RA, f'tong_hop_dat_truoc{truoc}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(tom, f, ensure_ascii=False, indent=1, default=float)
    print(f'-> {tep}')


if __name__ == '__main__':
    main()
