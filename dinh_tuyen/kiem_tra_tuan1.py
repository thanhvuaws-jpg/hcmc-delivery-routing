"""
Kiểm tra đồ thị + bộ tìm đường của tuần 1 ("xong khi" trong note/KE_HOACH.md):
  tìm được đường giữa hai điểm bất kỳ trong khu vực, không đi ngược chiều,
  không vào đường cấm xe máy, không rẽ sai luật cấm rẽ.

Chạy:   python kiem_tra_tuan1.py
Kết quả: in bảng kết quả + ket_qua/tuan1_ban_do.html (mở qua máy chủ xem trước).
"""
import itertools
import json
import os
import sys
import time

from tim_duong import BanDo

DIA_DIEM = {
    'Chợ Bến Thành':        (10.7725, 106.6980),
    'Ngã tư Hàng Xanh':     (10.8010, 106.7110),
    'Lăng Cha Cả':          (10.8005, 106.6605),
    'Ngã sáu Cộng Hòa':     (10.7650, 106.6815),
    'Thảo Cầm Viên':        (10.7875, 106.7050),
    'Ga Sài Gòn':           (10.7820, 106.6770),
    'ĐH Bách Khoa':         (10.7725, 106.6578),
    'Ngã tư Phú Nhuận':     (10.7990, 106.6800),
    'Cầu Khánh Hội (Q4)':   (10.7650, 106.7030),
    'Chợ Bình Tây':         (10.7495, 106.6510),
}

THU_MUC_RA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ket_qua')


def soat_luat(bd, kq):
    """Đếm lỗi: cạnh không có trong đồ thị (ngược chiều/đường bị loại) và rẽ sai luật."""
    loi_canh = sum(1 for a, b in zip(kq['nut'], kq['nut'][1:]) if not bd.G.has_edge(a, b))
    loi_re = 0
    for (w_vao, w_ra), nut in zip(zip(kq['duong_dung'], kq['duong_dung'][1:]), kq['nut'][1:-1]):
        if not bd._duoc_re(w_vao, nut, w_ra):
            loi_re += 1
    return loi_canh, loi_re


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bd = BanDo.nap()
    print(f'Nap do thi {time.time() - t0:.1f}s — {bd.thong_ke["nut"]:,} nut, {bd.thong_ke["canh"]:,} canh\n')

    hang = []
    khac_khi_bo_luat = 0
    tong_loi = 0
    thoi_gian = []
    for (a, pa), (b, pb) in itertools.permutations(DIA_DIEM.items(), 2):
        t = time.time()
        ngan = bd.tim(pa, pb, 'dai')
        nhanh = bd.tim(pa, pb, 'tg')
        thoi_gian.append((time.time() - t) / 2)
        bo_luat = bd.tim(pa, pb, 'dai', ap_luat_re=False)
        if ngan is None or nhanh is None:
            hang.append((a, b, None, None, None))
            tong_loi += 1
            continue
        l1, r1 = soat_luat(bd, ngan)
        l2, r2 = soat_luat(bd, nhanh)
        tong_loi += l1 + r1 + l2 + r2
        if bo_luat and bo_luat['dai_m'] != ngan['dai_m']:
            khac_khi_bo_luat += 1
        hang.append((a, b, ngan, nhanh, bo_luat))

    so_cap = len(hang)
    tim_duoc = sum(1 for h in hang if h[2])
    print(f'{"Tu":<22}{"Den":<22}{"ngan nhat":>11}{"nhanh nhat":>12}{"phut":>6}')
    for a, b, ngan, nhanh, _ in hang[:12]:
        if ngan:
            print(f'{a:<22}{b:<22}{ngan["dai_m"]:>9} m{nhanh["dai_m"]:>10} m{nhanh["tg_s"] / 60:>6.1f}')
    print('...')
    print(f'\nSo cap diem: {so_cap} | tim duoc duong: {tim_duoc}/{so_cap}')
    print(f'Loi luat (nguoc chieu / duong cam / re sai): {tong_loi}')
    print(f'So cap ma luat cam re lam doi tuyen ngan nhat: {khac_khi_bo_luat}')
    print(f'Thoi gian tim 1 tuyen: trung binh {1000 * sum(thoi_gian) / len(thoi_gian):.0f} ms, '
          f'cham nhat {1000 * max(thoi_gian):.0f} ms')

    # Bản đồ: 3 cặp tiêu biểu, mỗi cặp vẽ đường ngắn nhất + nhanh nhất.
    os.makedirs(THU_MUC_RA, exist_ok=True)
    chon = [('Chợ Bến Thành', 'Ngã tư Hàng Xanh'), ('Lăng Cha Cả', 'Chợ Bến Thành'),
            ('Chợ Bình Tây', 'Thảo Cầm Viên')]
    lop = []
    for a, b in chon:
        for kieu, mau in (('dai', '#c0392b'), ('tg', '#1f6feb')):
            kq = bd.tim(DIA_DIEM[a], DIA_DIEM[b], kieu)
            lop.append({'ten': f'{a} → {b} ({"ngắn nhất" if kieu == "dai" else "nhanh nhất"}: '
                                f'{kq["dai_m"] / 1000:.2f} km, {kq["tg_s"] / 60:.0f} phút)',
                        'mau': mau, 'toa_do': kq['toa_do'], 'duong': kq['ten_duong']})
    with open(os.path.join(THU_MUC_RA, 'tuan1_ban_do.html'), 'w', encoding='utf-8') as f:
        f.write(TRANG.replace('__DU_LIEU__', json.dumps(lop, ensure_ascii=False))
                     .replace('__DIA_DIEM__', json.dumps(DIA_DIEM, ensure_ascii=False)))
    print('\nBan do ->', os.path.join(THU_MUC_RA, 'tuan1_ban_do.html'))
    return tong_loi == 0 and tim_duoc == so_cap


TRANG = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tuần 1 — Tìm đường xe máy</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body{margin:0;height:100%;font:14px system-ui,sans-serif}#ban_do{height:100%}
.chu_thich{background:#fff;padding:8px 10px;border-radius:6px;max-width:360px;line-height:1.5}
.chu_thich b{display:inline-block;width:18px;height:4px;vertical-align:middle;margin-right:6px}</style>
</head><body><div id="ban_do"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const lop = __DU_LIEU__, diaDiem = __DIA_DIEM__;
const bd = L.map('ban_do').setView([10.785, 106.685], 14);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'}).addTo(bd);
const nhom = {};
lop.forEach((l, i) => {
  const d = L.polyline(l.toa_do, {color: l.mau, weight: l.mau === '#c0392b' ? 6 : 3,
                                  opacity: .8, dashArray: l.mau === '#c0392b' ? null : '6 6'});
  d.bindPopup('<b>' + l.ten + '</b><br>' + l.duong.join(' → '));
  nhom[l.ten] = d.addTo(bd);
});
Object.entries(diaDiem).forEach(([ten, p]) => L.circleMarker(p, {radius: 5, color: '#333'}).bindTooltip(ten).addTo(bd));
L.control.layers(null, nhom, {collapsed: false}).addTo(bd);
const ct = L.control({position: 'bottomleft'});
ct.onAdd = () => { const d = L.DomUtil.create('div', 'chu_thich');
  d.innerHTML = '<b style="background:#c0392b"></b>ngắn nhất (mét)<br><b style="background:#1f6feb"></b>nhanh nhất (tốc độ đường trống)'
    + '<br><small>Đồ thị xe máy từ OSM: một chiều, cấm xe máy, cấm rẽ. Bấm vào tuyến để xem tên đường.</small>'; return d; };
ct.addTo(bd);
</script></body></html>
"""

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
