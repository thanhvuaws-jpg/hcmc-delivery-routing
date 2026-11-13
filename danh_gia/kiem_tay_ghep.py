"""
QĐ-033: kiểm tay 30 đoạn ghép TomTom -> cạnh đồ thị (việc tồn tuần 3). Bốc mẫu đúng như đăng ký trước, mỗi đoạn vẽ
một hình (không cần bản đồ nền: nền là chính các cạnh đồ thị trong vòng VUNG_M mét, có tên OSM), kèm số tự động.

  python kiem_tay_ghep.py
  -> danh_gia/ket_qua/kiem_tay_ghep/doan_XX.png, kiem_tay_ghep.json   (dữ liệu TomTom: KHÔNG lên git)

Đọc hình: mỗi cạnh vẽ lệch sang PHẢI chiều đi 2,5 m (xe chạy bên phải), nên hai chiều của đường hai chiều tách
thành hai nét. Đường TomTom: nét đen đứt + mũi tên chiều vẽ; chấm màu = mẫu đã ghép (màu của cạnh nhận), dấu x đỏ =
mẫu không ghép được. Kết luận đúng / sai ghi tay ở QĐ-033 mục 2.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ghep_tomtom import MX, MY, TEP_CANH, BoGhep  # noqa: E402

TEP = os.path.join(GOC, 'du_lieu', 'tomtom', 'tho', '2026-11-10', '1956.parquet')
RA = os.path.join(GOC, 'danh_gia', 'ket_qua', 'kiem_tay_ghep')
HAT, SO_DOAN, VUNG_M, LECH_PHAI_M = 20261114, 30, 60.0, 2.5
MAU = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22']


def lech_phai(x1, y1, x2, y2, m=LECH_PHAI_M):
    dx, dy = x2 - x1, y2 - y1
    L = np.hypot(dx, dy)
    L = np.where(L > 0, L, 1)
    ox, oy = dy / L * m, -dx / L * m          # pháp tuyến bên phải chiều đi (trục y hướng bắc)
    return x1 + ox, y1 + oy, x2 + ox, y2 + oy


def ve(stt, d, bo, canh, tep):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x, y, h, c = d['x'], d['y'], d['h'], d['c']
    x0, x1_, y0, y1_ = x.min() - VUNG_M, x.max() + VUNG_M, y.min() - VUNG_M, y.max() + VUNG_M
    xy = bo.xy
    gan = np.flatnonzero((np.maximum(xy[:, 0], xy[:, 2]) >= x0) & (np.minimum(xy[:, 0], xy[:, 2]) <= x1_) &
                         (np.maximum(xy[:, 1], xy[:, 3]) >= y0) & (np.minimum(xy[:, 1], xy[:, 3]) <= y1_))
    ghep = list(dict.fromkeys(int(i) for i in c[c >= 0]))
    mau_canh = {}
    for i in ghep:                              # cùng tên + loại -> cùng màu (một con đường)
        k = (canh.at[i, 'ten'], canh.at[i, 'loai'])
        mau_canh.setdefault(k, MAU[len(mau_canh) % len(MAU)])
    fig, ax = plt.subplots(figsize=(7.5, 7.5), dpi=90)
    da_ghi = set()
    for i in gan:
        a = lech_phai(*xy[i])
        la_ghep = i in ghep
        k = (canh.at[i, 'ten'], canh.at[i, 'loai'])
        ax.plot([a[0], a[2]], [a[1], a[3]], color=mau_canh[k] if la_ghep else '#b8b8b8', lw=3.2 if la_ghep else 1.0,
                zorder=3 if la_ghep else 1, solid_capstyle='butt')
        if la_ghep or np.hypot(a[2] - a[0], a[3] - a[1]) > 25:
            mx, my = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
            ax.annotate('', xy=(mx + (a[2] - a[0]) * 0.08, my + (a[3] - a[1]) * 0.08), xytext=(mx, my),
                        arrowprops=dict(arrowstyle='->', color=mau_canh[k] if la_ghep else '#a0a0a0', lw=1.0), zorder=4)
        ten = canh.at[i, 'ten'] or ''
        if ten and ten not in da_ghi and not la_ghep and x0 + 10 < a[0] < x1_ - 10 and y0 + 10 < a[1] < y1_ - 10:
            da_ghi.add(ten)
            ax.text((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, ten, fontsize=7, color='#707070', zorder=2, clip_on=True)
    p = d['pts']
    ax.plot(p[:, 0], p[:, 1], color='black', lw=1.2, ls=(0, (4, 3)), zorder=5)
    buoc = max(1, len(x) // 8)
    ax.quiver(x[::buoc], y[::buoc], np.sin(np.radians(h[::buoc])), np.cos(np.radians(h[::buoc])), color='black',
              scale=28, width=0.004, zorder=6)
    ok = c >= 0
    for i in ghep:
        m = c == i
        ax.scatter(x[m], y[m], s=14, color=mau_canh[(canh.at[i, 'ten'], canh.at[i, 'loai'])], edgecolor='black',
                   linewidth=0.4, zorder=7)
    ax.scatter(x[~ok], y[~ok], s=30, marker='x', color='red', zorder=7)
    ax.set_xlim(x0, x1_)
    ax.set_ylim(y0, y1_)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.plot([x0 + 8, x0 + 58], [y0 + 8, y0 + 8], color='black', lw=2)
    ax.text(x0 + 8, y0 + 11, '50 m', fontsize=8)
    ax.set_title(f'#{stt:02d}  TomTom: {d["loai_duong"]}, {d["phu"]}, muc {d["muc"]:.2f}, dai {d["dai"]:.0f} m, '
                 f'ghep {int(ok.sum())}/{len(c)} mau', fontsize=9)
    dong = [f'{n} mau -> {ten or "(khong ten)"} [{loai}]' for (ten, loai), n in d['theo_duong'].items()]
    ax.text(0.01, 0.99, '\n'.join(dong), transform=ax.transAxes, va='top', fontsize=8,
            bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc'), zorder=8)
    for (ten, loai), mau in mau_canh.items():
        ax.plot([], [], color=mau, lw=3, label=f'{ten or "(khong ten)"} [{loai}]')
    ax.legend(loc='lower right', fontsize=7)
    fig.tight_layout()
    fig.savefig(tep)
    plt.close(fig)


TRANG = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Kiểm tay ghép TomTom</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>body{margin:0;font:14px system-ui,sans-serif}#tren{padding:6px 10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#bd{height:calc(100vh - 44px)}#ghi{color:#333}</style></head><body>
<div id="tren"><button id="lui">&larr;</button><select id="chon"></select><button id="toi">&rarr;</button><span id="ghi"></span></div>
<div id="bd"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const DL = __DU_LIEU__;
const bd = L.map('bd', {maxZoom: 19});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'}).addTo(bd);
let lop = L.layerGroup().addTo(bd);
const chon = document.getElementById('chon');
DL.forEach((d, i) => chon.add(new Option('#' + String(d.stt).padStart(2, '0') + ' ' + d.loai_duong + ' ' + d.phu, i)));
function ve(i) {
  const d = DL[i]; lop.clearLayers();
  d.canh.forEach(c => L.polyline(c.ll, {color: c.mau, weight: 7, opacity: 0.75}).bindTooltip(c.ten + ' [' + c.loai + '] #' + c.i).addTo(lop));
  L.polyline(d.tomtom, {color: '#000', weight: 2, dashArray: '6 5'}).addTo(lop);
  L.circleMarker(d.tomtom[0], {radius: 6, color: '#0a0', fillOpacity: 1}).bindTooltip('đầu đoạn TomTom').addTo(lop);
  L.circleMarker(d.tomtom[d.tomtom.length - 1], {radius: 6, color: '#a00', fillOpacity: 1}).bindTooltip('cuối đoạn TomTom').addTo(lop);
  d.mau.forEach(m => L.circleMarker([m[0], m[1]], {radius: 3, color: m[2] ? '#222' : 'red', fillOpacity: 1}).addTo(lop));
  bd.fitBounds(L.polyline(d.tomtom).getBounds().pad(0.25));
  document.getElementById('ghi').textContent = 'mức ' + d.muc.toFixed(2) + ', dài ' + d.dai_m + ' m, ghép ' + d.mau_ghep + '/' + d.so_mau +
    ' mẫu — xanh lá: đầu, đỏ: cuối đoạn TomTom; nét màu: cạnh nhận dữ liệu';
  location.hash = 'd' + d.stt;
}
chon.onchange = () => ve(+chon.value);
document.getElementById('lui').onclick = () => { chon.value = Math.max(0, +chon.value - 1); ve(+chon.value); };
document.getElementById('toi').onclick = () => { chon.value = Math.min(DL.length - 1, +chon.value + 1); ve(+chon.value); };
const h = parseInt((location.hash || '').replace('#d', ''), 10);
chon.value = h ? DL.findIndex(d => d.stt === h) : 0; ve(+chon.value);
</script></body></html>"""


