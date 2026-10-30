"""
Ghép mức kẹt TomTom vào các cạnh CỐ ĐỊNH của đồ thị xe máy (map matching).

Vì sao phải ghép: TomTom cắt đoạn đường theo chỗ mức kẹt thay đổi — kẹt lan tới
đâu điểm cắt dời tới đó, nên hình học (và mã băm) của "đoạn TomTom" đổi giữa các
lần chụp: đo 29/10/2026, 28% đoạn đổi sau 5 phút. Cạnh của đồ thị OSM thì cố định,
nên chuỗi thời gian phải gắn vào cạnh.

Cách ghép, cho mỗi đoạn TomTom (đường gấp khúc có chiều):
  1. Lấy mẫu điểm dọc đoạn, cách nhau BUOC_M mét, mỗi điểm mang hướng đi tại đó.
  2. Với mỗi điểm, tìm cạnh đồ thị gần nhất trong vòng XA_TOI_DA_M mét có hướng
     lệch không quá LECH_TOI_DA độ (đoạn "full" — phủ cả hai chiều — thì nhận cả
     cạnh ngược hướng).
  3. Mức kẹt của cạnh = trung bình theo chiều dài các mẫu rơi vào cạnh đó.

Tính bằng mảng numpy cho mọi mẫu cùng lúc (30/10/2026: 19 s → ~1 s một lần chụp,
kết quả trùng bản cũ — xem kiem_tra_ghep_nhanh.py). Chỉ mục lưới: mỗi ô 40 m giữ mọi
cạnh mà khung bao nới thêm XA_TOI_DA_M chạm vào ô, nên một mẫu chỉ cần tra đúng ô
của nó là đủ mọi cạnh trong vòng 15 m.

Bảng cạnh cố định: du_lieu/do_thi/canh.parquet (chi_so, u, v, way, loai, dai).
Chỉ số cạnh giữ nguyên chừng nào chưa dựng lại đồ thị. Đồ thị dựng lại thì phải
ghép lại từ bản thô (du_lieu/tomtom/tho/).
"""
import math
import os
import pickle
from collections import defaultdict

import numpy as np

from do_thi import TEP_RA as TEP_DO_THI

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TEP_CHI_MUC = os.path.join(GOC, 'du_lieu', 'do_thi', 'chi_muc_ghep.pkl')
TEP_CANH = os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet')

BUOC_M = 10.0          # khoảng cách lấy mẫu dọc đoạn TomTom
XA_TOI_DA_M = 15.0     # mẫu xa cạnh hơn mức này thì bỏ
LECH_TOI_DA = 35.0     # độ lệch hướng tối đa
O_LUOI_M = 40.0        # cỡ ô lưới chỉ mục

VD0 = 10.78                                   # vĩ độ gốc để đổi sang mét
MY = 110_574.0
MX = 111_320.0 * math.cos(math.radians(VD0))


def sang_met(lat, lon):
    return lon * MX, lat * MY


def huong(dx, dy):
    """Góc phương vị 0..360 (0 = bắc, 90 = đông)."""
    return math.degrees(math.atan2(dx, dy)) % 360


def _ghi_an_toan(tep, ghi):
    """Ghi ra tệp tạm rồi đổi tên: bộ thu chạy song song không bao giờ đọc phải tệp ghi dở."""
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    tam = tep + '.tam'
    ghi(tam)
    os.replace(tam, tep)


def _ma_o(ox, oy):
    return ox * 1_000_000 + oy


