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
Chấm: cho xe chạy lại trên tuyến: tới cạnh lúc τ thì tốc độ = v_trống × r ĐO THẬT ở lần chụp ứng với τ
(khung 5 phút); cạnh không có số đo lúc đó dùng hồ sơ (ghi tỉ lệ chiều dài được chấm bằng số đo thật);
đi vào cạnh đang ĐÓNG lúc τ: +300 s (phải quay đầu/đi vòng) và đếm lại.

Tiêu chí kế hoạch (note/KE_HOACH.md mục 1): trên ≥ 30 cặp điểm, tuyến tối ưu không chậm hơn tuyến ngắn
nhất ở ≥ 80% chuyến và nhanh hơn trung bình ≥ 5%.

Giới hạn: hồ sơ giờ dùng cho cạnh KHÔNG có số đo được dựng từ cùng dữ liệu (chỉ ảnh hưởng hẻm/đường nhỏ,
cả 4 phương án cùng chịu). Số đo thật của cạnh có TomTom thì C/D chỉ biết tới lúc t.

Chạy:  python cham_tuyen_that.py [2026-10-30] [--khat-khe] [--nguong=60]
       --khat-khe: cạnh không có số đo lúc chấm coi chậm hơn hồ sơ 30% (kiểm kết luận có còn đứng
       khi hẻm thực tế chậm hơn ước lượng — tuyến C/D hay luồn hẻm nên dễ được chấm ưu ái).
       --nguong=N: ngưỡng đổi tuyến của E (giây), mặc định NGUONG_DOI_S.
       --phat-re-trai=N: phạt rẽ trái qua trục lớn của D/E (giây), mặc định ba_phuong_an.PHAT_RE_TRAI_S.
Ra:    danh_gia/ket_qua/cham_tuyen_<ngày>.csv + tóm tắt in ra màn hình
"""
import datetime as dt
import itertools
import os
import sys
import time

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ba_phuong_an import PHAT_RE_TRAI_S, DinhTuyen  # noqa: E402
from kiem_tra_tuan1 import DIA_DIEM  # noqa: E402

GIO_XUAT_PHAT = ['06:30', '07:30', '08:30', '10:00', '12:00', '14:00', '15:30']
PHAT_DONG_S = 300.0
HE_SO_KHONG_DO = 1.0          # phép thử khắt khe: --khat-khe -> 0,7 (cạnh không có số đo chậm hơn hồ sơ 30%)
# E chỉ đổi tuyến khi đỡ ≥ 60 s (QĐ-013). Chấm 30/10: ngưỡng 0 nhanh hơn chút (D−2,2% so với −1,6%) nhưng
# đổi tuyến 1.227 lần (tới 6 lần/chuyến, mỗi lần chỉ đỡ 0,19 phút); 60 s giữ 74% phần tiết kiệm với 147 lần
# đổi (tối đa 2/chuyến) — người chạy xe theo được.
NGUONG_DOI_S = 60.0
R_SAN, V_SAN = 0.1, 3.0
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')


def nap_quan_sat(ngay, tu='06:00'):
    """Ma trận (lần chụp × cạnh): r đo được (NaN nếu không đo / đóng hết), đóng hết?, phần đóng."""
    s = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'tomtom_canh', f'{ngay}.parquet'),
                        columns=['khung', 'chi_so', 'muc', 'phu', 'phu_dong'])
    s = s[s['khung'] >= pd.Timestamp(f'{ngay} {tu}')]
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

    def lan_chup(t):
        k = int(np.searchsorted(khung, np.datetime64(t), side='right')) - 1
        return k if 0 <= k < len(khung) and (t - khung[k]).total_seconds() < 600 else None

    def buoc(i, t, k):
        """Xe vào cạnh i lúc t (lần chụp k): (giây thật qua cạnh, mét chấm bằng số đo thật, 1 nếu cạnh đang đóng)."""
        dong = int(DONG[k, i])
        r = R[k, i]
        do = dai[i] if r == r else 0.0
        if r != r:
            r = r_ho_so[t.hour, i] * he_so
        return dai[i] / (max(v_trong[i] * r, V_SAN) / 3.6) * (1 + PD[k, i]) + PHAT_DONG_S * dong, do, dong

    def cham(canh, t0):
        """Phút thật, tỉ lệ chiều dài chấm bằng số đo thật, số lần vào cạnh đóng. None nếu ra ngoài dữ liệu."""
        tau, co_do, vao_dong = 0.0, 0.0, 0
        for i in canh:
            t = t0 + dt.timedelta(seconds=tau)
            k = lan_chup(t)
            if k is None:
                return None
            s, m, dong = buoc(i, t, k)
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

    cap = list(itertools.permutations(DIA_DIEM.items(), 2))
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
            c = e.get((a, b))
            if not ok or c is None or c['hong'] or not c['xong']:
                continue
            dong.update(phut_E=c['tau'] / 60, do_that_E=c['co_do'] / max(sum(dai[i] for i in c['da_di']), 1),
                        vao_dong_E=c['vao_dong'], m_E=round(sum(dai[i] for i in c['da_di'])),
                        so_tinh_E=c['so_tinh'], so_doi_E=c['so_doi'], ket_dong_E=c['ket_dong'])
            dong['du_doan_C'] = cd[(a, b)]['nhanh_nhat']['tg_du_kien_s'] / 60
            hang.append(dong)
        print(f'{gio}: {sum(1 for h in hang if h["gio"] == gio)} chuyen, {time.time() - t1:.0f}s', flush=True)

    kq = pd.DataFrame(hang)
    os.makedirs(RA, exist_ok=True)
    hau_to = ('_khat_khe' if he_so != 1 else '') + (f'_nguong{nguong:.0f}' if nguong != NGUONG_DOI_S else '') + \
        (f'_retrai{d.phat_re_trai_s:.0f}' if d.phat_re_trai_s != PHAT_RE_TRAI_S else '')
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
    dat = len(kq[['di', 'den']].drop_duplicates()) >= 30 and khong_cham >= 0.8 and tk_D >= 5
    print('\nTIEU CHI KE HOACH (>=30 cap, D khong cham hon A >= 80%, nhanh hon >= 5%):', 'DAT' if dat else 'CHUA DAT')
    print(f'({time.time() - t_bat_dau:.0f}s)')


if __name__ == '__main__':
    main()