def ban_do(chon, bo, canh, ra):
    """Trang Leaflet (nền OpenStreetMap) chồng đoạn TomTom + cạnh nhận dữ liệu — để người xem lại từng đoạn."""
    dl = []
    for k, (d, r) in enumerate(zip(chon, ra), 1):
        ok = d['c'] >= 0
        mau_ten = {}
        cac = []
        for i in r['canh_ghep']:
            t = (canh.at[i, 'ten'], canh.at[i, 'loai'])
            mau_ten.setdefault(t, MAU[len(mau_ten) % len(MAU)])
            x1, y1, x2, y2 = bo.xy[i]
            cac.append({'i': int(i), 'ten': t[0] or '(không tên)', 'loai': t[1], 'mau': mau_ten[t],
                        'll': [[y1 / MY, x1 / MX], [y2 / MY, x2 / MX]]})
        dl.append({**{k2: r[k2] for k2 in ('stt', 'loai_duong', 'phu', 'muc', 'dai_m', 'so_mau', 'mau_ghep')},
                   'tomtom': [[p[1] / MY, p[0] / MX] for p in d['pts']], 'canh': cac,
                   'mau': [[float(y / MY), float(x / MX), bool(o)] for x, y, o in zip(d['x'], d['y'], ok)]})
    tep = os.path.join(RA, 'ban_do.html')
    with open(tep, 'w', encoding='utf-8') as f:
        f.write(TRANG.replace('__DU_LIEU__', json.dumps(dl, ensure_ascii=False)))
    return tep


