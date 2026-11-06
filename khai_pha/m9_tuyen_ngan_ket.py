"""
M9 — Tuyến ngắn nhất có hay dính kẹt không? Số liệu cho phần "đặt vấn đề" của đề tài.

Điểm đi–đến là điểm giao hàng THẬT của bộ Zenodo HCM_1000 (D13), không phải vài địa danh chọn tay. Bốc ngẫu nhiên
SO_TUYEN cặp trong vùng bản đồ, cách nhau (đường chim bay) KC_TU–KC_DEN km — tầm một chặng giao hàng trong phố.
Tuyến ngắn nhất tính một lần (ít mét nhất, đúng luật một chiều / cấm rẽ, không biết giao thông), rồi soi nó qua
TỪNG lần chụp TomTom thật:
  dính kẹt    tuyến có ≥ NGUONG_KET_M mét đang kẹt nặng (r < 0,4) — ngưỡng để không tính vài mét lẻ;
  % kẹt, đông phần chiều dài có số đo đang r < 0,4, r < 0,75;
  qua đường đóng  tuyến đi vào cạnh đang đóng hẳn;
  thêm thời gian  thời gian thật so với đường trống, CHỈ trên phần có số đo.

Giới hạn: hẻm và đường nhỏ TomTom không đo nên chỉ tính trên phần có số đo (in tỉ lệ phủ); đây là ĐỘ PHƠI NHIỄM
của tuyến ngắn nhất, chưa so với tuyến khác (so sánh tuyến ở danh_gia/cham_tuyen_that.py).

Chạy:  python m9_tuyen_ngan_ket.py
Ra:    khai_pha/ket_qua/m9_theo_gio.csv, m9_theo_gio.png, m9_tom_tat.json (không lên git — từ dữ liệu TomTom)
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
import scipy.sparse as sp                             # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from tim_duong import BanDo                           # noqa: E402

BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA = os.path.join(GOC, 'khai_pha', 'ket_qua')
SO_TUYEN = 500
KC_TU, KC_DEN = 1.5, 8.0        # km đường chim bay
NGUONG_KET_M = 200.0
NGUONG_KET_LON_M = 1000.0       # 200 m khá thấp với tuyến ~7 km: in thêm mức này để khỏi thổi phồng
R_KET, R_DONG = 40, 75          # muc (điểm %) của tầng bạc


def khoang_cach_km(a, b):
    dy = (a[0] - b[0]) * 110.574
    dx = (a[1] - b[1]) * 111.320 * np.cos(np.radians(10.78))
    return float(np.hypot(dx, dy))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bd = BanDo.nap()
    dai = np.array([d['dai'] for _, _, d in bd.G.edges(data=True)], np.float64)
    diem = pd.read_parquet(os.path.join(BAC, 'zenodo_diem.parquet'))
    diem = diem[diem['trong_vung']][['lat', 'lon']].to_numpy()
    rng = np.random.default_rng(42)
    tuyen, thu = [], 0
    while len(tuyen) < SO_TUYEN and thu < SO_TUYEN * 20:
        thu += 1
        a, b = diem[rng.choice(len(diem), 2, replace=False)]
        if not KC_TU <= khoang_cach_km(a, b) <= KC_DEN:
            continue
        r = bd.tim(tuple(a), tuple(b), 'dai')
        if r and len(r['nut']) >= 2:
            tuyen.append([bd.G[x][y]['i'] for x, y in zip(r['nut'], r['nut'][1:])])
    dai_tuyen = np.array([dai[t].sum() for t in tuyen])
    print(f'{len(diem):,} diem giao hang trong vung; {len(tuyen)} tuyen ngan nhat (bo {thu - len(tuyen)} cap ngoai khoang '
          f'cach / khong co duong), dai TB {dai_tuyen.mean() / 1000:.1f} km; {time.time() - t0:.0f}s', flush=True)

    # Ma trận tuyến × cạnh dùng tới (giá trị = mét).
    canh_dung = np.unique(np.concatenate([np.asarray(t) for t in tuyen]))
    vi_tri = np.full(len(dai), -1)
    vi_tri[canh_dung] = np.arange(len(canh_dung))
    hang = np.concatenate([np.full(len(t), i) for i, t in enumerate(tuyen)])
    cot = vi_tri[np.concatenate([np.asarray(t) for t in tuyen])]
    A = sp.csr_matrix((dai[canh_dung][cot], (hang, cot)), shape=(len(tuyen), len(canh_dung)))

    v_trong = pd.read_parquet(os.path.join(BAC, 'toc_do_canh.parquet'), columns=['chi_so', 'v_trong', 'v_trong_loai'])
    v_trong = v_trong.set_index('chi_so').reindex(range(len(dai)))
    toc_do_do_thi = np.array([d['toc_do'] for _, _, d in bd.G.edges(data=True)], np.float64)   # km/h mặc định theo loại đường
    vt = v_trong['v_trong'].fillna(v_trong['v_trong_loai']).to_numpy(dtype=np.float64)
    vt = np.where(np.isfinite(vt) & (vt > 0), vt, toc_do_do_thi)[canh_dung]

    dong_kq = []
    for tep in sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet'))):
        s = pd.read_parquet(tep, columns=['khung', 'chi_so', 'muc', 'phu', 'phu_dong'])
        s = s[vi_tri[s['chi_so'].to_numpy()] >= 0]
        cac_khung, ti = np.unique(s['khung'].to_numpy(), return_inverse=True)
        ni = vi_tri[s['chi_so'].to_numpy()]
        muc = np.full((len(cac_khung), len(canh_dung)), np.nan, np.float32)
        mo = s['phu'].to_numpy() > 0
        muc[ti[mo], ni[mo]] = s['muc'].to_numpy()[mo]
        dong = np.zeros(muc.shape, bool)
        dong[ti[~mo], ni[~mo]] = s['phu_dong'].to_numpy()[~mo] > 0
        do = ~np.isnan(muc)
        with np.errstate(invalid='ignore'):
            ket, dong_duc = muc < R_KET, muc < R_DONG
        # Thời gian trên phần có số đo: dài / (v_trống × r); đường trống: dài / v_trống.
        with np.errstate(invalid='ignore', divide='ignore'):
            tg_that = np.where(do, 1 / (vt * np.maximum(muc / 100, 0.1)), 0.0)
        tg_trong = np.where(do, 1 / vt, 0.0)
        L_do = A @ do.T.astype(np.float64)
        L_ket = A @ ket.T.astype(np.float64)
        L_dong = A @ dong_duc.T.astype(np.float64)
        L_dongduong = A @ dong.T.astype(np.float64)
        T_that, T_trong = A @ tg_that.T, A @ tg_trong.T
        for k, luc in enumerate(pd.DatetimeIndex(cac_khung)):
            dong_kq.append({'khung': luc, 'dinh_ket': float((L_ket[:, k] >= NGUONG_KET_M).mean()),
                            'dinh_ket_1km': float((L_ket[:, k] >= NGUONG_KET_LON_M).mean()),
                            'pct_ket': L_ket[:, k].sum() / max(L_do[:, k].sum(), 1),
                            'pct_dong': L_dong[:, k].sum() / max(L_do[:, k].sum(), 1),
                            'qua_dong_duong': float((L_dongduong[:, k] > 0).mean()),
                            'them_tg': T_that[:, k].sum() / max(T_trong[:, k].sum(), 1e-9) - 1,
                            'phu_so_do': L_do[:, k].sum() / dai_tuyen.sum()})
        print(f'  {os.path.basename(tep)[:10]}: {len(cac_khung)} lan chup', flush=True)
    kq = pd.DataFrame(dong_kq)
    kq['cuoi_tuan'] = kq['khung'].dt.dayofweek >= 5
    kq['gio'] = kq['khung'].dt.hour
    cot_so = ['dinh_ket', 'dinh_ket_1km', 'pct_ket', 'pct_dong', 'qua_dong_duong', 'them_tg', 'phu_so_do']
    theo_gio = kq.groupby(['cuoi_tuan', 'gio'])[cot_so].mean().reset_index()
    ngay_thuong = theo_gio[~theo_gio['cuoi_tuan']].set_index('gio')
    cuoi_tuan = theo_gio[theo_gio['cuoi_tuan']].set_index('gio')
    print(f'{len(kq):,} lan chup; ty le chieu dai tuyen co so do TB {kq["phu_so_do"].mean():.0%}')
    print(f'{"gio":<5}{"ket >=200m":>11}{"ket >=1km":>11}{"% ket":>8}{"% dong":>8}{"qua d.dong":>12}{"them tg":>9}{"| CT >=200m":>13}{">=1km":>7}')
    for g in range(24):
        x, y = ngay_thuong.loc[g], cuoi_tuan.loc[g]
        print(f'{g:02d}h  {x["dinh_ket"]:>10.0%}{x["dinh_ket_1km"]:>11.0%}{x["pct_ket"]:>8.1%}{x["pct_dong"]:>8.0%}'
              f'{x["qua_dong_duong"]:>12.1%}{x["them_tg"]:>9.0%}{y["dinh_ket"]:>13.0%}{y["dinh_ket_1km"]:>7.0%}')
    gio_cao = kq[(~kq['cuoi_tuan']) & (kq['gio'].isin([7, 8, 17, 18]))]
    gio_nay = kq[(~kq['cuoi_tuan']) & (kq['gio'].between(6, 21))]
    tom_tat = {'so_tuyen': len(tuyen), 'dai_tb_km': float(dai_tuyen.mean() / 1000), 'so_lan_chup': len(kq),
               'phu_so_do': float(kq['phu_so_do'].mean()),
               'cao_diem_7_8_17_18': {c: float(gio_cao[c].mean()) for c in cot_so},
               'ban_ngay_6_22': {c: float(gio_nay[c].mean()) for c in cot_so},
               'dem_1_4': {c: float(kq[kq['gio'].between(1, 4)][c].mean()) for c in cot_so}}
    print(json.dumps(tom_tat, ensure_ascii=False, indent=1))

    os.makedirs(RA, exist_ok=True)
    theo_gio.round(4).to_csv(os.path.join(RA, 'm9_theo_gio.csv'), index=False)
    with open(os.path.join(RA, 'm9_tom_tat.json'), 'w', encoding='utf-8') as f:
        json.dump(tom_tat, f, ensure_ascii=False, indent=1)
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.plot(ngay_thuong.index, ngay_thuong['dinh_ket'] * 100, color='#2a78d6', lw=2, label='Ngày thường')
    ax.plot(cuoi_tuan.index, cuoi_tuan['dinh_ket'] * 100, color='#eb6834', lw=2, label='Cuối tuần')
    ax.set_xlim(0, 23)
    ax.set_xticks(range(0, 24, 3))
    ax.set_ylim(0, 100)
    ax.set_xlabel('Giờ trong ngày')
    ax.set_ylabel(f'% tuyến có ≥ {NGUONG_KET_M:.0f} m kẹt nặng')
    ax.set_title(f'Tuyến ngắn nhất dính kẹt theo giờ ({len(tuyen)} tuyến giao hàng)')
    ax.grid(axis='y', color='#e4e3df', lw=0.8)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(RA, 'm9_theo_gio.png'), dpi=150)
    print(f'-> {RA} ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
