"""
Chấm tuyến đường bằng tốc độ THẬT quan sát được (việc tuần 10, làm sớm) — không dùng dữ liệu tương lai.

Mỗi chuyến = (điểm đi, điểm đến, giờ xuất phát t) trong một ngày đã có dữ liệu TomTom (tầng bạc).
Bộ định tuyến chỉ biết những gì có tới lúc t:
  A  ngan_nhat       ít mét nhất — không cần dữ liệu giao thông
  B  ban_do_thuong   nhanh nhất theo tốc độ ĐƯỜNG TRỐNG (như bản đồ không có dữ liệu giao thông),
                     không biết đường đóng
  C  nhanh_hien_tai  nhanh nhất theo tình trạng ĐO ĐƯỢC ở lần chụp mới nhất ≤ t, coi như giữ nguyên
                     suốt chuyến; cạnh không đo dùng hồ sơ cạnh/loại đường × giờ; cấm đường đang đóng
  D  toi_uu_hien_tai như C + phạt đoạn đang kẹt (ba_phuong_an.RUI_RO)
  E  tinh_lai        bắt đầu bằng tuyến D; mỗi khi có LẦN CHỤP MỚI, ở nút giao xe đang đứng tính lại tuyến
                     tối ưu với tình trạng mới nhất (ba_phuong_an.DinhTuyen.tim(di_tu=...)) và chỉ ĐỔI khi
                     tuyến mới đỡ ≥ NGUONG_DOI_S (giây chi phí) hoặc tuyến cũ đi qua đường vừa đóng
  Có --du-bao=TEN (QĐ-027; chỉ ngày thuộc phần KIỂM TRA của mô hình, dự báo lấy ở khung 15 phút vừa xong trước lúc đi):
  F  nhanh_du_bao    như C nhưng r mỗi cạnh theo khe 15 phút xe tới cạnh: 15 phút đầu giữ lần chụp lúc đi (lần chụp
                     đó đã nằm trong khe này nên giữ nguyên đúng nhất), từ phút 15 dùng DỰ BÁO 30/45/60 phút của ĐOẠN chứa
                     cạnh; cạnh không thuộc đoạn có dự báo giữ như C. Chọn cách này bằng kiem_du_bao_canh.py trên tối 08/11
                     (ngoài 4 ngày chấm): sai thời gian qua cạnh 15,7% so với 19,9–23,0% của giữ nguyên.
                     --cach-du-bao=cong: bản đầu, r lúc đi + (dự báo − r đoạn ở khung vừa xong) — chấm 09/11 kém C.
  G  toi_uu_du_bao   như D, theo dự báo như F
  H  toi_uu_biet_truoc như D nhưng biết r THẬT từng khe (dùng dữ liệu tương lai — KHÔNG làm được ngoài đời): trần
                     của mọi bộ dự báo; G nằm giữa D (không dự báo) và H cho biết dự báo lấy được bao nhiêu phần
Chấm: cho xe chạy lại trên tuyến: tới cạnh lúc τ thì tốc độ = v_trống × r ĐO THẬT ở lần chụp ứng với τ
(khung 5 phút); cạnh không có số đo lúc đó dùng hồ sơ (ghi tỉ lệ chiều dài được chấm bằng số đo thật);
đi vào cạnh đang ĐÓNG lúc τ: +300 s (phải quay đầu/đi vòng) và đếm lại.

Tiêu chí kế hoạch (note/KE_HOACH.md mục 1): trên ≥ 30 cặp điểm, tuyến tối ưu không chậm hơn tuyến ngắn
nhất ở ≥ 80% chuyến và nhanh hơn trung bình ≥ 5%.

Giới hạn: hồ sơ giờ dùng cho cạnh KHÔNG có số đo được dựng từ cùng dữ liệu (chỉ ảnh hưởng hẻm/đường nhỏ,
cả 4 phương án cùng chịu). Số đo thật của cạnh có TomTom thì C/D chỉ biết tới lúc t.

Tổng hợp nhiều ngày + khoảng tin cậy + kiểm định: tong_hop_cham.py.

Chạy:  python cham_tuyen_that.py [2026-10-30] [--diem=zenodo] [--khat-khe] [--nguong=60]
       --diem=zenodo: cặp đi–đến là điểm giao hàng thật (D13) thay vì 10 địa danh chọn tay.
       --khat-khe: cạnh không có số đo lúc chấm coi chậm hơn hồ sơ 30% (kiểm kết luận có còn đứng
       khi hẻm thực tế chậm hơn ước lượng — tuyến C/D hay luồn hẻm nên dễ được chấm ưu ái). Phương án A–D
       đã có sẵn số này ở cột phut_kk_* trong mọi lần chạy; cờ này chỉ cần khi muốn E.
       --nguong=N: ngưỡng đổi tuyến của E (giây), mặc định NGUONG_DOI_S.
       --phat-re-trai=N: phạt rẽ trái qua trục lớn của D/E (giây), mặc định ba_phuong_an.PHAT_RE_TRAI_S.
       --du-bao=TEN: thêm F, G, H. TEN = gbm_ls (mo_hinh/so_sanh_du_bao.py) hoặc tên mô hình học sâu đã xuất dự báo
       (hoc_sau_hcm.py --chi-du-bao), vd gwn_ho_so_them_che. --cach-du-bao=muc|cong (mặc định muc, xem F).
Ra:    danh_gia/ket_qua/cham_tuyen_<ngày>.csv + tóm tắt in ra màn hình
"""
import datetime as dt
import glob
import itertools
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ba_phuong_an import PHAT_RE_TRAI_S, DinhTuyen  # noqa: E402
from kiem_tra_tuan1 import DIA_DIEM  # noqa: E402

