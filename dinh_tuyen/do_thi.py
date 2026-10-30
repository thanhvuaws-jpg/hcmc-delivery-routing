"""
Dựng đồ thị đường cho XE MÁY từ tệp OpenStreetMap đã tải (thu_thap/tai_osm.py).

Đồ thị có hướng: mỗi cạnh là một đoạn giữa hai nút OSM liền nhau trên cùng một
con đường, đi được theo đúng chiều đó.

Luật đang áp:
  - Bỏ cao tốc (motorway) — cấm xe máy ở Việt Nam — và lối đi bộ, bậc thang,
    đường đang thi công, bãi đỗ xe.
  - Bỏ đường ghi motorcycle=no; bỏ đường access/vehicle/motor_vehicle = no/private
    trừ khi ghi rõ motorcycle=yes.
  - Một chiều: oneway=yes/-1, vòng xoay; oneway:motorcycle=no thì xe máy đi hai chiều.
  - Cấm rẽ: quan hệ restriction có "via" là một NÚT (no_*/only_*). Loại "via" là
    cả một con đường thì chưa xử lý — đếm và ghi vào thống kê. Luật ghi
    except=motorcycle (rất phổ biến ở TP.HCM: "cấm rẽ, trừ xe máy") không áp.
  - Cấm theo giờ (restriction:conditional): lưu riêng vào 'theo_gio', áp ở tuần 7.

Tốc độ: tạm dùng tốc độ "đường trống" theo loại đường cho xe máy nội đô. Từ tuần 5
sẽ thay bằng tốc độ dự báo theo từng đoạn và từng khung giờ.

Chạy:   python do_thi.py
Kết quả: ../du_lieu/do_thi/do_thi_xe_may.pkl
"""
import json
import math
import os
import pickle
import sys
import time
from collections import Counter

import networkx as nx

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# Toàn vùng 30 ô TomTom (QĐ-006, 30/10/2026). Bản cũ osm_trung_tam.json giữ làm gốc.
TEP_OSM = os.path.join(GOC, 'du_lieu', 'ban_do', 'osm_vung_tomtom.json')
TEP_RA = os.path.join(GOC, 'du_lieu', 'do_thi', 'do_thi_xe_may.pkl')

# km/h khi đường trống, xe máy, nội đô TP.HCM.
TOC_DO = {
    'trunk': 40, 'trunk_link': 30,
    'primary': 35, 'primary_link': 25,
    'secondary': 30, 'secondary_link': 25,
    'tertiary': 28, 'tertiary_link': 22,
    'unclassified': 25, 'road': 20,
    'residential': 20, 'living_street': 10,
    'service': 15,          # phần lớn hẻm ở TP.HCM được vẽ là service hoặc residential
}

# service kiểu này là lối trong bãi xe / làn mua hàng, không phải hẻm.
SERVICE_BO = {'parking_aisle', 'drive-through', 'emergency_access'}


