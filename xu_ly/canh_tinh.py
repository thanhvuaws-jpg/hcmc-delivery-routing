"""
Đặc trưng TĨNH của từng cạnh đồ thị (không đổi theo thời gian) — dùng cho mô hình và khai phá.

Đầu vào: du_lieu/do_thi/do_thi_xe_may.pkl, canh.parquet, ban_do/osm_vung_tomtom.json (thẻ
của từng con đường), ban_do/osm_poi_vung_tomtom.json (D16), toạ độ 5 điểm thời tiết.

Đầu ra: du_lieu/bac/canh_tinh.parquet — mỗi cạnh (chi_so) một dòng:
  loai, dai, toc_do_mac_dinh, mot_chieu, so_lan, gioi_han (km/h, thẻ maxspeed), cau, ham,
  bac_vao_u / bac_ra_v (số cạnh vào nút đầu / ra khỏi nút cuối — độ phức tạp nút giao),
  poi_<nhom>_300 (số điểm trong 300 m quanh trung điểm cạnh), kc_<nhom> (m tới điểm gần nhất),
  diem_thoi_tiet (điểm gần nhất trong 5 điểm), x_m, y_m (trung điểm, mét),
  trung_gian (độ trung gian của cạnh, ước lượng từ 300 nút nguồn ngẫu nhiên, seed 42).

Chạy:  python canh_tinh.py
"""
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
sys.path.insert(0, os.path.join(GOC, 'thu_thap'))

from ghep_tomtom import MX, MY, TEP_CANH  # noqa: E402

BAN_DO = os.path.join(GOC, 'du_lieu', 'ban_do')
RA = os.path.join(GOC, 'du_lieu', 'bac', 'canh_tinh.parquet')
BAN_KINH = 300.0
SO_NGUON_TRUNG_GIAN = 300

NHOM_POI = {
    'truong': {('amenity', 'school'), ('amenity', 'kindergarten')},
    'dai_hoc': {('amenity', 'university'), ('amenity', 'college')},
    'cho': {('amenity', 'marketplace')},
    'sieu_thi': {('shop', 'supermarket'), ('shop', 'mall'), ('shop', 'department_store')},
    'benh_vien': {('amenity', 'hospital'), ('amenity', 'clinic')},
    'tram_bus': {('highway', 'bus_stop'), ('amenity', 'bus_station')},
    'tho_cung': {('amenity', 'place_of_worship')},
    'bai_xe': {('amenity', 'parking')},
}


def so(chuoi):
    """'2', '2;3', '40 km/h' -> số đầu tiên, không đọc được thì NaN."""
    try:
        return float(str(chuoi).replace(';', ' ').split()[0])
    except (ValueError, IndexError):
        return np.nan


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    from do_thi import TEP_RA
    with open(TEP_RA, 'rb') as f:
        G = pickle.load(f)['G']
    canh = pd.read_parquet(TEP_CANH)
    ds = list(G.edges(data=True))
    assert len(ds) == len(canh), 'canh.parquet không khớp đồ thị — chạy lại BoGhep.dung()'

    # Thẻ OSM của con đường chứa cạnh.
    with open(os.path.join(BAN_DO, 'osm_vung_tomtom.json'), encoding='utf-8') as f:
        the = {e['id']: e.get('tags', {}) for e in json.load(f)['elements'] if e['type'] == 'way'}
    tg = [the.get(w, {}) for w in canh['way']]
    bang = canh[['chi_so', 'loai', 'dai', 'ten']].copy()
    bang['toc_do_mac_dinh'] = np.array([d['toc_do'] for _, _, d in ds], dtype=np.float32)
    bang['mot_chieu'] = [t.get('oneway') in ('yes', '1', '-1', 'true') or t.get('junction') == 'roundabout'
                         for t in tg]
    bang['so_lan'] = np.array([so(t.get('lanes')) for t in tg], dtype=np.float32)
    bang['gioi_han'] = np.array([so(t.get('maxspeed')) for t in tg], dtype=np.float32)
    bang['cau'] = [t.get('bridge') not in (None, 'no') for t in tg]
    bang['ham'] = [t.get('tunnel') not in (None, 'no') for t in tg]
    bang['bac_vao_u'] = np.array([G.in_degree(u) for u, _, _ in ds], dtype=np.uint8)
    bang['bac_ra_v'] = np.array([G.out_degree(v) for _, v, _ in ds], dtype=np.uint8)

    # Trung điểm cạnh (mét, cùng hệ với ghep_tomtom).
    lat = np.array([(G.nodes[u]['y'] + G.nodes[v]['y']) / 2 for u, v, _ in ds])
    lon = np.array([(G.nodes[u]['x'] + G.nodes[v]['x']) / 2 for u, v, _ in ds])
    xy = np.column_stack([lon * MX, lat * MY])
    bang['x_m'], bang['y_m'] = xy[:, 0].astype(np.float32), xy[:, 1].astype(np.float32)

    # Điểm thu hút giao thông.
    with open(os.path.join(BAN_DO, 'osm_poi_vung_tomtom.json'), encoding='utf-8') as f:
        poi = json.load(f)['elements']
    for nhom, khoa in NHOM_POI.items():
        p = [(e.get('lat') or e.get('center', {}).get('lat'), e.get('lon') or e.get('center', {}).get('lon'))
             for e in poi if any(e.get('tags', {}).get(k) == v for k, v in khoa)]
        p = np.array([(b * MX, a * MY) for a, b in p if a is not None])
        cay = cKDTree(p)
        bang[f'poi_{nhom}_300'] = cay.query_ball_point(xy, BAN_KINH, return_length=True).astype(np.uint16)
        bang[f'kc_{nhom}'] = cay.query(xy)[0].astype(np.float32)
        print(f'  {nhom:<10} {len(p):>5} diem | canh co >=1 trong 300 m: {(bang[f"poi_{nhom}_300"] > 0).mean():.1%}')

    # Điểm thời tiết gần nhất (Voronoi của 5 điểm).
    from tai_thoi_tiet import DIEM
    ten = list(DIEM)
    tt = np.array([(DIEM[t][1] * MX, DIEM[t][0] * MY) for t in ten])
    bang['diem_thoi_tiet'] = pd.Categorical(np.array(ten)[cKDTree(tt).query(xy)[1]], categories=ten)

    # Độ trung gian (edge betweenness) ước lượng: cạnh nằm trên nhiều đường ngắn nhất = trục chính.
    import networkx as nx
    t1 = time.time()
    tg_g = nx.edge_betweenness_centrality(G, k=SO_NGUON_TRUNG_GIAN, weight='dai', seed=42, normalized=True)
    bang['trung_gian'] = np.array([tg_g[(u, v)] for u, v, _ in ds], dtype=np.float32)
    print(f'  trung gian: {SO_NGUON_TRUNG_GIAN} nguon, {time.time() - t1:.0f}s')

    bang.to_parquet(RA, index=False)
    print(f'{len(bang):,} canh, {bang.shape[1]} cot -> {RA} ({time.time() - t0:.0f}s)')
    print(f'  so_lan co gia tri: {bang["so_lan"].notna().mean():.1%}, gioi_han: {bang["gioi_han"].notna().mean():.1%}, '
          f'mot chieu: {bang["mot_chieu"].mean():.1%}')
    top = bang.nlargest(8, 'trung_gian')[['ten', 'loai', 'trung_gian']]
    print('  canh trung gian cao nhat:', ', '.join(f'{t or "?"} ({l})' for t, l in zip(top['ten'], top['loai'])))


if __name__ == '__main__':
    main()
