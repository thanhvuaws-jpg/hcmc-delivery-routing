"""
M5 — Kẹt lan ra sao? Tương quan chéo có độ trễ và Granger giữa các đoạn CÙNG TUYẾN đường, 5 phút/lần.

Bẫy: mọi đường đều đông cùng giờ cao điểm, nên hai đoạn bất kỳ cũng tương quan mà không có gì "lan". Vì vậy
không dùng r thô mà dùng PHẦN DƯ e = r − hồ sơ (đoạn, ngày thường/cuối tuần, ô 30 phút): chỉ còn biến động
khác thường so với nhịp ngày. Chỉ xét 06:00–22:00 (ban đêm gần như đường trống, không có gì để lan).

Cặp (u, d): đoạn u ở THƯỢNG NGUỒN, d ở HẠ NGUỒN cùng tên đường, dò theo chiều xe chạy, khoảng cách tâm–tâm
tới KC_TOI_DA_KM. Tương quan chéo c(L) = corr(e_u[t + L], e_d[t]):
  L > 0  thượng nguồn đổi SAU hạ nguồn: kẹt lan NGƯỢC chiều xe (hàng chờ dồn về phía sau) — điều lý thuyết dòng
         xe dự đoán khi có nút thắt;
  L < 0  thượng nguồn đổi TRƯỚC: thay đổi trôi XUÔI theo dòng xe.
Với mỗi nhóm khoảng cách lấy TB c(L) mọi cặp, tìm độ trễ đỉnh (nội suy parabol vì lần chụp cách 5 phút), rồi hồi
quy độ trễ đỉnh theo khoảng cách ra tốc độ lan (phút/km). Khoảng tin cậy 95%: bootstrap trên các cặp.

Granger (3 độ trễ, cặp cách 0,5–2 km): quá khứ của d có giúp dự báo u ngoài quá khứ của chính u không, và
chiều ngược lại; kiểm F, hiệu chỉnh nhiều phép thử Benjamini–Hochberg 5%. Granger chỉ nói "báo trước được",
không chứng minh nguyên nhân.

Giới hạn: lấy mẫu 5 phút; TomTom gán cùng tốc độ cho các đoạn thuộc một đoạn của họ nên cặp rất gần có đỉnh
giả ở L = 0 (xem nhóm khoảng cách nhỏ nhất).

Chạy:  python m5_lan_ket.py [--bo-chung]   (--bo-chung: trừ biến động chung toàn mạng ở từng lần chụp)
Ra:    khai_pha/ket_qua/m5_ccf.csv, m5_lan_ket.png, m5_tom_tat.json (không lên git — từ dữ liệu TomTom)
"""
import glob
import json
import os
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from scipy.stats import f as phan_phoi_f              # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m2_diem_nong import bh                           # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
CHINH = {'trunk', 'primary', 'secondary', 'tertiary'}
GIO_TU, GIO_DEN = 6, 22
PHU_TOI_THIEU = 0.7             # đoạn có số đo ở ≥ 70% lần chụp ban ngày
LS_TOI_THIEU = 0.03             # phần dư phải dao động ≥ 3 điểm %: đoạn luôn trống không có gì để đo
KC_TOI_DA_KM = 4.0
NHOM_KM = np.arange(0, KC_TOI_DA_KM + 0.5, 0.5)
TOI_DA_CAP_NHOM = 6000
TRE_MAX = 8                     # ±8 lần chụp = ±40 phút
BOOT = 200
GRANGER_TRE, GRANGER_CAP = 3, 3000


