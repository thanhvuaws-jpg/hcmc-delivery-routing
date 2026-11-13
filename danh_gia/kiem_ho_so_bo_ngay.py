"""
QĐ-031 mục 4: hồ sơ giờ r_gio (cạnh không có số đo, dùng cả lúc C/D lập tuyến lẫn lúc chấm) là TB mọi ngày tầng bạc,
gồm cả chính ngày đang chấm. Phép thử: chấm lại vài ngày với hồ sơ BỎ ngày đó rồi so với lần chạy có luật.

  python cham_tuyen_that.py <ngay> --diem=zenodo --ho-so-bo-ngay   -> ket_qua/cham_tuyen_<ngay>_zenodo_hosobongay.csv
  python kiem_ho_so_bo_ngay.py

Đạt (ĐĂNG KÝ TRƯỚC, ghi 14/11 03:05): MỖI ngày |Δ "D không chậm hơn A"| ≤ 1 điểm, |Δ "D nhanh hơn A"| ≤ 0,5 điểm,
và kết luận ngày (≥ 80% và ≥ 5%) không đổi. Không đạt -> chấm lại cả 14 ngày bằng --ho-so-bo-ngay, lấy đó làm số chính.
C, E chỉ báo kèm. Mỗi lần chạy so phương án với tuyến A CỦA CHÍNH LẦN ĐÓ (A cũng được chấm bằng hồ sơ của lần đó).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from thu_gioi_han_toi_uu import KHOA, RA, chi_so, theo_phuong_an

NGAY = ['2026-11-01', '2026-11-08', '2026-11-11']        # CN trong 7 ngày chọn, CN yếu nhất 7 ngày kiểm, một T4
NGUONG_KC, NGUONG_NH = 0.01, 0.5


def doc(ngay, hau_to=''):
    t = os.path.join(RA, f'cham_tuyen_{ngay}_zenodo{hau_to}.csv')
    return pd.read_csv(t, encoding='utf-8-sig').assign(ngay=ngay) if os.path.exists(t) else None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kq, dat_het, thieu = {}, True, False
    for ngay in NGAY:
        goc, bo = doc(ngay), doc(ngay, '_hosobongay')
        if goc is None or bo is None:
            print(f'{ngay}: thieu tep ({"co" if goc is not None else "KHONG co"} goc, '
                  f'{"co" if bo is not None else "KHONG co"} _hosobongay)')
            thieu = True
            continue
        x = goc.merge(bo, on=KHOA, suffixes=('', '_bo'))
        assert len(x) == len(goc) == len(bo), f'{ngay}: bo chuyen khac nhau'
        dong = {'n': len(x),
                'phut_A_lech_TB': float((x['phut_A_bo'] - x['phut_A']).mean()),
                'tuyen_D_khac': float((x['m_D_bo'] != x['m_D']).mean()),
                'D_doi_sang_C': [float(goc['D_doi_sang_C'].mean()), float(bo['D_doi_sang_C'].mean())]}
        for p in ('C', 'D', 'E'):
            a, b = chi_so(theo_phuong_an(goc, p)), chi_so(theo_phuong_an(bo, p))
            dong[p] = {'goc': a, 'bo_ngay': b, 'd_khong_cham': b['khong_cham'] - a['khong_cham'],
                       'd_nhanh_hon': b['nhanh_hon_pct'] - a['nhanh_hon_pct']}
        d = dong['D']
        ket_luan = [v['khong_cham'] >= 0.8 and v['nhanh_hon_pct'] >= 5 for v in (d['goc'], d['bo_ngay'])]
        dat = abs(d['d_khong_cham']) <= NGUONG_KC and abs(d['d_nhanh_hon']) <= NGUONG_NH and ket_luan[0] == ket_luan[1]
        dong['dat'] = bool(dat)
        dat_het &= dat
        kq[ngay] = dong
        print(f'{ngay}: {len(x)} chuyen; phut A lech TB {dong["phut_A_lech_TB"]:+.3f}; tuyen D khac {100 * dong["tuyen_D_khac"]:.1f}%;'
              f' D doi sang C {100 * dong["D_doi_sang_C"][0]:.1f}% -> {100 * dong["D_doi_sang_C"][1]:.1f}%')
        for p in ('C', 'D', 'E'):
            v = dong[p]
            print(f'   {p}: khong cham {v["goc"]["khong_cham"]:.4f} -> {v["bo_ngay"]["khong_cham"]:.4f} '
                  f'({100 * v["d_khong_cham"]:+.2f} diem) | nhanh hon {v["goc"]["nhanh_hon_pct"]:.2f}% -> '
                  f'{v["bo_ngay"]["nhanh_hon_pct"]:.2f}% ({v["d_nhanh_hon"]:+.2f} diem)')
        print(f'   -> {"DAT" if dat else "KHONG DAT"} (|d khong cham| <= {100 * NGUONG_KC:.0f} diem, |d nhanh hon| <= '
              f'{NGUONG_NH} diem, ket luan ngay {ket_luan[0]} -> {ket_luan[1]})')
    if thieu:
        print('\nTONG: chua du tep, chua ket luan')
        return
    print(f'\nTONG: {"DAT" if dat_het else "KHONG DAT"} — ' +
          ('ho so co ngay dang cham KHONG lam dep so dinh tuyen' if dat_het else
           'cham lai 14 ngay bang --ho-so-bo-ngay va lay do lam so chinh'))
    with open(os.path.join(RA, 'kiem_ho_so_bo_ngay.json'), 'w', encoding='utf-8') as f:
        json.dump({'ngay': NGAY, 'dat': bool(dat_het), 'theo_ngay': kq}, f, ensure_ascii=False, indent=1,
                  default=lambda o: None if isinstance(o, float) and np.isnan(o) else o)


if __name__ == '__main__':
    main()