GIO_XUAT_PHAT = ['06:30', '07:30', '08:30', '10:00', '12:00', '14:00', '15:30', '17:00', '18:00', '19:30']
PHAT_DONG_S = 300.0
HE_SO_KHONG_DO = 1.0          # phép thử khắt khe: --khat-khe -> 0,7 (cạnh không có số đo chậm hơn hồ sơ 30%)
HE_SO_KHAT_KHE = 0.7          # cột phut_kk_* tính sẵn mức này cho A–D trong mọi lần chạy
SO_CAP_ZENODO = 90
# E chỉ đổi tuyến khi đỡ ≥ 60 s (QĐ-013). Chấm 30/10: ngưỡng 0 nhanh hơn chút (D−2,2% so với −1,6%) nhưng
# đổi tuyến 1.227 lần (tới 6 lần/chuyến, mỗi lần chỉ đỡ 0,19 phút); 60 s giữ 74% phần tiết kiệm với 147 lần
# đổi (tối đa 2/chuyến) — người chạy xe theo được.
NGUONG_DOI_S = 60.0
R_SAN, V_SAN = 0.1, 3.0
# Khe dự báo (giây kể từ lúc đi): [0, 15), [15, 30), [30, 45), [45, ...) phút <-> dự báo 15 / 30 / 45 / 60 phút
# của khung 15 phút vừa xong (khung t = lúc đi − 15 phút: 3 lần chụp t, t+5, t+10 đều có trước lúc đi).
KHE_S = [900, 1800, 2700]
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')


def cap_zenodo(so_cap=SO_CAP_ZENODO):
    """Cặp đi–đến là điểm giao hàng THẬT (D13), cách nhau 1,5–8 km đường chim bay; cố định qua các ngày (hạt 42)."""
    diem = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'zenodo_diem.parquet'))
    diem = diem[diem['trong_vung']][['lat', 'lon']].to_numpy()
    rng = np.random.default_rng(42)
    cap = []
    while len(cap) < so_cap:
        a, b = diem[rng.choice(len(diem), 2, replace=False)]
        km = np.hypot((a[0] - b[0]) * 110.574, (a[1] - b[1]) * 111.320 * np.cos(np.radians(10.78)))
        if 1.5 <= km <= 8.0:
            cap.append(((f'z{len(cap)}_di', tuple(a)), (f'z{len(cap)}_den', tuple(b))))
    return cap