class BoGhep:
    CHUNK = 2048       # số mẫu xử lý một đợt (giới hạn bộ nhớ của ma trận ứng viên)

    def __init__(self, xy, huong_canh, khoa, dau, phang, ma_do_thi=''):
        self.xy = xy                # (n, 4): x1, y1, x2, y2 (mét)
        self.huong = huong_canh     # (n,) phương vị từng cạnh
        self.khoa = khoa            # mã các ô lưới có cạnh, tăng dần
        self.dau = dau              # ô thứ k giữ phang[dau[k]:dau[k + 1]]
        self.phang = phang          # chỉ số cạnh, tăng dần trong mỗi ô
        self.ma_do_thi = ma_do_thi  # dấu vân tay của đồ thị, ghi kèm dữ liệu đã ghép

    @classmethod
    def dung(cls):
        """Dựng chỉ mục từ đồ thị + ghi bảng cạnh cố định. Chạy lại mỗi khi dựng lại đồ thị."""
        import hashlib
        import pandas as pd
        with open(TEP_DO_THI, 'rb') as f:
            G = pickle.load(f)['G']
        ds = list(G.edges(data=True))
        xy = np.empty((len(ds), 4))
        hg = np.empty(len(ds))
        for i, (u, v, _) in enumerate(ds):
            x1, y1 = sang_met(G.nodes[u]['y'], G.nodes[u]['x'])
            x2, y2 = sang_met(G.nodes[v]['y'], G.nodes[v]['x'])
            xy[i] = (x1, y1, x2, y2)
            hg[i] = huong(x2 - x1, y2 - y1)
        ox0 = np.floor((np.minimum(xy[:, 0], xy[:, 2]) - XA_TOI_DA_M) / O_LUOI_M).astype(np.int64)
        ox1 = np.floor((np.maximum(xy[:, 0], xy[:, 2]) + XA_TOI_DA_M) / O_LUOI_M).astype(np.int64)
        oy0 = np.floor((np.minimum(xy[:, 1], xy[:, 3]) - XA_TOI_DA_M) / O_LUOI_M).astype(np.int64)
        oy1 = np.floor((np.maximum(xy[:, 1], xy[:, 3]) + XA_TOI_DA_M) / O_LUOI_M).astype(np.int64)
        luoi = defaultdict(list)
        for i in range(len(ds)):        # i tăng dần → danh sách mỗi ô tự sắp xếp
            for ox in range(ox0[i], ox1[i] + 1):
                for oy in range(oy0[i], oy1[i] + 1):
                    luoi[_ma_o(ox, oy)].append(i)
        khoa = np.array(sorted(luoi), dtype=np.int64)
        dau = np.concatenate([[0], np.cumsum([len(luoi[k]) for k in khoa])]).astype(np.int64)
        phang = np.concatenate([np.array(luoi[k], dtype=np.int32) for k in khoa])
        u = np.array([a for a, _, _ in ds], dtype=np.int64)
        v = np.array([b for _, b, _ in ds], dtype=np.int64)
        ma = hashlib.sha1(u.tobytes() + v.tobytes()).hexdigest()[:12]
        bo = cls(xy, hg, khoa, dau, phang, ma)
        def ghi_chi_muc(t):
            with open(t, 'wb') as f:
                pickle.dump({'xy': xy, 'huong': hg, 'khoa': khoa, 'dau': dau, 'phang': phang,
                             'so_canh': len(ds), 'ma_do_thi': ma}, f)
        _ghi_an_toan(TEP_CHI_MUC, ghi_chi_muc)
        bang = pd.DataFrame({
            'chi_so': np.arange(len(ds), dtype=np.int32), 'u': u, 'v': v,
            'way': [d['way'] for _, _, d in ds], 'loai': [d['loai'] for _, _, d in ds],
            'ten': [d['ten'] for _, _, d in ds], 'dai': [d['dai'] for _, _, d in ds],
        })
        _ghi_an_toan(TEP_CANH, lambda t: bang.to_parquet(t, index=False))
        return bo

    @classmethod
    def nap(cls):
        if os.path.exists(TEP_CHI_MUC):
            with open(TEP_CHI_MUC, 'rb') as f:
                d = pickle.load(f)
            if 'khoa' in d:         # chỉ mục kiểu cũ (trước 30/10/2026) thì dựng lại
                return cls(d['xy'], d['huong'], d['khoa'], d['dau'], d['phang'], d.get('ma_do_thi', ''))
        return cls.dung()

    def _gan_nhat(self, x, y, hg, hai_chieu):
        """Mảng mẫu -> chỉ số cạnh gần nhất hợp lệ của từng mẫu (-1 nếu không có)."""
        ra = np.full(len(x), -1, dtype=np.int64)
        ma = _ma_o(np.floor(x / O_LUOI_M).astype(np.int64), np.floor(y / O_LUOI_M).astype(np.int64))
        k = np.minimum(np.searchsorted(self.khoa, ma), len(self.khoa) - 1)
        co = np.nonzero(self.khoa[k] == ma)[0]
        # Xếp mẫu theo số ứng viên của ô: mỗi đợt có bề rộng ma trận gần nhau, đỡ phí
        # công tính cho phần đệm (trung bình 16 ứng viên/ô, ô đông nhất >120).
        co = co[np.argsort(self.dau[k[co] + 1] - self.dau[k[co]], kind='stable')]
        for s in range(0, len(co), self.CHUNK):
            m = co[s:s + self.CHUNK]
            a, dem = self.dau[k[m]], self.dau[k[m] + 1] - self.dau[k[m]]
            j = np.arange(dem.max())
            trong = j < dem[:, None]
            ung = self.phang[np.where(trong, a[:, None] + j, 0)]
            px, py, ph = x[m, None], y[m, None], hg[m, None]
            x1, y1, x2, y2 = (self.xy[ung, c] for c in range(4))
            dx, dy = x2 - x1, y2 - y1
            dd = dx * dx + dy * dy
            t = np.clip(((px - x1) * dx + (py - y1) * dy) / np.where(dd > 0, dd, 1), 0, 1)
            kc = np.hypot(x1 + t * dx - px, y1 + t * dy - py)
            lech = np.abs((self.huong[ung] - ph + 180) % 360 - 180)
            lech = np.where(hai_chieu[m, None], np.minimum(lech, 180 - lech), lech)
            # Ưu tiên gần, phạt nhẹ lệch hướng (1 độ ~ 0,2 m) để chọn đúng làn chiều.
            diem = np.where(trong & (kc <= XA_TOI_DA_M) & (lech <= LECH_TOI_DA), kc + 0.2 * lech, np.inf)
            b = diem.argmin(axis=1)
            hang = np.arange(len(m))
            tot = np.isfinite(diem[hang, b])
            ra[m[tot]] = ung[hang, b][tot]
        return ra

    @staticmethod
    def _lay_mau(pts):
        """
        pts (m, 2) mét -> x, y, hướng của các điểm mẫu ở quãng BUOC/2, 3·BUOC/2, … dọc
        đường gấp khúc. Khúc ngắn hơn 0,5 m bị bỏ (không tính vào quãng đường).
        """
        d = np.diff(pts, axis=0)
        dai = np.hypot(d[:, 0], d[:, 1])
        giu = dai >= 0.5
        if not giu.any():
            return None
        goc, d, dai = pts[:-1][giu], d[giu], dai[giu]
        cuoi = np.cumsum(dai)
        dau = np.concatenate([[0.0], cuoi[:-1]])
        s = np.arange(BUOC_M / 2, cuoi[-1], BUOC_M)
        if not len(s):
            return None
        i = np.searchsorted(cuoi, s, side='left')
        k = (s - dau[i]) / dai[i]
        return (goc[i, 0] + k * d[i, 0], goc[i, 1] + k * d[i, 1],
                np.degrees(np.arctan2(d[i, 0], d[i, 1])) % 360)

    def ghep(self, doan):
        """
        doan: list {'diem': [(lat, lon), ...], 'tt': {traffic_level, traffic_road_coverage, road_closure}}
        Trả về dict chỉ số cạnh -> [tổng mức × mét, tổng mét, đóng đường?], và số mét không ghép được.
        """
        xs, ys, hs, mucs, dongs, hais = [], [], [], [], [], []
        for d in doan:
            muc = d['tt'].get('traffic_level')
            if not isinstance(muc, (int, float)) or muc != muc:     # thiếu hoặc NaN
                continue
            p = np.asarray(d['diem'], dtype=float)
            if len(p) < 2:
                continue
            mau = self._lay_mau(np.column_stack([p[:, 1] * MX, p[:, 0] * MY]))
            if mau is None:
                continue
            n = len(mau[0])
            xs.append(mau[0]); ys.append(mau[1]); hs.append(mau[2])
            mucs.append(np.full(n, float(muc)))
            dongs.append(np.full(n, bool(d['tt'].get('road_closure', False))))
            hais.append(np.full(n, d['tt'].get('traffic_road_coverage') == 'full'))
        if not xs:
            return {}, 0.0
        x, y, hg = np.concatenate(xs), np.concatenate(ys), np.concatenate(hs)
        muc, dong, hai = np.concatenate(mucs), np.concatenate(dongs), np.concatenate(hais)
        c = self._gan_nhat(x, y, hg, hai)
        ok = c >= 0
        n = len(self.xy)
        tong = np.bincount(c[ok], weights=muc[ok] * BUOC_M, minlength=n)
        met = np.bincount(c[ok], minlength=n) * BUOC_M
        bi_dong = np.bincount(c[ok], weights=dong[ok], minlength=n) > 0
        cong = {int(i): [float(tong[i]), float(met[i]), bool(bi_dong[i])] for i in np.nonzero(met)[0]}
        return cong, float(BUOC_M * (~ok).sum())