def pham_vi(bo, tho):
    """
    Cả lần chụp: cỡ của hai chỗ yếu thấy khi kiểm tay (QĐ-033 mục 2).
      (a) đoạn phu = 'full' trên đường hai chiều: mẫu chỉ vào MỘT chiều, cạnh chiều ngược có nhận mẫu nào không.
      (b) mẫu ghép vào cạnh cầu / cầu vượt (OSM bridge=yes hoặc layer ≥ 1) mà có cạnh KHÔNG phải cầu, cùng hướng
          (lệch ≤ 35°), xa hơn không quá 3 m -> dễ nhầm tầng.
    """
    c_bang = pd.read_parquet(TEP_CANH, columns=['chi_so', 'u', 'v', 'way'])
    osm = json.load(open(os.path.join(GOC, 'du_lieu', 'ban_do', 'osm_vung_tomtom.json'), encoding='utf-8'))
    cau_way = {e['id'] for e in osm['elements'] if e['type'] == 'way' and
               (e.get('tags', {}).get('bridge', 'no') != 'no' or str(e.get('tags', {}).get('layer', '0')).lstrip('-').isdigit()
                and int(e.get('tags', {}).get('layer', '0')) >= 1)}
    del osm
    la_cau = c_bang['way'].isin(cau_way).to_numpy()
    cap = dict(zip(zip(c_bang['u'], c_bang['v']), c_bang['chi_so']))
    nguoc = np.array([cap.get((v, u), -1) for u, v in zip(c_bang['u'], c_bang['v'])])
    xs, ys, hs, hai = [], [], [], []
    for h_, p_ in zip(tho['hinh_hoc'], tho['phu']):
        diem = np.asarray(json.loads(h_), dtype=float)
        if len(diem) < 2:
            continue
        m = bo._lay_mau(np.column_stack([diem[:, 1] * MX, diem[:, 0] * MY]))
        if m is None:
            continue
        xs.append(m[0]); ys.append(m[1]); hs.append(m[2]); hai.append(np.full(len(m[0]), p_ == 'full'))
    x, y, h, hai = map(np.concatenate, (xs, ys, hs, hai))
    c = bo._gan_nhat(x, y, h, hai)
    ok = c >= 0
    nhan = np.zeros(len(c_bang), dtype=bool)
    nhan[c[ok]] = True
    f = ok & hai
    hai_chieu = f & (nguoc[np.where(ok, c, 0)] >= 0)
    nguoc_trong = hai_chieu & ~nhan[np.where(hai_chieu, nguoc[np.where(ok, c, 0)], 0)]
    # (b): ứng viên không phải cầu, cùng hướng, gần nhất — so với khoảng cách tới cạnh cầu đã nhận.
    tren_cau = np.flatnonzero(ok & la_cau[np.where(ok, c, 0)])
    de_nham = 0
    xy = bo.xy
    x_min, x_max = np.minimum(xy[:, 0], xy[:, 2]) - 20, np.maximum(xy[:, 0], xy[:, 2]) + 20
    y_min, y_max = np.minimum(xy[:, 1], xy[:, 3]) - 20, np.maximum(xy[:, 1], xy[:, 3]) + 20
    for j in tren_cau:
        gx = np.flatnonzero((x_min <= x[j]) & (x[j] <= x_max) & (y_min <= y[j]) & (y[j] <= y_max))
        dx, dy = xy[gx, 2] - xy[gx, 0], xy[gx, 3] - xy[gx, 1]
        dd = dx * dx + dy * dy
        t = np.clip(((x[j] - xy[gx, 0]) * dx + (y[j] - xy[gx, 1]) * dy) / np.where(dd > 0, dd, 1), 0, 1)
        kc = np.hypot(xy[gx, 0] + t * dx - x[j], xy[gx, 1] + t * dy - y[j])
        lech = np.abs((bo.huong[gx] - h[j] + 180) % 360 - 180)
        if hai[j]:
            lech = np.minimum(lech, 180 - lech)
        kc_nhan = kc[gx == c[j]].min()
        khac = (~la_cau[gx]) & (lech <= 35) & (kc <= kc_nhan + 3)
        de_nham += bool(khac.any())
    ra = {'mau': int(len(c)), 'mau_ghep': int(ok.sum()), 'mau_full': int(f.sum()),
          'mau_full_duong_hai_chieu': int(hai_chieu.sum()), 'mau_full_chieu_nguoc_khong_co_so': int(nguoc_trong.sum()),
          'mau_tren_cau': int(len(tren_cau)), 'mau_tren_cau_de_nham_tang': int(de_nham)}
    print(f'\nPHAM VI (ca lan chup, {ra["mau"]:,} mau, ghep {ra["mau_ghep"]:,}):')
    print(f'  (a) mau "full": {ra["mau_full"]:,}; tren duong hai chieu {ra["mau_full_duong_hai_chieu"]:,}; '
          f'chieu nguoc KHONG nhan mau nao {ra["mau_full_chieu_nguoc_khong_co_so"]:,} '
          f'({100 * ra["mau_full_chieu_nguoc_khong_co_so"] / max(ra["mau_ghep"], 1):.1f}% so mau da ghep)')
    print(f'  (b) mau tren cau / cau vuot: {ra["mau_tren_cau"]:,} ({100 * ra["mau_tren_cau"] / max(ra["mau_ghep"], 1):.1f}%); '
          f'co canh khong-cau cung huong xa hon <= 3 m: {ra["mau_tren_cau_de_nham_tang"]:,} '
          f'({100 * ra["mau_tren_cau_de_nham_tang"] / max(ra["mau_ghep"], 1):.2f}% so mau da ghep)')
    return ra


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    bo = BoGhep.nap()
    canh = pd.read_parquet(TEP_CANH, columns=['chi_so', 'loai', 'ten']).set_index('chi_so')
    canh['ten'] = canh['ten'].fillna('').astype(str)
    tho = pd.read_parquet(TEP)
    tho = tho[tho['muc'].notna()].reset_index(drop=True)
    thu_tu = np.random.default_rng(HAT).permutation(len(tho))
    chon, dem = [], {'xet': 0, 'qua_ngan': 0, 'khong_ghep': 0}
    for j in thu_tu:
        r = tho.iloc[int(j)]
        dem['xet'] += 1
        diem = np.asarray(json.loads(r['hinh_hoc']), dtype=float)
        pts = np.column_stack([diem[:, 1] * MX, diem[:, 0] * MY])
        mau = bo._lay_mau(pts) if len(pts) >= 2 else None
        if mau is None:
            dem['qua_ngan'] += 1
            continue
        x, y, h = mau
        c = bo._gan_nhat(x, y, h, np.full(len(x), r['phu'] == 'full'))
        if not (c >= 0).any():
            dem['khong_ghep'] += 1
            continue
        theo = pd.Series([(canh.at[int(i), 'ten'], canh.at[int(i), 'loai']) for i in c[c >= 0]]).value_counts()
        dai = float(np.hypot(*np.diff(pts, axis=0).T).sum())
        chon.append({'x': x, 'y': y, 'h': h, 'c': c, 'pts': pts, 'loai_duong': str(r['loai_duong']), 'phu': str(r['phu']),
                     'muc': float(r['muc']), 'dai': dai, 'theo_duong': theo.to_dict(), 'dong_tho': int(j),
                     'giua': [float(diem[len(diem) // 2, 0]), float(diem[len(diem) // 2, 1])]})
        if len(chon) == SO_DOAN:
            break
    os.makedirs(RA, exist_ok=True)
    ra = []
    for k, d in enumerate(chon, 1):
        ve(k, d, bo, canh, os.path.join(RA, f'doan_{k:02d}.png'))
        ok = d['c'] >= 0
        ra.append({'stt': k, 'dong_tho': d['dong_tho'], 'loai_duong': d['loai_duong'], 'phu': d['phu'], 'muc': d['muc'],
                   'dai_m': round(d['dai']), 'so_mau': int(len(ok)), 'mau_ghep': int(ok.sum()),
                   'canh_ghep': sorted({int(i) for i in d['c'][ok]}),
                   'theo_duong': [{'ten': t, 'loai': l, 'mau': int(n)} for (t, l), n in d['theo_duong'].items()],
                   'osm': f'https://www.openstreetmap.org/?mlat={d["giua"][0]:.5f}&mlon={d["giua"][1]:.5f}#map=18/'
                          f'{d["giua"][0]:.5f}/{d["giua"][1]:.5f}'})
        duong = '; '.join(f'{t or "(khong ten)"} [{l}] {n}' for (t, l), n in d['theo_duong'].items())
        print(f'#{k:02d} {d["loai_duong"]:<18} {d["phu"]:<9} {d["dai"]:6.0f} m  ghep {int(ok.sum()):3d}/{len(ok):3d}  {duong}')
    print('ban do:', ban_do(chon, bo, canh, ra))
    pv = pham_vi(bo, tho)
    with open(os.path.join(RA, 'kiem_tay_ghep.json'), 'w', encoding='utf-8') as f:
        json.dump({'tep': os.path.relpath(TEP, GOC), 'hat': HAT, 'dem': dem, 'doan': ra, 'pham_vi': pv}, f,
                  ensure_ascii=False, indent=1)
    print(f'\nxet {dem["xet"]} doan theo thu tu ngau nhien: qua ngan {dem["qua_ngan"]}, khong ghep duoc mau nao '
          f'{dem["khong_ghep"]}, lay {len(chon)} -> {RA}')


if __name__ == '__main__':
    main()