def nap_quan_sat(ngay, tu='06:00', den='22:00'):
    """Ma trận (lần chụp × cạnh): r đo được (NaN nếu không đo / đóng hết), đóng hết?, phần đóng."""
    s = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'tomtom_canh', f'{ngay}.parquet'),
                        columns=['khung', 'chi_so', 'muc', 'phu', 'phu_dong'])
    s = s[(s['khung'] >= pd.Timestamp(f'{ngay} {tu}')) & (s['khung'] < pd.Timestamp(f'{ngay} {den}'))]
    khung = np.sort(s['khung'].unique())
    k = np.searchsorted(khung, s['khung'].to_numpy())
    i = s['chi_so'].to_numpy()
    n = int(pd.read_parquet(os.path.join(GOC, 'du_lieu', 'do_thi', 'canh.parquet'), columns=['chi_so'])['chi_so'].max()) + 1
    R = np.full((len(khung), n), np.nan, dtype=np.float32)
    DONG = np.zeros((len(khung), n), dtype=bool)
    PD = np.zeros((len(khung), n), dtype=np.float32)
    mo = (s['phu'] > 0).to_numpy()
    R[k[mo], i[mo]] = np.maximum(s['muc'].to_numpy()[mo] / 100, R_SAN)
    DONG[k[~mo], i[~mo]] = (s['phu_dong'].to_numpy()[~mo] > 0)
    PD[k, i] = s['phu_dong'].to_numpy() / 100
    return pd.DatetimeIndex(khung), R, DONG, PD


