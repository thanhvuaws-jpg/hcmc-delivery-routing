"""
Kiểm tra bước ghép TomTom -> cạnh đồ thị trên MỘT lần chụp thật (gọi TomTom 30 ô).

In: thời gian ghép, % chiều dài TomTom ghép được, % chiều dài đường theo loại có
dữ liệu, kiểm tra chiều ở đường một chiều, và vẽ ket_qua/tuan3_ket_xe.png.

Chạy:   python kiem_tra_ghep.py
"""
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'thu_thap'))

import matplotlib                                   # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                     # noqa: E402
import pandas as pd                                 # noqa: E402
from matplotlib.collections import LineCollection   # noqa: E402

from ghep_tomtom import TEP_CANH, BoGhep, bang_canh  # noqa: E402
from thu_tomtom import chup, doc_khoa                # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bo = BoGhep.dung()
    print(f'Dung chi muc: {time.time() - t0:.1f}s')

    luc, _, doan, loi, _ = chup(doc_khoa())
    t0 = time.time()
    cong, khong_ghep = bo.ghep(doan)
    bang = bang_canh(cong)
    giay = time.time() - t0
    da_ghep = sum(v[1] + v[2] for v in cong.values())
    print(f'Chup {luc:%H:%M}: {len(doan):,} doan TomTom -> {len(bang):,} canh, ghep {giay:.1f}s')
    print(f'Chieu dai mau TomTom ghep duoc: {100 * da_ghep / (da_ghep + khong_ghep):.1f}% '
          f'({da_ghep / 1000:.0f} km / {(da_ghep + khong_ghep) / 1000:.0f} km)')

    canh = pd.read_parquet(TEP_CANH)
    c = canh.merge(bang, on='chi_so', how='left')
    c['co'] = c['muc'].notna()
    c['nhom'] = c['loai'].str.replace('_link', '', regex=False)
    tk = c.groupby('nhom').apply(lambda g: 100 * g.loc[g.co, 'dai'].sum() / g['dai'].sum(), include_groups=False)
    print('% chieu dai canh co du lieu theo loai duong:')
    for k in ['trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'service']:
        if k in tk:
            print(f'   {k:<13} {tk[k]:5.1f}%')

    # Kiểm tra chiều: ở đường một chiều chỉ có MỘT cạnh (u->v). Nếu ghép đúng chiều
    # thì đoạn TomTom "one_side" chạy ngược chiều cạnh sẽ không ghép được vào đó.
    hai_canh = set(zip(canh.u, canh.v)) & set(zip(canh.v, canh.u))
    mot_chieu = c[[(u, v) not in hai_canh for u, v in zip(c.u, c.v)]]
    print(f'Canh duong mot chieu co du lieu: {100 * mot_chieu.co.mean():.1f}% '
          f'(duong hai chieu: {100 * c[~c.index.isin(mot_chieu.index)].co.mean():.1f}%)')

    # Hình: cạnh tô màu theo mức kẹt.
    with open(os.path.join(os.path.dirname(TEP_CANH), 'do_thi_xe_may.pkl'), 'rb') as f:
        import pickle
        G = pickle.load(f)['G']
    nen, mau_net = [], defaultdict(list)
    for r in c.itertuples():
        seg = [(G.nodes[r.u]['x'], G.nodes[r.u]['y']), (G.nodes[r.v]['x'], G.nodes[r.v]['y'])]
        if not r.co:
            nen.append(seg)
        else:
            m = r.muc / 100
            mau_net['#c62828' if m < 0.4 else '#ef8f00' if m < 0.75 else '#2e7d32'].append(seg)
    fig, ax = plt.subplots(figsize=(13, 11), dpi=110)
    ax.add_collection(LineCollection(nen, colors='#ddd6ca', linewidths=0.4))
    for mau, segs in mau_net.items():
        ax.add_collection(LineCollection(segs, colors=mau, linewidths=1.6))
    ax.set_xlim(106.635, 106.725); ax.set_ylim(10.742, 10.815); ax.set_aspect(1 / 0.983)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f'Mức kẹt xe thật lúc {luc:%H:%M %d/%m/%Y} ghép vào đồ thị xe máy — '
                 f'đỏ: kẹt (<40% tốc độ đường trống), cam: đông, xanh: thông\n'
                 f'Traffic data © TomTom · nền © OpenStreetMap contributors', fontsize=10)
    tep = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ket_qua', 'tuan3_ket_xe.png')
    fig.savefig(tep, bbox_inches='tight')
    print('->', tep)


if __name__ == '__main__':
    main()
