"""
Định tuyến 3 phương án theo THỜI ĐIỂM xuất phát (tuần 7, note/KE_HOACH.md).

  ngan_nhat   ít mét nhất.
  nhanh_nhat  ít phút dự kiến nhất: thời gian qua cạnh = dài / v(cạnh, giờ XE TỚI cạnh) —
              mo_hinh_toc_do.MoHinhTocDo; xuất phát gần lần chụp mới nhất thì 30 phút đầu dùng số đo thật.
  toi_uu      thời gian × (1 + RUI_RO × mức kẹt) + phạt ngập:
                mức kẹt = max(0, 0,75 − r) / 0,75   (đoạn càng kẹt càng khó đoán giờ tới -> né bớt)
                mưa ≥ 5 mm/h: +PHAT_NGAP_S['to'] giây mỗi cạnh dễ ngập do mưa (D8, bac/ngap_canh.parquet);
                1–5 mm/h: +PHAT_NGAP_S['vua']; triều cường (bật tay): cạnh dễ ngập do triều cũng bị phạt.
Cả 3 đều CẤM cạnh đang đóng hẳn và tôn trọng một chiều / cấm rẽ / cấm xe máy (tim_duong.BanDo).
Kết quả mỗi phương án được CHẤM LẠI bằng cùng một thước đo thời gian (không tính phạt) để so công bằng.

    from ba_phuong_an import DinhTuyen
    dt_ = DinhTuyen.nap()
    kq = dt_.tim((10.7725, 106.6980), (10.8010, 106.7110), datetime(2026, 10, 30, 8, 0), mua_mm=0)
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mo_hinh_toc_do import MoHinhTocDo  # noqa: E402
from tim_duong import BanDo  # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RUI_RO = 0.5
PHAT_NGAP_S = {'to': 600.0, 'vua': 180.0}
V_SAN_KMH = 3.0


class DinhTuyen:
    def __init__(self, bd, mh, ngap_mua, ngap_trieu):
        self.bd, self.mh = bd, mh
        self.dai = np.array([d['dai'] for _, _, d in bd.G.edges(data=True)], dtype=np.float64)
        self.ngap_mua, self.ngap_trieu = ngap_mua, ngap_trieu
        self._cache = {}
        self._cam_list = mh.cam.tolist()
        self._dai_list = self.dai.tolist()
        self._dung_alt()

    def _dung_alt(self, so_moc=8):
        """
        ALT (A*, Landmarks, Triangle inequality): khoảng cách THỜI GIAN ĐƯỜNG TRỐNG từ/tới SO_MOC nút mốc
        ở rìa bản đồ. Vì tốc độ thật luôn ≤ tốc độ đường trống (r ≤ 1) và phạt chỉ cộng thêm, mọi chi phí
        của phương án nhanh nhất / tối ưu ≥ thời gian đường trống, nên |d(L, đích) − d(L, n)| là CẬN DƯỚI
        hợp lệ — A* vẫn ra đường tối ưu nhưng xét ít nút hơn nhiều so với cận khoảng cách / v_max.
        """
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        G, stt = self.bd.G, self.bd._thu_tu_nut
        u = np.array([stt[a] for a, _ in G.edges()])
        v = np.array([stt[b] for _, b in G.edges()])
        w = self.dai / (np.maximum(self.mh.v_trong, V_SAN_KMH) / 3.6)
        n = G.number_of_nodes()
        A = csr_matrix((w, (u, v)), shape=(n, n))
        rng = np.random.default_rng(42)
        trong_tplt = np.array([stt[x] for x in self.bd._nut])
        moc = [int(rng.choice(trong_tplt))]
        xa = dijkstra(A, indices=moc[0])
        for _ in range(so_moc):                 # chọn mốc xa nhất so với các mốc đã chọn
            ung = np.where(np.isfinite(xa[trong_tplt]), xa[trong_tplt], -1)
            moc.append(int(trong_tplt[int(np.argmax(ung))]))
            xa = np.minimum(xa, dijkstra(A, indices=moc[-1]))
        moc = moc[1:]                           # bỏ nút ngẫu nhiên ban đầu
        self._alt_di = dijkstra(A, indices=moc)            # d(mốc, n)
        self._alt_ve = dijkstra(A.T.tocsr(), indices=moc)  # d(n, mốc)
        self._alt_cache = {}

    def _can_duoi(self, dich):
        k = self.bd._thu_tu_nut[dich]
        if k not in self._alt_cache:
            with np.errstate(invalid='ignore'):
                a = self._alt_di[:, k][:, None] - self._alt_di       # d(L, đích) − d(L, n)
                b = self._alt_ve - self._alt_ve[:, k][:, None]       # d(n, L) − d(đích, L)
            lb = np.maximum(np.where(np.isfinite(a), a, -np.inf).max(axis=0),
                            np.where(np.isfinite(b), b, -np.inf).max(axis=0))
            self._alt_cache = {k: np.maximum(lb, 0).tolist()}     # chỉ giữ đích gần nhất
        return self._alt_cache[k]

    @classmethod
    def nap(cls, luc=None):
        bd = BanDo.nap()
        mh = MoHinhTocDo.nap(luc)
        n = bd.G.number_of_edges()
        ngap_mua, ngap_trieu = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
        tep = os.path.join(GOC, 'du_lieu', 'bac', 'ngap_canh.parquet')
        if os.path.exists(tep):
            ng = pd.read_parquet(tep)
            ngap_mua[ng.loc[ng['nguyen_nhan'] == 'mua', 'chi_so'].to_numpy()] = True
            ngap_trieu[ng.loc[ng['nguyen_nhan'] == 'trieu_cuong', 'chi_so'].to_numpy()] = True
        return cls(bd, mh, ngap_mua, ngap_trieu)

    def _thoi_gian(self, i, t_s, t0, dung_ht):
        """Giây đi qua cạnh i khi xe tới cạnh sau t_s giây kể từ lúc xuất phát t0 (giây trong ngày)."""
        gio = int((t0 + t_s) // 3600) % 24
        v = max(self.mh.km_h(i, gio, dung_ht and t_s < 1800), V_SAN_KMH)
        return self.dai[i] / (v / 3.6) * (1 + self.mh.phan_dong[i])

    def _r(self, i, t_s, t0):
        return self.mh.r_gio[int((t0 + t_s) // 3600) % 24, i]

    def _bang(self, gio, dung_ht):
        """Bảng tính sẵn cho MỘT giờ: [giây qua từng cạnh], [hệ số phạt kẹt 1 + RUI_RO·kẹt] — list Python
        (tra list nhanh hơn nhiều so với tra mảng numpy từng phần tử trong vòng lặp A*)."""
        k = (gio, dung_ht)
        if k not in self._cache:
            r = self.mh.r_gio[gio].astype(np.float64)
            if dung_ht and self.mh.r_hien_tai is not None:
                r = np.where(np.isnan(self.mh.r_hien_tai), r, self.mh.r_hien_tai)
            v = np.maximum(self.mh.v_trong * r, V_SAN_KMH)
            tg = self.dai / (v / 3.6) * (1 + self.mh.phan_dong)
            he_so = 1 + RUI_RO * np.maximum(0.0, 0.75 - self.mh.r_gio[gio]) / 0.75
            self._cache[k] = (tg.tolist(), he_so.tolist(), (self.mh.r_gio[gio] < 0.4).tolist())
        return self._cache[k]

    def tim(self, diem_di, diem_den, luc, mua_mm=0.0, trieu_cuong=False, dung_alt=True):
        """dung_alt=False: bỏ cận ALT (chỉ dùng cận khoảng cách) — để kiểm ALT không làm đổi kết quả."""
        t0 = luc.hour * 3600 + luc.minute * 60 + luc.second
        dung_ht = self.mh.r_hien_tai is not None and self.mh.luc_hien_tai is not None and \
            abs((pd.Timestamp(luc) - self.mh.luc_hien_tai).total_seconds()) <= 1800
        cam = self._cam_list
        phat = np.zeros(len(self.dai))
        if mua_mm >= 5:
            phat[self.ngap_mua] += PHAT_NGAP_S['to']
        elif mua_mm >= 1:
            phat[self.ngap_mua] += PHAT_NGAP_S['vua']
        if trieu_cuong:
            phat[self.ngap_trieu] += PHAT_NGAP_S['to']
        phat_l = phat.tolist()
        dai_l = self._dai_list
        bang = self._bang

        def bang_luc(t):
            return bang(int((t0 + t) // 3600) % 24, dung_ht and t < 1800)

        def cp_ngan(i, t):
            if cam[i]:
                return None
            return dai_l[i], bang_luc(t)[0][i]

        def cp_nhanh(i, t):
            if cam[i]:
                return None
            s = bang_luc(t)[0][i]
            return s, s

        def cp_toi_uu(i, t):
            if cam[i]:
                return None
            b = bang_luc(t)
            s = b[0][i]
            return s * b[1][i] + phat_l[i], s

        # Ước lượng A* chặt hơn: tốc độ lớn nhất TRONG 3 GIỜ kể từ lúc xuất phát (chuyến nội đô < 3 giờ),
        # thay vì lớn nhất cả ngày — vẫn không vượt chi phí thật nên vẫn ra đường tối ưu, mà xét ít nút hơn.
        h0 = int(t0 // 3600) % 24
        v_max = max(float(np.max(self.mh.v_trong * self.mh.r_gio[(h0 + k) % 24])) for k in range(3))
        if dung_ht and self.mh.r_hien_tai is not None:
            v_max = max(v_max, float(np.nanmax(self.mh.v_trong * self.mh.r_hien_tai)))

        kq = {}
        # Phương án ngắn nhất: chi phí là MÉT -> ước lượng A* = khoảng cách (v_max_kmh = 3,6 nghĩa là 1 m/s).
        alt_ = self._can_duoi if dung_alt else None
        for ten, cp, v_max, alt in (('ngan_nhat', cp_ngan, 3.6, None), ('nhanh_nhat', cp_nhanh, v_max, alt_),
                                    ('toi_uu', cp_toi_uu, v_max, alt_)):
            r = self.bd.tim(diem_di, diem_den, chi_phi=cp, v_max_kmh=v_max, uoc_luong_them=alt)
            if r is not None:
                self._cham(r, t0, dung_ht, phat)
            kq[ten] = r
        kq['_boi_canh'] = {'luc': str(luc), 'mua_mm': mua_mm, 'trieu_cuong': trieu_cuong, 'dung_so_do_hien_tai': dung_ht,
                          'gio_uoc_luong': getattr(self.mh, 'gio_uoc_luong', [])}
        return kq

    def _cham(self, r, t0, dung_ht, phat):
        """Chấm lại tuyến bằng CÙNG thước đo thời gian; đếm cạnh kẹt / dễ ngập / đóng."""
        G = self.bd.G
        idx = [G[a][b]['i'] for a, b in zip(r['nut'], r['nut'][1:])]
        t, so_ket, so_ngap, so_cam = 0.0, 0, 0, 0
        for i in idx:
            tg, _, ket = self._bang(int((t0 + t) // 3600) % 24, dung_ht and t < 1800)
            so_ket += ket[i]
            so_ngap += int(phat[i] > 0)
            so_cam += int(self.mh.cam[i])
            t += tg[i]
        r.update({'phut': round(t / 60, 1), 'canh': idx, 'so_canh_ket': so_ket, 'so_canh_ngap': so_ngap,
                  'so_canh_dong': so_cam})


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    luc = dt.datetime(2026, 10, 30, 8, 0)
    d = DinhTuyen.nap(luc)
    for gio, mua in ((3, 0), (8, 0), (8, 10)):
        luc = luc.replace(hour=gio)
        kq = d.tim((10.7725, 106.6980), (10.8005, 106.6605), luc, mua_mm=mua)    # Bến Thành -> Lăng Cha Cả
        print(f'Ben Thanh -> Lang Cha Ca, {luc:%H:%M}, mua {mua} mm/h:')
        for ten in ('ngan_nhat', 'nhanh_nhat', 'toi_uu'):
            r = kq[ten]
            print(f'  {ten:<11} {r["dai_m"]:>6} m  {r["phut"]:>5} phut  ket {r["so_canh_ket"]:>3}  ngap {r["so_canh_ngap"]}'
                  f'  | {" > ".join(r["ten_duong"][:6])}')
