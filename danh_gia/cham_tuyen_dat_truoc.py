"""
Chấm tuyến LẬP TRƯỚC (QĐ-028): lên tuyến lúc p cho chuyến xuất phát lúc τ = p + TRUOC phút (vd đơn hẹn giao, điều
phối xếp chuyến trước). Đây là chỗ "giữ nguyên tình trạng lúc lập" yếu nhất và dự báo mạnh nhất (QĐ-026: ở 30–60
phút MAE giữ nguyên 8,1–9,6 so với GBM 6,2–6,3), khác chấm tuyến đi ngay (QĐ-027: dự báo ≈ 0).

Bộ định tuyến chỉ biết những gì có tới lúc p (lần chụp p, đường đóng lúc p, khung 15 phút vừa xong f = p − 15).
Mỗi "cách biết" cho r từng cạnh theo khe 15 phút kể từ τ (ba_phuong_an.dat_du_bao); cạnh không thuộc đoạn có số
thì giữ như lúc p (lần chụp p, cạnh không đo lấy hồ sơ giờ):
  giu        lần chụp lúc p, coi như giữ nguyên tới hết chuyến (như C/D của cham_tuyen_that.py, nhưng cũ TRUOC phút)
  ls         hồ sơ lịch sử của ĐOẠN (TB r cùng loại ngày, cùng ô 15 phút, CHỈ trên phần học của mô hình) ở giờ xe tới
  <mô hình>  dự báo của đoạn cho khe trong tầm (TRUOC + 15 .. 60 phút kể từ f), quá tầm thì như ls
  that       r THẬT từng khe (dùng tương lai — trần, không làm được ngoài đời)
Mỗi cách tính 2 tuyến: n_ (nhanh nhất) và t_ (tối ưu, như D). Kèm A (ngắn nhất) và N (tối ưu lập NGAY lúc đi τ — như D
của cham_tuyen_that.py, để biết lập trước thiệt bao nhiêu; tự kiểm: N phải trùng phut_D của lần chấm đi ngay).
Chấm: như cham_tuyen_that.py (tốc độ đo thật lúc xe tới từng cạnh). Ghi cả giờ đến DỰ KIẾN lúc lập (du_doan_*) để đo
sai giờ đến — điều đơn hẹn cần nhất.

Chạy:  python cham_tuyen_dat_truoc.py 2026-11-09 [--truoc=30] [--du-bao=gbm_ls,gwn_ho_so_them_che] [--gio=06:30,17:00]
Ra:    danh_gia/ket_qua/dat_truoc<TRUOC>_<ngày>.csv; tổng hợp: tong_hop_dat_truoc.py
"""
import datetime as dt
import glob
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
sys.path.insert(0, os.path.join(GOC, 'mo_hinh'))
from ba_phuong_an import DinhTuyen  # noqa: E402
from cham_tuyen_that import (GIO_XUAT_PHAT, HE_SO_KHONG_DO, KHE_S, PHAT_DONG_S, R_SAN, RA, V_SAN,  # noqa: E402
                             cap_zenodo, nap_du_bao, nap_quan_sat)
from dac_trung import TY_LE_HOC  # noqa: E402


