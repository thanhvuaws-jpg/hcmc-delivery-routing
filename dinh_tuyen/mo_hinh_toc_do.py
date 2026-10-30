"""
Mô hình tốc độ theo GIỜ cho từng cạnh — đầu vào của định tuyến theo thời điểm (tuần 7).

  v(cạnh, giờ) = v_trống(cạnh) × r(cạnh, giờ)

  v_trống  : tốc độ đường trống đo thật (xu_ly/toc_do_canh.py, km/h ÷ r khi đường gần trống);
             cạnh không có số đo -> trung vị cùng loại đường; loại không có -> bảng đoán do_thi.TOC_DO.
  r        : tỉ lệ tốc độ / đường trống RIÊNG từng cạnh × giờ (TB điều hòa các lần chụp, cần ≥ 3 lần);
             không đủ thì theo loại đường × giờ, TB ĐIỀU HÒA trọng số chiều dài (đúng cho
             thời gian đi) từ tầng bạc TomTom — có đủ 24 giờ (khác km/h absolute mới có từ 30/10 04:11).
             Loại không có dữ liệu (hẻm/service…) -> r của nhóm residential, không có nữa -> r chung.
  Hiện tại : nếu giờ xuất phát cách lần chụp mới nhất ≤ HIEU_LUC_PHUT phút, cạnh có số đo dùng r ĐO
             THẬT lúc đó thay cho r trung bình (kẹt hôm nay khác TB các ngày).
  Đóng đường (lần chụp mới nhất): cạnh đóng hết (phu = 0) -> CẤM; đóng một phần -> thời gian × (1 + phần đóng).

Chạy thử:  python mo_hinh_toc_do.py      (in tốc độ TB theo giờ, số cạnh cấm)
"""
import datetime as dt
import glob
import os

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
R_SAN = 0.1                 # r nhỏ nhất khi tính thời gian (đứng yên trong hàng kẹt vẫn nhích)
TOI_THIEU_CANH = 3          # số lần chụp tối thiểu của một cạnh trong một giờ để dùng r riêng của cạnh
HIEU_LUC_PHUT = 30
NHOM_HEM = ('residential', 'service', 'living_street', 'unclassified', 'road')


