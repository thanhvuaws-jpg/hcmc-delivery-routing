"""
M8 — Số tự đo có đáng tin không? Đối chiếu với TomTom Traffic Index TP.HCM 2025 (D12).

Công thức theo định nghĩa của TomTom (tomtom.com/traffic-index/about): mức kẹt = thời gian đi THÊM so với lúc
đường trống, trên toàn mạng và toàn kỳ:  mức kẹt = Σ thời gian / Σ thời gian đường trống − 1.
Mỗi dòng tầng vàng (đoạn, khung 15 phút): thời gian = dài / kmh; r = v / v_trống nên thời gian đường trống
= thời gian × r. Tốc độ TB là TB điều hoà: Σ dài / Σ thời gian (đi 10 km mất bao lâu thì phải tính kiểu này).
Lấy trọn 7 NGÀY GẦN NHẤT có đủ dữ liệu để mọi thứ trong tuần cân bằng.

KHÔNG so được hoàn toàn (ghi rõ khi báo cáo):
  - Index tính theo chuyến xe thật nên đường đông xe nặng ký hơn; ở đây cân theo chiều dài (không có lưu lượng)
    -> in nhiều lớp đường để thấy khoảng dao động thay vì một con số;
  - vùng khác: Index là thành phố / vùng đô thị, ở đây là vùng 30 ô trung tâm;
  - Index là ô tô năm 2025, ở đây 7 ngày tháng 11/2026.
Số D12 lấy từ note ghi ngày 29/10/2026; trang riêng của TP.HCM không mở lại được khi viết script này.

Chạy:  python m8_doi_chieu.py
Ra:    khai_pha/ket_qua/m8_doi_chieu.csv, m8_theo_gio.csv, m8_theo_gio.png (không lên git — từ dữ liệu TomTom)
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VANG = os.path.join(GOC, 'du_lieu', 'vang')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
D12 = {'muc_ket_pct': 46.9, 'phut_10km': 31 + 55 / 60, 'cao_diem_chieu_kmh': 14.8}
LOP = {'moi duong co so do': None,
       'tertiary tro len': {'trunk', 'primary', 'secondary', 'tertiary'},
       'secondary tro len': {'trunk', 'primary', 'secondary'},
       'primary tro len': {'trunk', 'primary'}}
KMH_SAN = 3.0                   # TomTom bước 5 km/h: dưới mức này coi như số đo không dùng được để chia
KHUNG_DU_NGAY = 96


def chi_so(g):
    """Mức kẹt (%), tốc độ TB điều hoà (km/h), phút mỗi 10 km."""
    tg = g['tg'].sum()
    v = g['dai'].sum() / 1000 / (tg / 3600)
    return {'muc_ket_pct': 100 * (tg / g['tg_trong'].sum() - 1), 'kmh': v, 'phut_10km': 600 / v}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cac_tep = sorted(glob.glob(os.path.join(VANG, '*.parquet')))
    # 7 ngày trọn vẹn gần nhất có số km/h (TomTom absolute có từ 30/10 04:11).
    ngay_du = []
    for t in reversed(cac_tep):
        x = pd.read_parquet(t, columns=['khung', 'kmh'])
        if x.loc[x['kmh'].notna(), 'khung'].nunique() >= KHUNG_DU_NGAY:
            ngay_du.append(t)
        if len(ngay_du) == 7:
            break
    if len(ngay_du) < 7:
        print(f'Moi co {len(ngay_du)} ngay tron km/h, can 7')
    v = pd.concat([pd.read_parquet(t, columns=['khung', 'doan', 'r', 'kmh', 'dai', 'loai']) for t in ngay_du], ignore_index=True)
    v['loai'] = v['loai'].astype(str)
    v = v[v['r'].notna() & v['kmh'].notna() & (v['kmh'] >= KMH_SAN) & (v['r'] > 0)]
    v['tg'] = v['dai'] / (v['kmh'] / 3.6)
    v['tg_trong'] = v['tg'] * v['r'].clip(upper=1)
    v['gio'] = v['khung'].dt.hour
    v['thu'] = v['khung'].dt.dayofweek
    ngay = sorted(v['khung'].dt.date.unique())
    print(f'{len(ngay)} ngay {ngay[0]} -> {ngay[-1]}; {len(v):,} dong; thu {sorted(v["thu"].unique())}')
    chieu = (v['thu'] < 5) & (v['gio'] >= 17) & (v['gio'] < 19)
    sang = (v['thu'] < 5) & (v['gio'] >= 7) & (v['gio'] < 9)
    ban_ngay = (v['gio'] >= 6) & (v['gio'] < 22)

    # Index cân theo chuyến xe thật (ban đêm gần như không có xe); ở đây không có lưu lượng nên in hai cực:
    # cân đều 24 giờ (đêm nặng ký hơn thực tế) và chỉ 06:00–22:00 (bỏ hẳn đêm). Số thật nằm khoảng giữa.
    hang = []
    for ten, lop in LOP.items():
        g = v if lop is None else v[v['loai'].isin(lop)]
        tc, ng = chi_so(g), chi_so(g[ban_ngay.reindex(g.index)])
        ch, sa = chi_so(g[chieu.reindex(g.index)]), chi_so(g[sang.reindex(g.index)])
        hang.append({'lop_duong': ten, 'km_doan': round(g.drop_duplicates('doan')['dai'].sum() / 1000),
                     'muc_ket_24h': round(tc['muc_ket_pct'], 1), 'muc_ket_6_22': round(ng['muc_ket_pct'], 1),
                     'phut_10km_24h': round(tc['phut_10km'], 1), 'phut_10km_6_22': round(ng['phut_10km'], 1),
                     'kmh_24h': round(tc['kmh'], 1), 'kmh_6_22': round(ng['kmh'], 1),
                     'kmh_chieu_17_19': round(ch['kmh'], 1), 'kmh_sang_7_9': round(sa['kmh'], 1)})
    bang = pd.DataFrame(hang)
    print(bang.to_string(index=False))
    print(f'D12 (Index TP.HCM 2025): muc ket {D12["muc_ket_pct"]}%, 10 km mat {D12["phut_10km"]:.1f} phut '
          f'({600 / D12["phut_10km"]:.1f} km/h), cao diem chieu {D12["cao_diem_chieu_kmh"]} km/h')

    os.makedirs(RA, exist_ok=True)
    bang.to_csv(os.path.join(RA, 'm8_doi_chieu.csv'), index=False, encoding='utf-8-sig')
    g = v[v['loai'].isin(LOP['secondary tro len'])]
    theo_gio = g.groupby([g['thu'] < 5, 'gio']).apply(lambda x: pd.Series(chi_so(x)), include_groups=False).reset_index()
    theo_gio.columns = ['ngay_thuong', 'gio', 'muc_ket_pct', 'kmh', 'phut_10km']
    theo_gio.round(2).to_csv(os.path.join(RA, 'm8_theo_gio.csv'), index=False)

    fig, ax = plt.subplots(figsize=(8.5, 4))
    for la, nhan, mau in ((True, 'Ngày thường', '#2a78d6'), (False, 'Cuối tuần', '#eb6834')):
        x = theo_gio[theo_gio['ngay_thuong'] == la]
        ax.plot(x['gio'], x['muc_ket_pct'], color=mau, lw=2, label=nhan)
    ax.axhline(D12['muc_ket_pct'], color='#52514e', lw=1, ls='--')
    ax.text(0.2, D12['muc_ket_pct'] + 1.5, f'Index 2025: TB cả tuần {D12["muc_ket_pct"]}%', color='#52514e', fontsize=9)
    ax.set_xlim(0, 23)
    ax.set_xticks(range(0, 24, 3))
    ax.set_ylim(bottom=0)
    ax.set_xlabel('Giờ trong ngày')
    ax.set_ylabel('Mức kẹt: thời gian đi thêm (%)')
    ax.set_title('Mức kẹt theo giờ, đường secondary trở lên, 7 ngày')
    ax.grid(axis='y', color='#e4e3df', lw=0.8)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, 'm8_theo_gio.png'), dpi=150)
    print(f'-> {RA}')


if __name__ == '__main__':
    main()
