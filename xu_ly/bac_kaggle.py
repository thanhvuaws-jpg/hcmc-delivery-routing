"""
Tầng bạc D11 (Kaggle — ĐH Bách Khoa TP.HCM, 07/2020–04/2021, CC0).

Ba bảng:
  du_lieu/bac/kaggle_canh.parquet      đoạn của họ -> cạnh đồ thị của mình
      segment_id, chi_so, ty_trong (phần chiều dài đoạn nằm trên cạnh), cach ('canh' |
      'duong_di' | 'hinh_hoc'), dai_ho (m), dai_minh (m)
  du_lieu/bac/kaggle_toc_do.parquet    báo cáo tốc độ (segment_status.csv)
      thoi_diem (giờ VN), segment_id, toc_do (km/h), co (uint16)
  du_lieu/bac/kaggle_los.parquet       nhãn LOS 30 phút (train.csv)
      khung (giờ VN, đầu khung 30 phút), segment_id, los ('A'..'F'), los_so (0..5), co

Bẫy đã kiểm (30/10/2026):
  - updated_at là UTC ("Z") -> đổi giờ VN.
  - train.csv: cột period ("period_7_30") CŨNG LÀ GIỜ UTC — giờ của nó khớp giờ UTC của
    báo cáo tốc độ cùng đoạn cùng ngày ở 42% dòng, khớp giờ VN chỉ 0,3%. Đổi sang giờ VN
    thì 7h sáng là lúc kẹt nhất (D/E 57%), đúng thực tế; để nguyên sẽ lệch 7 tiếng.
  - Tốc độ = 1 km/h chiếm 23% báo cáo, tối đa 200 km/h; có giây nhận 1.263 báo cáo.

Cờ (bit n-1 = Ln):
  L1 bit 0  toc_do > 80 hoặc toc_do = 0
  L1 bit 8  toc_do = 1 (nghi giá trị mặc định, không phải đo thật) — bit riêng để thử có/không
  L3 bit 2  nhập hàng loạt: giây có > 20 báo cáo, hoặc phút có số báo cáo z > 4 so với cùng giờ
  L8 bit 7  ngày thuộc giai đoạn COVID / quanh Tết (du_lieu/bac/lich.parquet)

Ghép đoạn -> cạnh (mã nút của họ là mã nút OSM):
  1. Hai nút kề nhau trong đồ thị (đúng chiều s -> e): đúng cạnh đó.
  2. Cả hai nút có trong đồ thị: đường đi ngắn nhất s -> e; nhận nếu dài 0,67–1,5 × length của họ.
  3. Còn lại: ghép hình học đoạn thẳng s -> e (toạ độ nodes.csv) bằng BoGhep như TomTom.

Chạy:  python bac_kaggle.py
"""
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))

NGUON = os.path.join(GOC, 'du_lieu', 'kaggle_hcmc')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
CO_L1, CO_L3, CO_L8, CO_MAC_DINH = 1 << 0, 1 << 2, 1 << 7, 1 << 8
LOS = {k: i for i, k in enumerate('ABCDEF')}


def ghep_doan(seg, nut):
    import networkx as nx
    from do_thi import TEP_RA
    from ghep_tomtom import BoGhep
    with open(TEP_RA, 'rb') as f:
        G = pickle.load(f)['G']
    bo = BoGhep.nap()
    chi_so = {(u, v): i for i, (u, v) in enumerate(G.edges())}
    dai = nx.get_edge_attributes(G, 'dai')
    hang, dem = [], {'canh': 0, 'duong_di': 0, 'hinh_hoc': 0, 'khong': 0}
    toa_do = nut.set_index('_id')[['lat', 'long']]
    for sid, s, e, ln in seg[['_id', 's_node_id', 'e_node_id', 'length']].itertuples(index=False):
        if (s, e) in chi_so:
            hang.append((sid, chi_so[(s, e)], 1.0, 'canh', ln, dai[(s, e)]))
            dem['canh'] += 1
            continue
        if s in G and e in G:
            try:
                # cutoff: chỉ loang trong bán kính 1,5 × length, khỏi duyệt cả đồ thị.
                tong, p = nx.single_source_dijkstra(G, s, target=e, cutoff=1.5 * ln, weight='dai')
                if 0.67 * ln <= tong and len(p) <= 30:
                    for a, b in zip(p, p[1:]):
                        hang.append((sid, chi_so[(a, b)], dai[(a, b)] / tong, 'duong_di', ln, tong))
                    dem['duong_di'] += 1
                    continue
            except nx.NetworkXNoPath:
                pass
        if s in toa_do.index and e in toa_do.index:
            (la1, lo1), (la2, lo2) = toa_do.loc[s].to_numpy(), toa_do.loc[e].to_numpy()
            cong, _ = bo.ghep([{'diem': [(la1, lo1), (la2, lo2)],
                                'tt': {'traffic_level': 1.0, 'traffic_road_coverage': 'one_side'}}])
            tong = sum(v[1] for v in cong.values())
            if tong >= 0.5 * ln and tong > 0:
                for c, v in cong.items():
                    hang.append((sid, c, v[1] / tong, 'hinh_hoc', ln, tong))
                dem['hinh_hoc'] += 1
                continue
        dem['khong'] += 1
    bang = pd.DataFrame(hang, columns=['segment_id', 'chi_so', 'ty_trong', 'cach', 'dai_ho', 'dai_minh'])
    bang['chi_so'] = bang['chi_so'].astype(np.int32)
    bang['ty_trong'] = bang['ty_trong'].astype(np.float32)
    bang['ma_do_thi'] = bo.ma_do_thi
    return bang, dem