class MoHinhTocDo:
    def __init__(self, v_trong, r_gio, r_hien_tai=None, luc_hien_tai=None, cam=None, phan_dong=None):
        self.v_trong = v_trong              # (n,) km/h
        self.r_gio = r_gio                  # (24, n)
        self.r_hien_tai = r_hien_tai        # (n,) NaN nếu không đo; None nếu không có lần chụp gần
        self.luc_hien_tai = luc_hien_tai
        self.cam = cam if cam is not None else np.zeros(len(v_trong), dtype=bool)
        self.phan_dong = phan_dong if phan_dong is not None else np.zeros(len(v_trong), dtype=np.float32)
        self.v_max = float(np.nanmax(v_trong * np.nanmax(r_gio, axis=0)))

    @classmethod
    def nap(cls, luc=None):
        """Dựng từ tầng bạc. luc: thời điểm xuất phát dự kiến (để quyết định có dùng số đo hiện tại)."""
        from do_thi import TOC_DO
        canh = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['loai', 'dai'])
        n, loai = len(canh), canh['loai'].to_numpy()

        # v_trống từng cạnh.
        v = np.array([TOC_DO.get(l, 15.0) for l in loai], dtype=np.float32)
        tc = pd.read_parquet(os.path.join(BAC, 'toc_do_canh.parquet'))
        trung_vi_loai = tc.groupby('loai')['v_trong'].median()
        for l, gt in trung_vi_loai.items():
            if (tc['loai'] == l).sum() >= 30:
                v[loai == l] = gt
        v[tc['chi_so'].to_numpy()] = tc['v_trong'].to_numpy()

        # r theo loại × giờ (TB điều hòa trọng số chiều dài) từ mọi ngày tầng bạc; đồng thời r RIÊNG
        # từng cạnh × giờ (TB điều hòa các lần chụp) — dùng khi cạnh có ≥ TOI_THIEU_CANH lần chụp trong giờ đó.
        dai = canh['dai'].to_numpy()
        tong_t = {}                          # (loại, giờ) -> [Σ dài, Σ dài / r]
        dem_c = np.zeros((24, n), dtype=np.float32)
        nghich_c = np.zeros((24, n), dtype=np.float32)
        for tep in sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet'))):
            s = pd.read_parquet(tep, columns=['khung', 'chi_so', 'muc', 'phu'])
            s = s[s['phu'] > 0]
            r = np.maximum(s['muc'].to_numpy() / 100, R_SAN)
            gi, ci = s['khung'].dt.hour.to_numpy(), s['chi_so'].to_numpy()
            np.add.at(dem_c, (gi, ci), 1)
            np.add.at(nghich_c, (gi, ci), 1 / r)
            d = dai[s['chi_so'].to_numpy()]
            g = pd.DataFrame({'loai': loai[s['chi_so'].to_numpy()], 'gio': s['khung'].dt.hour.to_numpy(),
                              'd': d, 'dr': d / r}).groupby(['loai', 'gio'])[['d', 'dr']].sum()
            for k, (a, b) in g.iterrows():
                o = tong_t.setdefault(k, [0.0, 0.0])
                o[0] += a
                o[1] += b
        bang = pd.Series({k: a / b for k, (a, b) in tong_t.items()})
        gio_co = sorted({g for _, g in tong_t})
        chung = pd.Series({h: sum(a for (l, g), (a, b) in tong_t.items() if g == h) /
                           sum(b for (l, g), (a, b) in tong_t.items() if g == h) for h in gio_co})

        # Giờ CHƯA có dữ liệu không được coi là "đường trống" (r = 1) — sẽ đánh giá sai cao điểm.
        # Lấy TB các giờ đã đo CÙNG NHÓM (ban ngày 6–21 / ban đêm), theo từng loại đường.
        def nhom_gio(h):
            return 6 <= h <= 21
        thieu = [h for h in range(24) if h not in gio_co]

        def thay_the(l, h):
            cung = [bang[(l, g)] for g in gio_co if nhom_gio(g) == nhom_gio(h) and (l, g) in bang]
            return float(np.mean(cung)) if cung else None

        r_gio = np.ones((24, n), dtype=np.float32)
        for h in range(24):
            for l in np.unique(loai):
                gt = bang.get((l, h))
                if gt is None:
                    gt = thay_the(l, h) if h in thieu else None
                if gt is None:
                    nguon_l = 'residential' if l in NHOM_HEM else None
                    gt = (bang.get((nguon_l, h)) if nguon_l else None) or \
                        (thay_the(nguon_l, h) if nguon_l and h in thieu else None)
                if gt is None:
                    cung = [chung[g] for g in gio_co if nhom_gio(g) == nhom_gio(h)]
                    gt = chung.get(h, float(np.mean(cung)) if cung else 1.0)
                r_gio[h, loai == l] = gt
        rieng = dem_c >= TOI_THIEU_CANH
        r_gio[rieng] = dem_c[rieng] / nghich_c[rieng]
        self_thieu = thieu

        # Lần chụp mới nhất: đo hiện tại + đóng đường.
        tep = sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet')))
        r_ht = cam = phan_dong = luc_ht = None
        if tep:
            s = pd.read_parquet(tep[-1], columns=['khung', 'chi_so', 'muc', 'phu', 'phu_dong'])
            luc_ht = s['khung'].max()
            s = s[s['khung'] == luc_ht]
            i = s['chi_so'].to_numpy()
            cam = np.zeros(n, dtype=bool)
            cam[i[(s['phu'] == 0).to_numpy() & (s['phu_dong'] > 0).to_numpy()]] = True
            phan_dong = np.zeros(n, dtype=np.float32)
            phan_dong[i] = s['phu_dong'].to_numpy() / 100
            if luc is not None and abs((pd.Timestamp(luc) - luc_ht).total_seconds()) <= HIEU_LUC_PHUT * 60:
                r_ht = np.full(n, np.nan, dtype=np.float32)
                mo = (s['phu'] > 0).to_numpy()
                r_ht[i[mo]] = np.maximum(s['muc'].to_numpy()[mo] / 100, R_SAN)
        m = cls(v, r_gio, r_ht, luc_ht, cam, phan_dong)
        m.gio_uoc_luong = self_thieu         # giờ chưa có dữ liệu thật, r đang ước lượng
        m.co_so_do = dem_c.sum(axis=0) > 0   # cạnh từng có số đo TomTom (còn lại: hẻm/đường nhỏ, ước lượng)
        return m

    def km_h(self, i, gio, dung_hien_tai=False):
        """Tốc độ dự kiến (km/h) của cạnh i ở giờ `gio` (0–23)."""
        if dung_hien_tai and self.r_hien_tai is not None:
            r = self.r_hien_tai[i]
            if r == r:                       # không NaN
                return self.v_trong[i] * r
        return self.v_trong[i] * self.r_gio[gio, i]


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.stdout.reconfigure(encoding='utf-8')
    m = MoHinhTocDo.nap(dt.datetime.now())
    canh = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['loai', 'dai'])
    for l in ('primary', 'secondary', 'tertiary', 'residential', 'service'):
        mask = (canh['loai'] == l).to_numpy()
        d = canh['dai'].to_numpy()[mask]
        tb = {h: d.sum() / (d / (m.v_trong[mask] * m.r_gio[h, mask])).sum() for h in (3, 8, 12, 18)}
        print(f'  {l:<12} v TB (dieu hoa) 3h {tb[3]:.1f} | 8h {tb[8]:.1f} | 12h {tb[12]:.1f} | 18h {tb[18]:.1f} km/h')
    if m.gio_uoc_luong:
        print(f'CANH BAO: gio chua co du lieu that (r dang uoc luong tu cac gio cung nhom): {m.gio_uoc_luong}')
    print(f'lan chup moi nhat {m.luc_hien_tai}, dung so do hien tai: {m.r_hien_tai is not None}, '
          f'canh cam (dong het): {int(m.cam.sum())}, dong mot phan: {int((m.phan_dong > 0).sum() - m.cam.sum())}, '
          f'v_max {m.v_max:.0f} km/h')
