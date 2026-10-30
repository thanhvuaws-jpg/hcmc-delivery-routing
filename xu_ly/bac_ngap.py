"""
Tầng bạc D8: điểm nguy cơ ngập (PC08, 06/10/2026) -> tập cạnh đồ thị.

Đầu vào: thu_thap/chep_tay/ngap_pc08_2026-10-06.csv (xem README cùng thư mục).

Cách ghép, theo tên đường OSM (bỏ chữ "Đường", không phân biệt hoa thường, bỏ tên "Hẻm …"):
  giao_lo   có cột giao: nút chung của đường chính và đường giao -> mọi cạnh của HAI đường trong
            BAN_KINH_GIAO m quanh nút đó.
  doan      có cả tu và den: đi dọc đường chính giữa nút giao với tu và nút giao với den
            (đường đi ngắn nhất trên riêng các cạnh của đường chính, lấy cả hai chiều).
  gan_moc   chỉ có tu hoặc den: cạnh đường chính trong BAN_KINH_MOC m quanh nút giao đó.
  ca_tuyen  dòng chỉ ghi "Đường X.": cả con đường trong vùng bản đồ (thô — ghi rõ để mô hình biết).
            Có chi tiết (số nhà, phường, chân cầu…) mà không định vị được thì bỏ, không đánh cả tuyến.
  Địa danh không có tên đường (chân cầu…): tìm cạnh có tên chứa từ khóa trong DIA_DANH.
Bỏ qua: khu vực ngoài TP.HCM cũ (Bình Dương, Bà Rịa – Vũng Tàu), tên đường chung chung
("Đường số 2"…) khi không có điểm giao để khoanh vùng.

Đầu ra:
  du_lieu/bac/ngap_canh.parquet   chi_so, stt, nguyen_nhan, cach_khop
  du_lieu/bac/ngap_diem.parquet   mỗi điểm: trang_thai, so_canh, dai_m
Chạy:  python bac_ngap.py
"""
import os
import pickle
import re
import sys
import unicodedata
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ghep_tomtom import MX, MY, TEP_CANH  # noqa: E402

TEP = os.path.join(GOC, 'thu_thap', 'chep_tay', 'ngap_pc08_2026-10-06.csv')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
BAN_KINH_GIAO, BAN_KINH_MOC, NUT_GAN_M = 100.0, 300.0, 60.0
NGOAI = ('Bình Dương', 'Vũng Tàu')
DIA_DANH = {28: 'cầu rạch chiếc', 62: 'cầu bà tàng', 107: 'cầu lò gốm', 115: 'cầu rạch chiếc'}
DONG_NGHIA = {'cách mạng tháng tám': 'cách mạng tháng 8'}


def chuan(ten):
    """'Đường số 32' / 'Đường 32' / '32' -> '32'; 'Đường Võ Văn Kiệt' -> 'võ văn kiệt'."""
    t = unicodedata.normalize('NFC', str(ten)).strip().lower()
    t = re.sub(r'^đường\s+', '', t)
    t = re.sub(r'^số\s+', '', t)
    t = re.sub(r'\s+', ' ', t)
    return DONG_NGHIA.get(t, t)


def chung_chung(ten):
    return re.fullmatch(r'\d+[a-z]?', chuan(ten)) is not None


