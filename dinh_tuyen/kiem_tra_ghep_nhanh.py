"""
Kiểm bộ ghép numpy (ghep_tomtom.BoGhep.ghep) cho ra ĐÚNG kết quả của cách ghép
từng điểm một (bản 29/10/2026, viết lại ở đây làm mốc), trên các lần chụp thật.

    python kiem_tra_ghep_nhanh.py            (3 lần chụp gần nhất)
    python kiem_tra_ghep_nhanh.py 10

Đạt khi: cùng tập cạnh, mức (%) lệch nhau ở không quá 0,1% số cạnh (do cộng số thực
khác thứ tự), số mét không ghép được bằng nhau.
"""
import glob
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ghep_tomtom import (BUOC_M, GOC, LECH_TOI_DA, O_LUOI_M, XA_TOI_DA_M,  # noqa: E402
                         BoGhep, bang_canh, doan_tu_tho, huong, sang_met)


class GhepMoc:
    """Cách cũ: mỗi điểm mẫu tra 3×3 ô lưới quanh nó, vòng lặp Python."""

    def __init__(self, bo):
        self.xy, self.huong = bo.xy, bo.huong
        luoi = {}
        for i, (x1, y1, x2, y2) in enumerate(bo.xy):
            for ox in range(int(min(x1, x2) // O_LUOI_M), int(max(x1, x2) // O_LUOI_M) + 1):
                for oy in range(int(min(y1, y2) // O_LUOI_M), int(max(y1, y2) // O_LUOI_M) + 1):
                    luoi.setdefault((ox, oy), []).append(i)
        self.luoi = {k: np.array(v) for k, v in luoi.items()}

    def _gan_nhat(self, x, y, hg, hai_chieu):
        ox, oy = int(x // O_LUOI_M), int(y // O_LUOI_M)
        ung = [self.luoi[k] for k in ((ox + a, oy + b) for a in (-1, 0, 1) for b in (-1, 0, 1)) if k in self.luoi]
        if not ung:
            return -1
        idx = np.unique(np.concatenate(ung))
        x1, y1, x2, y2 = self.xy[idx].T
        dx, dy = x2 - x1, y2 - y1
        dd = dx * dx + dy * dy
        t = np.clip(((x - x1) * dx + (y - y1) * dy) / np.where(dd > 0, dd, 1), 0, 1)
        kc = np.hypot(x1 + t * dx - x, y1 + t * dy - y)
        lech = np.abs((self.huong[idx] - hg + 180) % 360 - 180)
        if hai_chieu:
            lech = np.minimum(lech, 180 - lech)
        hop_le = (kc <= XA_TOI_DA_M) & (lech <= LECH_TOI_DA)
        if not hop_le.any():
            return -1
        return int(idx[int(np.argmin(np.where(hop_le, kc + 0.2 * lech, np.inf)))])

    @staticmethod
    def _lay_mau(pts):
        doan, tich = [], 0.0
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            dai = math.hypot(xb - xa, yb - ya)
            if dai >= 0.5:
                doan.append((tich, dai, xa, ya, xb, yb))
                tich += dai
        if not doan:
            return
        s, i = BUOC_M / 2, 0
        while s < tich:
            while doan[i][0] + doan[i][1] < s:
                i += 1
            bat_dau, dai, xa, ya, xb, yb = doan[i]
            k = (s - bat_dau) / dai
            yield xa + k * (xb - xa), ya + k * (yb - ya), huong(xb - xa, yb - ya)
            s += BUOC_M

    def ghep(self, doan):
        cong, khong_ghep = {}, 0.0
        for d in doan:
            muc = d['tt'].get('traffic_level')
            if not isinstance(muc, (int, float)):
                continue
            hai_chieu = d['tt'].get('traffic_road_coverage') == 'full'
            dong = bool(d['tt'].get('road_closure', False))
            for x, y, hg in self._lay_mau([sang_met(a, b) for a, b in d['diem']]):
                c = self._gan_nhat(x, y, hg, hai_chieu)
                if c < 0:
                    khong_ghep += BUOC_M
                    continue
                o = cong.setdefault(c, [0.0, 0.0, False])
                o[0] += muc * BUOC_M
                o[1] += BUOC_M
                o[2] = o[2] or dong
        return cong, khong_ghep


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    so = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tep = sorted(glob.glob(os.path.join(GOC, 'du_lieu', 'tomtom', 'tho', '*', '*.parquet')))[-so:]
    bo = BoGhep.nap()
    moc = GhepMoc(bo)
    dat = True
    for t in tep:
        doan = doan_tu_tho(pd.read_parquet(t))
        t0 = time.time()
        c1, k1 = bo.ghep(doan)
        t1 = time.time() - t0
        t0 = time.time()
        c2, k2 = moc.ghep(doan)
        t2 = time.time() - t0
        b1, b2 = bang_canh(c1).set_index('chi_so'), bang_canh(c2).set_index('chi_so')
        cung_tap = b1.index.equals(b2.index)
        lech_muc = int((b1['muc'] != b2['muc']).sum()) if cung_tap else -1
        ok = cung_tap and lech_muc <= 0.001 * len(b2) and abs(k1 - k2) < 1e-6 \
            and (b1['dong_duong'] == b2['dong_duong']).all() if cung_tap else False
        dat &= bool(ok)
        print(f'{os.path.relpath(t, GOC)}: nhanh {t1:.2f}s / moc {t2:.1f}s | canh {len(b1)} vs {len(b2)} '
              f'| lech muc {lech_muc} | khong ghep {k1:.0f} vs {k2:.0f} m -> {"DAT" if ok else "KHONG DAT"}')
    print('DAT' if dat else 'KHONG DAT')
    return 0 if dat else 1


if __name__ == '__main__':
    sys.exit(main())
