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

    def tim(self, diem_di, diem_den, trong_so='dai', ap_luat_re=True):
        """
        trong_so: 'dai' (mét — đường ngắn nhất) hoặc 'tg' (giây — đường nhanh nhất).
        Trả về dict: nut, dai_m, tg_s, so_nut_da_xet, ten_duong (các đường đi qua).
        """
        nguon, lech_di = self.nut_gan_nhat(*diem_di)
        dich, lech_den = self.nut_gan_nhat(*diem_den)
        G = self.G
        yd, xd = G.nodes[dich]['y'], G.nodes[dich]['x']

        def h(n):
            d = khoang_cach(G.nodes[n]['y'], G.nodes[n]['x'], yd, xd)
            return d if trong_so == 'dai' else d / self._v_max

        bat_dau = (nguon, None)
        tot_nhat = {bat_dau: 0.0}
        truoc = {bat_dau: None}
        hang_doi = [(h(nguon), 0.0, nguon, None)]
        da_xet = 0
        while hang_doi:
            _, g, u, w = heapq.heappop(hang_doi)
            if g > tot_nhat.get((u, w), math.inf):
                continue
            da_xet += 1
            if u == dich:
                return self._ket_qua((u, w), truoc, da_xet, lech_di, lech_den)
            nut_truoc = truoc[(u, w)][0] if truoc[(u, w)] else None
            for v, d in G[u].items():
                w2 = d['way']
                if ap_luat_re and not self._duoc_re(w, u, w2):
                    continue
                if v == nut_truoc and w2 == w:
                    continue        # không quay đầu giữa đường
                g2 = g + d[trong_so]
                tt = (v, w2)
                if g2 < tot_nhat.get(tt, math.inf):
                    tot_nhat[tt] = g2
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