def khoang_cach(lat1, lon1, lat2, lon2):
    """Mét, công thức haversine."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def xe_may_duoc_di(t):
    if t.get('highway') not in TOC_DO:
        return False
    if t.get('highway') == 'service' and t.get('service') in SERVICE_BO:
        return False
    if t.get('motorcycle') == 'no':
        return False
    if t.get('motorcycle') in ('yes', 'designated', 'permissive', 'destination'):
        return True
    for k in ('motor_vehicle', 'vehicle', 'access'):
        if t.get(k) in ('no', 'private'):
            return False
    return True


def chieu_di(t):
    """1 = theo chiều vẽ, -1 = ngược chiều vẽ, 0 = hai chiều."""
    if t.get('oneway:motorcycle') == 'no':
        return 0
    ow = t.get('oneway')
    if ow in ('yes', 'true', '1'):
        return 1
    if ow in ('-1', 'reverse'):
        return -1
    if t.get('junction') in ('roundabout', 'circular') and ow != 'no':
        return 1
    return 0


def toc_do(t):
    v = TOC_DO[t['highway']]
    try:
        gioi_han = float(str(t.get('maxspeed', '')).split()[0])
        v = min(v, gioi_han)
    except (ValueError, IndexError):
        pass
    return v


def luat_cam_re(quan_he, duong_giu):
    """
    Trả về (cam, chi, bo_qua):
      cam[(tu_duong, nut_via)] = {den_duong, ...}   — cấm đi sang
      chi[(tu_duong, nut_via)] = den_duong          — chỉ được đi sang
    """
    cam, chi, bo_qua = {}, {}, Counter()
    theo_gio = []
    for r in quan_he:
        t = r.get('tags', {})
        if 'motorcycle' in t.get('except', ''):
            bo_qua['tru_xe_may'] += 1
            continue
        loai = t.get('restriction:motorcycle') or t.get('restriction')
        if not loai:
            # Luật theo giờ, vd "no_left_turn @ (Mo-Fr 06:00-09:00)". Chưa áp ở
            # tuần 1 — giữ nguyên chuỗi để bộ định tuyến theo thời điểm (tuần 7) đọc.
            if t.get('restriction:conditional'):
                theo_gio.append({'id': r['id'], 'dieu_kien': t['restriction:conditional'],
                                 'members': r['members']})
                bo_qua['theo_gio_de_tuan_7'] += 1
            else:
                bo_qua['khong_co_loai'] += 1
            continue
        tu = [m['ref'] for m in r['members'] if m['role'] == 'from' and m['type'] == 'way']
        den = [m['ref'] for m in r['members'] if m['role'] == 'to' and m['type'] == 'way']
        via = [m for m in r['members'] if m['role'] == 'via']
        if len(via) != 1 or via[0]['type'] != 'node' or not tu or not den:
            bo_qua['via_la_duong'] += 1
            continue
        if not (set(tu) & duong_giu and set(den) & duong_giu):
            bo_qua['ngoai_do_thi'] += 1
            continue
        nut = via[0]['ref']
        for a in tu:
            if loai.startswith('no_'):
                cam.setdefault((a, nut), set()).update(den)
            elif loai.startswith('only_'):
                chi[(a, nut)] = den[0]
            else:
                bo_qua['loai_la'] += 1
    return cam, chi, bo_qua, theo_gio


def dung():
    t0 = time.time()
    with open(TEP_OSM, encoding='utf-8') as f:
        osm = json.load(f)
    el = osm['elements']
    nut = {e['id']: (e['lat'], e['lon']) for e in el if e['type'] == 'node'}
    duong = [e for e in el if e['type'] == 'way']
    quan_he = [e for e in el if e['type'] == 'relation']

    G = nx.DiGraph()
    dem = Counter()
    duong_giu = set()
    for w in duong:
        t = w.get('tags', {})
        if not xe_may_duoc_di(t):
            dem['bo_' + str(t.get('highway'))] += 1
            continue
        nds = [n for n in w['nodes'] if n in nut]
        if len(nds) < 2:
            continue
        duong_giu.add(w['id'])
        huong = chieu_di(t)
        v = toc_do(t)
        ten = t.get('name', '')
        for a, b in zip(nds, nds[1:]):
            d = khoang_cach(*nut[a], *nut[b])
            thuoc_tinh = dict(dai=d, tg=d / (v / 3.6), way=w['id'], loai=t['highway'], ten=ten, toc_do=v)
            if huong in (0, 1):
                G.add_edge(a, b, **thuoc_tinh)
            if huong in (0, -1):
                G.add_edge(b, a, **thuoc_tinh)
        dem['mot_chieu' if huong else 'hai_chieu'] += 1

    for n in G.nodes:
        G.nodes[n]['y'], G.nodes[n]['x'] = nut[n]

    # Thành phần liên thông mạnh lớn nhất: chỉ "bắt" điểm đi/đến vào đây,
    # để không bao giờ chọn trúng một khúc cụt một chiều không có lối ra.
    tplt = max(nx.strongly_connected_components(G), key=len)

    cam, chi, bo_qua, theo_gio = luat_cam_re(quan_he, duong_giu)

    thong_ke = {
        'nut': G.number_of_nodes(), 'canh': G.number_of_edges(),
        'duong_giu': len(duong_giu),
        'duong_mot_chieu': dem['mot_chieu'], 'duong_hai_chieu': dem['hai_chieu'],
        'nut_trong_tplt_lon_nhat': len(tplt),
        'luat_cam': sum(len(v) for v in cam.values()), 'luat_chi': len(chi),
        'luat_bo_qua': dict(bo_qua),
        'duong_bo_theo_loai': {k[3:]: v for k, v in dem.most_common() if k.startswith('bo_')},
        'tong_km': round(sum(d['dai'] for _, _, d in G.edges(data=True)) / 1000, 1),
    }
    os.makedirs(os.path.dirname(TEP_RA), exist_ok=True)
    with open(TEP_RA, 'wb') as f:
        pickle.dump({'G': G, 'tplt': tplt, 'cam': cam, 'chi': chi, 'theo_gio': theo_gio, 'thong_ke': thong_ke,
                     'nguon': osm.get('nguon'), 'khu_vuc': osm.get('khu_vuc')}, f)
    thong_ke['giay'] = round(time.time() - t0, 1)
    return thong_ke


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    tk = dung()
    print(json.dumps(tk, ensure_ascii=False, indent=2))
    print('->', os.path.abspath(TEP_RA))
