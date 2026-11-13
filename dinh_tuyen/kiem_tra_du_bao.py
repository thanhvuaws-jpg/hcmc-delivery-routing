"""
Kiểm phần dự báo theo khe của bộ định tuyến (ba_phuong_an.DinhTuyen.dat_du_bao, QĐ-027) trên bản đồ thật:
  1. Không bật dự báo: kết quả TRÙNG KHÍT bản ba_phuong_an.py ở commit trước (cùng chi phí, cùng cạnh) —
     sửa mã không được làm đổi C/D/E đã chấm.
  2. Dự báo mà mọi khe = tình trạng lúc đi: trùng khít chế độ "giữ nguyên" (dat_tinh_trang) — logic khe không
     tự thêm gì.
  3. Dự báo khác nhau từng khe: A* có ALT và không ALT ra CÙNG chi phí — cận dưới vẫn hợp lệ.
  4. Mốc khe: 0 / 899 s -> khe 0, 900 -> 1, 2700 -> 3, 10.000 -> 3.

Chạy:  python kiem_tra_du_bao.py [ref git, mặc định HEAD]
"""
import datetime as dt
import importlib.util
import itertools
import os
import subprocess
import sys

import numpy as np
import pandas as pd

from ba_phuong_an import DinhTuyen
from kiem_tra_tuan1 import DIA_DIEM

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NGAY = '2026-11-10'
KHE_S = [900, 1800, 2700]


def nap_ban_cu(ref):
    """Nạp ba_phuong_an.py ở commit `ref` thành module riêng (dùng chung tim_duong, mo_hinh_toc_do hiện tại)."""
    ma = subprocess.run(['git', 'show', f'{ref}:dinh_tuyen/ba_phuong_an.py'], cwd=GOC, capture_output=True,
                        check=True).stdout.decode('utf-8')
    spec = importlib.util.spec_from_loader('ba_phuong_an_cu', loader=None)
    m = importlib.util.module_from_spec(spec)
    m.__file__ = os.path.join(GOC, 'dinh_tuyen', 'ba_phuong_an.py')     # bản cũ tính GOC từ __file__
    exec(compile(ma, 'ba_phuong_an_cu.py', 'exec'), m.__dict__)
    return m


def tom(kq):
    return {k: (None if kq[k] is None else (round(kq[k]['chi_phi'], 6), tuple(kq[k]['canh'])))
            for k in ('nhanh_nhat', 'toi_uu')}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ref = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'
    d = DinhTuyen.nap(None)
    n = len(d.dai)
    cu = nap_ban_cu(ref).DinhTuyen(d.bd, d.mh, d.ngap_mua, d.ngap_trieu)
    r_ho_so = np.array(d.mh.r_gio, dtype=np.float32)
    s = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'tomtom_canh', f'{NGAY}.parquet'),
                        columns=['khung', 'chi_so', 'muc', 'phu', 'phu_dong'])
    luc = pd.Timestamp(f'{NGAY} 08:00')
    s = s[s['khung'] == luc - pd.Timedelta(minutes=5)]
    nen = r_ho_so[8].copy()
    mo = (s['phu'] > 0).to_numpy()
    nen[s['chi_so'].to_numpy()[mo]] = np.maximum(s['muc'].to_numpy()[mo] / 100, 0.1)
    cam = np.zeros(n, dtype=bool)
    cam[s['chi_so'].to_numpy()[~mo]] = (s['phu_dong'].to_numpy()[~mo] > 0)
    pd_ = np.zeros(n, dtype=np.float32)
    pd_[s['chi_so'].to_numpy()] = s['phu_dong'].to_numpy() / 100
    cap = list(itertools.permutations(DIA_DIEM.items(), 2))[::5][:18]
    loi = 0

    # 1. Không dự báo: trùng bản cũ.
    trung = 0
    for (a, pa), (b, pb) in cap:
        d.dat_tinh_trang(nen, cam, pd_)
        moi = tom(d.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu')))
        cu.dat_tinh_trang(nen, cam, pd_)
        trung += moi == tom(cu.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu')))
    print(f'1. khong du bao trung ban {ref}: {trung}/{len(cap)}')
    loi += trung != len(cap)

    # 2. Mọi khe = tình trạng lúc đi: trùng chế độ giữ nguyên.
    trung = 0
    for (a, pa), (b, pb) in cap:
        d.dat_tinh_trang(nen, cam, pd_)
        giu = tom(d.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu')))
        d.dat_tinh_trang(nen, cam, pd_)
        d.dat_du_bao(np.broadcast_to(nen, (4, n)), KHE_S)
        trung += giu == tom(d.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu')))
    print(f'2. moi khe = luc di trung che do giu nguyen: {trung}/{len(cap)}')
    loi += trung != len(cap)

    # 3. Khe khác nhau (chậm dần + nhiễu): có ALT và không ALT cùng chi phí.
    rng = np.random.default_rng(0)
    r_khe = np.clip(nen[None] * np.array([1.0, 0.85, 0.7, 0.6])[:, None]
                    + rng.normal(0, 0.1, (4, n)), 0.1, 1).astype(np.float32)
    trung = khong_duong = 0
    for (a, pa), (b, pb) in cap:
        d.dat_tinh_trang(nen, cam, pd_)
        d.dat_du_bao(r_khe, KHE_S)
        co = d.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu'))
        khong = d.tim(pa, pb, luc, phuong_an=('nhanh_nhat', 'toi_uu'), dung_alt=False)
        # Cả hai cùng không có đường (đích bị đường đóng bao quanh, như Lăng Cha Cả 10/11 — QĐ-023) cũng là khớp.
        trung += all((co[k] is None and khong[k] is None) or
                     (co[k] is not None and khong[k] is not None and abs(co[k]['chi_phi'] - khong[k]['chi_phi']) < 1e-6)
                     for k in ('nhanh_nhat', 'toi_uu'))
        khong_duong += co['toi_uu'] is None
    print(f'3. du bao theo khe: co / khong ALT cung chi phi {trung}/{len(cap)} '
          f'({khong_duong} cap ca hai cung khong co duong vi duong dong)')
    loi += trung != len(cap)

    # 4. Mốc khe.
    khe = [d._khoa(0, t, False)[2] for t in (0, 899, 900, 2700, 10000)]
    print(f'4. khe cua 0/899/900/2700/10000 s: {khe}')
    loi += khe != [0, 0, 1, 3, 3]
    print('DAT' if loi == 0 else f'KHONG DAT ({loi} muc)')
    sys.exit(1 if loi else 0)


if __name__ == '__main__':
    main()
