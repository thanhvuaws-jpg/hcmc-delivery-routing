"""
Kết luận "tuyến D nhanh hơn tuyến A" còn đứng không khi đổi các số giả định trong cách chấm?

cham_tuyen_that.py có hai số KHÔNG đo được, đều có thể làm lệch kết quả:
  1. Cạnh không có số đo lúc chấm dùng hồ sơ giờ. Hẻm thực tế có thể chậm hoặc NHANH hơn hồ sơ.
     Tuyến nào đi nhiều cạnh không đo hơn thì chịu ảnh hưởng nhiều hơn, nên phải thử cả hai chiều.
  2. Vào cạnh đang đóng bị cộng cứng 300 s.

Không chạy lại bộ định tuyến, chỉ tách từ CSV: mỗi tuyến có phut (hệ số 1) và phut_kk (hệ số 0,7), nên
  phút trên cạnh không đo U = (phut_kk - phut) * 0,7 / 0,3;  thời gian ở hệ số h: T(h) = phut + U * (1/h - 1).
Đây là xấp xỉ bậc nhất: đổi hệ số làm xe tới các cạnh sau ở lần chụp hơi khác, phần đó bỏ qua.

Chạy:  python do_ben_cham.py [--bo=zenodo|dia_danh]
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')
HS_KK = 0.7
SAI_SO_BANG = 0.05
BOOT = 2000


def nap(bo):
    mau = re.compile(r'cham_tuyen_(\d{4}-\d\d-\d\d)' + ('_zenodo' if bo == 'zenodo' else '') + r'\.csv$')
    phan = []
    for tep in sorted(glob.glob(os.path.join(RA, 'cham_tuyen_*.csv'))):
        m = mau.search(os.path.basename(tep))
        if m:
            phan.append(pd.read_csv(tep, encoding='utf-8-sig').assign(ngay=m.group(1)))
    kq = pd.concat(phan, ignore_index=True)
    kq['cap'] = kq['di'] + '>' + kq['den']
    return kq


def thoi_gian(kq, x, hs=1.0, phat_dong_phut=5.0):
    """Phút của phương án x ở hệ số hs cho cạnh không đo và mức phạt đóng đường phat_dong_phut."""
    u = (kq[f'phut_kk_{x}'] - kq[f'phut_{x}']) * HS_KK / (1 - HS_KK)
    return kq[f'phut_{x}'] + u * (1 / hs - 1) + kq[f'vao_dong_{x}'] * (phat_dong_phut - 5.0)


def so_sanh(kq, a, b, nhan, rng):
    """b nhanh hơn a bao nhiêu %, tỉ lệ chuyến không chậm hơn, CI 95% lấy mẫu lại theo cặp điểm."""
    g = pd.DataFrame({'cap': kq['cap'].to_numpy(), 'a': a.to_numpy(), 'b': b.to_numpy()}).groupby('cap').sum().to_numpy()
    chon = rng.integers(0, len(g), size=(BOOT, len(g)))
    tl = 100 * (1 - g[chon, 1].sum(axis=1) / g[chon, 0].sum(axis=1))
    print(f'  {nhan:<44} {100 * (1 - b.sum() / a.sum()):>6.1f}%   CI {np.percentile(tl, 2.5):>5.1f} .. '
          f'{np.percentile(tl, 97.5):>5.1f}   khong cham hon {(b <= a + SAI_SO_BANG).mean():>4.0%}')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    bo = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--bo=')), 'zenodo')
    kq = nap(bo)
    rng = np.random.default_rng(42)
    print(f'{bo}: {len(kq):,} chuyen, {kq["ngay"].nunique()} ngay, {kq["cap"].nunique()} cap\n')

    print('1. Phan da do that (chieu dai) va phan thoi gian tren canh KHONG do:')
    for x in 'ABCD':
        u = (kq[f'phut_kk_{x}'] - kq[f'phut_{x}']) * HS_KK / (1 - HS_KK)
        print(f'  {x}: do that {kq[f"do_that_{x}"].mean():>4.0%} chieu dai; thoi gian khong do {u.sum() / kq[f"phut_{x}"].sum():>4.0%}; '
              f'TB {kq[f"m_{x}"].mean() / 1000:.2f} km; re trai qua truc lon {kq[f"re_trai_{x}"].mean():.2f}')
    u_am = ((kq['phut_kk_D'] - kq['phut_D']) < -1e-6).sum()
    print(f'  Tu kiem: {u_am} chuyen D co U am (phai gan 0 thi phep tach moi dung)\n')

    print('2. Doi he so canh khong do (h > 1: duong nho THUC TE NHANH hon ho so, co loi cho A):')
    for hs in [0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 2.0]:
        so_sanh(kq, thoi_gian(kq, 'A', hs), thoi_gian(kq, 'D', hs), f'he so {hs}', rng)
    a, d = kq['phut_A'], kq['phut_D']
    ua, ud = [(kq[f'phut_kk_{x}'] - kq[f'phut_{x}']) * HS_KK / (1 - HS_KK) for x in 'AD']
    # T_A(h) = T_D(h) <=> (a - ua) + ua/h = (d - ud) + ud/h
    h_hoa = (ua.sum() - ud.sum()) / (d.sum() - ud.sum() - (a.sum() - ua.sum()))
    if h_hoa >= 1:
        print(f'  Diem hoa: duong nho phai nhanh hon ho so {h_hoa:.2f} lan thi tong thoi gian D moi bang A\n')
    elif h_hoa > 0:
        print(f'  Diem hoa: duong nho phai cham hon ho so {1 / h_hoa:.2f} lan thi tong thoi gian D moi bang A\n')
    else:
        print(f'  Khong co diem hoa: phan khong do cua A ({ua.sum() / a.sum():.1%}) va D ({ud.sum() / d.sum():.1%}) gan nhu bang nhau\n')

    print('3. Doi muc phat vao duong dong (dang dung 5 phut):')
    for p in [0.0, 2.0, 5.0, 10.0]:
        so_sanh(kq, thoi_gian(kq, 'A', 1, p), thoi_gian(kq, 'D', 1, p), f'phat {p:.0f} phut', rng)
    sach = kq[(kq['vao_dong_A'] == 0) & (kq['vao_dong_D'] == 0)]
    so_sanh(sach, sach['phut_A'], sach['phut_D'], f'bo han chuyen dinh duong dong ({len(sach):,} chuyen)', rng)
    print(f'  A dinh duong dong o {(kq["vao_dong_A"] > 0).mean():.1%} chuyen, D o {(kq["vao_dong_D"] > 0).mean():.1%}\n')

    print('4. Khi D cham hon A thi cham bao nhieu (phut):')
    tre = (d - a)[d > a + SAI_SO_BANG]
    print(f'  {len(tre):,} chuyen ({len(tre) / len(kq):.1%}): trung vi {tre.median():.1f}, p90 {tre.quantile(.9):.1f}, lon nhat {tre.max():.1f}')
    dat = (a - d)[d <= a + SAI_SO_BANG]
    print(f'  Khi khong cham hon: trung vi nhanh hon {dat.median():.1f} phut, p90 {dat.quantile(.9):.1f}\n')

    print('5. Khung 06:30 (ngay thuong) va cac khung khac:')
    thuong = kq[pd.to_datetime(kq['ngay']).dt.dayofweek < 5]
    for gio, g in thuong.groupby('gio', sort=False):
        print(f'  {gio}: D khong cham A {(g["phut_D"] <= g["phut_A"] + SAI_SO_BANG).mean():>4.0%}, C khong cham A '
              f'{(g["phut_C"] <= g["phut_A"] + SAI_SO_BANG).mean():>4.0%}, E khong cham A {(g["phut_E"] <= g["phut_A"] + SAI_SO_BANG).mean():>4.0%}; '
              f'D dai hon A {100 * (g["m_D"].sum() / g["m_A"].sum() - 1):>4.0f}%; '
              f'khi D cham: TB {(g["phut_D"] - g["phut_A"])[g["phut_D"] > g["phut_A"] + SAI_SO_BANG].mean():.1f} phut')

    if '2026-11-01' in set(kq['ngay']):
        print('\n6. Ngay 01/11 (khong dat):')
        g = kq[kq['ngay'] == '2026-11-01']
        for gio, h in g.groupby('gio', sort=False):
            print(f'  {gio}: A {h["phut_A"].mean():>5.1f}, D {h["phut_D"].mean():>5.1f}, E {h["phut_E"].mean():>5.1f} phut; '
                  f'D khong cham A {(h["phut_D"] <= h["phut_A"] + SAI_SO_BANG).mean():>4.0%}, E khong cham A {(h["phut_E"] <= h["phut_A"] + SAI_SO_BANG).mean():>4.0%}; '
                  f'vao dong A {int(h["vao_dong_A"].sum())}, D {int(h["vao_dong_D"].sum())}, E {int(h["vao_dong_E"].sum())}')
        bo_1930 = g[g['gio'] != '19:30']
        print(f'  Bo khung 19:30: D khong cham A {(bo_1930["phut_D"] <= bo_1930["phut_A"] + SAI_SO_BANG).mean():.1%}, '
              f'nhanh hon {100 * (1 - bo_1930["phut_D"].sum() / bo_1930["phut_A"].sum()):.1f}%')
        print(f'  Ca ngay, E khong cham A {(g["phut_E"] <= g["phut_A"] + SAI_SO_BANG).mean():.1%}, '
              f'E nhanh hon A {100 * (1 - g["phut_E"].sum() / g["phut_A"].sum()):.1f}%')


if __name__ == '__main__':
    main()
