"""
Hiệu chỉnh giờ đến dự kiến (QĐ-029). Mọi cách biết (trừ biết trước) đều HỨA SỚM: đi ngay sai TB −0,5 phút, lập trước
30 phút −1,2 .. −1,5 phút (QĐ-027, QĐ-028). Nguyên nhân: bộ định tuyến chọn đúng những cạnh đang được đoán nhanh hơn
thật, cộng TB r của đoạn thay cho TB thời gian.

Cách sửa: nhân giờ đi dự kiến với hệ số k theo GIỜ XUẤT PHÁT, k = Σ phút thật / Σ phút dự kiến trên ngày HỌC hệ số;
chấm trên ngày KHÁC (không chọn hệ số trên ngày đem chấm):
  đi ngay (C, F)   học trên 30/10–06/11 (cu_phat_canh/, chỉ dùng cột giờ đến của C), chấm trên 09–12/11.
  lập trước 30'    chỉ có 4 ngày có dự báo: chia đôi theo ngày (09–10 / 11–12), học một nửa chấm nửa kia, đổi chiều.
Chỉ dùng chuyến KHÔNG đi vào đường đóng (vao_dong = 0): phạt đường đóng không phải lỗi đoán giờ.
Ra: danh_gia/ket_qua/hieu_chinh_gio_den.json; hệ số đi ngay theo giờ chép vào he_thong/api/dich_vu.HE_SO_GIO_DEN.
Chạy:  python hieu_chinh_gio_den.py
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')


def he_so(g, k):
    """Hệ số theo giờ xuất phát + hệ số chung (giờ không có mẫu)."""
    sach = g[g[f'vao_dong_{k}'] == 0]
    theo_gio = (sach.groupby('gio')[f'phut_{k}'].sum() / sach.groupby('gio')[f'du_doan_{k}'].sum()).to_dict()
    return {'chung': float(sach[f'phut_{k}'].sum() / sach[f'du_doan_{k}'].sum()),
            'theo_gio': {h: float(v) for h, v in theo_gio.items()}}


def cham(g, k, hs):
    """Sai giờ đến trước / sau hiệu chỉnh (chuyến không vào đường đóng)."""
    g = g[g[f'vao_dong_{k}'] == 0]
    he = g['gio'].map(hs['theo_gio']).fillna(hs['chung']).to_numpy()
    du, that = g[f'du_doan_{k}'].to_numpy(), g[f'phut_{k}'].to_numpy()
    ra = {}
    for ten, v in (('truoc', du), ('sau', du * he)):
        s = v - that
        ra[ten] = {'sai_tb_phut': round(float(np.abs(s).mean()), 3), 'lech_tb_phut': round(float(s.mean()), 3),
                   'sai_tb_phan_tram': round(float(100 * (np.abs(s) / that).mean()), 2),
                   'p90_phut': round(float(np.quantile(np.abs(s), 0.9)), 3)}
    ra['so_chuyen'] = len(g)
    return ra


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kq = {}
    # ── Đi ngay ──
    hoc = pd.concat([pd.read_csv(t) for t in sorted(glob.glob(os.path.join(RA, 'cu_phat_canh', 'cham_tuyen_*_zenodo.csv')))],
                    ignore_index=True)
    kiem = pd.concat([pd.read_csv(t) for t in sorted(glob.glob(os.path.join(RA, 'cham_tuyen_2026-11-*_zenodo_dubao-gbm_ls.csv')))],
                     ignore_index=True)
    hs = he_so(hoc, 'C')
    kq['di_ngay'] = {'he_so': hs, 'hoc_tren': f'{len(hoc)} chuyen 30/10-06/11',
                     'C': cham(kiem, 'C', hs), 'F_dung_he_so_cua_C': cham(kiem, 'F', hs)}
    print('DI NGAY: he so chung %.4f, theo gio %s' % (hs['chung'], {h: round(v, 3) for h, v in hs['theo_gio'].items()}))
    for k in ('C', 'F_dung_he_so_cua_C'):
        print(f'  {k}: {kq["di_ngay"][k]}')
    # ── Lập trước 30 phút: chia đôi theo ngày ──
    dt = {os.path.basename(t)[len('dat_truoc30_'):][:10]: pd.read_csv(t)
          for t in sorted(glob.glob(os.path.join(RA, 'dat_truoc30_*.csv')))}
    ngay = sorted(dt)
    nua = [ngay[:len(ngay) // 2], ngay[len(ngay) // 2:]]
    kq['lap_truoc_30'] = {}
    for cach in ('giu', 'ls', 'gbm_ls', 'gwn_ho_so_them_che'):
        k = f'n_{cach}'
        tong = {'truoc': [], 'sau': []}
        for a, b in ((0, 1), (1, 0)):
            h = he_so(pd.concat([dt[n] for n in nua[a]]), k)
            c = cham(pd.concat([dt[n] for n in nua[b]]), k, h)
            for t in tong:
                tong[t].append((c[t], c['so_chuyen']))
        gop = {t: {m: round(sum(x[m] * w for x, w in v) / sum(w for _, w in v), 3) for m in v[0][0]}
               for t, v in tong.items()}
        kq['lap_truoc_30'][cach] = gop
        print(f'LAP TRUOC 30 {cach}: truoc {gop["truoc"]} -> sau {gop["sau"]}')
    tep = os.path.join(RA, 'hieu_chinh_gio_den.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'-> {tep}')


if __name__ == '__main__':
    main()