def nap_du_bao(ten, ngay):
    """Dự báo phần kiểm tra của mô hình `ten` cho các khung trong ngày: (khung, đoạn, r, du_15/30/45/60)."""
    kq = os.path.join(GOC, 'mo_hinh', 'ket_qua')
    tep = sorted(glob.glob(os.path.join(kq, 'du_bao_gbm_ls_*.parquet')) if ten == 'gbm_ls' else
                 glob.glob(os.path.join(kq, 'hoc_sau', f'hcm_{ten}_*_du_bao.parquet')))
    if not tep:
        sys.exit(f'chua co du bao {ten} (mo_hinh/so_sanh_du_bao.py hoac hoc_sau_hcm.py --chi-du-bao)')
    d = pd.read_parquet(tep[-1])
    d = d[d['khung'].dt.normalize() == pd.Timestamp(ngay)]
    if 'du_45' not in d:            # GBM không có tầm 45 phút: lấy giữa 30 và 60
        d = d.assign(du_45=(d['du_30'] + d['du_60']) / 2)
    return d, tep[-1]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    thong_so = [a for a in sys.argv[1:] if not a.startswith('--')]
    ngay = thong_so[0] if thong_so else '2026-10-30'
    he_so = 0.7 if '--khat-khe' in sys.argv else HE_SO_KHONG_DO
    nguong = next((float(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--nguong=')), NGUONG_DOI_S)
    t_bat_dau = time.time()
    khung, R, DONG, PD = nap_quan_sat(ngay)
    d = DinhTuyen.nap(None)
    d.phat_re_trai_s = next((float(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--phat-re-trai=')),
                            d.phat_re_trai_s)
    r_ho_so = np.array(d.mh.r_gio, dtype=np.float32)          # (24, n): cạnh có đủ dữ liệu / loại đường
    v_trong, dai = d.mh.v_trong.astype(np.float64), d.dai
    n = len(dai)
    dau_cuoi = list(d.bd.G.edges())                           # chỉ số cạnh -> (nút đầu, nút cuối)
    print(f'{ngay}: {len(khung)} lan chup ({khung[0]:%H:%M} -> {khung[-1]:%H:%M}), nap {time.time() - t_bat_dau:.0f}s')
    ten_du_bao = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--du-bao=')), None)
    if ten_du_bao:
        du_bao, tep_du_bao = nap_du_bao(ten_du_bao, ngay)
        doan_cua = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'canh_doan.parquet'),
                                   columns=['chi_so', 'doan']).sort_values('chi_so')['doan'].to_numpy()
        assert len(doan_cua) == n
        print(f'du bao {ten_du_bao}: {du_bao["khung"].nunique()} khung trong ngay ({os.path.basename(tep_du_bao)})')

    cach_du_bao = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--cach-du-bao=')), 'muc')

    def r_du_bao(t0, nen):
        """(4, n) r theo khe cho F/G từ dự báo của khung vừa xong (lúc đi − 15 phút); None nếu khung đó không có dự
        báo (ngoài phần kiểm tra). nen = cái C/D biết (lần chụp lúc đi, cạnh không đo lấy hồ sơ)."""
        x = du_bao[du_bao['khung'] == t0 - pd.Timedelta(minutes=15)]
        if x.empty:
            return None
        ra = np.empty((4, n), dtype=np.float32)
        for j, p in enumerate(('du_15', 'du_30', 'du_45', 'du_60')):
            if cach_du_bao == 'muc' and j == 0:
                ra[j] = nen
                continue
            v = np.full(int(doan_cua.max()) + 1, np.nan, dtype=np.float32)
            v[x['doan'].to_numpy()] = (x[p] if cach_du_bao == 'muc' else x[p] - x['r']).to_numpy()
            v = v[doan_cua]
            ra[j] = np.where(np.isnan(v), nen, v) if cach_du_bao == 'muc' else nen + np.nan_to_num(v)
        return np.clip(ra, R_SAN, 1)

    def r_that_tung_khe(t0, nen):
        """(4, n): r THẬT (TB điều hòa các lần chụp) trong từng khe sau lúc đi; không đo -> `nen` (dùng tương lai)."""
        ra = np.empty((4, n), dtype=np.float32)
        for j in range(4):
            a, b = t0 + pd.Timedelta(seconds=900 * j), t0 + pd.Timedelta(seconds=900 * (j + 1))
            k = np.flatnonzero((khung >= a) & (khung < b))
            with np.errstate(invalid='ignore', divide='ignore'), warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)         # cạnh không đo trong khe: NaN
                hm = 1 / np.nanmean(1 / R[k], axis=0) if len(k) else np.full(n, np.nan)
            ra[j] = np.where(np.isnan(hm), nen, hm)
        return ra

    def lan_chup(t):
        k = int(np.searchsorted(khung, np.datetime64(t), side='right')) - 1
        return k if 0 <= k < len(khung) and (t - khung[k]).total_seconds() < 600 else None

    def buoc(i, t, k, hs=he_so):
        """Xe vào cạnh i lúc t (lần chụp k): (giây thật qua cạnh, mét chấm bằng số đo thật, 1 nếu cạnh đang đóng).
        hs: hệ số nhân hồ sơ cho cạnh không có số đo."""
        dong = int(DONG[k, i])
        r = R[k, i]
        do = dai[i] if r == r else 0.0
        if r != r:
            r = r_ho_so[t.hour, i] * hs
        return dai[i] / (max(v_trong[i] * r, V_SAN) / 3.6) * (1 + PD[k, i]) + PHAT_DONG_S * dong, do, dong

    def cham(canh, t0, hs=he_so):
        """Phút thật, tỉ lệ chiều dài chấm bằng số đo thật, số lần vào cạnh đóng. None nếu ra ngoài dữ liệu."""
        tau, co_do, vao_dong = 0.0, 0.0, 0
        for i in canh:
            t = t0 + dt.timedelta(seconds=tau)
            k = lan_chup(t)
            if k is None:
                return None
            s, m, dong = buoc(i, t, k, hs)
            tau, co_do, vao_dong = tau + s, co_do + m, vao_dong + dong
        return tau / 60, co_do / max(sum(dai[i] for i in canh), 1), vao_dong

    def biet_luc(k, gio):
        """Bộ định tuyến biết tình trạng đo được ở lần chụp k; cạnh không đo dùng hồ sơ giờ `gio`."""
        d.dat_tinh_trang(np.where(np.isnan(R[k]), r_ho_so[gio], R[k]), DONG[k], PD[k])

    def chay_tinh_lai(chuyen, t0, k0):
        """
        Phương án E cho MỌI chuyến cùng giờ xuất phát, chạy song song theo lần chụp: mỗi chuyến đi theo
        tuyến hiện có tới khi xe vào cạnh thuộc lần chụp MỚI hơn lần chụp nó đang biết thì dừng ở nút đó;
        lấy lần chụp nhỏ nhất đang có chuyến chờ, nạp tình trạng một lần, tính lại cho các chuyến đó.
        """
        for c in chuyen:
            c.update(vi_tri=0, tau=0.0, co_do=0.0, vao_dong=0, da_di=[], k_biet=k0, cho=None, xong=False,
                     hong=False, so_tinh=0, so_doi=0, ket_dong=0)

        def tien(c):
            while c['vi_tri'] < len(c['canh']):
                i = c['canh'][c['vi_tri']]
                t = t0 + dt.timedelta(seconds=c['tau'])
                k = lan_chup(t)
                if k is None:
                    c['hong'] = True
                    return
                if k > c['k_biet'] and c['da_di']:
                    c['cho'] = k
                    return
                s, m, dong = buoc(i, t, k)
                c['tau'] += s
                c['co_do'] += m
                c['vao_dong'] += dong
                c['da_di'].append(i)
                c['vi_tri'] += 1
            c['xong'] = True

        while True:
            for c in chuyen:
                if not (c['xong'] or c['hong']) and c['cho'] is None:
                    tien(c)
            dang_cho = [c for c in chuyen if c['cho'] is not None]
            if not dang_cho:
                return
            k = min(c['cho'] for c in dang_cho)
            biet_luc(k, khung[k].hour)
            # Gom các chuyến cùng đích liền nhau: cận ALT chỉ nhớ đích gần nhất (DinhTuyen._can_duoi_luc).
            for c in sorted((c for c in dang_cho if c['cho'] == k), key=lambda c: c['den']):
                luc = t0 + dt.timedelta(seconds=c['tau'])
                cu = d.chi_phi_tuyen(c['canh'][c['vi_tri']:], luc, di_tu=dau_cuoi[c['da_di'][-1]])
                moi = d.tim(None, c['pb'], luc, phuong_an=('toi_uu',), di_tu=dau_cuoi[c['da_di'][-1]])['toi_uu']
                c['so_tinh'] += 1
                c['ket_dong'] += cu is None and moi is None     # tuyến cũ qua đường đóng mà KHÔNG còn đường tránh
                if moi is not None and moi['canh'] and (cu is None or moi['chi_phi'] < cu[0] - nguong):
                    c['canh'], c['vi_tri'] = moi['canh'], 0
                    c['so_doi'] += 1
                c['k_biet'], c['cho'] = k, None

    dung_zenodo = '--diem=zenodo' in sys.argv
    cap = cap_zenodo() if dung_zenodo else list(itertools.permutations(DIA_DIEM.items(), 2))
    hang = []
    for gio in GIO_XUAT_PHAT:
        t0 = pd.Timestamp(f'{ngay} {gio}')
        k0 = lan_chup(t0)
        if k0 is None:
            print(f'{gio}: khong co lan chup -> bo')
            continue
        t1 = time.time()
        # A, B: không biết giao thông.
        d.dat_tinh_trang(np.ones(n), np.zeros(n, dtype=bool), np.zeros(n))
        ab = {(a, b): d.tim(pa, pb, t0, phuong_an=('ngan_nhat', 'nhanh_nhat')) for (a, pa), (b, pb) in cap}
        # C, D: biết tình trạng đo được ở lần chụp mới nhất <= t0.
        biet_luc(k0, t0.hour)
        cd = {(a, b): d.tim(pa, pb, t0, phuong_an=('nhanh_nhat', 'toi_uu')) for (a, pa), (b, pb) in cap}
        # F, G: theo dự báo; H: biết trước r thật (trần). Làm trước E (biet_luc của E xóa dự báo).
        fgh = {}
        nen = np.where(np.isnan(R[k0]), r_ho_so[t0.hour], R[k0])
        r_khe = r_du_bao(t0, nen) if ten_du_bao else None
        if r_khe is not None:
            d.dat_tinh_trang(nen, DONG[k0], PD[k0])
            d.dat_du_bao(r_khe, KHE_S)
            fgh = {(a, b): d.tim(pa, pb, t0, phuong_an=('nhanh_nhat', 'toi_uu')) for (a, pa), (b, pb) in cap}
            d.dat_tinh_trang(nen, DONG[k0], PD[k0])
            d.dat_du_bao(np.clip(r_that_tung_khe(t0, nen), R_SAN, 1), KHE_S)
            for (a, pa), (b, pb) in cap:
                fgh[(a, b)]['biet_truoc'] = d.tim(pa, pb, t0, phuong_an=('toi_uu',))['toi_uu']
        elif ten_du_bao:
            print(f'{gio}: khung {t0 - pd.Timedelta(minutes=15):%H:%M} khong co du bao -> khong co F, G, H')
        # E: xuất phát bằng tuyến D, tính lại khi có lần chụp mới (đổi tình trạng của d -> làm SAU C, D).
        chuyen = [{'di': a, 'den': b, 'pb': pb, 'canh': cd[(a, b)]['toi_uu']['canh']}
                  for (a, _), (b, pb) in cap if cd[(a, b)]['toi_uu']]
        chay_tinh_lai(chuyen, t0, k0)
        e = {(c['di'], c['den']): c for c in chuyen}
        for (a, _), (b, _) in cap:
            tuyen = {'A': ab[(a, b)]['ngan_nhat'], 'B': ab[(a, b)]['nhanh_nhat'], 'C': cd[(a, b)]['nhanh_nhat'],
                     'D': cd[(a, b)]['toi_uu']}
            dong = {'gio': gio, 'di': a, 'den': b}
            ok = True
            for k, r in tuyen.items():
                c = cham(r['canh'], t0) if r else None
                if c is None:
                    ok = False
                    break
                dong[f'phut_{k}'], dong[f'do_that_{k}'], dong[f'vao_dong_{k}'] = c
                dong[f'm_{k}'] = r['dai_m']
                dong[f're_trai_{k}'] = r['so_re_trai_lon']
                kk = cham(r['canh'], t0, HE_SO_KHAT_KHE)
                if kk is None:
                    ok = False
                    break
                dong[f'phut_kk_{k}'] = kk[0]
            c = e.get((a, b))
            if not ok or c is None or c['hong'] or not c['xong']:
                continue
            if (a, b) in fgh:
                # Không làm rơi chuyến của A–E khi F/G/H hỏng: để trống cột (NaN).
                for k, r in (('F', fgh[(a, b)]['nhanh_nhat']), ('G', fgh[(a, b)]['toi_uu']),
                             ('H', fgh[(a, b)]['biet_truoc'])):
                    c_k = cham(r['canh'], t0) if r else None
                    if c_k is None:
                        continue
                    dong[f'phut_{k}'], dong[f'do_that_{k}'], dong[f'vao_dong_{k}'] = c_k
                    dong[f'm_{k}'] = r['dai_m']
                    dong[f're_trai_{k}'] = r['so_re_trai_lon']
                    kk = cham(r['canh'], t0, HE_SO_KHAT_KHE)
                    dong[f'phut_kk_{k}'] = kk[0] if kk else np.nan
                    if k == 'F':
                        dong['du_doan_F'] = r['tg_du_kien_s'] / 60
            dong.update(phut_E=c['tau'] / 60, do_that_E=c['co_do'] / max(sum(dai[i] for i in c['da_di']), 1),
                        vao_dong_E=c['vao_dong'], m_E=round(sum(dai[i] for i in c['da_di'])),
                        so_tinh_E=c['so_tinh'], so_doi_E=c['so_doi'], ket_dong_E=c['ket_dong'])
            dong['du_doan_C'] = cd[(a, b)]['nhanh_nhat']['tg_du_kien_s'] / 60
            hang.append(dong)
        print(f'{gio}: {sum(1 for h in hang if h["gio"] == gio)} chuyen, {time.time() - t1:.0f}s', flush=True)

    kq = pd.DataFrame(hang)
    os.makedirs(RA, exist_ok=True)
    hau_to = ('_zenodo' if dung_zenodo else '') + ('_khat_khe' if he_so != 1 else '') + \
        (f'_nguong{nguong:.0f}' if nguong != NGUONG_DOI_S else '') + \
        (f'_retrai{d.phat_re_trai_s:.0f}' if d.phat_re_trai_s != PHAT_RE_TRAI_S else '') + \
        (f'_dubao-{ten_du_bao}' + ('' if cach_du_bao == 'muc' else f'-{cach_du_bao}') if ten_du_bao else '')
    kq.to_csv(os.path.join(RA, f'cham_tuyen_{ngay}{hau_to}.csv'), index=False, encoding='utf-8-sig')
    print(f'he so canh khong co so do: {he_so}; nguong doi tuyen E: {nguong:.0f}s')

    print(f'\n{len(kq)} chuyen ({kq[["di", "den"]].drop_duplicates().shape[0]} cap diem x {kq["gio"].nunique()} gio)')
    print(f'Ty le chieu dai tuyen duoc cham bang so do that: C {kq["do_that_C"].mean():.0%}, A {kq["do_that_A"].mean():.0%}')
    print(f'\n{"gio":<6}{"A ngan":>9}{"B ban do":>10}{"C hien tai":>12}{"D toi uu":>10}{"E tinh lai":>12}'
          f'   C nhanh hon A   D khong cham hon A')
    for gio, g in kq.groupby('gio', sort=False):
        print(f'{gio:<6}{g["phut_A"].mean():>8.1f}p{g["phut_B"].mean():>9.1f}p{g["phut_C"].mean():>11.1f}p'
              f'{g["phut_D"].mean():>9.1f}p{g["phut_E"].mean():>11.1f}p'
              f'   {100 * (1 - g["phut_C"].mean() / g["phut_A"].mean()):>6.1f}%'
              f'        {(g["phut_D"] <= g["phut_A"] + 0.05).mean():>5.0%}')
    # Tự kiểm: chuyến E không đổi tuyến lần nào thì chạy đúng tuyến D -> phút phải trùng khít.
    giu = kq[kq['so_doi_E'] == 0]
    lech = int(((giu['phut_E'] - giu['phut_D']).abs() > 1e-6).sum())
    doi = kq[kq['so_doi_E'] > 0]
    print(f'\nE: tinh lai TB {kq["so_tinh_E"].mean():.1f} lan/chuyen; doi tuyen o {len(doi)}/{len(kq)} chuyen '
          f'({len(doi) / len(kq):.0%}); tu kiem chuyen khong doi = D: {len(giu) - lech}/{len(giu)}')
    if len(doi):
        print(f'   tren cac chuyen co doi: D {doi["phut_D"].mean():.1f}p -> E {doi["phut_E"].mean():.1f}p, '
              f'E nhanh hon D o {(doi["phut_E"] < doi["phut_D"] - 0.05).mean():.0%}, '
              f'cham hon o {(doi["phut_E"] > doi["phut_D"] + 0.05).mean():.0%}')
    print(f'TOAN BO: E nhanh hon D {100 * (1 - kq["phut_E"].sum() / kq["phut_D"].sum()):.2f}% (tong thoi gian), '
          f'E nhanh hon A {100 * (1 - kq["phut_E"].sum() / kq["phut_A"].sum()):.1f}%, '
          f'E khong cham hon A o {(kq["phut_E"] <= kq["phut_A"] + 0.05).mean():.0%} chuyen')
    tk_D = 100 * (1 - kq['phut_D'].sum() / kq['phut_A'].sum())
    khong_cham = (kq['phut_D'] <= kq['phut_A'] + 0.05).mean()
    print(f'\nTOAN BO: D nhanh hon A {tk_D:.1f}% (tong thoi gian), D khong cham hon A o {khong_cham:.0%} chuyen; '
          f'C nhanh hon B {100 * (1 - kq["phut_C"].sum() / kq["phut_B"].sum()):.1f}%')
    print(f'Vao canh dang dong: A {int(kq["vao_dong_A"].sum())}, B {int(kq["vao_dong_B"].sum())}, '
          f'C {int(kq["vao_dong_C"].sum())}, D {int(kq["vao_dong_D"].sum())}, E {int(kq["vao_dong_E"].sum())} '
          f'(E: {int(kq["ket_dong_E"].sum())} lan tinh lai thay tuyen cu qua duong dong ma khong con duong tranh, '
          f'o {int((kq["ket_dong_E"] > 0).sum())} chuyen)')
    print('Re trai qua truc lon TB/chuyen (thoi gian cho re KHONG nam trong so phut — du lieu khong do duoc): '
          + ', '.join(f'{k} {kq[f"re_trai_{k}"].mean():.2f}' for k in 'ABCD'))
    sai = (kq['du_doan_C'] - kq['phut_C']).abs()
    print(f'Du doan thoi gian den cua C: sai TB {sai.mean():.1f} phut ({100 * (sai / kq["phut_C"]).mean():.0f}%), '
          f'du doan {"som" if (kq["du_doan_C"] < kq["phut_C"]).mean() > 0.5 else "muon"} hon thuc te o '
          f'{max((kq["du_doan_C"] < kq["phut_C"]).mean(), (kq["du_doan_C"] > kq["phut_C"]).mean()):.0%} chuyen')
    if 'phut_G' in kq:
        f = kq[kq['phut_G'].notna() & kq['phut_F'].notna() & kq['phut_H'].notna()]
        print(f'\nDU BAO {ten_du_bao} ({len(f)} chuyen co F, G, H):')
        print(f'  F nhanh hon C {100 * (1 - f["phut_F"].sum() / f["phut_C"].sum()):.2f}%, '
              f'G nhanh hon D {100 * (1 - f["phut_G"].sum() / f["phut_D"].sum()):.2f}%, '
              f'H (biet truoc) nhanh hon D {100 * (1 - f["phut_H"].sum() / f["phut_D"].sum()):.2f}%')
        print(f'  G nhanh hon A {100 * (1 - f["phut_G"].sum() / f["phut_A"].sum()):.1f}%, '
              f'G khong cham hon A o {(f["phut_G"] <= f["phut_A"] + 0.05).mean():.0%}; '
              f'G khac tuyen D o {(f["m_G"] != f["m_D"]).mean():.0%} chuyen')
        sai_f = (f['du_doan_F'] - f['phut_F']).abs()
        sai_c = (f['du_doan_C'] - f['phut_C']).abs()
        print(f'  du doan gio den: C sai TB {sai_c.mean():.2f} phut ({100 * (sai_c / f["phut_C"]).mean():.1f}%), '
              f'F sai TB {sai_f.mean():.2f} phut ({100 * (sai_f / f["phut_F"]).mean():.1f}%)')
    dat = len(kq[['di', 'den']].drop_duplicates()) >= 30 and khong_cham >= 0.8 and tk_D >= 5
    print('\nTIEU CHI KE HOACH (>=30 cap, D khong cham hon A >= 80%, nhanh hon >= 5%):', 'DAT' if dat else 'CHUA DAT')
    print(f'({time.time() - t_bat_dau:.0f}s)')


if __name__ == '__main__':
    main()
