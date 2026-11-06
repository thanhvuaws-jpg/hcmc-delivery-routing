"""
Phần tính toán của API định tuyến (QĐ-018), tách khỏi HTTP để kiểm thử được.

Mọi câu hỏi đều gắn với một THỜI ĐIỂM trong dữ liệu đã thu: bộ định tuyến chỉ biết lần chụp TomTom mới nhất ≤ thời
điểm đó (coi như giữ nguyên suốt chuyến), giống phương án C, D của danh_gia/cham_tuyen_that.py, nên không dùng dữ liệu
tương lai. Vì là dữ liệu quá khứ nên trả thêm được "thực tế đã xảy ra": cho xe chạy lại trên tuyến theo tốc độ đo
thật ở từng lần chụp sau đó — so được dự kiến với thực tế.

DinhTuyen giữ tình trạng bên trong (dat_tinh_trang) nên mọi yêu cầu đi qua một khóa, chạy lần lượt.
"""
import glob
import os
import sys
import threading
from functools import lru_cache

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ba_phuong_an import DinhTuyen  # noqa: E402
from chi_dan import chi_dan, ten_theo_doan  # noqa: E402
from mo_hinh_toc_do import MoHinhTocDo, R_SAN  # noqa: E402

BAC = os.path.join(GOC, 'du_lieu', 'bac')
SILVER = os.path.join(BAC, 'tomtom_canh')
TEP_HO_SO = os.path.join(BAC, 'ho_so_api.npz')
VUNG = (10.721, 106.607, 10.838, 106.748)       # nam, tây, bắc, đông — vùng 30 ô TomTom (thu_thap/tai_osm.py)
V_SAN_KMH = 3.0
PHAT_DONG_S = 300.0                             # như danh_gia/cham_tuyen_that.py
CUA_SO_THUC_TE = pd.Timedelta(hours=2)
CACH_GIO_TOI_DA_S = 600                         # lần chụp cách quá 10 phút thì coi như không có dữ liệu
PHUONG_AN = ('ngan_nhat', 'nhanh_nhat', 'toi_uu')
NGUONG_DOI_S = 60.0                             # như danh_gia/cham_tuyen_that.py, QĐ-013
NGUON_DO, NGUON_HO_SO, NGUON_HET = 0, 1, 2      # tốc độ xe ảo: đo thật / hồ sơ vì cạnh không đo / đã hết số đo


class LoiYeuCau(ValueError):
    """Yêu cầu sai (ngoài vùng, ngoài khoảng dữ liệu): API trả 400 kèm thông báo này."""


def dung_ho_so():
    """Tính hồ sơ từ toàn bộ tầng bạc rồi lưu ra TEP_HO_SO (chạy lại sau mỗi lần kéo dữ liệu mới)."""
    MoHinhTocDo.nap(None).luu(TEP_HO_SO)


@lru_cache(maxsize=8)
def _doc_lan_chup(ngay, luc):
    """(chỉ số cạnh, r, phần đóng, đóng hết?) của một lần chụp; đọc riêng lần chụp đó từ tệp của ngày."""
    s = pd.read_parquet(os.path.join(SILVER, f'{ngay}.parquet'), columns=['chi_so', 'muc', 'phu', 'phu_dong'],
                        filters=[('khung', '==', pd.Timestamp(luc))])
    return (s['chi_so'].to_numpy(), s['muc'].to_numpy(), s['phu'].to_numpy(), s['phu_dong'].to_numpy())