def nap_chuoi():
    """(lần chụp × đoạn chính có tên): r theo 5 phút, trọng số dài × phủ, chỉ phần đường đang mở."""
    d = pd.read_parquet(os.path.join(BAC, 'doan.parquet'), columns=['doan', 'u_dau', 'v_cuoi', 'dai', 'loai', 'ten'])
    d = d[d['loai'].astype(str).isin(CHINH) & d['ten'].notna() & (d['ten'] != '')].reset_index(drop=True)
    vi_tri = np.full(int(pd.read_parquet(os.path.join(BAC, 'doan.parquet'), columns=['doan'])['doan'].max()) + 1, -1)
    vi_tri[d['doan'].to_numpy()] = np.arange(len(d))
    doan_cua = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))['doan'].to_numpy()
    dai_canh = pd.read_parquet(os.path.join(BAC, 'canh_tinh.parquet'), columns=['dai'])['dai'].to_numpy()
    cac_tep = sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet')))
    t0 = pd.Timestamp(os.path.basename(cac_tep[0])[:10])
    T = (pd.Timestamp(os.path.basename(cac_tep[-1])[:10]) - t0).days * 288 + 288
    tu, mau = np.zeros((T, len(d)), np.float32), np.zeros((T, len(d)), np.float32)
    for tep in cac_tep:
        s = pd.read_parquet(tep, columns=['khung', 'chi_so', 'muc', 'phu'])
        s = s[s['phu'] > 0]
        n = vi_tri[doan_cua[s['chi_so'].to_numpy()]]
        giu = n >= 0
        ti = ((s['khung'].to_numpy()[giu] - np.datetime64(t0)) // np.timedelta64(5, 'm')).astype(np.int64)
        w = dai_canh[s['chi_so'].to_numpy()[giu]] * s['phu'].to_numpy()[giu] / 100
        np.add.at(tu, (ti, n[giu]), (s['muc'].to_numpy()[giu] / 100 * w).astype(np.float32))
        np.add.at(mau, (ti, n[giu]), w.astype(np.float32))
    with np.errstate(invalid='ignore', divide='ignore'):
        R = np.where(mau > 0, tu / mau, np.nan).astype(np.float32)
    return d, R, pd.date_range(t0, periods=T, freq='5min')


def phan_du(R, luc):
    """e = r − hồ sơ (đoạn, loại ngày, ô 30 phút); ngoài 06:00–22:00 đặt NaN (cũng ngăn độ trễ vượt qua ngày)."""
    cuoi = np.asarray(luc.dayofweek >= 5, dtype=np.int64)
    o = np.asarray(luc.hour * 2 + luc.minute // 30, dtype=np.int64)
    co = ~np.isnan(R)
    tong, dem = np.zeros((2, 48, R.shape[1])), np.zeros((2, 48, R.shape[1]))
    np.add.at(tong, (cuoi, o), np.where(co, R, 0).astype(np.float64))
    np.add.at(dem, (cuoi, o), co)
    with np.errstate(invalid='ignore', divide='ignore'):
        H = (tong / dem)[cuoi, o]
    E = (R - H).astype(np.float32)
    E[(luc.hour < GIO_TU) | (luc.hour >= GIO_DEN)] = np.nan
    return E


def cac_cap(d, hop_le):
    """Dò xuôi theo chiều xe trên cùng tên đường: (u, d, khoảng cách km) cho các cặp đều hợp lệ."""
    theo_nut = {}
    for i, (u, ten) in enumerate(zip(d['u_dau'].to_numpy(), d['ten'].to_numpy())):
        theo_nut.setdefault((u, ten), []).append(i)
    u_dau, v_cuoi, dai, ten = d['u_dau'].to_numpy(), d['v_cuoi'].to_numpy(), d['dai'].to_numpy(), d['ten'].to_numpy()
    cap = []
    for i in np.flatnonzero(hop_le):
        cur, di, da_qua = i, dai[i] / 2, {i}
        while di < KC_TOI_DA_KM * 1000:
            ke = [c for c in theo_nut.get((v_cuoi[cur], ten[i]), ())
                  if c not in da_qua and v_cuoi[c] != u_dau[cur]]     # không quay đầu sang chiều ngược lại
            if not ke:
                break
            c = ke[0]
            km = (di + dai[c] / 2) / 1000
            if hop_le[c] and km <= KC_TOI_DA_KM:
                cap.append((i, c, km))
            da_qua.add(c)
            di += dai[c]
            cur = c
    return np.array(cap, dtype=[('u', 'i4'), ('d', 'i4'), ('km', 'f4')])


def ccf_tung_cap(E, u, d):
    """c(L) cho từng cặp, L = −TRE_MAX..TRE_MAX: mảng (số cặp, 2·TRE_MAX + 1)."""
    ra = np.full((len(u), 2 * TRE_MAX + 1), np.nan, np.float32)
    for j, L in enumerate(range(-TRE_MAX, TRE_MAX + 1)):
        a = E[max(L, 0):E.shape[0] + min(L, 0)][:, u]         # e_u[t + L]
        b = E[max(-L, 0):E.shape[0] + min(-L, 0)][:, d]       # e_d[t]
        m = ~(np.isnan(a) | np.isnan(b))
        n = m.sum(axis=0)
        a0, b0 = np.where(m, a, 0), np.where(m, b, 0)
        ma, mb = a0.sum(axis=0) / np.maximum(n, 1), b0.sum(axis=0) / np.maximum(n, 1)
        sa, sb = np.where(m, a - ma, 0), np.where(m, b - mb, 0)
        tu = (sa * sb).sum(axis=0)
        mau = np.sqrt((sa * sa).sum(axis=0) * (sb * sb).sum(axis=0))
        with np.errstate(invalid='ignore', divide='ignore'):
            ra[:, j] = np.where((mau > 0) & (n >= 100), tu / mau, np.nan)
    return ra


def dinh_parabol(c):
    """Độ trễ đỉnh (số lần chụp, có phần lẻ) của đường c(L) trung bình."""
    j = int(np.nanargmax(c))
    if 0 < j < len(c) - 1:
        a, b, g = c[j - 1], c[j], c[j + 1]
        mau = a - 2 * b + g
        return (j - TRE_MAX) + (0.5 * (a - g) / mau if mau != 0 else 0.0)
    return float(j - TRE_MAX)


def do_doc(km, tre):
    """Hệ số góc (phút/km) của độ trễ đỉnh theo khoảng cách, bình phương tối thiểu."""
    return float(np.polyfit(km, tre, 1)[0])


def granger(E, u, d, p=GRANGER_TRE):
    """p-value F: quá khứ của d có giúp dự báo u không (ngoài quá khứ của u). Chỉ dòng đủ số liệu."""
    T = E.shape[0]
    y = E[p:, u]
    tre_y = np.stack([E[p - k:T - k, u] for k in range(1, p + 1)], axis=1)
    tre_x = np.stack([E[p - k:T - k, d] for k in range(1, p + 1)], axis=1)
    m = ~(np.isnan(y) | np.isnan(tre_y).any(axis=1) | np.isnan(tre_x).any(axis=1))
    n = int(m.sum())
    if n < 200:
        return np.nan
    mot = np.ones((n, 1), np.float32)
    A0 = np.hstack([mot, tre_y[m]])
    A1 = np.hstack([A0, tre_x[m]])
    y_ = y[m]
    rss0 = float(((y_ - A0 @ np.linalg.lstsq(A0, y_, rcond=None)[0]) ** 2).sum())
    rss1 = float(((y_ - A1 @ np.linalg.lstsq(A1, y_, rcond=None)[0]) ** 2).sum())
    bac = n - A1.shape[1]
    if rss1 <= 0 or bac <= 0:
        return np.nan
    return float(phan_phoi_f.sf(((rss0 - rss1) / p) / (rss1 / bac), p, bac))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t_bd = time.time()
    d, R, luc = nap_chuoi()
    E = phan_du(R, luc)
    del R
    # --bo-chung: trừ biến động chung toàn mạng ở từng lần chụp (mưa, ngày vắng…). Lần chạy đầu cho c(L) đỉnh ở L = 0
    # ở mọi khoảng cách, tới 4 km vẫn 0,38 — dấu hiệu mọi đoạn đổi cùng lúc vì một nguyên nhân chung, không phải lan.
    bo_chung = '--bo-chung' in sys.argv
    hau_to = '_bo_chung' if bo_chung else ''
    if bo_chung:
        with np.errstate(invalid='ignore'):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                E = E - np.nanmean(E, axis=1, keepdims=True)
        print('Da tru bien dong chung toan mang o tung lan chup')
    ban_ngay = (luc.hour >= GIO_TU) & (luc.hour < GIO_DEN)
    co_du_lieu = ~np.isnan(E[ban_ngay]).all(axis=1)
    phu = (~np.isnan(E[ban_ngay][co_du_lieu])).mean(axis=0)
    with np.errstate(invalid='ignore'):
        ls = np.nanstd(E[ban_ngay][co_du_lieu], axis=0)
    hop_le = (phu >= PHU_TOI_THIEU) & (ls >= LS_TOI_THIEU)
    cap = cac_cap(d, hop_le)
    print(f'{len(d):,} doan chinh co ten, {int(hop_le.sum()):,} hop le (phu >= {PHU_TOI_THIEU:.0%}, phan du dao dong '
          f'>= {LS_TOI_THIEU * 100:.0f} diem); {len(cap):,} cap cung tuyen <= {KC_TOI_DA_KM:.0f} km; {time.time() - t_bd:.0f}s', flush=True)

    rng = np.random.default_rng(42)
    tam, ccf_tb, c_cap, hang = [], [], [], []
    for a, b in zip(NHOM_KM[:-1], NHOM_KM[1:]):
        chon = cap[(cap['km'] >= a) & (cap['km'] < b)]
        if len(chon) > TOI_DA_CAP_NHOM:
            chon = rng.choice(chon, TOI_DA_CAP_NHOM, replace=False)
        c = ccf_tung_cap(E, chon['u'], chon['d'])
        tb = np.nanmean(c, axis=0)
        tam.append((a + b) / 2)
        ccf_tb.append(tb)
        c_cap.append(c)
        tre = float(dinh_parabol(tb)) * 5
        dinh_cap = np.nanargmax(np.nan_to_num(c, nan=-2), axis=1) - TRE_MAX
        hang.append({'tu_km': a, 'den_km': b, 'so_cap': len(chon), 'tre_dinh_phut': round(tre, 2),
                     'c_dinh': round(float(np.nanmax(tb)), 3), 'c_L0': round(float(tb[TRE_MAX]), 3),
                     'ty_le_cap_L_duong': round(float((dinh_cap > 0).mean()), 3),
                     'ty_le_cap_L_am': round(float((dinh_cap < 0).mean()), 3),
                     'ty_le_cap_L0': round(float((dinh_cap == 0).mean()), 3)})
        print(f'  {a:.1f}-{b:.1f} km: {len(chon):>5} cap, tre dinh {tre:+6.2f} phut, c dinh {np.nanmax(tb):.3f} '
              f'(c(0) {tb[TRE_MAX]:.3f}); dinh sau hạ nguồn {hang[-1]["ty_le_cap_L_duong"]:.0%}, trước {hang[-1]["ty_le_cap_L_am"]:.0%}, '
              f'cung luc {hang[-1]["ty_le_cap_L0"]:.0%}', flush=True)
    tam = np.array(tam)
    bang = pd.DataFrame(hang)
    tre_nhom = bang['tre_dinh_phut'].to_numpy()
    doc = do_doc(tam, tre_nhom)
    # Bootstrap trên cặp, trong từng nhóm khoảng cách.
    mau_doc = []
    for _ in range(BOOT):
        t = [dinh_parabol(np.nanmean(c[rng.integers(0, len(c), len(c))], axis=0)) * 5 for c in c_cap]
        mau_doc.append(do_doc(tam, np.array(t)))
    d_lo, d_hi = np.percentile(mau_doc, [2.5, 97.5])
    print(f'Do doc do tre theo khoang cach: {doc:+.2f} phut/km (95% CI {d_lo:+.2f} .. {d_hi:+.2f})', flush=True)

    # Granger trên cặp 0,5–2 km.
    gan = cap[(cap['km'] >= 0.5) & (cap['km'] < 2.0)]
    if len(gan) > GRANGER_CAP:
        gan = rng.choice(gan, GRANGER_CAP, replace=False)
    p_du = np.array([granger(E, a, b) for a, b in zip(gan['u'], gan['d'])])    # d (hạ nguồn) báo trước u
    p_ud = np.array([granger(E, b, a) for a, b in zip(gan['u'], gan['d'])])    # u (thượng nguồn) báo trước d
    tot = ~(np.isnan(p_du) | np.isnan(p_ud))
    co = bh(np.concatenate([p_du[tot], p_ud[tot]]), 0.05)
    sig_du, sig_ud = co[:tot.sum()], co[tot.sum():]
    g = {'so_cap': int(tot.sum()), 'chi_ha_bao_thuong': float((sig_du & ~sig_ud).mean()),
         'chi_thuong_bao_ha': float((sig_ud & ~sig_du).mean()), 'ca_hai': float((sig_du & sig_ud).mean()),
         'khong_chieu_nao': float((~sig_du & ~sig_ud).mean())}
    print(f'Granger ({g["so_cap"]} cap 0,5-2 km, FDR 5%): chi ha nguon bao truoc {g["chi_ha_bao_thuong"]:.1%}; '
          f'chi thuong nguon bao truoc {g["chi_thuong_bao_ha"]:.1%}; ca hai {g["ca_hai"]:.1%}; khong chieu nao {g["khong_chieu_nao"]:.1%}')

    os.makedirs(RA, exist_ok=True)
    bang.to_csv(os.path.join(RA, f'm5_ccf{hau_to}.csv'), index=False)
    with open(os.path.join(RA, f'm5_tom_tat{hau_to}.json'), 'w', encoding='utf-8') as f:
        json.dump({'do_doc_phut_km': doc, 'ci95': [float(d_lo), float(d_hi)], 'granger': g, 'nhom': hang,
                   'so_doan_hop_le': int(hop_le.sum()), 'so_cap': int(len(cap))}, f, ensure_ascii=False, indent=1)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    tre_truc = np.arange(-TRE_MAX, TRE_MAX + 1) * 5
    for k, mau in zip((0, 2, 4, 7), ('#2a78d6', '#eb6834', '#1baf7a', '#eda100')):
        a1.plot(tre_truc, ccf_tb[k], color=mau, lw=2, label=f'{NHOM_KM[k]:.1f}–{NHOM_KM[k + 1]:.1f} km')
    a1.axvline(0, color='#a8a7a1', lw=0.8)
    a1.set_xlabel('Độ trễ L (phút): dương = thượng nguồn đổi SAU hạ nguồn')
    a1.set_ylabel('Tương quan phần dư TB')
    a1.set_title('Tương quan chéo theo khoảng cách')
    a1.legend(frameon=False, fontsize=9)
    a2.plot(tam, tre_nhom, color='#2a78d6', lw=2, marker='o', ms=6)
    a2.axhline(0, color='#a8a7a1', lw=0.8)
    a2.set_xlabel('Khoảng cách theo tuyến (km)')
    a2.set_ylabel('Độ trễ đỉnh (phút)')
    a2.set_title(f'Độ dốc {doc:+.2f} phút/km (95% CI {d_lo:+.2f} .. {d_hi:+.2f})')
    for ax in (a1, a2):
        ax.grid(axis='y', color='#e4e3df', lw=0.8)
        ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, f'm5_lan_ket{hau_to}.png'), dpi=150)
    print(f'-> {RA} ({time.time() - t_bd:.0f}s)')


if __name__ == '__main__':
    main()
