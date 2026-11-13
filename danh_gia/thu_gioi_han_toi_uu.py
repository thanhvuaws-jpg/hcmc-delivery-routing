"""
Thử luật "tuyến tối ưu chỉ được dự kiến chậm hơn một chút" để vá điểm yếu Chủ nhật / 06:30 (QĐ-031).

Đọc cham_tuyen_<ngày>_zenodo.csv của lần chạy KHÔNG luật (ket_qua/qd031_khong_luat/, 13/11 23:05 → 14/11 00:44, có cột
du_doan_D, du_doan_A). Luật chỉ chọn GIỮA hai tuyến đã có (D hoặc C), nên tính lại offline được, không phải tìm đường lại:
  R1(δ)  D' = D nếu dự kiến D ≤ (1 + δ) × dự kiến C, ngược lại C
  R2(μ)  D' = D nếu dự kiến D ≤ (1 − μ) × dự kiến A (A theo cùng tình trạng lúc đi), ngược lại C
Chọn trên 7 ngày đầu (CHON), báo số trên 7 ngày sau (KIEM) không chỉnh gì — cách chọn đăng ký trước ở QĐ-031 mục 2.

Tự kiểm 1 (với ket_qua/cu_truoc_qd031/): tuyến A, B (không phụ thuộc hồ sơ giờ) phải trùng hẳn. Phút thì KHÔNG trùng: hồ sơ
  r_gio (mo_hinh_toc_do.MoHinhTocDo.nap) tính lại từ MỌI tệp bac/tomtom_canh đang có, giữa hai lần chạy có thêm 12–13/11.
Tự kiểm 2 (khi ket_qua/cham_tuyen_*_zenodo.csv là lần chạy CÓ luật — có cột D_doi_sang_C): A, B, C trùng hẳn lần không
  luật; D trùng đúng lựa chọn offline R2 μ=0 ở mọi chuyến có dự kiến A (chuyến A đi qua đường đóng: luật trong
  ba_phuong_an so với tuyến ngắn nhất TRÁNH đường đóng, offline thì giữ D). In số chính của D mới và E mới.

Chạy:  python thu_gioi_han_toi_uu.py
Ra:    in bảng; danh_gia/ket_qua/thu_gioi_han_toi_uu.json
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
KHONG_LUAT = os.path.join(RA, 'qd031_khong_luat')
EPS = 0.05                      # chênh dưới 3 giây coi như bằng (như tong_hop_cham.SAI_SO_BANG)
CHON = ['2026-10-30', '2026-10-31', '2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05']
KIEM = ['2026-11-06', '2026-11-07', '2026-11-08', '2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12']
BIEN_THE = ([('D (hien tai)', None, None)] + [(f'R1 d={x:g}', 'R1', x) for x in (0, .01, .02, .03, .05, .08, .10, .15)]
            + [(f'R2 mu={x:g}', 'R2', x) for x in (0, .02, .05)])
KHOA = ['ngay', 'gio', 'di', 'den']


def nap(thu_muc):
    phan = []
    for t in sorted(glob.glob(os.path.join(thu_muc, 'cham_tuyen_*_zenodo.csv'))):
        m = re.search(r'cham_tuyen_(\d{4}-\d\d-\d\d)_zenodo\.csv$', t)
        if m:
            phan.append(pd.read_csv(t, encoding='utf-8-sig').assign(ngay=m[1]))
    if not phan:
        return None
    d = pd.concat(phan, ignore_index=True)
    d['cuoi_tuan'] = pd.to_datetime(d['ngay']).dt.dayofweek >= 5
    return d


def tu_kiem(d):
    """Tuyến A, B phải trùng lần chạy cũ; phút lệch do hồ sơ r_gio (xem đầu tệp) — in mức lệch và D cũ / mới."""
    cu = nap(os.path.join(RA, 'cu_truoc_qd031'))
    if cu is None:
        print('tu kiem 1: khong co tep cu')
        return
    x = cu.merge(d, on=KHOA, suffixes=('_cu', ''))
    tuyen = max(float((x[f'{c}_cu'] - x[c]).abs().max()) for c in ('m_A', 'm_B', 're_trai_A', 're_trai_B'))
    lech_a = x['phut_A'] - x['phut_A_cu']

    def d_kc(g, h=''):
        return (g[f'phut_D{h}'] <= g[f'phut_A{h}'] + EPS).mean()
    print(f'tu kiem 1 voi lan chay cu: {len(x):,}/{len(cu):,} chuyen trung khoa; tuyen A, B lech {tuyen:.0f} (phai 0); '
          f'phut A lech TB {lech_a.mean():+.3f}, |max| {lech_a.abs().max():.2f} (ho so r_gio); '
          f'D khong cham A: cu {d_kc(x, "_cu"):.4f} / moi {d_kc(x):.4f}')


def ap_luat(d, luat, x):
    """Mảng bool: chuyến dùng C thay cho D."""
    if luat is None:
        return np.zeros(len(d), bool)
    if luat == 'R1':
        return (d['du_doan_D'] > (1 + x) * d['du_doan_C']).to_numpy()
    a = d['du_doan_A'].fillna(np.inf)
    return (d['du_doan_D'] > (1 - x) * a).to_numpy()


def chi_so(g):
    kc = g['p'] <= g['phut_A'] + EPS
    return {'n': len(g), 'khong_cham': float(kc.mean()),
            'nhanh_hon_pct': float(100 * (1 - g['p'].sum() / g['phut_A'].sum())),
            'kk_khong_cham': float((g['pkk'] <= g['phut_kk_A'] + EPS).mean()) if g['pkk'].notna().any() else np.nan,
            're_trai': float(g['rt'].mean()), 'dai_so_A': float(g['m'].sum() / g['m_A'].sum()),
            'do_that': float(g['dt'].mean()), 'dung_C': float(g['dung_C'].mean())}


def danh_gia(d, ngay):
    g = d[d['ngay'].isin(ngay)]
    tong = chi_so(g)
    theo_ngay = {n: chi_so(x) for n, x in g.groupby('ngay')}
    theo_khung = {f'{"cuoi tuan" if c else "thuong"} {h}': chi_so(x) for (c, h), x in g.groupby(['cuoi_tuan', 'gio'])}
    dat = (all(v['khong_cham'] >= 0.8 for v in theo_ngay.values()) and all(v['khong_cham'] >= 0.8 for v in theo_khung.values())
           and all(v['nhanh_hon_pct'] >= 5 for v in theo_ngay.values()) and tong['kk_khong_cham'] >= 0.8)
    return {'tong': tong, 'theo_ngay': theo_ngay, 'theo_khung': theo_khung, 'dat': bool(dat),
            'ngay_dat': sum(v['khong_cham'] >= 0.8 and v['nhanh_hon_pct'] >= 5 for v in theo_ngay.values()),
            'khung_dat': sum(v['khong_cham'] >= 0.8 for v in theo_khung.values()), 'so_khung': len(theo_khung),
            'khung_truot': {k: round(v['khong_cham'], 3) for k, v in theo_khung.items() if v['khong_cham'] < 0.8},
            'ngay_truot': {k: round(v['khong_cham'], 3) for k, v in theo_ngay.items() if v['khong_cham'] < 0.8}}


def theo_phuong_an(d, p):
    """Bảng chi_so cho phương án p (cột phut_p...) của một lần chạy."""
    kk = d[f'phut_kk_{p}'] if f'phut_kk_{p}' in d else np.nan          # E không có cột khắt khe, rẽ trái
    rt = d[f're_trai_{p}'] if f're_trai_{p}' in d else np.nan
    return d.assign(p=d[f'phut_{p}'], pkk=kk, rt=rt, m=d[f'm_{p}'], dt=d[f'do_that_{p}'],
                    dung_C=d['D_doi_sang_C'] if 'D_doi_sang_C' in d else False)


def kiem_luat(goc, ket):
    """Tự kiểm 2 + số chính của lần chạy CÓ luật (nếu có)."""
    moi = nap(RA)
    if moi is None or 'D_doi_sang_C' not in moi:
        print('\ntu kiem 2: chua co lan chay CO luat (cot D_doi_sang_C) trong ket_qua/')
        return None
    x = goc.merge(moi, on=KHOA, suffixes=('_g', ''))
    cot_abc = [f'{a}_{p}' for p in 'ABC' for a in ('phut', 'phut_kk', 'm', 're_trai')]
    lech_abc = max(float((x[f'{c}_g'] - x[c]).abs().max()) for c in cot_abc)
    co_a = x['du_doan_A_g'].notna()
    ky_vong = (x['du_doan_D_g'] > x['du_doan_A_g']) & co_a
    sai_co = int((x.loc[co_a, 'D_doi_sang_C'] != ky_vong[co_a]).sum())
    lech_d = {a: float((np.where(ky_vong, x[f'{a}_C_g'], x[f'{a}_D_g']) - x[f'{a}_D'])[co_a].abs().max())
              for a in ('phut', 'phut_kk', 'm', 're_trai')}
    nan_doi = int(x.loc[~co_a, 'D_doi_sang_C'].sum())
    print(f'\ntu kiem 2 (lan chay CO luat): {len(x):,} chuyen; A,B,C lech {lech_abc:.2e} (phai 0); '
          f'co D_doi_sang_C sai ky vong: {sai_co}/{int(co_a.sum()):,}; D lech lua chon offline: '
          + ', '.join(f'{k} {v:.2e}' for k, v in lech_d.items())
          + f'; chuyen A qua duong dong ({int((~co_a).sum())}): luat doi sang C o {nan_doi}')
    ra = {'lech_abc': lech_abc, 'sai_co': sai_co, 'lech_d': lech_d, 'chuyen_khong_du_kien_A': int((~co_a).sum()),
          'doi_o_chuyen_khong_du_kien_A': nan_doi}
    print(f'\n{"":<22}| {"khong cham":>10} {"nhanh hon":>10} {"ngay":>5} {"khung":>6} {"kk":>6} {"re trai":>8} {"dai/A":>6} {"do that":>7}')
    for nhan, bang, p in (('D cu (khong luat)', goc, 'D'), ('D moi (co luat)', moi, 'D'),
                          ('E cu (khong luat)', goc, 'E'), ('E moi (co luat)', moi, 'E')):
        v = theo_phuong_an(bang, p)
        for ten, ngay in (('7 ngay kiem', KIEM), ('ca 14 ngay', CHON + KIEM)):
            k = danh_gia(v, ngay)
            t = k['tong']
            print(f'{nhan:<17}{ten[:4]:>5}| {t["khong_cham"]:>10.3f} {t["nhanh_hon_pct"]:>9.1f}% {k["ngay_dat"]:>3}/{len(ngay):<2}'
                  f'{k["khung_dat"]:>3}/{k["so_khung"]} {t["kk_khong_cham"]:>6.3f} {t["re_trai"]:>8.2f} {t["dai_so_A"]:>6.3f} {t["do_that"]:>7.3f}'
                  + (f'  truot: {k["khung_truot"]}' if k['khung_truot'] else ''))
            ra[f'{nhan} {ten}'] = k
    return ra


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = nap(KHONG_LUAT)
    if d is None or 'du_doan_D' not in d:
        sys.exit('thieu ket_qua/qd031_khong_luat/ (lan chay khong luat, co cot du_doan_D)')
    print(f'{len(d):,} chuyen, {d["ngay"].nunique()} ngay; chon tren {CHON[0]}..{CHON[-1]}, kiem tren {KIEM[0]}..{KIEM[-1]}')
    tu_kiem(d)
    ket = {}
    for ten, luat, x in BIEN_THE:
        c = ap_luat(d, luat, x)
        v = d.assign(p=np.where(c, d['phut_C'], d['phut_D']), pkk=np.where(c, d['phut_kk_C'], d['phut_kk_D']),
                     rt=np.where(c, d['re_trai_C'], d['re_trai_D']), m=np.where(c, d['m_C'], d['m_D']),
                     dt=np.where(c, d['do_that_C'], d['do_that_D']), dung_C=c)
        ket[ten] = {'chon': danh_gia(v, CHON), 'kiem': danh_gia(v, KIEM), 'ca_14': danh_gia(v, CHON + KIEM)}

    print(f'\n{"bien the":<14}| {"7 NGAY CHON: khong cham":>23} {"ngay":>5} {"khung":>6} {"kk":>6} {"re trai":>8} {"dung C":>7} {"DAT":>4}')
    for ten, k in ket.items():
        c = k['chon']
        print(f'{ten:<14}| {c["tong"]["khong_cham"]:>23.3f} {c["ngay_dat"]:>3}/7 {c["khung_dat"]:>3}/{c["so_khung"]}'
              f' {c["tong"]["kk_khong_cham"]:>6.3f} {c["tong"]["re_trai"]:>8.2f} {c["tong"]["dung_C"]:>7.1%} {"x" if c["dat"] else "":>4}')
    dat = [t for t, k in ket.items() if k['chon']['dat']]
    # Ít rẽ trái nhất; hòa thì gần D nhất (ít chuyến phải đổi sang C nhất).
    chon = min(dat, key=lambda t: (round(ket[t]['chon']['tong']['re_trai'], 4), ket[t]['chon']['tong']['dung_C'])) if dat else None
    print(f'\nDat tren 7 ngay chon: {dat or "khong co"} -> CHON: {chon}')

    print(f'\n{"bien the":<14}| {"7 NGAY KIEM: khong cham":>23} {"nhanh hon":>10} {"ngay":>5} {"khung":>6} {"kk":>6} {"re trai":>8}'
          f' {"dai/A":>6} {"do that":>7} {"dung C":>7}')
    for ten, k in ket.items():
        c = k['kiem']
        print(f'{ten:<14}| {c["tong"]["khong_cham"]:>23.3f} {c["tong"]["nhanh_hon_pct"]:>9.1f}% {c["ngay_dat"]:>3}/7'
              f' {c["khung_dat"]:>3}/{c["so_khung"]} {c["tong"]["kk_khong_cham"]:>6.3f} {c["tong"]["re_trai"]:>8.2f}'
              f' {c["tong"]["dai_so_A"]:>6.3f} {c["tong"]["do_that"]:>7.3f} {c["tong"]["dung_C"]:>7.1%}' + ('   <- chon' if ten == chon else ''))
    for ten in dict.fromkeys(['D (hien tai)', chon]):
        if ten:
            k = ket[ten]['kiem']
            print(f'\n{ten} tren 7 ngay kiem: ngay truot {k["ngay_truot"] or "khong"}; khung truot {k["khung_truot"] or "khong"}')
            print('  theo ngay: ' + ', '.join(f'{n[5:]} {v["khong_cham"]:.3f}/{v["nhanh_hon_pct"]:.1f}%' for n, v in k['theo_ngay'].items()))
    if chon:
        c14 = ket[chon]['ca_14']
        print(f'\n{chon} ca 14 ngay: khong cham {c14["tong"]["khong_cham"]:.3f}, nhanh hon {c14["tong"]["nhanh_hon_pct"]:.1f}%, '
              f'{c14["ngay_dat"]}/14 ngay, {c14["khung_dat"]}/{c14["so_khung"]} khung, re trai {c14["tong"]["re_trai"]:.2f}')
    luat = kiem_luat(d, ket)
    json.dump({'chon': chon, 'ket': ket, 'lan_chay_co_luat': luat},
              open(os.path.join(RA, 'thu_gioi_han_toi_uu.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