def doan_tu_tho(df):
    """Bảng thô (du_lieu/tomtom/tho/*.parquet) -> list đoạn đúng dạng BoGhep.ghep nhận."""
    import json
    import pandas as pd
    return [{'diem': json.loads(h),
             'tt': {'traffic_level': None if pd.isna(m) else float(m),
                    'traffic_road_coverage': p, 'road_closure': bool(c)}}
            for h, m, p, c in zip(df['hinh_hoc'], df['muc'], df['phu'], df['dong_duong'])]


def bang_canh(cong):
    """dict ghép -> DataFrame gọn để lưu: chi_so (int32), muc (uint8, %), phu_m (uint16), dong_duong."""
    import pandas as pd
    if not cong:
        return pd.DataFrame({'chi_so': pd.Series(dtype='int32'), 'muc': pd.Series(dtype='uint8'),
                             'phu_m': pd.Series(dtype='uint16'), 'dong_duong': pd.Series(dtype='bool')})
    k = np.fromiter(cong.keys(), dtype=np.int32)
    v = np.array(list(cong.values()), dtype=object)
    tong, met = v[:, 0].astype(float), v[:, 1].astype(float)
    df = pd.DataFrame({
        'chi_so': k,
        'muc': np.clip(np.round(100 * tong / met), 0, 100).astype(np.uint8),
        'phu_m': np.minimum(met, 65535).astype(np.uint16),
        'dong_duong': v[:, 2].astype(bool),
    })
    return df.sort_values('chi_so', ignore_index=True)
