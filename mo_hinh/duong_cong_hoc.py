"""
Đường cong học của GBM + hồ sơ (QĐ-027): học với 50 / 75 / 100% số khung của phần học — bỏ NGÀY CŨ NHẤT, giữ ngày
gần tập kiểm tra — rồi chấm trên CÙNG phần kiểm tra. Hồ sơ và tình trạng chung cũng chỉ dựng từ phần còn lại.

Câu hỏi: thêm dữ liệu còn giúp không? Nếu MAE vẫn giảm rõ từ 75% lên 100% thì lần train cuối (2–3 tháng dữ liệu)
đáng chờ; nếu đã phẳng thì phần còn thiếu nằm ở đặc trưng / mô hình, không phải số ngày.
Giới hạn: bỏ ngày cũ nhất cũng bỏ bớt cuối tuần (phần học 29/10 → 08/11 chỉ có 2 cuối tuần) — bớt ngày và bớt
cuối tuần lẫn vào nhau; xem MAE theo ngày (tối Chủ nhật 08/11 tách riêng).

Chạy:  python duong_cong_hoc.py [0.5,0.75,1]
Ra:    mo_hinh/ket_qua/duong_cong_hoc_gbm_ls_<ngày cuối dữ liệu>.json
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from dac_trung import NHAN, BangHoc
from moc_so_sanh import RA, LichSu, danh_gia, mae_theo_ngay, tao_gbm_chung


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    phan = [float(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '0.5,0.75,1').split(',')]
    bang = BangHoc()
    kiem = bang.kiem
    print(f'hoc {bang.khung[0]} -> {bang.het_hoc} ({bang.cat} khung) | kiem tu {bang.dau_kiem}')
    kq = {'hoc_toi': str(bang.het_hoc), 'kiem_tu': str(bang.dau_kiem), 'ket_qua': {}}
    for p in phan:
        bang.dat_bo_dau(1 - p)
        hoc = bang.hoc
        so_ngay = (bang.het_hoc - bang.dau_hoc) / np.timedelta64(1, 'D')
        lich_su = LichSu(hoc)
        kq_p = {'hoc_tu': str(bang.dau_hoc), 'so_khung_hoc': bang.cat - bang.dau, 'so_ngay': round(float(so_ngay), 2),
                'so_dong_hoc': len(hoc), 'dac_trung_bo': bang.bo_vi_trong}
        print(f'\n{p:.0%} phan hoc: tu {bang.dau_hoc} ({so_ngay:.1f} ngay, {len(hoc):,} dong)', flush=True)
        for h, y in NHAN.items():
            t = time.time()
            a, b = bang.nhan(hoc, y), bang.nhan(kiem, y)
            m = tao_gbm_chung(bang.dac_trung.index('loai'))
            m.fit(bang.X(a, int(h)), (a[y] - a['r']).to_numpy())
            du = np.clip(b['r'].to_numpy() + m.predict(bang.X(b, int(h))), 0, 1)
            del m
            yt, r = b[y].to_numpy(), b['r'].to_numpy()
            gio = b['khung'].dt.hour.to_numpy()
            ngay = b['khung'].dt.strftime('%Y-%m-%d').to_numpy()
            ls, _ = lich_su.du_bao(b, int(h))
            kq_p[h] = {'gbm_ls': danh_gia(yt, du, r, gio), 'lich_su': danh_gia(yt, ls, r, gio),
                       'mae_theo_ngay': {'gbm_ls': mae_theo_ngay(yt, du, ngay), 'lich_su': mae_theo_ngay(yt, ls, ngay)}}
            g = kq_p[h]
            print(f'  {h:>2} phut: GBM+ho so {g["gbm_ls"]["mae"]:.3f} | lich su {g["lich_su"]["mae"]:.3f} '
                  f'(thap hon {100 * (1 - g["gbm_ls"]["mae"] / g["lich_su"]["mae"]):.1f}%) | F1 ket '
                  f'{g["gbm_ls"]["f1_ket"]:.3f} | theo ngay {g["mae_theo_ngay"]["gbm_ls"]} ({time.time() - t:.0f}s)',
                  flush=True)
        kq['ket_qua'][f'{p:g}'] = kq_p
    tep = os.path.join(RA, f'duong_cong_hoc_gbm_ls_{pd.Timestamp(bang.khung[-1]):%Y-%m-%d}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'\n-> {tep} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
