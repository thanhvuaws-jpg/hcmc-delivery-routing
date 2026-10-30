"""
M1 — Kẹt lúc nào, ở đâu? (thống kê mô tả, KE_HOACH_DU_LIEU mục 6)

Từ tầng bạc TomTom (mức cạnh, 5 phút) của MỘT ngày:
  1. Hồ sơ theo giờ: tỉ lệ tốc độ TB và % chiều dài đường đông (r < 0,75) / kẹt (r < 0,4),
     theo nhóm loại đường. Trọng số = chiều dài cạnh.
  2. Bản đồ kẹt trong khung cao điểm (mặc định 07:30–09:00): mỗi cạnh tô màu theo r TB.
  3. Top đoạn đường chính kẹt nhất trong khung đó (đoạn = xu_ly/doan_duong.py), có tên đường.
Cạnh đang ĐÓNG (TomTom road_closure, mức 0) bị loại khỏi mọi thống kê kẹt, in danh sách riêng.

Chạy:  python m1_mo_ta.py 2026-10-30 [07:30 09:00]
Ra:    khai_pha/ket_qua/m1_<ngày>_gio.csv, _gio.png, _ban_do_<từ>-<đến>.png, _top_doan.csv
"""
import os
import pickle
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from matplotlib.collections import LineCollection    # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
NHOM = {'trunk': 'truc_chinh', 'trunk_link': 'truc_chinh', 'primary': 'chinh', 'primary_link': 'chinh',
        'secondary': 'cap_2', 'secondary_link': 'cap_2', 'tertiary': 'cap_3', 'tertiary_link': 'cap_3'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ngay = sys.argv[1] if len(sys.argv) > 1 else '2026-10-30'
    tu, den = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ('07:30', '09:00')
    os.makedirs(RA, exist_ok=True)
    s = pd.read_parquet(os.path.join(BAC, 'tomtom_canh', f'{ngay}.parquet'),
                        columns=['khung', 'chi_so', 'muc', 'co', 'dong_duong'])
    # Đường ĐÓNG: TomTom ghi mức 0 — không phải kẹt xe. Tách riêng, không tính vào thống kê kẹt.
    dong = s[s['dong_duong']]
    s = s[~s['dong_duong']]
    canh = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'),
                           columns=['chi_so', 'u', 'v', 'loai', 'ten', 'dai'])
    s = s.merge(canh[['chi_so', 'loai', 'dai']], on='chi_so')
    s['nhom'] = s['loai'].map(NHOM).fillna('nho')
    s['r'] = s['muc'] / 100
    s['gio'] = s['khung'].dt.hour

    # 1. Hồ sơ theo giờ.
    def tom(g):
        w = g['dai']
        return pd.Series({'r_tb': np.average(g['r'], weights=w),
                          'pt_dong': 100 * w[g['r'] < 0.75].sum() / w.sum(),
                          'pt_ket': 100 * w[g['r'] < 0.4].sum() / w.sum(),
                          'km_co_du_lieu': w.sum() / 1000 / g['khung'].nunique()})
    ho_so = s.groupby(['gio', 'nhom']).apply(tom, include_groups=False).reset_index()
    tong = s.groupby('gio').apply(tom, include_groups=False).reset_index().assign(nhom='tat_ca')
    ho_so = pd.concat([tong, ho_so], ignore_index=True).round(3)
    ho_so.to_csv(os.path.join(RA, f'm1_{ngay}_gio.csv'), index=False, encoding='utf-8-sig')
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    for nhom, g in ho_so.groupby('nhom'):
        ax[0].plot(g['gio'], g['r_tb'], marker='o', label=nhom, lw=2.5 if nhom == 'tat_ca' else 1)
        ax[1].plot(g['gio'], g['pt_dong'], marker='o', label=nhom, lw=2.5 if nhom == 'tat_ca' else 1)
    ax[0].set(title=f'Ti le toc do / duong trong - {ngay}', xlabel='Gio', ylabel='r (trong so chieu dai)')
    ax[1].set(title='% chieu dai duong dong (r < 0,75)', xlabel='Gio', ylabel='%')
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, f'm1_{ngay}_gio.png'), dpi=130)
    plt.close(fig)

    # 2. Bản đồ cao điểm.
    t0, t1 = pd.Timestamp(f'{ngay} {tu}'), pd.Timestamp(f'{ngay} {den}')
    cd = s[(s['khung'] >= t0) & (s['khung'] < t1)]
    if cd.empty:
        print(f'Khong co du lieu {tu}-{den} ngay {ngay}')
        return
    r_canh = cd.groupby('chi_so')['r'].mean()
    from do_thi import TEP_RA
    with open(TEP_RA, 'rb') as f:
        G = pickle.load(f)['G']
    c = canh.set_index('chi_so')
    nen = [((G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y']))
           for u, v, l in zip(c['u'], c['v'], c['loai']) if l in NHOM]
    co = c.loc[r_canh.index]
    seg = [((G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])) for u, v in zip(co['u'], co['v'])]
    thu_tu = np.argsort(-r_canh.to_numpy())                # vẽ đoạn kẹt sau cùng để nổi lên trên
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.add_collection(LineCollection(nen, colors='#d9d9d9', linewidths=0.4))
    lc = LineCollection([seg[i] for i in thu_tu], array=r_canh.to_numpy()[thu_tu], cmap='RdYlGn',
                        norm=plt.Normalize(0.2, 1.0), linewidths=1.6)
    ax.add_collection(lc)
    ax.autoscale()
    ax.set_aspect(1 / np.cos(np.radians(10.78)))
    fig.colorbar(lc, ax=ax, shrink=0.6, label='r = toc do hien tai / toc do duong trong')
    ax.set_title(f'Muc ket TomTom TB {tu}-{den} ngay {ngay} ({len(r_canh):,} canh co du lieu)')
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.01, 0.01, '(c) OpenStreetMap contributors; du lieu giao thong: TomTom', transform=ax.transAxes, fontsize=7)
    fig.tight_layout()
    tep_bd = os.path.join(RA, f'm1_{ngay}_ban_do_{tu.replace(":", "")}-{den.replace(":", "")}.png')
    fig.savefig(tep_bd, dpi=140)
    plt.close(fig)

    # 3. Top đoạn đường chính kẹt nhất.
    cd2 = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))
    doan = pd.read_parquet(os.path.join(BAC, 'doan.parquet'))
    x = cd.merge(cd2, on='chi_so')
    x = x[x['nhom'] != 'nho']
    g = x.groupby('doan').apply(lambda g: pd.Series({'r_tb': np.average(g['r'], weights=g['dai']),
                                                     'so_lan_chup': g['khung'].nunique()}), include_groups=False)
    g = g.join(doan.set_index('doan')[['ten', 'loai', 'dai']])
    top = g[(g['dai'] >= 150) & (g['so_lan_chup'] >= 0.8 * cd['khung'].nunique())].nsmallest(20, 'r_tb')
    top.round(3).to_csv(os.path.join(RA, f'm1_{ngay}_top_doan.csv'), encoding='utf-8-sig')
    ten_dong = canh.set_index('chi_so').loc[dong['chi_so'].unique(), 'ten'].replace('', '?')

    t = ho_so[ho_so['nhom'] == 'tat_ca'].set_index('gio')
    print(f'{ngay}: r TB theo gio:', t['r_tb'].round(2).to_dict())
    print(f'  % duong dong theo gio:', t['pt_dong'].round(1).to_dict())
    print(f'Ban do {tu}-{den}: {len(r_canh):,} canh -> {tep_bd}')
    print(f'Duong dang DONG (khong tinh la ket): {dong["chi_so"].nunique()} canh: '
          + ', '.join(sorted(set(ten_dong))[:15]))
    print('Top doan duong chinh ket nhat (dai >= 150 m):')
    for d_, r in top.head(15).iterrows():
        print(f'  {r["ten"] or "?":<28} {r["loai"]:<10} {r["dai"]:>6.0f} m  r={r["r_tb"]:.2f}')


if __name__ == '__main__':
    main()
