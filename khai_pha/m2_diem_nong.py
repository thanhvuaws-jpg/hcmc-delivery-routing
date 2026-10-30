"""
M2 — Điểm nóng ùn tắc có ý nghĩa thống kê: Getis-Ord Gi* trên các ĐOẠN đường.

Biến: x_i = 1 − r TB của đoạn i trong khung giờ chọn (r từ tầng vàng, đã bỏ phần đường đóng).
Lân cận: các đoạn có trung điểm cách nhau ≤ BAN_KINH_M (gồm chính nó), trọng số nhị phân.
  Gi*_i = (Σ_j w_ij x_j − x̄ W_i) / (S · sqrt((n·W_i − W_i²) / (n − 1)))     (W_i = Σ_j w_ij)
Gi* xấp xỉ chuẩn tắc: z > 0 nổi = cụm KẸT hơn mức chung, z < 0 = cụm THÔNG.
Hàng nghìn đoạn kiểm cùng lúc nên hiệu chỉnh p theo Benjamini–Hochberg (FDR 5%), không dùng
ngưỡng 1,96 trần — tránh "điểm nóng" do kiểm nhiều lần.

Chạy:  python m2_diem_nong.py 2026-10-30 07:30 09:00
Ra:    khai_pha/ket_qua/m2_<ngày>_<từ>-<đến>.csv (+ .png bản đồ nóng/lạnh)
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
import scipy.sparse as sp                             # noqa: E402
from scipy.spatial import cKDTree                     # noqa: E402
from scipy.stats import norm                          # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
VANG = os.path.join(GOC, 'du_lieu', 'vang')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
BAN_KINH_M = 400.0
FDR = 0.05
TOI_THIEU_KHUNG = 4             # đoạn phải có dữ liệu ở ít nhất 4 khung 15 phút trong cửa sổ


def bh(p, q):
    """Benjamini–Hochberg: mảng bool 'có ý nghĩa' ở mức FDR q."""
    n = len(p)
    thu_tu = np.argsort(p)
    nguong = q * np.arange(1, n + 1) / n
    dat = p[thu_tu] <= nguong
    k = np.max(np.nonzero(dat)[0]) + 1 if dat.any() else 0
    ra = np.zeros(n, dtype=bool)
    ra[thu_tu[:k]] = True
    return ra


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ngay = sys.argv[1] if len(sys.argv) > 1 else '2026-10-30'
    tu, den = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ('07:30', '09:00')
    v = pd.read_parquet(os.path.join(VANG, f'{ngay}.parquet'), columns=['khung', 'doan', 'r'])
    v = v[(v['khung'] >= pd.Timestamp(f'{ngay} {tu}')) & (v['khung'] < pd.Timestamp(f'{ngay} {den}'))]
    g = v.groupby('doan')['r'].agg(['mean', 'count'])
    g = g[g['count'] >= TOI_THIEU_KHUNG]
    x = 1 - g['mean'].to_numpy()

    # Trung điểm đoạn = TB trung điểm các cạnh, trọng số chiều dài.
    tinh = pd.read_parquet(os.path.join(BAC, 'canh_tinh.parquet'), columns=['x_m', 'y_m', 'dai'])
    cd = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))
    tinh['doan'] = cd['doan'].to_numpy()
    tinh = tinh[tinh['doan'].isin(g.index)]
    tam = tinh.assign(xw=tinh['x_m'] * tinh['dai'], yw=tinh['y_m'] * tinh['dai']).groupby('doan')[
        ['xw', 'yw', 'dai']].sum()
    xy = np.column_stack([tam['xw'] / tam['dai'], tam['yw'] / tam['dai']])[np.searchsorted(tam.index, g.index)]

    # Gi* với lân cận khoảng cách (gồm chính nó).
    cap = cKDTree(xy).query_pairs(BAN_KINH_M, output_type='ndarray')
    n = len(x)
    W = sp.coo_matrix((np.ones(2 * len(cap)), (np.r_[cap[:, 0], cap[:, 1]], np.r_[cap[:, 1], cap[:, 0]])),
                      shape=(n, n)).tocsr() + sp.identity(n, format='csr')
    Wi = np.asarray(W.sum(axis=1)).ravel()
    tb, S = x.mean(), np.sqrt((x ** 2).mean() - x.mean() ** 2)
    z = (W @ x - tb * Wi) / (S * np.sqrt((n * Wi - Wi ** 2) / (n - 1)))
    p = 2 * norm.sf(np.abs(z))
    y_nghia = bh(p, FDR)

    doan = pd.read_parquet(os.path.join(BAC, 'doan.parquet')).set_index('doan')
    kq = pd.DataFrame({'doan': g.index, 'r_tb': g['mean'].round(3), 'so_khung': g['count'], 'z': z.round(2),
                       'p': p, 'lan_can': Wi.astype(int),
                       'loai_diem': np.where(y_nghia & (z > 0), 'nong', np.where(y_nghia & (z < 0), 'lanh', 'khong')),
                       'ten': doan.loc[g.index, 'ten'].to_numpy(), 'loai': doan.loc[g.index, 'loai'].to_numpy(),
                       'dai': doan.loc[g.index, 'dai'].round(0).to_numpy(), 'x_m': xy[:, 0], 'y_m': xy[:, 1]})
    os.makedirs(RA, exist_ok=True)
    goc_ten = f'm2_{ngay}_{tu.replace(":", "")}-{den.replace(":", "")}'
    kq.to_csv(os.path.join(RA, goc_ten + '.csv'), index=False, encoding='utf-8-sig')

    fig, ax = plt.subplots(figsize=(10, 9))
    mau = {'khong': '#cfcfcf', 'lanh': '#2c7bb6', 'nong': '#d7191c'}
    for loai_d in ('khong', 'lanh', 'nong'):
        m = kq['loai_diem'] == loai_d
        ax.scatter(kq.loc[m, 'x_m'], kq.loc[m, 'y_m'], s=4 if loai_d == 'khong' else 7, c=mau[loai_d],
                   label=f'{loai_d} ({m.sum():,})', linewidths=0)
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    ax.legend(markerscale=3, loc='lower right')
    ax.set_title(f'Getis-Ord Gi* (ban kinh {BAN_KINH_M:.0f} m, FDR {FDR:.0%}) - {ngay} {tu}-{den}')
    ax.text(0.01, 0.01, '(c) OpenStreetMap contributors; du lieu giao thong: TomTom', transform=ax.transAxes, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, goc_ten + '.png'), dpi=140)
    plt.close(fig)

    dem = kq['loai_diem'].value_counts().to_dict()
    print(f'{ngay} {tu}-{den}: {n:,} doan, lan can TB {Wi.mean():.0f} doan trong {BAN_KINH_M:.0f} m')
    print(f'  co y nghia (FDR {FDR:.0%}): nong {dem.get("nong", 0):,}, lanh {dem.get("lanh", 0):,}, '
          f'khong {dem.get("khong", 0):,} | (neu dung |z|>1,96 tran: {(np.abs(z) > 1.96).sum():,})')
    nong = kq[kq['loai_diem'] == 'nong']
    dai_theo_ten = nong[nong['ten'] != ''].groupby('ten')['dai'].sum().sort_values(ascending=False)
    print('  duong co nhieu chieu dai trong vung nong nhat:',
          ', '.join(f'{t} ({d / 1000:.1f} km)' for t, d in dai_theo_ten.head(12).items()))


if __name__ == '__main__':
    main()
