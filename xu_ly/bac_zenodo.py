"""
Tầng bạc D13 (Zenodo HCM_1000 V2): 56 bài toán giao hàng có khung giờ (VRPTW), mỗi bài
1.000 khách + kho (Bưu cục Viettel Post Quận 10, 37 Hòa Hưng), bán kính 10 km.
Khách là điểm TỔNG HỢP (synthetic) nhưng đặt trên toạ độ thật của TP.HCM — dùng làm điểm
đi–đến để đánh giá định tuyến giao hàng (M9, tuần 9–10).

Đầu vào: du_lieu/zenodo_hcm1000/HCM_1000_V2/data/instances/*/*.txt
Đơn vị gốc: demand gram, ready/due/service PHÚT (tính từ đầu ca), toạ độ WGS84 + UTM 48N.

Đầu ra:
  du_lieu/bac/zenodo_bai_toan.parquet  bai_toan, nhom, so (0 = kho), lat, lon, khoi_luong_g,
                                       mo_phut, dong_phut, phuc_vu_phut, so_xe, tai_trong_g
  du_lieu/bac/zenodo_diem.parquet      mỗi toạ độ duy nhất -> nut (nút gần nhất trong thành phần
                                       liên thông mạnh lớn nhất của đồ thị), kc_m, trong_vung
                                       (kc_m <= 100 m: nằm trong vùng bản đồ, dùng được)

Chạy:  python bac_zenodo.py
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ghep_tomtom import MX, MY  # noqa: E402

NGUON = os.path.join(GOC, 'du_lieu', 'zenodo_hcm1000', 'HCM_1000_V2', 'data', 'instances')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
KC_TOI_DA = 100.0


def doc_bai(tep):
    dong = [d.split() for d in open(tep, encoding='utf-8').read().splitlines()]
    i_xe = next(i for i, d in enumerate(dong) if d[:2] == ['NUMBER', 'CAPACITY'])
    so_xe, tai_trong = int(dong[i_xe + 1][0]), int(dong[i_xe + 1][1])
    hang = [d for d in dong if len(d) == 9 and d[0].isdigit()]
    df = pd.DataFrame(hang, columns=['so', 'x_utm', 'y_utm', 'lat', 'lon', 'khoi_luong_g',
                                     'mo_phut', 'dong_phut', 'phuc_vu_phut'])
    df = df.astype({'so': 'int16', 'x_utm': float, 'y_utm': float, 'lat': float, 'lon': float,
                    'khoi_luong_g': 'int32', 'mo_phut': 'int16', 'dong_phut': 'int16', 'phuc_vu_phut': 'int16'})
    ten = os.path.basename(tep)[:-4].replace('HCMC_', '')
    df.insert(0, 'bai_toan', ten)
    df.insert(1, 'nhom', os.path.basename(os.path.dirname(tep)))
    df['so_xe'], df['tai_trong_g'] = so_xe, tai_trong
    return df


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    bt = pd.concat([doc_bai(t) for t in sorted(glob.glob(os.path.join(NGUON, '*', '*.txt')))], ignore_index=True)
    bt.to_parquet(os.path.join(BAC, 'zenodo_bai_toan.parquet'), index=False)

    from do_thi import TEP_RA
    with open(TEP_RA, 'rb') as f:
        d = pickle.load(f)
    G, tplt = d['G'], d['tplt']
    nut = np.array(sorted(tplt))
    xy_nut = np.array([(G.nodes[n]['x'] * MX, G.nodes[n]['y'] * MY) for n in nut])
    diem = bt[['lat', 'lon']].drop_duplicates().reset_index(drop=True)
    kc, i = cKDTree(xy_nut).query(np.column_stack([diem['lon'] * MX, diem['lat'] * MY]))
    diem['nut'] = nut[i]
    diem['kc_m'] = kc.astype(np.float32)
    diem['trong_vung'] = diem['kc_m'] <= KC_TOI_DA
    diem.to_parquet(os.path.join(BAC, 'zenodo_diem.parquet'), index=False)

    gop = bt.merge(diem, on=['lat', 'lon'])
    print(f'{bt["bai_toan"].nunique()} bai toan, {len(bt):,} dong, {len(diem):,} toa do duy nhat')
    print(f'  toa do trong vung ban do (<= {KC_TOI_DA:.0f} m toi nut): {diem["trong_vung"].mean():.1%}; '
          f'kc trung vi {diem["kc_m"].median():.0f} m')
    print('  ty le khach trong vung theo nhom:',
          gop[gop['so'] > 0].groupby('nhom')['trong_vung'].mean().round(3).to_dict())
    kho = gop[gop['so'] == 0].iloc[0]
    print(f'  kho: {kho["lat"]}, {kho["lon"]} -> nut {kho["nut"]} ({kho["kc_m"]:.0f} m)')


if __name__ == '__main__':
    main()