class DichVu:
    def __init__(self):
        if not os.path.exists(TEP_HO_SO):
            dung_ho_so()
        self.d = DinhTuyen.nap(None, TEP_HO_SO)
        self.khoa = threading.RLock()
        self.r_ho_so = np.array(self.d.mh.r_gio, dtype=np.float32)      # (24, n): dat_tinh_trang sẽ đè mh.r_gio
        self.v_trong = self.d.mh.v_trong.astype(np.float64)
        self.n = len(self.d.dai)
        self.lan_chup_dang_biet = None
        self._hinh_doan = None
        self._doan_cua = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))['doan'].to_numpy()
        self.cac_ngay = sorted(os.path.basename(t)[:10] for t in glob.glob(os.path.join(SILVER, '*.parquet')))

    # ── Dữ liệu có tới đâu, chọn lần chụp ──
    def _cac_khung(self, ngay):
        return np.sort(pd.read_parquet(os.path.join(SILVER, f'{ngay}.parquet'), columns=['khung'])['khung'].unique())

    @property
    def khung_moi_nhat(self):
        return pd.Timestamp(self._cac_khung(self.cac_ngay[-1])[-1])

    def thong_tin(self):
        return {'ngay': self.cac_ngay, 'moi_nhat': str(self.khung_moi_nhat), 'vung': VUNG,
                'so_canh': self.n, 'so_nut': self.d.bd.G.number_of_nodes()}

    def lan_chup_gan(self, luc=None):
        """Lần chụp mới nhất ≤ luc (mặc định: mới nhất có dữ liệu)."""
        luc = self.khung_moi_nhat if luc is None else pd.Timestamp(luc)
        ngay = f'{luc:%Y-%m-%d}'
        if ngay not in self.cac_ngay:
            raise LoiYeuCau(f'Chua co du lieu ngay {ngay}. Co: {self.cac_ngay[0]} -> {self.cac_ngay[-1]}.')
        khung = self._cac_khung(ngay)
        k = int(np.searchsorted(khung, np.datetime64(luc), side='right')) - 1
        if k < 0 or (luc - pd.Timestamp(khung[k])).total_seconds() > CACH_GIO_TOI_DA_S:
            raise LoiYeuCau(f'Khong co lan chup gan {luc}.')
        return pd.Timestamp(khung[k])

    def _biet_luc(self, kh):
        """Đặt tình trạng bộ định tuyến theo lần chụp kh; bỏ qua nếu đang đúng lần chụp đó (dựng lại tốn ~1 s)."""
        if self.lan_chup_dang_biet == kh:
            return
        i, muc, phu, phu_dong = _doc_lan_chup(f'{kh:%Y-%m-%d}', kh.to_datetime64())
        r = self.r_ho_so[kh.hour].astype(np.float32).copy()
        mo = phu > 0
        r[i[mo]] = np.maximum(muc[mo] / 100, R_SAN)
        cam, phan_dong = np.zeros(self.n, dtype=bool), np.zeros(self.n, dtype=np.float32)
        cam[i[~mo & (phu_dong > 0)]] = True
        phan_dong[i] = phu_dong / 100
        self.d.dat_tinh_trang(r, cam, phan_dong)
        self.lan_chup_dang_biet = kh

    @staticmethod
    def _kiem_diem(ten, p):
        if not (VUNG[0] <= p[0] <= VUNG[2] and VUNG[1] <= p[1] <= VUNG[3]):
            raise LoiYeuCau(f'Diem {ten} nam ngoai vung ban do ({VUNG[0]}–{VUNG[2]}, {VUNG[1]}–{VUNG[3]}).')

    # ── Thực tế đã xảy ra ──
    def _bang_thuc_te(self, kh, canh_can):
        """{lần chụp: (r theo cạnh cần, đóng, phần đóng)} trong CUA_SO_THUC_TE kể từ kh (chỉ cạnh cần, để nhẹ)."""
        den = kh + CUA_SO_THUC_TE
        cot = ['khung', 'chi_so', 'muc', 'phu', 'phu_dong']
        loc = [('khung', '>=', kh), ('khung', '<=', den), ('chi_so', 'in', canh_can.tolist())]
        phan = [pd.read_parquet(os.path.join(SILVER, f'{n:%Y-%m-%d}.parquet'), columns=cot, filters=loc)
                for n in sorted({kh.normalize(), den.normalize()}) if f'{n:%Y-%m-%d}' in self.cac_ngay]
        s = pd.concat(phan, ignore_index=True)
        cac_khung = np.sort(s['khung'].unique())
        vi_tri = {int(c): j for j, c in enumerate(canh_can)}
        R = np.full((len(cac_khung), len(canh_can)), np.nan, dtype=np.float32)
        DONG = np.zeros(R.shape, dtype=bool)
        PD = np.zeros(R.shape, dtype=np.float32)
        ki = np.searchsorted(cac_khung, s['khung'].to_numpy())
        ni = s['chi_so'].map(vi_tri).to_numpy()
        mo = (s['phu'] > 0).to_numpy()
        R[ki[mo], ni[mo]] = np.maximum(s['muc'].to_numpy()[mo] / 100, R_SAN)
        DONG[ki[~mo], ni[~mo]] = (s['phu_dong'].to_numpy()[~mo] > 0)
        PD[ki, ni] = s['phu_dong'].to_numpy() / 100
        return cac_khung, R, DONG, PD, vi_tri

    def _chay_lai(self, canh, luc, bang):
        """
        Cho xe chạy lại trên tuyến từ lúc luc theo số đo thật ở lần chụp ứng với lúc xe tới từng cạnh (công thức như
        cham_tuyen_that.buoc). Từng cạnh: giây, r (%), nguồn số đo, có đóng không.
        Hết số đo (quá lần chụp cuối) thì chạy tiếp bằng lần chụp cuối, đánh dấu NGUON_HET và het_du_lieu = True.
        """
        cac_khung, R, DONG, PD, vi_tri = bang
        tau, co_do, vao_dong, het = 0.0, 0.0, 0, False
        giay, ra_r, nguon, dong_ra = [], [], [], []
        for i in canh:
            i = int(i)
            t = luc + pd.Timedelta(seconds=tau)
            k = int(np.searchsorted(cac_khung, np.datetime64(t), side='right')) - 1
            con_so = k >= 0 and (t - pd.Timestamp(cac_khung[k])).total_seconds() < CACH_GIO_TOI_DA_S
            het = het or not con_so
            j = vi_tri[i]
            r, dong, phan_dong = (R[k, j], int(DONG[k, j]), PD[k, j]) if k >= 0 else (np.nan, 0, 0.0)
            dai = self.d.dai[i]
            do_duoc = r == r
            if do_duoc:
                co_do += dai
            else:
                r = self.r_ho_so[t.hour, i]
            vao_dong += dong
            s = dai / (max(self.v_trong[i] * r, V_SAN_KMH) / 3.6) * (1 + phan_dong) + PHAT_DONG_S * dong
            tau += s
            giay.append(round(float(s), 2))
            ra_r.append(int(round(float(r) * 100)))
            nguon.append(NGUON_HET if not con_so else NGUON_DO if do_duoc else NGUON_HO_SO)
            dong_ra.append(dong)
        return {'giay': giay, 'r': ra_r, 'nguon': nguon, 'dong': dong_ra, 'tong_s': tau, 'co_do_m': co_do,
                'vao_dong': vao_dong, 'het_du_lieu': het}

    def _thuc_te(self, canh, kh, bang):
        """Tóm tắt _chay_lai từ lần chụp kh. None nếu hết dữ liệu giữa chừng."""
        c = self._chay_lai(canh, kh, bang)
        if c['het_du_lieu']:
            return None
        return {'phut': round(c['tong_s'] / 60, 1), 'ty_le_do_that': round(c['co_do_m'] / max(self.d.dai[canh].sum(), 1), 3),
                'vao_duong_dong': c['vao_dong']}

    # ── Dẫn đường: xe ảo chạy lại trên số đo thật ──
    def _kiem_tuyen(self, canh):
        """Danh sách cạnh do giao diện gửi lên: phải có thật và nối liền nhau."""
        if not canh:
            raise LoiYeuCau('Tuyen rong.')
        dc = self.d._dau_cuoi
        if any(not 0 <= i < self.n for i in canh):
            raise LoiYeuCau('Canh khong co trong ban do.')
        if any(dc[a][1] != dc[b][0] for a, b in zip(canh, canh[1:])):
            raise LoiYeuCau('Cac canh khong noi lien nhau.')
        return np.asarray(canh, dtype=np.int64)

    def _biet_tung_canh(self, canh, luc):
        """Những gì bộ định tuyến ĐANG BIẾT (phải gọi _biet_luc trước): giây dự kiến từng cạnh cùng thước đo với
        tim(), r (%) từng cạnh. Giao diện chỉ dùng số này cho giờ đến và màu tuyến, không dùng số đo tương lai."""
        t0, dung_ht, _ = self.d._boi_canh(luc, 0.0, False)
        giay, t = [], 0.0
        for i in canh:
            s = self.d._bang(int((t0 + t) // 3600) % 24, dung_ht and t < 1800)[0][int(i)]
            giay.append(round(s, 2))
            t += s
        r = np.nan_to_num(self.d.mh.r_gio[luc.hour, canh], nan=1.0)
        return giay, (r * 100).round().astype(int).tolist()

    def _chi_dan_cua(self, canh):
        G, dc, xy = self.d.bd.G, self.d._dau_cuoi, self.d.bd._xy
        nut = [dc[canh[0]][0]] + [dc[i][1] for i in canh]

        def loi_khac(j):
            return [xy[v] for v in G.successors(nut[j]) if v not in (nut[j - 1], nut[j + 1])]

        ten = [G[a][b]['ten'] if isinstance(G[a][b]['ten'], str) else '' for a, b in zip(nut, nut[1:])]
        dai = self.d.dai[canh].tolist()
        return nut, chi_dan([xy[n] for n in nut], ten, dai, loi_khac), ten_theo_doan(ten, dai)

    def _goi_dan_duong(self, canh, luc, kh):
        """Mọi thứ màn hình dẫn đường cần cho một tuyến, tính từ lúc luc. Phải gọi _biet_luc(kh) trước."""
        c = self._chay_lai(canh, luc, self._bang_thuc_te(kh, np.unique(canh)))
        nut, buoc, ten_doan = self._chi_dan_cua(canh)
        du_kien, r_biet = self._biet_tung_canh(canh, luc)
        G = self.d.bd.G
        return {'luc': str(luc), 'lan_chup': str(kh), 'canh': canh.tolist(),
                'toa_do': [[round(G.nodes[n]['y'], 5), round(G.nodes[n]['x'], 5)] for n in nut],
                'dai': self.d.dai[canh].round(1).tolist(), 'buoc': buoc, 'ten_doan': ten_doan, 'du_kien': du_kien, 'r_biet': r_biet,
                'giay': c['giay'], 'r': c['r'], 'nguon': c['nguon'], 'dong': c['dong'],
                'ty_le_do_that': round(c['co_do_m'] / max(self.d.dai[canh].sum(), 1), 3), 'het_du_lieu': c['het_du_lieu']}

    def dan_duong(self, canh, luc=None):
        canh = self._kiem_tuyen(canh)
        with self.khoa:
            kh = self.lan_chup_gan(luc)
            self._biet_luc(kh)
            return self._goi_dan_duong(canh, kh if luc is None else pd.Timestamp(luc), kh)

    def tinh_lai(self, canh_vua_qua, canh_con_lai, den, luc, mua_mm=0.0, trieu_cuong=False):
        """
        Xe vừa đi hết canh_vua_qua, có lần chụp mới: tính lại như phương án E của cham_tuyen_that.py. Chỉ đổi khi tuyến
        mới đỡ ≥ NGUONG_DOI_S giây chi phí hoặc tuyến cũ đi qua đường vừa đóng. Sau lần chụp cuối thì không tính được.
        """
        self._kiem_diem('den', den)
        canh = self._kiem_tuyen(canh_con_lai)
        if not 0 <= canh_vua_qua < self.n or self.d._dau_cuoi[canh_vua_qua][1] != self.d._dau_cuoi[canh[0]][0]:
            raise LoiYeuCau('Canh vua qua khong noi voi tuyen con lai.')
        luc = pd.Timestamp(luc)
        with self.khoa:
            try:
                kh = self.lan_chup_gan(luc)
            except LoiYeuCau:
                return {'het_du_lieu': True, 'doi': False, 'ly_do': None}
            self._biet_luc(kh)
            di_tu = self.d._dau_cuoi[canh_vua_qua]
            cu = self.d.chi_phi_tuyen(canh.tolist(), luc, mua_mm=mua_mm, trieu_cuong=trieu_cuong, di_tu=di_tu)
            moi = self.d.tim(None, tuple(den), luc, mua_mm=mua_mm, trieu_cuong=trieu_cuong, phuong_an=('toi_uu',),
                             di_tu=di_tu)['toi_uu']
            doi = moi is not None and bool(moi['canh']) and (cu is None or moi['chi_phi'] < cu[0] - NGUONG_DOI_S)
            du_kien, r_biet = self._biet_tung_canh(canh, luc)
            ra = {'het_du_lieu': False, 'lan_chup': str(kh), 'doi': doi, 'du_kien': du_kien, 'r_biet': r_biet,
                  'ly_do': None if not doi else 'duong_dong' if cu is None else 'nhanh_hon',
                  'ket_dong': cu is None and moi is None, 'phut_cu': round(sum(du_kien) / 60, 1)}
            if doi:
                ra['dan_duong'] = self._goi_dan_duong(self._kiem_tuyen(moi['canh']), luc, kh)
                ra['phut_moi'] = round(sum(ra['dan_duong']['du_kien']) / 60, 1)
            return ra

    @staticmethod
    def _gon(r):
        """Bỏ các trường nội bộ, giữ những gì giao diện cần."""
        return {'toa_do': [[round(a, 5), round(b, 5)] for a, b in r['toa_do']], 'canh': r['canh'], 'dai_m': r['dai_m'], 'phut': r['phut'],
                'so_canh_ket': r['so_canh_ket'], 'so_canh_ngap': r['so_canh_ngap'], 'so_canh_dong': r['so_canh_dong'],
                'so_re_trai_lon': r['so_re_trai_lon'], 'ten_duong': r['ten_duong'], 'lech_di_m': r['lech_diem_di_m'],
                'lech_den_m': r['lech_diem_den_m']}

    # ── Tuyến ──
    def tuyen(self, di, den, luc=None, mua_mm=0.0, trieu_cuong=False):
        """3 phương án tại lần chụp gần luc, kèm thực tế đã xảy ra của từng tuyến."""
        self._kiem_diem('di', di)
        self._kiem_diem('den', den)
        with self.khoa:
            kh = self.lan_chup_gan(luc)
            self._biet_luc(kh)
            kq = self.d.tim(tuple(di), tuple(den), kh, mua_mm=mua_mm, trieu_cuong=trieu_cuong)
            ra = {'lan_chup': str(kh), 'mua_mm': mua_mm, 'trieu_cuong': trieu_cuong, 'phuong_an': {}}
            co_tuyen = [kq[p] for p in PHUONG_AN if kq[p]]
            if not co_tuyen:
                raise LoiYeuCau('Khong tim duoc duong giua hai diem nay (co the do duong dang dong).')
            bang = self._bang_thuc_te(kh, np.unique(np.concatenate([r['canh'] for r in co_tuyen])))
            for p in PHUONG_AN:
                ra['phuong_an'][p] = None if kq[p] is None else {**self._gon(kq[p]), 'thuc_te': self._thuc_te(kq[p]['canh'], kh, bang)}
            return ra

    def tuyen_thay_the(self, di, den, luc=None, mua_mm=0.0, trieu_cuong=False):
        self._kiem_diem('di', di)
        self._kiem_diem('den', den)
        with self.khoa:
            kh = self.lan_chup_gan(luc)
            self._biet_luc(kh)
            ds = self.d.tuyen_thay_the(tuple(di), tuple(den), kh, mua_mm=mua_mm, trieu_cuong=trieu_cuong)
            if not ds:
                raise LoiYeuCau('Khong tim duoc duong giua hai diem nay.')
            bang = self._bang_thuc_te(kh, np.unique(np.concatenate([r['canh'] for r in ds])))
            return {'lan_chup': str(kh), 'tuyen': [{**self._gon(r), 'gian': r['gian'], 'trung': r['trung'],
                                                    'thuc_te': self._thuc_te(r['canh'], kh, bang)} for r in ds]}

    # ── Lớp bản đồ ──
    def hinh_doan(self):
        """Đoạn đường CHÍNH (đi xe được, đủ dài để thấy trên bản đồ): {mã đoạn: [[vĩ, kinh], ...]}. Tính một lần."""
        if self._hinh_doan is None:
            chinh = {'trunk', 'primary', 'secondary', 'tertiary', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'}
            d = pd.read_parquet(os.path.join(BAC, 'doan.parquet'), columns=['doan', 'loai'])
            giu = set(d.loc[d['loai'].astype(str).isin(chinh), 'doan'].tolist())
            cd = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))
            cd = cd[cd['doan'].isin(giu)].sort_values(['doan', 'thu_tu'])
            G, dau_cuoi = self.d.bd.G, self.d._dau_cuoi
            hinh = {}
            for doan, chi_so in zip(*(lambda g: (g.index, g.values))(cd.groupby('doan')['chi_so'].apply(list))):
                nut = [dau_cuoi[chi_so[0]][0]] + [dau_cuoi[i][1] for i in chi_so]
                hinh[int(doan)] = [[round(G.nodes[n]['y'], 5), round(G.nodes[n]['x'], 5)] for n in nut]
            self._hinh_doan = hinh
        return self._hinh_doan

    def tinh_trang(self, luc=None):
        """Mức r (điểm %) từng đoạn chính ở lần chụp gần luc, trọng số dài × phủ; đoạn đóng hết r = −1."""
        with self.khoa:
            kh = self.lan_chup_gan(luc)
        i, muc, phu, phu_dong = _doc_lan_chup(f'{kh:%Y-%m-%d}', kh.to_datetime64())
        doan = self._doan_cua[i]
        w = self.d.dai[i] * phu / 100
        w_dong = self.d.dai[i] * phu_dong / 100
        g = pd.DataFrame({'doan': doan, 'w': w, 'rw': muc * w, 'dong': w_dong}).groupby('doan').sum()
        hinh = self.hinh_doan()
        g = g[g.index.isin(list(hinh))]
        r = np.where(g['w'] > 0, g['rw'] / g['w'].where(g['w'] > 0), -1).round().astype(int)
        return {'lan_chup': str(kh), 'doan': g.index.astype(int).tolist(), 'r': r.tolist()}

    def ngap(self, trieu_cuong=True):
        """Các đoạn dễ ngập đã ghép được vào đồ thị (D8): đường gấp khúc theo từng điểm ngập."""
        nc = pd.read_parquet(os.path.join(BAC, 'ngap_canh.parquet'))
        di = pd.read_parquet(os.path.join(BAC, 'ngap_diem.parquet'), columns=['stt', 'duong', 'mo_ta'])
        G, dau_cuoi = self.d.bd.G, self.d._dau_cuoi
        ra = []
        for (stt, nguyen_nhan), g in nc.groupby(['stt', 'nguyen_nhan']):
            if nguyen_nhan != 'mua' and not trieu_cuong:
                continue
            x = di[di['stt'] == stt].iloc[0]
            canh = [[[round(G.nodes[n]['y'], 5), round(G.nodes[n]['x'], 5)] for n in dau_cuoi[int(i)]] for i in g['chi_so']]
            ra.append({'stt': int(stt), 'nguyen_nhan': nguyen_nhan, 'duong': x['duong'], 'mo_ta': x['mo_ta'], 'canh': canh})
        return ra