def co_lich(ngay):
    tep = os.path.join(BAC, 'lich.parquet')
    lich = pd.read_parquet(tep, columns=['ngay', 'giai_doan', 'quanh_tet']).set_index('ngay')
    bat_thuong = lich.index[(lich['giai_doan'] != '') | lich['quanh_tet']]
    return np.where(pd.DatetimeIndex(ngay).normalize().isin(bat_thuong), CO_L8, 0).astype(np.uint16)


def toc_do():
    s = pd.read_csv(os.path.join(NGUON, 'segment_status.csv'), parse_dates=['updated_at'])
    utc = s['updated_at']
    df = pd.DataFrame({
        'thoi_diem': utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None),
        'segment_id': s['segment_id'].astype(np.int32), 'toc_do': s['velocity'].astype(np.float32)})
    co = np.zeros(len(df), dtype=np.uint16)
    v = df['toc_do']
    co[((v > 80) | (v == 0)).to_numpy()] |= CO_L1
    co[(v == 1).to_numpy()] |= CO_MAC_DINH
    # L3: cùng giây quá nhiều báo cáo, hoặc số báo cáo/phút bất thường so với cùng giờ trong ngày.
    giay = utc.dt.floor('s')
    co[(giay.map(giay.value_counts()) > 20).to_numpy()] |= CO_L3
    phut = df['thoi_diem'].dt.floor('min')
    dem_phut = phut.value_counts()
    theo_gio = dem_phut.groupby(dem_phut.index.hour)
    z = (dem_phut - theo_gio.transform('mean')) / theo_gio.transform('std').replace(0, np.nan)
    co[phut.map(z).fillna(0).gt(4).to_numpy()] |= CO_L3
    co |= co_lich(df['thoi_diem'])
    df['co'] = co
    return df.sort_values(['thoi_diem', 'segment_id'], ignore_index=True)


def los():
    t = pd.read_csv(os.path.join(NGUON, 'train.csv'))
    hm = t['period'].str.extract(r'period_(\d+)_(\d+)').astype(int)
    utc = pd.to_datetime(t['date']) + pd.to_timedelta(hm[0], unit='h') + pd.to_timedelta(hm[1], unit='m')
    df = pd.DataFrame({
        'khung': utc + pd.Timedelta(hours=7),           # period là giờ UTC (xem đầu tệp)
        'segment_id': t['segment_id'].astype(np.int32),
        'los': t['LOS'], 'los_so': t['LOS'].map(LOS).astype(np.uint8)})
    df['co'] = co_lich(df['khung'])
    return df.sort_values(['khung', 'segment_id'], ignore_index=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(BAC, exist_ok=True)
    t0 = time.time()
    td = toc_do()
    td.to_parquet(os.path.join(BAC, 'kaggle_toc_do.parquet'), index=False)
    ty = {ten: round(float(((td['co'] & b) > 0).mean()), 4)
          for ten, b in (('L1', CO_L1), ('mac_dinh_1kmh', CO_MAC_DINH), ('L3', CO_L3), ('L8', CO_L8))}
    print(f'toc do: {len(td):,} bao cao, {td["thoi_diem"].min()} -> {td["thoi_diem"].max()} | co: {ty}')
    nh = los()
    nh.to_parquet(os.path.join(BAC, 'kaggle_los.parquet'), index=False)
    gio = nh.groupby(nh['khung'].dt.hour)['los_so'].agg(['size', 'mean']).round(2)
    print(f'LOS: {len(nh):,} nhan; LOS trung binh theo gio VN (0=A..5=F):')
    print('  ' + ' '.join(f'{h}h:{r["mean"]:.1f}(n={int(r["size"])})' for h, r in gio.iterrows()))

    seg = pd.read_csv(os.path.join(NGUON, 'segments.csv'))
    seg = seg[seg['_id'].isin(pd.concat([td['segment_id'], nh['segment_id']]).unique())]
    nut = pd.read_csv(os.path.join(NGUON, 'nodes.csv'))
    bang, dem = ghep_doan(seg, nut)
    bang.to_parquet(os.path.join(BAC, 'kaggle_canh.parquet'), index=False)
    print(f'ghep {len(seg):,} doan co du lieu -> {dem} ({time.time() - t0:.0f}s)')
    co_canh = set(bang['segment_id'])
    print(f'  bao cao toc do tren doan ghep duoc: {td["segment_id"].isin(co_canh).mean():.1%}, '
          f'nhan LOS: {nh["segment_id"].isin(co_canh).mean():.1%}')


if __name__ == '__main__':
    main()
