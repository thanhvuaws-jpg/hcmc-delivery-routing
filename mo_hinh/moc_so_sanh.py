"""
Mốc so sánh cho dự báo kẹt xe 15/30/60 phút trên tầng vàng (du_lieu/vang/).

So 5 cách, cùng một tập kiểm tra chia THEO THỜI GIAN (KE_HOACH_DU_LIEU mục 8):
  giu_nguyen   y(t+h) = r(t)                         — mốc ngây thơ, mô hình nào cũng phải thắng
  tb_1h        y(t+h) = TB r của 1 giờ gần nhất
  lich_su      y(t+h) = TB r theo (đoạn, thứ, ô 15 phút) trên phần học — lớp LichSu, mốc của tiêu chí ≥ 10%
  gbm          HistGradientBoosting (scikit-learn) học PHẦN THAY ĐỔI y − r từ mọi đặc trưng tầng vàng
  gbm_ls       gbm + hồ sơ lịch sử ở giờ đích và tình trạng chung toàn mạng (dac_trung.py, QĐ-020, QĐ-021)
Chia: 70% khung thời gian đầu để học, chừa KHOẢNG_HO khung, phần sau để kiểm tra (nhãn 60 phút
của khung học cuối không được rơi vào thời gian kiểm tra).

Thước đo: MAE, RMSE (điểm %, r × 100) — toàn bộ, ban ngày 6–22h, và khi ĐANG đông/kẹt (r < 0,75);
độ đúng + F1 3 mức thông/đông/kẹt, F1 riêng mức kẹt; MAE từng ngày kiểm tra (xem độ ổn định).
Kết quả ghi mo_hinh/ket_qua/moc_<ngày chạy>.json — dữ liệu ít ngày thì số chỉ để kiểm đường ống.

Chạy:  python moc_so_sanh.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import f1_score

from dac_trung import GOC, KHOANG_HO, NHAN, TY_LE_HOC, BangHoc  # noqa: F401 (KHOANG_HO, TY_LE_HOC: hoc_sau_hcm dùng)

RA = os.path.join(GOC, 'mo_hinh', 'ket_qua')


def tao_gbm_chung(cot_loai):
    return HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=63, min_samples_leaf=200,
                                         l2_regularization=1.0, categorical_features=[cot_loai], random_state=42)


def muc(r):
    return np.select([r < 0.4, r < 0.75], [0, 1], 2)


def danh_gia(y, du, r_hien_tai, gio):
    e = np.abs(y - du) * 100
    ban_ngay = (gio >= 6) & (gio < 22)
    dong = r_hien_tai < 0.75
    my, mdu = muc(y), muc(du)
    return {'mae': round(float(e.mean()), 3), 'rmse': round(float(np.sqrt((e * e).mean())), 3),
            'mae_ban_ngay': round(float(e[ban_ngay].mean()), 3) if ban_ngay.any() else None,
            'mae_dang_dong_ket': round(float(e[dong].mean()), 3) if dong.any() else None,
            'dung_3_muc': round(float((my == mdu).mean()), 4),
            'f1_3_muc': round(float(f1_score(my, mdu, average='macro', labels=[0, 1, 2], zero_division=0)), 4),
            'f1_ket': round(float(f1_score(my == 0, mdu == 0, zero_division=0)), 4), 'n': int(len(y))}


def mae_theo_ngay(y, du, ngay):
    """MAE (điểm %) từng ngày của phần kiểm tra — để xem mô hình có ổn định qua các ngày không."""
    e = pd.Series(np.abs(y - du) * 100).groupby(ngay).mean()
    return {str(k): round(float(v), 3) for k, v in e.items()}


class LichSu:
    """
    Mốc TRUNG BÌNH LỊCH SỬ (tiêu chí KE_HOACH: mô hình phải thấp hơn mốc này ≥ 10% MAE). r trung bình theo
    (đoạn, thứ, ô 15 phút trong ngày) CHỈ trên phần học, tra theo giờ ĐÍCH t+h. Mới vài tuần dữ liệu thì có thứ
    chưa xuất hiện trong phần học -> lùi về (đoạn, ngày thường/cuối tuần, ô), rồi (đoạn, ô), rồi r hiện tại.
    """

    def __init__(self, hoc):
        a = hoc.loc[hoc['r'].notna(), ['doan', 'khung', 'r']]
        k = self._khoa(a['khung'])
        a = pd.DataFrame({'doan': a['doan'].to_numpy(), 'r': a['r'].to_numpy(), **k})
        self.m1 = a.groupby(['doan', 'thu', 'o'], sort=False)['r'].mean().rename('m1')
        self.m2 = a.groupby(['doan', 'cuoi', 'o'], sort=False)['r'].mean().rename('m2')
        self.m3 = a.groupby(['doan', 'o'], sort=False)['r'].mean().rename('m3')

    @staticmethod
    def _khoa(t):
        thu = t.dt.dayofweek.to_numpy()
        return {'thu': thu, 'cuoi': thu >= 5, 'o': (t.dt.hour * 4 + t.dt.minute // 15).to_numpy()}

    def du_bao(self, b, phut):
        """Dự báo r ở t + phut cho các dòng b; kèm tỉ lệ dòng tra được đúng (đoạn, thứ, ô)."""
        q = pd.DataFrame({'doan': b['doan'].to_numpy(), **self._khoa(b['khung'] + pd.Timedelta(minutes=phut))})
        q = q.join(self.m1, on=['doan', 'thu', 'o']).join(self.m2, on=['doan', 'cuoi', 'o']).join(self.m3, on=['doan', 'o'])
        du = q['m1'].fillna(q['m2']).fillna(q['m3']).fillna(pd.Series(b['r'].to_numpy()))
        return du.to_numpy(), float(q['m1'].notna().mean())


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bang = BangHoc()
    d, khung, hoc, kiem = bang.d, bang.khung, bang.hoc, bang.kiem
    if bang.bo_vi_trong:
        print('bo cot chua co du lieu de hoc:', bang.bo_vi_trong)
    print(f'{len(d):,} dong, {len(khung)} khung ({khung[0]} -> {khung[-1]})')
    print(f'hoc: {len(hoc):,} dong toi {bang.het_hoc} | kiem: {len(kiem):,} dong tu {bang.dau_kiem} | '
          f'{len(bang.dac_trung)} dac trung')

    kq = {'tao_luc': time.strftime('%Y-%m-%d %H:%M:%S'), 'hoc_toi': str(bang.het_hoc), 'kiem_tu': str(bang.dau_kiem),
          'so_dong_hoc': len(hoc), 'so_dong_kiem': len(kiem), 'dac_trung': bang.dac_trung, 'ket_qua': {}}
    lich_su = LichSu(hoc)

    def tao_gbm():
        return tao_gbm_chung(bang.dac_trung.index('loai'))

    for h, y in NHAN.items():
        a, b = bang.nhan(hoc, y), bang.nhan(kiem, y)
        dich_y = (a[y] - a['r']).to_numpy()
        m = tao_gbm()
        m.fit(bang.X(a, int(h), co_ho_so=False), dich_y)
        du = np.clip(b['r'].to_numpy() + m.predict(bang.X(b, int(h), co_ho_so=False)), 0, 1)
        # Cùng đặc trưng + hồ sơ lịch sử + tình trạng chung toàn mạng (dac_trung.py).
        m = tao_gbm()
        m.fit(bang.X(a, int(h)), dich_y)
        du_ls = np.clip(b['r'].to_numpy() + m.predict(bang.X(b, int(h))), 0, 1)
        del m
        gio = b['khung'].dt.hour.to_numpy()
        yt, r = b[y].to_numpy(), b['r'].to_numpy()
        ls, dung_thu = lich_su.du_bao(b, int(h))
        ngay = b['khung'].dt.strftime('%Y-%m-%d').to_numpy()
        kq['ket_qua'][h] = {
            'giu_nguyen': danh_gia(yt, r, r, gio),
            'tb_1h': danh_gia(yt, b['r_tb_1h'].fillna(b['r']).to_numpy(), r, gio),
            'lich_su': danh_gia(yt, ls, r, gio),
            'gbm': danh_gia(yt, du, r, gio),
            'gbm_ls': danh_gia(yt, du_ls, r, gio),
            'lich_su_dung_thu': round(dung_thu, 4),
            'mae_theo_ngay': {'giu_nguyen': mae_theo_ngay(yt, r, ngay), 'lich_su': mae_theo_ngay(yt, ls, ngay),
                              'gbm': mae_theo_ngay(yt, du, ngay), 'gbm_ls': mae_theo_ngay(yt, du_ls, ngay)}}
        g = kq['ket_qua'][h]
        print(f'{h:>2} phut | MAE giu nguyen {g["giu_nguyen"]["mae"]:.2f} | TB 1h {g["tb_1h"]["mae"]:.2f} | '
              f'lich su {g["lich_su"]["mae"]:.2f} (dung thu {dung_thu:.0%}) | GBM {g["gbm"]["mae"]:.2f} | '
              f'GBM+ho so {g["gbm_ls"]["mae"]:.2f} '
              f'(thap hon lich su {100 * (1 - g["gbm_ls"]["mae"] / g["lich_su"]["mae"]):.1f}%)', flush=True)
        for k in ('lich_su', 'gbm', 'gbm_ls'):
            x = g[k]
            print(f'        {k:<8} RMSE {x["rmse"]:.2f} | ban ngay {x["mae_ban_ngay"]:.2f} | dang dong/ket '
                  f'{x["mae_dang_dong_ket"]:.2f} | dung 3 muc {x["dung_3_muc"]:.1%} | F1 3 muc {x["f1_3_muc"]:.3f} | '
                  f'F1 ket {x["f1_ket"]:.3f} | theo ngay {g["mae_theo_ngay"][k]}', flush=True)

    os.makedirs(RA, exist_ok=True)
    tep = os.path.join(RA, f'moc_{time.strftime("%Y-%m-%d_%H%M")}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(f'-> {tep} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
