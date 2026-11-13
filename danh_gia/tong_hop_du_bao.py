"""
Tổng hợp chấm tuyến CÓ DỰ BÁO (cham_tuyen_that.py --du-bao=TEN, QĐ-027) qua các ngày:
  F so với C (nhanh nhất: dự báo / giữ nguyên tình trạng lúc đi), G so với D (tối ưu), H (biết trước, trần) so với D,
  phần dự báo lấy được = (D − G) / (D − H); G so với A (ngắn nhất) theo tiêu chí kế hoạch; sai số giờ đến C và F.
Khoảng tin cậy 95%: bootstrap theo CẶP ĐIỂM (mỗi cặp giữ mọi ngày, mọi giờ của nó), như tong_hop_cham.py.

Chạy:  python tong_hop_du_bao.py [gbm_ls]
Ra:    danh_gia/ket_qua/tong_hop_du_bao_<ten>.json
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


def tiet_kiem(g, cham, nhanh):
    """% tổng thời gian `nhanh` ít hơn `cham`."""
    return 100 * (1 - g[f'phut_{nhanh}'].sum() / g[f'phut_{cham}'].sum())


def ci_theo_cap(kq, ham, rng):
    cap = kq.groupby(['di', 'den'])
    nhom = [g for _, g in cap]
    mau = []
    for _ in range(SO_LAN):
        chon = rng.integers(0, len(nhom), len(nhom))
        mau.append(ham(pd.concat([nhom[i] for i in chon])))
    return [round(float(np.percentile(mau, 2.5)), 3), round(float(np.percentile(mau, 97.5)), 3)]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ten = sys.argv[1] if len(sys.argv) > 1 else 'gbm_ls'
    mau_ten = re.compile(r'cham_tuyen_(\d{4}-\d\d-\d\d)_zenodo_dubao-' + re.escape(ten) + r'\.csv$')
    bang = []
    for t in sorted(glob.glob(os.path.join(RA, 'cham_tuyen_*.csv'))):
        m = mau_ten.search(os.path.basename(t))
        if m:
            bang.append(pd.read_csv(t).assign(ngay=m.group(1)))
    if not bang:
        sys.exit(f'chua co cham_tuyen_<ngay>_zenodo_dubao-{ten}.csv')
    kq = pd.concat(bang, ignore_index=True)
    tat_ca = len(kq)
    kq = kq[kq[['phut_F', 'phut_G', 'phut_H']].notna().all(axis=1)]
    print(f'{len(kq)}/{tat_ca} chuyen co F, G, H; ngay: {sorted(kq["ngay"].unique())}')
    rng = np.random.default_rng(42)

    def phan_lay_duoc(g):
        return (g['phut_D'].sum() - g['phut_G'].sum()) / (g['phut_D'].sum() - g['phut_H'].sum())

    tom = {}
    for ten_so, (cham, nhanh) in {'F_so_C': ('C', 'F'), 'G_so_D': ('D', 'G'), 'H_so_D': ('D', 'H'),
                                  'G_so_A': ('A', 'G'), 'D_so_A': ('A', 'D'), 'E_so_D': ('D', 'E')}.items():
        tom[ten_so] = {'phan_tram': round(tiet_kiem(kq, cham, nhanh), 3),
                       'ci95': ci_theo_cap(kq, lambda g: tiet_kiem(g, cham, nhanh), rng),
                       'nhanh_hon': round(float((kq[f'phut_{nhanh}'] < kq[f'phut_{cham}'] - 0.05).mean()), 4),
                       'cham_hon': round(float((kq[f'phut_{nhanh}'] > kq[f'phut_{cham}'] + 0.05).mean()), 4)}
    tom['phan_du_bao_lay_duoc'] = {'ty_le': round(float(phan_lay_duoc(kq)), 3),
                                   'ci95': ci_theo_cap(kq, phan_lay_duoc, rng)}
    tom['G_khong_cham_hon_A'] = round(float((kq['phut_G'] <= kq['phut_A'] + 0.05).mean()), 4)
    tom['D_khong_cham_hon_A'] = round(float((kq['phut_D'] <= kq['phut_A'] + 0.05).mean()), 4)
    tom['G_khac_D_theo_met'] = round(float((kq['m_G'] != kq['m_D']).mean()), 4)
    tom['H_khac_D_theo_met'] = round(float((kq['m_H'] != kq['m_D']).mean()), 4)
    for k in ('C', 'F'):
        sai = (kq[f'du_doan_{k}'] - kq[f'phut_{k}'])
        tom[f'gio_den_{k}'] = {'sai_tb_phut': round(float(sai.abs().mean()), 3),
                               'sai_tb_phan_tram': round(float(100 * (sai.abs() / kq[f'phut_{k}']).mean()), 2),
                               'lech_tb_phut': round(float(sai.mean()), 3),
                               'p90_phut': round(float(sai.abs().quantile(0.9)), 3)}
    tom['theo_ngay'] = {n: {'G_so_D': round(tiet_kiem(g, 'D', 'G'), 3), 'H_so_D': round(tiet_kiem(g, 'D', 'H'), 3),
                            'F_so_C': round(tiet_kiem(g, 'C', 'F'), 3), 'so_chuyen': len(g)}
                        for n, g in kq.groupby('ngay')}
    tom['theo_gio'] = {h: {'G_so_D': round(tiet_kiem(g, 'D', 'G'), 3), 'H_so_D': round(tiet_kiem(g, 'D', 'H'), 3),
                           'F_so_C': round(tiet_kiem(g, 'C', 'F'), 3)}
                       for h, g in kq.groupby('gio')}
    tom['so_chuyen'] = len(kq)
    tom['phut_tb'] = {k: round(float(kq[f'phut_{k}'].mean()), 3) for k in 'ABCDEFGH'}

    for k, v in tom.items():
        print(f'{k}: {v}')
    tep = os.path.join(RA, f'tong_hop_du_bao_{ten}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(tom, f, ensure_ascii=False, indent=1)
    print(f'-> {tep}')


if __name__ == '__main__':
    main()
