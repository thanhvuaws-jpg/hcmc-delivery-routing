"""
Định tuyến 3 phương án theo THỜI ĐIỂM xuất phát (tuần 7, note/KE_HOACH.md).

  ngan_nhat   ít mét nhất.
  nhanh_nhat  ít phút dự kiến nhất: thời gian qua cạnh = dài / v(cạnh, giờ XE TỚI cạnh) —
              mo_hinh_toc_do.MoHinhTocDo; xuất phát gần lần chụp mới nhất thì 30 phút đầu dùng số đo thật.
  toi_uu      thời gian × (1 + RUI_RO × mức kẹt + RUI_RO_KHONG_DO × [cạnh không có số đo]) + phạt ngập:
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
# Cạnh KHÔNG có số đo (hẻm, đường nhỏ TomTom không đo) chỉ có tốc độ ước lượng: phương án tối ưu cộng thêm
# 30% thời gian dự phòng. Chấm khắt khe 30/10 (hẻm chậm hơn ước lượng 30%): không có dự phòng thì tuyến
# tối ưu luồn hẻm, chỉ 77% chuyến không chậm hơn tuyến ngắn nhất (danh_gia/cham_tuyen_that.py).
RUI_RO_KHONG_DO = 0.3
PHAT_NGAP_S = {'to': 600.0, 'vua': 180.0}
# Phương án tối ưu: mỗi lần rẽ TRÁI tại nút giao có trục lớn (tim_duong.la_re_trai_lon) cộng 30 s vào chi phí
# (không vào giờ tới dự kiến) — QĐ-016.
PHAT_RE_TRAI_S = 30.0
# Tuyến thay thế (QĐ-016): phạt lặp ×1,5 cạnh đã dùng; nhận khi chi phí ≤ 1,25 × tốt nhất và trùng ≤ 70% chiều dài
# (giới hạn kéo dãn 25% như Abraham và cs. 2010; trùng chặt hơn mức 80% của họ để tuyến khác nhau thấy rõ).
PHAT_LAP, GIAN_TOI_DA, TRUNG_TOI_DA = 1.5, 1.25, 0.7
V_SAN_KMH = 3.0


class DinhTuyen:
    def __init__(self, bd, mh, ngap_mua, ngap_trieu):
        self.bd, self.mh = bd, mh
        self.dai = np.array([d['dai'] for _, _, d in bd.G.edges(data=True)], dtype=np.float64)
        self.ngap_mua, self.ngap_trieu = ngap_mua, ngap_trieu
        self._cache = {}
        self._cam_list = mh.cam.tolist()
        self._dai_list = self.dai.tolist()
        self._dau_cuoi = list(bd.G.edges())          # chỉ số cạnh -> (nút đầu, nút cuối)
        self.phat_re_trai_s = PHAT_RE_TRAI_S
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
        self._moc, self._uv, self._n_nut = moc[1:], (u, v), n      # bỏ nút ngẫu nhiên ban đầu
        self._alt_bang = {}

    def _alt_cho(self, h0, dung_ht):
        """
        Khoảng cách ALT (từ / tới các mốc) với trọng số = thời gian qua cạnh ở tốc độ LỚN NHẤT của cạnh đó trong
        3 giờ kể từ giờ h0 (kèm số đo hiện tại nếu dùng). Mọi chi phí nhanh nhất / tối ưu của chuyến bắt đầu
        trong giờ h0 (chuyến < 2 giờ) ≥ trọng số này -> vẫn là CẬN DƯỚI hợp lệ, nhưng chặt hơn nhiều so với
        tốc độ đường trống khi đang kẹt (31/10/2026: chuyển sang trạng thái theo cạnh làm số trạng thái tăng,
        tuyến 8h chậm nhất lên 2,3–2,8 s; cận chặt hơn kéo lại). Nhớ theo (h0, dung_ht), xóa khi đổi tình trạng.
        Bảng riêng cho phương án tối ưu: nhân thêm hệ số phạt NHỎ NHẤT trong cửa sổ (r lớn nhất của r_gio — đúng
        như _bang tính hệ số; cạnh không có số đo luôn +RUI_RO_KHONG_DO).
        """
        if (h0, dung_ht) not in self._alt_bang:
            from scipy.sparse import csr_matrix
            from scipy.sparse.csgraph import dijkstra
            r_gio = self.mh.r_gio[[(h0 + j) % 24 for j in range(3)]].max(axis=0).astype(np.float64)
            r = np.fmax(r_gio, self.mh.r_hien_tai) if dung_ht and self.mh.r_hien_tai is not None else r_gio
            tg = self.dai / (np.maximum(self.mh.v_trong * r, V_SAN_KMH) / 3.6)
            khong_do = ~getattr(self.mh, 'co_so_do', np.ones(len(self.dai), dtype=bool))
            he_so = 1 + RUI_RO * np.maximum(0.0, 0.75 - r_gio) / 0.75 + RUI_RO_KHONG_DO * khong_do
            bang = {}
            for ten, w in (('nhanh_nhat', tg), ('toi_uu', tg * he_so)):
                A = csr_matrix((w, self._uv), shape=(self._n_nut, self._n_nut))
                bang[ten] = (dijkstra(A, indices=self._moc), dijkstra(A.T.tocsr(), indices=self._moc), {})
            self._alt_bang = {(h0, dung_ht): bang}
        return self._alt_bang[(h0, dung_ht)]

    def _can_duoi_luc(self, h0, dung_ht, phuong_an):
        """Hàm (nút đích) -> list cận dưới từ mọi nút, theo bảng ALT của giờ h0 cho phương án đó."""
        alt_di, alt_ve, nho = self._alt_cho(h0, dung_ht)[phuong_an]

        def can_duoi(dich):
            k = self.bd._thu_tu_nut[dich]
            if k not in nho:
                with np.errstate(invalid='ignore'):
                    a = alt_di[:, k][:, None] - alt_di       # d(L, đích) − d(L, n)
                    b = alt_ve - alt_ve[:, k][:, None]       # d(n, L) − d(đích, L)
                lb = np.maximum(np.where(np.isfinite(a), a, -np.inf).max(axis=0),
                                np.where(np.isfinite(b), b, -np.inf).max(axis=0))
                nho.clear()                                  # chỉ giữ đích gần nhất
                nho[k] = np.maximum(lb, 0).tolist()
            return nho[k]
        return can_duoi

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
            khong_do = ~getattr(self.mh, 'co_so_do', np.ones(len(self.dai), dtype=bool))
            he_so = (1 + RUI_RO * np.maximum(0.0, 0.75 - self.mh.r_gio[gio]) / 0.75
                     + RUI_RO_KHONG_DO * khong_do)
            self._cache[k] = (tg.tolist(), he_so.tolist(), (self.mh.r_gio[gio] < 0.4).tolist())
        return self._cache[k]

    def dat_tinh_trang(self, r_moi_gio=None, cam=None, phan_dong=None):
        """
        Thay "những gì bộ định tuyến biết" (dùng khi chấm lại bằng dữ liệu quá khứ, danh_gia/):
          r_moi_gio (n,): dùng CÙNG một r cho mọi giờ (tình trạng lúc xuất phát giữ nguyên suốt chuyến)
          cam (n,) bool, phan_dong (n,): đường đóng lúc xuất phát
        Không làm hỏng cận ALT (vẫn r ≤ 1 so với v_trống). Xóa bảng tính sẵn để tính lại.
        """
        n = len(self.dai)
        if r_moi_gio is not None:
            self.mh.r_gio = np.broadcast_to(np.asarray(r_moi_gio, dtype=np.float32), (24, n))
        if cam is not None:
            self.mh.cam = np.asarray(cam, dtype=bool)
            self._cam_list = self.mh.cam.tolist()
        if phan_dong is not None:
            self.mh.phan_dong = np.asarray(phan_dong, dtype=np.float32)
        self.mh.r_hien_tai = None
        self._cache = {}
        self._alt_bang = {}

    def _boi_canh(self, luc, mua_mm, trieu_cuong):
        """Giây trong ngày lúc xuất phát, có dùng số đo hiện tại không, mảng phạt ngập theo cạnh."""
        t0 = luc.hour * 3600 + luc.minute * 60 + luc.second
        dung_ht = self.mh.r_hien_tai is not None and self.mh.luc_hien_tai is not None and \
            abs((pd.Timestamp(luc) - self.mh.luc_hien_tai).total_seconds()) <= 1800
        phat = np.zeros(len(self.dai))
        if mua_mm >= 5:
            phat[self.ngap_mua] += PHAT_NGAP_S['to']
        elif mua_mm >= 1:
            phat[self.ngap_mua] += PHAT_NGAP_S['vua']
        if trieu_cuong:
            phat[self.ngap_trieu] += PHAT_NGAP_S['to']
        return t0, dung_ht, phat

    def _ham_chi_phi(self, t0, dung_ht, phat):
        """Hàm chi phí (chỉ số cạnh, giây đã đi) -> (chi phí, giây qua cạnh) | None của 3 phương án."""
        cam = self._cam_list
        phat_l = phat.tolist()
        dai_l = self._dai_list
        bang, nho = self._bang, self._cache

        def bang_luc(t):
            # Gọi mỗi lần nới một cạnh trong A*: tra thẳng bộ nhớ đệm, chỉ gọi _bang khi giờ đó chưa tính.
            k = (int((t0 + t) // 3600) % 24, dung_ht and t < 1800)
            b = nho.get(k)
            return b if b is not None else bang(*k)

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

        return {'ngan_nhat': cp_ngan, 'nhanh_nhat': cp_nhanh, 'toi_uu': cp_toi_uu}

    def chi_phi_tuyen(self, canh, luc, phuong_an='toi_uu', mua_mm=0.0, trieu_cuong=False, di_tu=None):
        """
        (chi phí, giây) của một tuyến CHO SẴN (danh sách chỉ số cạnh, đi từ lúc luc) theo đúng thước đo của
        tim(); None nếu tuyến đi qua đường đang đóng. Dùng khi tính lại giữa đường: so "đi tiếp tuyến cũ"
        với tuyến mới trên cùng một thước đo. di_tu = (nút trước, nút đầu tuyến) như tim() — để tính phạt rẽ
        trái ngay ở nút đầu.
        """
        t0, dung_ht, phat = self._boi_canh(luc, mua_mm, trieu_cuong)
        cp = self._ham_chi_phi(t0, dung_ht, phat)[phuong_an]
        c, t = 0.0, 0.0
        for i in canh:
            x = cp(i, t)
            if x is None:
                return None
            c, t = c + x[0], t + x[1]
        if phuong_an == 'toi_uu' and canh:
            nut = [self._dau_cuoi[canh[0]][0]] + [self._dau_cuoi[i][1] for i in canh]
            c += self.phat_re_trai_s * self.bd.dem_re_trai_lon(nut, di_tu[0] if di_tu else None)
        return c, t

    def _v_max(self, t0, dung_ht):
        """Giờ xuất phát, tốc độ lớn nhất (km/h) TRONG 3 GIỜ kể từ lúc xuất phát (chuyến nội đô < 3 giờ) — cho
        ước lượng khoảng cách của A*: không vượt chi phí thật nên vẫn ra đường tối ưu, mà xét ít nút hơn."""
        h0 = int(t0 // 3600) % 24
        v_max = max(float(np.max(self.mh.v_trong * self.mh.r_gio[(h0 + k) % 24])) for k in range(3))
        if dung_ht and self.mh.r_hien_tai is not None:
            v_max = max(v_max, float(np.nanmax(self.mh.v_trong * self.mh.r_hien_tai)))
        return h0, v_max

    def tuyen_thay_the(self, diem_di, diem_den, luc, k=3, phuong_an='toi_uu', mua_mm=0.0, trieu_cuong=False,
                       tuyen_dau=None):
        """
        Tối đa k tuyến KHÁC NHAU cho người dùng chọn, bằng PHƯƠNG PHÁP PHẠT (QĐ-016): tìm tuyến tốt nhất, nhân chi
        phí các cạnh vừa dùng × PHAT_LAP rồi tìm lại; nhận tuyến mới khi
          (a) chi phí THẬT (không phạt lặp) ≤ GIAN_TOI_DA × tuyến tốt nhất,
          (b) phần chiều dài trùng với MỖI tuyến đã nhận ≤ TRUNG_TOI_DA.
        Thử tối đa 2k lần. Trả về list tuyến (tuyến đầu = tim() cùng phương án), mỗi tuyến thêm chi_phi_that,
        gian (chi phí thật / tuyến tốt nhất), trung (phần trùng lớn nhất với các tuyến trước).
        tuyen_dau: kết quả tim() đã có (cùng điểm, lúc, phương án) -> bỏ được một lượt tìm.
        Tốn ~1 s trung bình, tới ~4 s cặp xa giờ cao điểm (mỗi lượt sau khi phạt xét nhiều trạng thái hơn):
        API nên trả 3 phương án trước, tuyến thay thế gọi riêng.
        """
        t0, dung_ht, phat = self._boi_canh(luc, mua_mm, trieu_cuong)
        cp = self._ham_chi_phi(t0, dung_ht, phat)[phuong_an]
        h0, v_max = self._v_max(t0, dung_ht)
        alt = self._can_duoi_luc(h0, dung_ht, phuong_an) if phuong_an != 'ngan_nhat' else None
        if phuong_an == 'ngan_nhat':
            v_max = 3.6
        nhan = {}

        def cp_phat(i, t):                  # phạt lặp chỉ NHÂN thêm (≥ 1) -> cận ALT / khoảng cách vẫn hợp lệ
            x = cp(i, t)
            if x is None:
                return None
            m = nhan.get(i)
            return x if m is None else (x[0] * m, x[1])

        nhan_tuyen, tot_nhat = [], None
        for lan in range(2 * k):
            if lan == 0 and tuyen_dau is not None:
                r = dict(tuyen_dau)
            else:
                r = self.bd.tim(diem_di, diem_den, chi_phi=cp_phat, v_max_kmh=v_max, uoc_luong_them=alt,
                                phat_re_trai_s=self.phat_re_trai_s if phuong_an == 'toi_uu' else 0.0)
                if r is None:
                    break
                self._cham(r, t0, dung_ht, phat)
            for i in r['canh']:
                nhan[i] = nhan.get(i, 1.0) * PHAT_LAP
            that = self.chi_phi_tuyen(r['canh'], luc, phuong_an, mua_mm, trieu_cuong)[0]
            if tot_nhat is None:
                tot_nhat = that
            if that > GIAN_TOI_DA * tot_nhat:
                break                       # phạt đã đẩy sang tuyến quá vòng — các lần sau chỉ tệ hơn
            dung = set(r['canh'])
            dai = max(sum(self._dai_list[i] for i in r['canh']), 1.0)
            trung = max((sum(self._dai_list[i] for i in dung & set(q['canh'])) / dai for q in nhan_tuyen), default=0.0)
            if trung <= TRUNG_TOI_DA:
                r.update(chi_phi_that=round(that, 1), gian=round(that / tot_nhat, 3), trung=round(trung, 3))
                nhan_tuyen.append(r)
                if len(nhan_tuyen) >= k:
                    break
        return nhan_tuyen

    def tim(self, diem_di, diem_den, luc, mua_mm=0.0, trieu_cuong=False, dung_alt=True,
            phuong_an=('ngan_nhat', 'nhanh_nhat', 'toi_uu'), di_tu=None):
        """dung_alt=False: bỏ cận ALT (chỉ dùng cận khoảng cách) — để kiểm ALT không làm đổi kết quả.
        phuong_an: chỉ tính những phương án cần (đỡ thời gian khi chấm hàng loạt).
        di_tu: (nút trước, nút hiện tại) — tính lại tuyến cho xe đang chạy (tim_duong.BanDo.tim), luc = bây giờ."""
        t0, dung_ht, phat = self._boi_canh(luc, mua_mm, trieu_cuong)
        ham = self._ham_chi_phi(t0, dung_ht, phat)
        h0, v_max = self._v_max(t0, dung_ht)
        kq = {}
        # Phương án ngắn nhất: chi phí là MÉT -> ước lượng A* = khoảng cách (v_max_kmh = 3,6 nghĩa là 1 m/s).
        for ten, v_max in (('ngan_nhat', 3.6), ('nhanh_nhat', v_max), ('toi_uu', v_max)):
            if ten not in phuong_an:
                continue
            alt = self._can_duoi_luc(h0, dung_ht, ten) if dung_alt and ten != 'ngan_nhat' else None
            r = self.bd.tim(diem_di, diem_den, chi_phi=ham[ten], v_max_kmh=v_max, uoc_luong_them=alt,
                            di_tu=di_tu, phat_re_trai_s=self.phat_re_trai_s if ten == 'toi_uu' else 0.0)
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