def chi_ten_duong(r):
    """Dòng chỉ ghi 'Đường X.' (không đoạn, không số nhà, không phường) -> được đánh dấu cả tuyến.
    Có chi tiết mà không định vị được thì KHÔNG đánh cả tuyến (vd 'Lê Văn Lương: đoạn qua xã
    Nhà Bè' — đoạn đó ngoài bản đồ, đánh cả tuyến sẽ gắn nhầm phần ở Quận 7)."""
    return not r.khu_vuc and chuan(r.mo_ta.rstrip('.')) == chuan(r.duong)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from do_thi import TEP_RA
    with open(TEP_RA, 'rb') as f:
        G = pickle.load(f)['G']
    canh = pd.read_parquet(TEP_CANH)
    chi_so = {(u, v): i for i, u, v in zip(canh['chi_so'], canh['u'], canh['v'])}
    theo_ten = defaultdict(set)
    for i, ten in zip(canh['chi_so'], canh['ten']):
        if ten and not ten.lower().startswith('hẻm'):
            theo_ten[chuan(ten)].add(int(i))
    uv = canh[['u', 'v']].to_numpy()
    toa = {n: (G.nodes[n]['x'] * MX, G.nodes[n]['y'] * MY) for n in G.nodes}
    giua = np.array([((toa[u][0] + toa[v][0]) / 2, (toa[u][1] + toa[v][1]) / 2) for u, v in uv])
    dai = canh['dai'].to_numpy()

    def nut_cua(tap):
        return {n for i in tap for n in uv[i]}

    def gan(tap, nut, r):
        """Cạnh trong tap có trung điểm cách một trong các nút <= r mét."""
        if not tap or not nut:
            return set()
        t = np.fromiter(tap, dtype=np.int64)
        p = np.array([toa[n] for n in nut])
        d = np.min(np.hypot(giua[t, None, 0] - p[None, :, 0], giua[t, None, 1] - p[None, :, 1]), axis=1)
        return set(t[d <= r].tolist())

    def nut_giao(chinh, ten_kia):
        """Nút giao giữa đường chính và đường kia. Đường đôi / nút giao có làn nối thì hai đường
        không chung nút: nhận các nút của đường chính cách đường kia <= NUT_GAN_M mét."""
        kia = set()
        for t in ten_kia.split(';'):
            kia |= theo_ten.get(chuan(t), set())
        a, b = nut_cua(chinh), nut_cua(kia)
        chung = a & b
        if chung or not a or not b:
            return chung, kia
        pa, pb = np.array([toa[n] for n in a]), np.array([toa[n] for n in b])
        from scipy.spatial import cKDTree
        d, _ = cKDTree(pb).query(pa)
        return {n for n, k in zip(a, d) if k <= NUT_GAN_M}, kia

    ds = pd.read_csv(TEP, dtype=str).fillna('')
    hang, diem = [], []
    for r in ds.itertuples(index=False):
        stt, tt, cach = int(r.stt), '', ''
        tap = set()
        chinh = theo_ten.get(chuan(r.duong), set()) if r.duong else set()
        if any(k in r.khu_vuc for k in NGOAI):
            tt = 'ngoai_vung'
        elif not r.duong:
            kw = DIA_DANH.get(stt)
            tap = {i for t, s in theo_ten.items() if kw and kw in t for i in s}
            cach, tt = ('dia_danh', 'khop') if tap else ('', 'chua_dinh_vi')
        elif not chinh:
            tt = 'khong_thay_ten'               # thường là đường ngoài vùng bản đồ
        elif r.giao:
            nut, kia = nut_giao(chinh, r.giao)
            tap = gan(chinh | kia, nut, BAN_KINH_GIAO)
            cach, tt = ('giao_lo', 'khop') if tap else ('', 'khong_thay_nut_giao')
        elif r.tu and r.den:
            a, _ = nut_giao(chinh, r.tu)
            b, _ = nut_giao(chinh, r.den)
            if a and b:
                H = nx.Graph()
                H.add_weighted_edges_from((uv[i][0], uv[i][1], dai[i]) for i in chinh)
                tot = None
                for x in a:
                    try:
                        d, p = nx.single_source_dijkstra(H, x)
                    except nx.NodeNotFound:
                        continue
                    for y in b:
                        if y in d and (tot is None or d[y] < tot[0]):
                            tot = (d[y], p[y])
                if tot:
                    p = tot[1]
                    tap = {chi_so[e] for x, y in zip(p, p[1:]) for e in ((x, y), (y, x)) if e in chi_so}
            if tap:
                cach, tt = 'doan', 'khop'
            else:
                moc = a or b
                tap = gan(chinh, moc, BAN_KINH_MOC)
                cach, tt = ('gan_moc', 'khop') if tap else ('', 'khong_thay_nut_giao')
        elif r.tu or r.den:
            moc, _ = nut_giao(chinh, r.tu or r.den)
            tap = gan(chinh, moc, BAN_KINH_MOC)
            cach, tt = ('gan_moc', 'khop') if tap else ('', 'khong_thay_nut_giao')
        elif chung_chung(r.duong):
            tt = 'ten_chung_chung'
        elif chi_ten_duong(r):
            tap, cach, tt = chinh, 'ca_tuyen', 'khop'
        else:
            tt = 'co_chi_tiet_khong_dinh_vi'
        for i in tap:
            hang.append((i, stt, r.nguyen_nhan, cach))
        diem.append({'stt': stt, 'nguyen_nhan': r.nguyen_nhan, 'duong': r.duong, 'trang_thai': tt,
                     'cach_khop': cach, 'so_canh': len(tap), 'dai_m': round(float(dai[list(tap)].sum())) if tap else 0,
                     'mo_ta': r.mo_ta})

    nc = pd.DataFrame(hang, columns=['chi_so', 'stt', 'nguyen_nhan', 'cach_khop'])
    nc['chi_so'] = nc['chi_so'].astype(np.int32)
    nc.to_parquet(os.path.join(BAC, 'ngap_canh.parquet'), index=False)
    dd = pd.DataFrame(diem)
    dd.to_parquet(os.path.join(BAC, 'ngap_diem.parquet'), index=False)

    print(f'{len(dd)} diem: {dd["trang_thai"].value_counts().to_dict()}')
    k = dd[dd['trang_thai'] == 'khop']
    print(f'  khop {len(k)} diem ({k.groupby("nguyen_nhan").size().to_dict()}), cach: {k["cach_khop"].value_counts().to_dict()}')
    print(f'  {nc["chi_so"].nunique():,} canh de ngap; mua {nc.loc[nc.nguyen_nhan == "mua", "chi_so"].nunique():,}, '
          f'trieu {nc.loc[nc.nguyen_nhan == "trieu_cuong", "chi_so"].nunique():,}')
    print('  khop:', '; '.join(f'{s}:{d}({c},{n} canh)' for s, d, c, n in
                               zip(k['stt'], k['duong'], k['cach_khop'], k['so_canh'])))


if __name__ == '__main__':
    main()
