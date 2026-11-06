"""
Tuyến có dễ đi theo không? Đếm số chỉ dẫn (số lần người lái phải làm gì đó) và phần đi trong hẻm của từng phương án.

Số phút (cham_tuyen_that.py) không cho biết điều này: tuyến nhanh hơn 10% mà phải rẽ gấp ba lần thì người lái vẫn có thể
không đi theo. Trên 90 cặp điểm giao hàng thật (cùng bộ với chấm tuyến). Gọi API đang chạy (he_thong/api/may_chu.py).

Chạy:  python do_phuc_tap_tuyen.py [2026-11-05T17:30:00] [2026-11-05T10:00:00] ...
"""
import json
import os
import sys
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cham_tuyen_that import cap_zenodo  # noqa: E402

GOC_API = 'http://127.0.0.1:8770'
PHUONG_AN = ('ngan_nhat', 'nhanh_nhat', 'toi_uu')


def goi(duong, than):
    y = urllib.request.Request(GOC_API + duong, json.dumps(than).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(y, timeout=120) as r:
        return json.load(r)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cac_luc = [a for a in sys.argv[1:] if not a.startswith('--')] or ['2026-11-05T17:30:00', '2026-11-05T10:00:00']
    for luc in cac_luc:
        hang, bo = [], {}
        for (_, a), (_, b) in cap_zenodo():
            try:
                kq = goi('/api/tuyen', {'di': [float(x) for x in a], 'den': [float(x) for x in b], 'luc': luc})
            except urllib.error.HTTPError as e:
                loi = json.load(e).get('loi', str(e))[:60]
                bo[loi] = bo.get(loi, 0) + 1
                continue
            for p in PHUONG_AN:
                r = kq['phuong_an'][p]
                if r is None:
                    continue
                d = goi('/api/dan-duong', {'canh': r['canh'], 'luc': luc})
                moc = d['ten_doan'] + [[r['dai_m'], '']]
                hem = sum(y[0] - x[0] for x, y in zip(moc, moc[1:]) if x[1].casefold().startswith(('hẻm', 'ngõ', 'ngách')) or not x[1])
                hang.append({'p': p, 'km': r['dai_m'] / 1000, 'phut': r['thuc_te']['phut'] if r['thuc_te'] else np.nan,
                             'chi_dan': len(d['buoc']) - 2, 'hem_pct': 100 * hem / max(r['dai_m'], 1)})
        t = pd.DataFrame(hang)
        t['chi_dan_km'] = t['chi_dan'] / t['km']
        print(f'\n{luc}: {len(t) // len(PHUONG_AN)} cap' + (f'; bo {bo}' if bo else ''))
        print(t.groupby('p', sort=False).agg(km=('km', 'mean'), phut=('phut', 'mean'), chi_dan_tb=('chi_dan', 'mean'), chi_dan_tv=('chi_dan', 'median'),
                                             chi_dan_max=('chi_dan', 'max'), moi_km=('chi_dan_km', 'mean'), hem_pct=('hem_pct', 'mean')).round(1).to_string())


if __name__ == '__main__':
    main()