def ho_so_doan(so_doan):
    """(2, 96, số đoạn): TB r của đoạn theo (ngày thường / cuối tuần, ô 15 phút) CHỈ trên phần học — cùng cách chia
    và cùng định nghĩa với ho_so_lich_su.ho_so (70% khung đầu của tầng vàng); NaN nếu không có mẫu. Kèm mốc hết học."""
    d = pd.concat([pd.read_parquet(t, columns=['khung', 'doan', 'r'])
                   for t in sorted(glob.glob(os.path.join(GOC, 'du_lieu', 'vang', '*.parquet')))], ignore_index=True)
    khung = np.sort(d['khung'].unique())
    het_hoc = khung[int(len(khung) * TY_LE_HOC) - 1]
    d = d[(d['khung'] <= het_hoc) & d['r'].notna()]
    cuoi = (d['khung'].dt.dayofweek >= 5).to_numpy().astype(np.int64)
    o = (d['khung'].dt.hour * 4 + d['khung'].dt.minute // 15).to_numpy()
    tong, dem = np.zeros((2, 96, so_doan)), np.zeros((2, 96, so_doan))
    np.add.at(tong, (cuoi, o, d['doan'].to_numpy()), d['r'].to_numpy())
    np.add.at(dem, (cuoi, o, d['doan'].to_numpy()), 1)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(dem > 0, tong / dem, np.nan).astype(np.float32), pd.Timestamp(het_hoc)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t_bat_dau = time.time()
    thong_so = [a for a in sys.argv[1:] if not a.startswith('--')]
    ngay = thong_so[0] if thong_so else '2026-11-09'
    truoc = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--truoc=')), 30)
    ten_du_bao = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--du-bao=')),
                      'gbm_ls,gwn_ho_so_them_che').split(',')
    khung, R, DONG, PD = nap_quan_sat(ngay, '05:00', '23:00')
    d = DinhTuyen.nap(None)
    r_ho_so = np.array(d.mh.r_gio, dtype=np.float32)
    v_trong, dai = d.mh.v_trong.astype(np.float64), d.dai
    n = len(dai)
    doan_cua = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'canh_doan.parquet'),
                               columns=['chi_so', 'doan']).sort_values('chi_so')['doan'].to_numpy()
    P, het_hoc = ho_so_doan(int(doan_cua.max()) + 1)
    du_bao = {t: nap_du_bao(t, ngay)[0] for t in ten_du_bao}
    for t in ten_du_bao:          # dự báo cần khung f = p − 15 của ngày; khung 15 phút đầu ngày nằm ở ngày trước -> bỏ qua
        du_bao[t] = du_bao[t].set_index('khung')
    print(f'{ngay}: lap truoc {truoc} phut; {len(khung)} lan chup; ho so doan tu phan hoc toi {het_hoc}; '
          f'du bao {ten_du_bao}; nap {time.time() - t_bat_dau:.0f}s', flush=True)
    he_so = HE_SO_KHONG_DO

    # ── Chấm bằng tốc độ thật: y hệt cham_tuyen_that.py ──
    def lan_chup(t):
        k = int(np.searchsorted(khung, np.datetime64(t), side='right')) - 1
        return k if 0 <= k < len(khung) and (t - khung[k]).total_seconds() < 600 else None

    phat_kieu = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--phat-dong=')), 'canh')

    def buoc(i, t, k, truoc_dong=False):
        dong = int(DONG[k, i])
        r = R[k, i]
        if r != r:
            r = r_ho_so[t.hour, i] * he_so
        phat = PHAT_DONG_S * dong if (phat_kieu == 'canh' or not truoc_dong) else 0.0
        return dai[i] / (max(v_trong[i] * r, V_SAN) / 3.6) * (1 + PD[k, i]) + phat, dong

    def cham(canh, t0):
        # Mặc định 'canh' để trùng các lượt đã chấm 13/11 (QĐ-028); QĐ-029 đổi sang mỗi lần gặp: --phat-dong=lan.
        tau, vao_dong, dong = 0.0, 0, 0
        for i in canh:
            t = t0 + dt.timedelta(seconds=tau)
            k = lan_chup(t)
            if k is None:
                return None
            s, dong = buoc(i, t, k, dong > 0)
            tau, vao_dong = tau + s, vao_dong + dong
        return tau / 60, vao_dong

    # ── Các cách biết r theo khe ──
    def theo_doan(v_doan, nen):
        """Giá trị theo đoạn (mảng theo mã đoạn, NaN = không có) -> theo cạnh; cạnh không có -> nen."""
        v = v_doan[doan_cua]
        return np.where(np.isnan(v), nen, v)

    def khe_ls(tau, nen):
        ra = np.empty((4, n), dtype=np.float32)
        for j in range(4):
            dich = tau + pd.Timedelta(minutes=15 * j)
            ra[j] = theo_doan(P[int(dich.dayofweek >= 5), dich.hour * 4 + dich.minute // 15], nen)
        return ra

    def khe_du_bao(ten, f, tau, nen, ls):
        """Khe j (bắt đầu τ + 15j) = dự báo tầm (τ + 15j) − f nếu ≤ 60 phút, quá tầm thì như ls."""
        if f not in du_bao[ten].index:
            return None
        x = du_bao[ten].loc[[f]]
        ra = ls.copy()
        for j in range(4):
            tam = int(((tau + pd.Timedelta(minutes=15 * j)) - f) / pd.Timedelta(minutes=1))
            cot = f'du_{tam}'
            if cot in x:
                v = np.full(int(doan_cua.max()) + 1, np.nan, dtype=np.float32)
                v[x['doan'].to_numpy()] = x[cot].to_numpy()
                ra[j] = theo_doan(v, ls[j])
        return ra

    def khe_that(tau, nen):
        ra = np.empty((4, n), dtype=np.float32)
        for j in range(4):
            a, b = tau + pd.Timedelta(minutes=15 * j), tau + pd.Timedelta(minutes=15 * (j + 1))
            k = np.flatnonzero((khung >= a) & (khung < b))
            with np.errstate(invalid='ignore', divide='ignore'), warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                hm = 1 / np.nanmean(1 / R[k], axis=0) if len(k) else np.full(n, np.nan)
            ra[j] = np.where(np.isnan(hm), nen, hm)
        return ra

    cap = cap_zenodo()
    hang = []
    cac_gio = next((a.split('=', 1)[1].split(',') for a in sys.argv if a.startswith('--gio=')), GIO_XUAT_PHAT)
    for gio in cac_gio:
        t1 = time.time()
        tau = pd.Timestamp(f'{ngay} {gio}')
        p = tau - pd.Timedelta(minutes=truoc)
        f = p - pd.Timedelta(minutes=15)
        k_p, k_tau = lan_chup(p), lan_chup(tau)
        if k_p is None or k_tau is None:
            print(f'{gio}: thieu lan chup -> bo')
            continue
        nen_p = np.where(np.isnan(R[k_p]), r_ho_so[p.hour], R[k_p])
        biet_p = (nen_p, DONG[k_p], PD[k_p])
        tuyen = {}

        def lap(ten, r_khe, pa_cac=('nhanh_nhat', 'toi_uu'), biet=biet_p):
            d.dat_tinh_trang(*biet)
            if r_khe is not None:
                d.dat_du_bao(np.clip(r_khe, R_SAN, 1), KHE_S)
            for (a, pa), (b, pb) in cap:
                kq = d.tim(pa, pb, tau, phuong_an=pa_cac)
                for pa_ in pa_cac:
                    khoa = ten if len(pa_cac) == 1 else f'{"n" if pa_ == "nhanh_nhat" else "t"}_{ten}'
                    tuyen.setdefault((a, b), {})[khoa] = kq[pa_]

        lap('A', None, ('ngan_nhat',))
        lap('N', None, ('toi_uu',), (np.where(np.isnan(R[k_tau]), r_ho_so[tau.hour], R[k_tau]), DONG[k_tau], PD[k_tau]))
        lap('giu', None)
        ls = khe_ls(tau, nen_p)
        lap('ls', ls)
        co_du_bao = []
        for ten in ten_du_bao:
            rk = khe_du_bao(ten, f, tau, nen_p, ls)
            if rk is not None:
                lap(ten, rk)
                co_du_bao.append(ten)
        lap('that', khe_that(tau, nen_p))

        for (a, _), (b, _) in cap:
            x = tuyen[(a, b)]
            dong = {'gio': gio, 'lap_luc': f'{p:%H:%M}', 'di': a, 'den': b}
            for k, r in x.items():
                c = cham(r['canh'], tau) if r else None
                if c is None:
                    continue
                dong[f'phut_{k}'], dong[f'vao_dong_{k}'] = c
                dong[f'm_{k}'] = r['dai_m']
                dong[f'du_doan_{k}'] = r['tg_du_kien_s'] / 60
            hang.append(dong)
        print(f'{gio} (lap {p:%H:%M}): {len(cap)} cap, du bao {co_du_bao}, {time.time() - t1:.0f}s', flush=True)

    kq = pd.DataFrame(hang)
    os.makedirs(RA, exist_ok=True)
    if cac_gio == GIO_XUAT_PHAT:              # chạy thử vài giờ (--gio=) thì không ghi đè kết quả
        kq.to_csv(os.path.join(RA, f'dat_truoc{truoc}_{ngay}.csv'), index=False, encoding='utf-8-sig')

    # Tự kiểm: N (lập lúc đi) phải trùng phut_D của lần chấm đi ngay cùng ngày.
    cu = sorted(glob.glob(os.path.join(RA, f'cham_tuyen_{ngay}_zenodo*.csv')))
    if cu:
        m = kq.merge(pd.read_csv(cu[0])[['gio', 'di', 'den', 'phut_D']], on=['gio', 'di', 'den'])
        print(f'Tu kiem N = D cua {os.path.basename(cu[0])}: '
              f'{int(((m["phut_N"] - m["phut_D"]).abs() < 1e-6).sum())}/{len(m)}')
    cach = ['giu', 'ls', *ten_du_bao, 'that']
    print(f'\n{len(kq)} chuyen. Phut that TB (toi uu / nhanh nhat) va sai gio den du kien luc lap (nhanh nhat):')
    for c in cach:
        if f'phut_t_{c}' not in kq:
            continue
        sai = (kq[f'du_doan_n_{c}'] - kq[f'phut_n_{c}'])
        print(f'  {c:<20} t {kq[f"phut_t_{c}"].mean():6.2f}p  n {kq[f"phut_n_{c}"].mean():6.2f}p | '
              f'gio den sai TB {sai.abs().mean():.2f}p, lech TB {sai.mean():+.2f}p | '
              f't nhanh hon giu {100 * (1 - kq[f"phut_t_{c}"].sum() / kq["phut_t_giu"].sum()):+.2f}%')
    print(f'  A ngan nhat {kq["phut_A"].mean():.2f}p, N lap luc di {kq["phut_N"].mean():.2f}p '
          f'({time.time() - t_bat_dau:.0f}s)')


if __name__ == '__main__':
    main()
