"""
M3 — Đường nào "kẹt giống nhau"? Phân cụm hồ sơ ngày của từng ĐOẠN đường (k-means), hai lớp.

Hồ sơ: mức kẹt 1 − r trung bình theo 48 ô nửa giờ, chỉ NGÀY THƯỜNG (cuối tuần có nhịp khác, lại ít ngày).
  Lớp MỨC  giữ nguyên hồ sơ: tách đoạn thông / vừa / nặng. Chạy thử cho thấy cụm khác nhau chủ yếu ở mức, cụm nào
           cũng đỉnh lúc 17:30 — nên chỉ một lớp này không trả lời được "kẹt lúc nào".
  Lớp DẠNG chuẩn hoá từng đoạn (trừ TB, chia độ lệch chuẩn) trên 06:00–22:00, chỉ các đoạn có kẹt thật
           (TB ban ngày ≥ NGUONG_DANG): bỏ mức đi, còn hình dáng trong ngày — đỉnh sáng, đỉnh chiều hay đều.
Không dùng DTW như dự tính ban đầu (KE_HOACH_DU_LIEU M3): DTW co giãn trục thời gian nên kéo đỉnh sáng khớp
với đỉnh chiều, ngược với mục đích; các hồ sơ đã cùng trục giờ nên Euclid hợp lý.

Chọn số cụm k bằng số đo, không bằng mắt:
  silhouette   các cụm tách nhau rõ cỡ nào;
  ổn định      chia ngày thường thành 2 nửa rời nhau, phân cụm riêng từng nửa, so bằng ARI (1 = trùng hoàn toàn,
               0 = như ngẫu nhiên) — cụm có thật thì nửa nào cũng ra gần giống nhau.

Chạy:  python m3_phan_cum.py [--k-muc=3] [--k-dang=3]
Ra:    khai_pha/ket_qua/m3_doan.csv, m3_muc.csv, m3_dang.csv, m3_ho_so.png, m3_ban_do.png
       (không lên git — từ dữ liệu TomTom)
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from sklearn.cluster import KMeans                    # noqa: E402
from sklearn.metrics import adjusted_rand_score, silhouette_score  # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
VANG = os.path.join(GOC, 'du_lieu', 'vang')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
SO_O = 48
GIO = np.arange(SO_O) / 2
BAN_NGAY = (GIO >= 6) & (GIO < 22)
PHU_TOI_THIEU = 0.9             # đoạn phải có số đo ở ≥ 90% ô nửa giờ
TOI_THIEU_KHUNG_NGAY = 90       # bỏ ngày thu dở (chỉ vài giờ): số khung 15 phút tối thiểu
NGUONG_DANG = 0.15              # lớp dạng: đoạn có 1 − r TB ban ngày ≥ 15 điểm (thông suốt thì "dạng" chỉ là nhiễu)
K_THU = range(2, 9)
MAU_SIL = 6000
MAU = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']   # thứ tự cố định


def ma_tran(v, doan_giu=None):
    """(đoạn × 48): 1 − r TB theo ô nửa giờ; ô thiếu nội suy theo chiều giờ. Chỉ đoạn đủ số đo."""
    v = v.assign(o=v['khung'].dt.hour * 2 + v['khung'].dt.minute // 30, x=1 - v['r'])
    p = v.pivot_table(index='doan', columns='o', values='x', aggfunc='mean').reindex(columns=range(SO_O))
    if doan_giu is None:
        p = p[p.notna().mean(axis=1) >= PHU_TOI_THIEU]
    else:
        p = p.reindex(doan_giu)
    return p.interpolate(axis=1, limit_direction='both')


def chuan_hoa_dang(p):
    """Dạng trong ngày: chỉ 06:00–22:00, mỗi đoạn trừ TB và chia độ lệch chuẩn của chính nó."""
    x = p.to_numpy()[:, BAN_NGAY]
    ls = x.std(axis=1, keepdims=True)
    return (x - x.mean(axis=1, keepdims=True)) / np.where(ls > 0, ls, 1)


def do_cum(X, Xa, Xb, nhan):
    """Thử các k: in silhouette và độ ổn định ARI giữa hai nửa ngày rời nhau; trả {k: (silhouette, ARI, mô hình)}."""
    mau = np.random.default_rng(42).choice(len(X), min(MAU_SIL, len(X)), replace=False)
    print(f'{nhan}: {len(X):,} doan\n{"k":>3}{"silhouette":>12}{"on dinh ARI":>13}')
    bang = {}
    for k in K_THU:
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        la_a = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xa)
        la_b = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xb)
        bang[k] = (silhouette_score(X[mau], km.labels_[mau]), adjusted_rand_score(la_a, la_b), km)
        print(f'{k:>3}{bang[k][0]:>12.3f}{bang[k][1]:>13.3f}', flush=True)
    return bang


def buoi(tam):
    """Chỉ số của một hồ sơ 48 ô: TB theo các buổi, giờ đỉnh."""
    moc = {'ban_ngay': (6, 22), 'sang': (7, 9), 'trua': (10.5, 15), 'chieu': (16, 19), 'dem': (0, 5)}
    ra = {k: float(tam[(GIO >= a) & (GIO < b)].mean()) for k, (a, b) in moc.items()}
    ra['dinh_gio'] = float(GIO[int(np.argmax(tam))])
    return ra


def ten_muc(m):
    return 'thông thoáng' if m['ban_ngay'] < 0.2 else 'kẹt vừa' if m['ban_ngay'] < 0.4 else 'kẹt nặng'


def ten_dang(m):
    """Theo tỉ lệ sáng / chiều của hồ sơ TB thật (chưa chuẩn hoá) của nhóm."""
    if m['sang'] > 1.1 * m['chieu']:
        return 'nặng sáng'
    if m['chieu'] > 1.25 * m['sang']:
        return 'nặng chiều'
    return 'hai đỉnh'


def mo_ta(p, d, nhom, ham_ten):
    """Bảng mô tả từng nhóm (nhóm: nhãn 0..k−1 đã xếp thứ tự): hồ sơ TB thật, km, đường tiêu biểu."""
    hang = []
    for c in range(nhom.max() + 1):
        m = buoi(p.to_numpy()[nhom == c].mean(axis=0))
        g = d[nhom == c]
        co_ten = g[g['ten'].notna() & (g['ten'] != '')]
        ten = co_ten.groupby('ten')['dai'].sum().sort_values(ascending=False).head(6).index
        hang.append({'nhom': c + 1, 'ten': ham_ten(m), 'so_doan': len(g), 'km': round(float(g['dai'].sum()) / 1000),
                     'ty_le_km': round(float(g['dai'].sum() / d['dai'].sum()), 3),
                     **{k: round(v, 3) for k, v in m.items()},
                     'loai_chinh': str(g.groupby('loai', observed=True)['dai'].sum().idxmax()),
                     'duong_tieu_bieu': ', '.join(str(x) for x in ten)})
    return pd.DataFrame(hang)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tuy_chon = {a.split('=')[0]: int(a.split('=')[1]) for a in sys.argv[1:] if a.startswith('--k-')}
    v = pd.concat([pd.read_parquet(t, columns=['khung', 'doan', 'r'])
                   for t in sorted(glob.glob(os.path.join(VANG, '*.parquet')))], ignore_index=True).dropna(subset=['r'])
    v['ngay'] = v['khung'].dt.normalize()
    so_khung = v.groupby('ngay')['khung'].nunique()
    v = v[v['ngay'].isin(so_khung[so_khung >= TOI_THIEU_KHUNG_NGAY].index) & (v['ngay'].dt.dayofweek < 5)]
    ngay = sorted(v['ngay'].unique())
    p = ma_tran(v)
    print(f'{len(ngay)} ngay thuong: {[f"{pd.Timestamp(n):%d/%m}" for n in ngay]}; {len(p):,} doan du so do')
    # Hai nửa ngày RỜI NHAU (xen kẽ để mỗi nửa có cả đầu và cuối kỳ) để đo độ ổn định.
    a = ma_tran(v[v['ngay'].isin(ngay[0::2])], p.index)
    b = ma_tran(v[v['ngay'].isin(ngay[1::2])], p.index)
    du = (a.notna().all(axis=1) & b.notna().all(axis=1)).to_numpy()
    p, a, b = p[du], a[du], b[du]
    d = pd.read_parquet(os.path.join(BAC, 'doan.parquet'), columns=['doan', 'dai', 'loai', 'ten']).set_index('doan').loc[p.index]

    # ── Lớp mức. Mặc định silhouette cao nhất trong k ≥ 3 (k = 2 chỉ tách "thông / kẹt") ──
    bang = do_cum(p.to_numpy(), a.to_numpy(), b.to_numpy(), 'Lop MUC')
    k = tuy_chon.get('--k-muc') or max((x for x in bang if x >= 3), key=lambda x: bang[x][0])
    print(f'Chon k muc = {k}: silhouette {bang[k][0]:.3f}, on dinh ARI {bang[k][1]:.3f}')
    km = bang[k][2]
    doi = np.argsort(np.argsort([buoi(c)['ban_ngay'] for c in km.cluster_centers_]))
    nhom_muc = doi[km.labels_]
    muc = mo_ta(p, d, nhom_muc, ten_muc)
    print(muc.drop(columns='duong_tieu_bieu').to_string(index=False))
    for _, h in muc.iterrows():
        print(f'  muc {h["nhom"]} ({h["ten"]}): {h["duong_tieu_bieu"]}')

    # ── Lớp dạng: chỉ các đoạn có kẹt thật, ở cả toàn kỳ và hai nửa ──
    co_ket = (p.to_numpy()[:, BAN_NGAY].mean(axis=1) >= NGUONG_DANG)
    pk, dk = p[co_ket], d[co_ket]
    bang2 = do_cum(chuan_hoa_dang(pk), chuan_hoa_dang(a[co_ket]), chuan_hoa_dang(b[co_ket]), 'Lop DANG')
    k2 = tuy_chon.get('--k-dang') or max(bang2, key=lambda x: bang2[x][0])
    print(f'Chon k dang = {k2}: silhouette {bang2[k2][0]:.3f}, on dinh ARI {bang2[k2][1]:.3f}')
    km2 = bang2[k2][2]
    tam_that = [pk.to_numpy()[km2.labels_ == c].mean(axis=0) for c in range(k2)]
    doi2 = np.argsort(np.argsort([buoi(t)['chieu'] / max(buoi(t)['sang'], 1e-6) for t in tam_that]))
    nhom_dang = doi2[km2.labels_]
    dang = mo_ta(pk, dk, nhom_dang, ten_dang)
    print(dang.drop(columns='duong_tieu_bieu').to_string(index=False))
    for _, h in dang.iterrows():
        print(f'  dang {h["nhom"]} ({h["ten"]}): {h["duong_tieu_bieu"]}')
    bang_cheo = pd.crosstab(pd.Series(nhom_muc[co_ket] + 1, name='muc'), pd.Series(nhom_dang + 1, name='dang'),
                            values=dk['dai'].to_numpy() / 1000, aggfunc='sum').round(0)
    print('km theo muc x dang:\n' + bang_cheo.to_string())

    os.makedirs(RA, exist_ok=True)
    ra = pd.DataFrame({'doan': p.index, 'muc': nhom_muc + 1})
    ra['dang'] = pd.Series(nhom_dang + 1, index=ra.index[co_ket])
    ra.to_csv(os.path.join(RA, 'm3_doan.csv'), index=False)
    muc.to_csv(os.path.join(RA, 'm3_muc.csv'), index=False, encoding='utf-8-sig')
    dang.to_csv(os.path.join(RA, 'm3_dang.csv'), index=False, encoding='utf-8-sig')

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for c, h in muc.iterrows():
        a1.plot(GIO, p.to_numpy()[nhom_muc == c].mean(axis=0) * 100, color=MAU[c], lw=2,
                label=f'{h["ten"]} ({h["ty_le_km"]:.0%} km)')
    for c, h in dang.iterrows():
        a2.plot(GIO, pk.to_numpy()[nhom_dang == c].mean(axis=0) * 100, color=MAU[c], lw=2,
                label=f'{h["ten"]} ({h["ty_le_km"]:.0%} km đoạn có kẹt)')
    a1.set_title(f'Theo mức: {k} nhóm, {len(p):,} đoạn', fontsize=11)
    a2.set_title(f'Theo dạng trong ngày: {k2} nhóm, {len(pk):,} đoạn có kẹt', fontsize=11)
    a1.set_ylabel('Mức kẹt 1 − r (%)')
    for ax in (a1, a2):
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 3))
        ax.set_xlabel('Giờ (ngày thường)')
        ax.grid(axis='y', color='#e4e3df', lw=0.8)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, 'm3_ho_so.png'), dpi=150)

    tinh = pd.read_parquet(os.path.join(BAC, 'canh_tinh.parquet'), columns=['x_m', 'y_m'])
    tinh['doan'] = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))['doan'].to_numpy()
    tt = tinh[tinh['doan'].isin(p.index)].groupby('doan')[['x_m', 'y_m']].mean().loc[p.index].to_numpy()
    tk = tt[co_ket]
    so_o = k + k2
    so_cot = (so_o + 1) // 2
    fig, truc = plt.subplots(2, so_cot, figsize=(3.6 * so_cot, 7), squeeze=False)
    o_ve = [(tt, nhom_muc == c, MAU[c], f'Mức: {muc.loc[c, "ten"]}') for c in range(k)] + \
           [(tk, nhom_dang == c, MAU[c], f'Dạng: {dang.loc[c, "ten"]}') for c in range(k2)]
    for stt, ax in enumerate(truc.ravel()):
        ax.set_axis_off()
        if stt < so_o:
            xy, chon, mau, ten = o_ve[stt]
            ax.scatter(xy[~chon, 0], xy[~chon, 1], s=1, color='#d9d8d3')
            ax.scatter(xy[chon, 0], xy[chon, 1], s=2, color=mau)
            ax.set_title(ten, fontsize=10)
            ax.set_aspect('equal')
    fig.tight_layout()
    fig.savefig(os.path.join(RA, 'm3_ban_do.png'), dpi=150)
    print(f'-> {RA}')


if __name__ == '__main__':
    main()
