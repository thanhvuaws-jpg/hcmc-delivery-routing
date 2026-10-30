"""
Tìm đường trên đồ thị xe máy (do_thi.py), có tôn trọng luật cấm rẽ.

Vì sao không dùng thẳng nx.shortest_path: luật cấm rẽ gắn với CẶP đường
(đi từ đường A, qua nút X, không được sang đường B). Đồ thị nút–cạnh thông
thường không nhớ "đang đi trên đường nào", nên không biết lúc tới X có được
rẽ sang B hay không. Ở đây trạng thái tìm kiếm là (nút, đường đang đi), nhờ
vậy áp được luật.

Thuật toán: A* với hàm ước lượng là khoảng cách đường chim bay (đảm bảo không
đánh giá quá cao, nên vẫn ra đường tối ưu).

    from tim_duong import BanDo
    bd = BanDo.nap()
    kq = bd.tim((10.7725, 106.6980), (10.8010, 106.7110), trong_so='dai')
"""
import heapq
import math
import os
import pickle

import numpy as np

from do_thi import TEP_RA, khoang_cach


class BanDo:
    def __init__(self, du_lieu):
        self.G = du_lieu['G']
        self.cam = du_lieu['cam']
        self.chi = du_lieu['chi']
        self.thong_ke = du_lieu['thong_ke']
        # Chỉ "bắt" điểm vào thành phần liên thông mạnh lớn nhất (xem do_thi.py).
        self._nut = np.array(list(du_lieu['tplt']))
        self._toa_do = np.array([(self.G.nodes[n]['y'], self.G.nodes[n]['x']) for n in self._nut])
        self._v_max = max(d['toc_do'] for _, _, d in self.G.edges(data=True)) / 3.6
        # Chỉ số cạnh = thứ tự G.edges(), trùng du_lieu/do_thi/canh.parquet (cùng dựng từ pickle này)
        # — để tra mảng tốc độ / đóng đường / ngập theo cạnh.
        for i, (u, v) in enumerate(self.G.edges()):
            self.G[u][v]['i'] = i
        # Tính sẵn cho vòng lặp A* (30/10/2026: lớp truy cập networkx + haversine + kiểm luật mỗi bước
        # chiếm phần lớn thời gian): danh sách kề dạng tuple, toạ độ mét phẳng, tập (đường, nút) có luật rẽ.
        self._ke = {u: [(v, d['way'], d['i'], d['dai'], d['tg']) for v, d in nbrs.items()]
                    for u, nbrs in self.G.adjacency()}
        cos0 = math.cos(math.radians(10.78))
        self._xy = {n: (d['x'] * 111_320 * cos0, d['y'] * 110_574) for n, d in self.G.nodes(data=True)}
        self._co_luat = set(self.cam) | set(self.chi)
        self._thu_tu_nut = {n: k for k, n in enumerate(self.G.nodes())}

    @classmethod
    def nap(cls, tep=TEP_RA):
        with open(tep, 'rb') as f:
            return cls(pickle.load(f))

    def nut_gan_nhat(self, vi_do, kinh_do):
        # Đổi độ sang mét gần đúng quanh vĩ độ TP.HCM — đủ để chọn nút gần nhất.
        dy = (self._toa_do[:, 0] - vi_do) * 111_320
        dx = (self._toa_do[:, 1] - kinh_do) * 111_320 * math.cos(math.radians(vi_do))
        i = int(np.argmin(dx * dx + dy * dy))
        return int(self._nut[i]), float(math.hypot(dx[i], dy[i]))

    def _duoc_re(self, duong_vao, nut, duong_ra):
        if duong_vao is None:
            return True
        chi_duoc = self.chi.get((duong_vao, nut))
        if chi_duoc is not None and chi_duoc != duong_ra:
            return False
        return duong_ra not in self.cam.get((duong_vao, nut), ())

    def tim(self, diem_di, diem_den, trong_so='dai', ap_luat_re=True, chi_phi=None, v_max_kmh=None,
            uoc_luong_them=None):
        """
        trong_so: 'dai' (mét — đường ngắn nhất) hoặc 'tg' (giây — đường nhanh nhất, tốc độ mặc định).
        chi_phi:  (tùy chọn) hàm (chỉ số cạnh, số giây đã đi) -> (chi phí, số giây qua cạnh), hoặc None
                  nếu cạnh bị cấm (đường đóng). Dùng cho định tuyến THEO THỜI ĐIỂM (dinh_tuyen/ba_phuong_an.py):
                  thời gian qua cạnh phụ thuộc lúc xe tới cạnh. Khi dùng thì trong_so bị bỏ qua và
                  v_max_kmh (tốc độ lớn nhất có thể) bắt buộc — để ước lượng A* không đánh giá quá cao.
        uoc_luong_them: (tùy chọn) hàm (nút đích) -> list cận dưới chi phí từ MỖI nút (theo thứ tự
                  G.nodes()) tới nút đích, vd từ landmark (ALT). A* lấy max với cận khoảng cách — chỉ
                  đúng khi mọi giá trị là CẬN DƯỚI thật (không làm mất tính tối ưu).
        Trả về dict: nut, dai_m, tg_s, so_nut_da_xet, ten_duong (các đường đi qua); có chi_phi thì thêm
        chi_phi (tổng) và tg_du_kien_s (tổng giây theo hàm chi_phi).
        """
        nguon, lech_di = self.nut_gan_nhat(*diem_di)
        dich, lech_den = self.nut_gan_nhat(*diem_den)
        if chi_phi is not None:
            v_h = v_max_kmh / 3.6               # chi phí >= thời gian (phạt chỉ cộng thêm)
        else:
            v_h = 1.0 if trong_so == 'dai' else self._v_max
        # Ước lượng A* = khoảng cách phẳng (mét) / v_h, nhân 0,995: mét phẳng lệch haversine < 0,1% trong
        # vùng bản đồ — hệ số này giữ ước lượng không vượt chi phí thật (A* vẫn ra đường tối ưu).
        xd, yd = self._xy[dich]
        he_so_h = 0.995 / v_h
        xy, ke, co_luat, hypot = self._xy, self._ke, self._co_luat, math.hypot
        them = uoc_luong_them(dich) if uoc_luong_them is not None else None
        stt = self._thu_tu_nut

        def h(n):
            x, y = xy[n]
            e = hypot(x - xd, y - yd) * he_so_h
            return e if them is None else max(e, them[stt[n]])

        bat_dau = (nguon, None)
        tot_nhat = {bat_dau: 0.0}
        giay = {bat_dau: 0.0}
        truoc = {bat_dau: None}
        hang_doi = [(h(nguon), 0.0, nguon, None)]
        da_xet = 0
        while hang_doi:
            _, g, u, w = heapq.heappop(hang_doi)
            if g > tot_nhat.get((u, w), math.inf):
                continue
            da_xet += 1
            if u == dich:
                kq = self._ket_qua((u, w), truoc, da_xet, lech_di, lech_den)
                if chi_phi is not None:
                    kq['chi_phi'] = round(g, 1)
                    kq['tg_du_kien_s'] = round(giay[(u, w)])
                return kq
            nut_truoc = truoc[(u, w)][0] if truoc[(u, w)] else None
            t_u = giay[(u, w)]
            kiem_re = ap_luat_re and (w, u) in co_luat
            for v, w2, i, dai, tg in ke.get(u, ()):
                if kiem_re and not self._duoc_re(w, u, w2):
                    continue
                if v == nut_truoc and w2 == w:
                    continue        # không quay đầu giữa đường
                if chi_phi is None:
                    c, s = (dai if trong_so == 'dai' else tg), tg
                else:
                    cp = chi_phi(i, t_u)
                    if cp is None:
                        continue    # cạnh bị cấm (đường đang đóng)
                    c, s = cp
                g2 = g + c
                tt = (v, w2)
                if g2 < tot_nhat.get(tt, math.inf):
                    tot_nhat[tt] = g2
                    giay[tt] = t_u + s
                    truoc[tt] = (u, w)
                    heapq.heappush(hang_doi, (g2 + h(v), g2, v, w2))
        return None

    def _ket_qua(self, tt, truoc, da_xet, lech_di, lech_den):
        nut = []
        while tt:
            nut.append(tt[0])
            tt = truoc[tt]
        nut.reverse()
        canh = [self.G[a][b] for a, b in zip(nut, nut[1:])]
        ten = []
        for c in canh:
            if c['ten'] and (not ten or ten[-1] != c['ten']):
                ten.append(c['ten'])
        return {
            'nut': nut,
            'toa_do': [(self.G.nodes[n]['y'], self.G.nodes[n]['x']) for n in nut],
            'dai_m': round(sum(c['dai'] for c in canh)),
            'tg_s': round(sum(c['tg'] for c in canh)),
            'duong_dung': [c['way'] for c in canh],
            'ten_duong': ten,
            'so_nut_da_xet': da_xet,
            'lech_diem_di_m': round(lech_di), 'lech_diem_den_m': round(lech_den),
        }


if __name__ == '__main__':
    import sys
    import time
    sys.stdout.reconfigure(encoding='utf-8')
    bd = BanDo.nap()
    t0 = time.time()
    kq = bd.tim((10.7725, 106.6980), (10.8010, 106.7110))
    print(f"Ben Thanh -> Hang Xanh: {kq['dai_m']} m, {kq['tg_s'] // 60} phut, {time.time() - t0:.2f}s")
    print(' -> '.join(kq['ten_duong']))
