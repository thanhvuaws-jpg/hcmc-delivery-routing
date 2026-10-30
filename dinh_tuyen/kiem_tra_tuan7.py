"""
Kiểm tra định tuyến 3 phương án theo thời điểm — tiêu chí "xong khi" của tuần 7 (note/KE_HOACH.md):
  1. 3 tuyến trả về < 2 giây (mỗi cặp điểm).
  2. Không đi ngược chiều / vào đường cấm xe máy / rẽ sai luật; không vào cạnh đang ĐÓNG.
  3. Bật "mưa to" thì tuyến tối ưu né điểm ngập: trên các cặp mà tuyến ngắn nhất đi qua cạnh dễ ngập,
     tuyến tối ưu phải qua ÍT cạnh ngập hơn (hoặc 0).
Kèm số liệu so sánh: tuyến nhanh nhất tiết kiệm bao nhiêu phút so với ngắn nhất, theo giờ xuất phát.

Chạy:  python kiem_tra_tuan7.py
"""
import datetime as dt
import itertools
import os
import sys
import time

import numpy as np

from ba_phuong_an import PHAT_NGAP_S, DinhTuyen
from kiem_tra_tuan1 import DIA_DIEM, soat_luat

NGAY = dt.date(2026, 10, 30)
GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = DinhTuyen.nap(dt.datetime.combine(NGAY, dt.time(8, 0)))
    if d.mh.gio_uoc_luong:
        print(f'Luu y: gio chua co du lieu that (dang uoc luong): {d.mh.gio_uoc_luong}')
    dat = True
    for gio in (3, 8):
        luc = dt.datetime.combine(NGAY, dt.time(gio, 0))
        thoi, tiet_kiem, loi_luat, loi_dong, khong_thay = [], [], 0, 0, 0
        ket_n, ket_o = [], []
        for (a, pa), (b, pb) in itertools.permutations(DIA_DIEM.items(), 2):
            t = time.time()
            kq = d.tim(pa, pb, luc)
            thoi.append(time.time() - t)
            if any(kq[k] is None for k in ('ngan_nhat', 'nhanh_nhat', 'toi_uu')):
                khong_thay += 1
                continue
            for k in ('ngan_nhat', 'nhanh_nhat', 'toi_uu'):
                lc, lr = soat_luat(d.bd, kq[k])
                loi_luat += lc + lr
                loi_dong += kq[k]['so_canh_dong']
            n, f = kq['ngan_nhat']['phut'], kq['nhanh_nhat']['phut']
            tiet_kiem.append((n - f, 100 * (n - f) / n))
            ket_n.append(kq['nhanh_nhat']['so_canh_ket'])
            ket_o.append(kq['toi_uu']['so_canh_ket'])
        tk = np.array(tiet_kiem)
        print(f'\nXuat phat {gio:02d}:00 — {len(thoi)} cap diem, khong tim duoc {khong_thay}')
        print(f'  thoi gian tra 3 tuyen: TB {np.mean(thoi):.2f}s, cham nhat {np.max(thoi):.2f}s')
        print(f'  loi luat: {loi_luat} | di vao canh dang dong: {loi_dong}')
        print(f'  nhanh nhat so voi ngan nhat: tiet kiem TB {tk[:, 0].mean():.1f} phut ({tk[:, 1].mean():.1f}%), '
              f'lon nhat {tk[:, 0].max():.1f} phut; nhanh hon o {(tk[:, 0] > 0.05).mean():.0%} cap')
        print(f'  so canh ket nang (r<0,4): nhanh nhat TB {np.mean(ket_n):.1f} -> toi uu TB {np.mean(ket_o):.1f}')
        dat &= khong_thay == 0 and loi_luat == 0 and loi_dong == 0 and np.max(thoi) < 2.0 and (tk[:, 0] >= -0.05).all()

    # Mưa to: tuyến tối ưu né cạnh dễ ngập. Mỗi điểm ngập đã ghép (bac/ngap_diem.parquet, nguyên nhân mưa):
    # đặt điểm đi / đến cách trung điểm cạnh ngập ~800 m về hai phía (đông–tây và bắc–nam), để tuyến
    # ngắn nhất có lý do đi ngang qua; kiểm tuyến tối ưu qua ÍT cạnh ngập hơn.
    import pandas as pd
    luc = dt.datetime.combine(NGAY, dt.time(8, 0))
    ng = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'ngap_canh.parquet'))
    G, ds = d.bd.G, list(d.bd.G.edges())
    co_ngap, ne_duoc = 0, 0
    for stt, g in ng[ng['nguyen_nhan'] == 'mua'].groupby('stt'):
        u, v = ds[int(g['chi_so'].iloc[len(g) // 2])]
        la, lo = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2, (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        for di, den in (((la, lo - 0.0073), (la, lo + 0.0073)), ((la - 0.0072, lo), (la + 0.0072, lo))):
            kq = d.tim(di, den, luc, mua_mm=10)
            if kq['ngan_nhat'] and kq['ngan_nhat']['so_canh_ngap'] > 0:
                co_ngap += 1
                if kq['toi_uu']['so_canh_ngap'] < kq['ngan_nhat']['so_canh_ngap']:
                    ne_duoc += 1
                    continue
                # Không né: chỉ chấp nhận nếu né là KHÔNG HỢP LÝ — cấm hẳn cạnh ngập mà không có đường,
                # hoặc đường vòng tốn hơn tổng phạt ngập (thuật toán cân đúng mới chọn đi qua).
                cam_cu, list_cu = d.mh.cam.copy(), d._cam_list
                d.mh.cam = cam_cu | d.ngap_mua
                d._cam_list = d.mh.cam.tolist()
                vong = d.tim(di, den, luc, mua_mm=10)['nhanh_nhat']
                d.mh.cam, d._cam_list = cam_cu, list_cu
                phat_phut = PHAT_NGAP_S['to'] * kq['toi_uu']['so_canh_ngap'] / 60
                them = None if vong is None else vong['phut'] - kq['toi_uu']['phut']
                hop_ly = vong is None or them >= phat_phut
                ne_duoc += hop_ly
                print(f'  diem ngap stt {stt}: toi uu van qua {kq["toi_uu"]["so_canh_ngap"]} canh ngap; '
                      f'duong vong {"khong co" if vong is None else f"them {them:.1f} phut"} vs phat '
                      f'{phat_phut:.0f} phut -> {"hop ly" if hop_ly else "LOI"}')
    print(f'\nMua to (10 mm/h): {co_ngap} cap ma tuyen ngan nhat qua canh de ngap; tuyen toi uu ne duoc '
          f'(hoac khong the ne hop ly) o {ne_duoc}/{co_ngap}')
    dat &= co_ngap > 0 and ne_duoc == co_ngap

    # ALT chỉ được TĂNG TỐC, không được đổi kết quả: chi phí tối ưu có / không ALT phải bằng nhau.
    lech = 0
    cap = list(itertools.permutations(DIA_DIEM.values(), 2))[::9]
    for pa, pb in cap:
        co, khong = d.tim(pa, pb, luc), d.tim(pa, pb, luc, dung_alt=False)
        for k in ('nhanh_nhat', 'toi_uu'):
            lech += abs(co[k]['chi_phi'] - khong[k]['chi_phi']) > 0.5
    print(f'ALT khong doi ket qua: {len(cap) * 2 - lech}/{len(cap) * 2} tuyen cung chi phi')
    dat &= lech == 0
    print('\nDAT' if dat else '\nKHONG DAT')
    return 0 if dat else 1


if __name__ == '__main__':
    sys.exit(main())
