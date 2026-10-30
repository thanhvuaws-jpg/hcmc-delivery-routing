"""
Tầng vàng: bảng huấn luyện mô hình dự báo kẹt xe — mỗi dòng = (đoạn đường, khung 15 phút).

Đơn vị không gian: ĐOẠN (xu_ly/doan_duong.py), chỉ những đoạn từng có dữ liệu TomTom.
Đơn vị thời gian: khung 15 phút (KE_HOACH_DU_LIEU mục 3.2). Thời điểm t = ĐẦU khung.

Đặc trưng (chỉ dùng thông tin có được trước hoặc tại khung t — chống rò rỉ, mục 8):
  r            tỉ lệ tốc độ/đường trống của khung t (TB các lần chụp 5 phút, trọng số dài × phủ,
               chỉ phần đường đang MỞ — đường đóng TomTom ghi 0, không phải kẹt)
  kmh          km/h (TomTom absolute, có từ 30/10/2026 04:11)
  n_chup       số lần chụp có dữ liệu trong khung (0–3)
  r_tru_1/2/4  r ở t−15, −30, −60 phút;  r_tb_1h, r_sd_1h: TB / độ lệch 4 khung gần nhất
  r_hom_qua, r_tuan_truoc   r cùng khung hôm qua / tuần trước
  r_thuong, r_ha            TB r các đoạn ngay trước (đổ vào) / ngay sau (nhận từ) đoạn này
  ty_le_dong   phần chiều dài đoạn đang ĐÓNG (TomTom road_closure; phần đó không tính vào r)
  su_co, tre_su_co_s           số sự cố đang ghi trên đoạn / tổng độ trễ (s)
  gio_sin/cos, thu_sin/cos, cuoi_tuan, nghi, di_hoc, quanh_tet
  mua_db_0, mua_db_1, kn_mua_db_1  mưa DỰ BÁO (mm) cho giờ của t và giờ kế, xác suất mưa giờ kế —
                                   lấy bản phát hành gần nhất TRƯỚC t (không dùng mưa thật)
  tĩnh: loai, dai, so_lan, trung_gian, poi_*, de_ngap_mua, de_ngap_trieu
Nhãn: y_15, y_30, y_60 = r ở t+15, t+30, t+60 phút (NaN nếu khung đó không có dữ liệu).

Đầu ra: du_lieu/vang/YYYY-MM-DD.parquet (+ _mo_ta.json: danh sách cột, ngày, mã đồ thị).
Chạy:  python vang.py
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA = os.path.join(GOC, 'du_lieu', 'vang')
K = 96                          # số khung 15 phút một ngày


def tb_trong_so(gt, ts):
    """Trung bình có trọng số theo cột, bỏ NaN (gt, ts cùng hình)."""
    m = ~np.isnan(gt)
    tu = np.where(m, gt * ts, 0).sum(axis=0)
    mau = np.where(m, ts, 0).sum(axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(mau > 0, tu / mau, np.nan)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    doan = pd.read_parquet(os.path.join(BAC, 'doan.parquet'))
    cd = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))
    tinh = pd.read_parquet(os.path.join(BAC, 'canh_tinh.parquet'))
    dai_canh = tinh['dai'].to_numpy()
    doan_cua = cd['doan'].to_numpy()

    # ── Silver TomTom -> (khung 5 phút, đoạn): TB theo dài × phủ ──
    phan = []
    for tep in sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet'))):
        s = pd.read_parquet(tep, columns=['khung', 'chi_so', 'muc', 'toc_do', 'phu', 'dong_duong'])
        w_tong = dai_canh[s['chi_so']] * s['phu'].to_numpy() / 100
        dong = s['dong_duong'].to_numpy()
        # Cạnh đang ĐÓNG: TomTom trả mức 0 (đo 30/10: 100% ô mức 0 ở đoạn có road_closure).
        # Đóng đường không phải kẹt xe -> không tính vào r; ghi riêng tỉ lệ chiều dài bị đóng.
        w = w_tong * ~dong
        s = pd.DataFrame({'khung': s['khung'], 'doan': doan_cua[s['chi_so']], 'w': w, 'w_tong': w_tong,
                          'w_dong': w_tong * dong,
                          'rw': s['muc'].to_numpy() / 100 * w,
                          'kw': s['toc_do'].astype('float64').fillna(0).to_numpy() * w,
                          'kmask': w * s['toc_do'].notna().to_numpy()})
        g = s.groupby(['khung', 'doan'], sort=False).agg(w=('w', 'sum'), w_tong=('w_tong', 'sum'),
                                                        w_dong=('w_dong', 'sum'), rw=('rw', 'sum'),
                                                        kw=('kw', 'sum'), km=('kmask', 'sum'))
        phan.append(g.reset_index())
    g = pd.concat(phan, ignore_index=True)
    g = g[g['w_tong'] > 0]
    g['ty_le_dong'] = g['w_dong'] / g['w_tong']
    g['r'] = np.where(g['w'] > 0, g['rw'] / g['w'].where(g['w'] > 0), np.nan)
    g['kmh'] = np.where(g['km'] > 0, g['kw'] / g['km'].where(g['km'] > 0), np.nan)
    co_du_lieu = np.sort(g['doan'].unique())
    N = len(co_du_lieu)
    vi_tri = pd.Series(np.arange(N), index=co_du_lieu)

    ngay0 = g['khung'].min().normalize()
    ngay1 = g['khung'].max().normalize()
    so_ngay = (ngay1 - ngay0).days + 1
    T = so_ngay * K
    moc = pd.date_range(ngay0, periods=T, freq='15min')
    ti = ((g['khung'] - ngay0) // pd.Timedelta('15min')).to_numpy()
    ni = vi_tri[g['doan']].to_numpy()

    # ── Ma trận (khung 15 phút × đoạn): TB các lần chụp 5 phút trong khung ──
    def ma_tran(gt, khong_co=np.nan):
        tong = np.zeros((T, N)); dem = np.zeros((T, N))
        np.add.at(tong, (ti, ni), np.nan_to_num(gt))
        np.add.at(dem, (ti, ni), ~np.isnan(gt))
        with np.errstate(invalid='ignore'):
            return np.where(dem > 0, tong / np.maximum(dem, 1), khong_co).astype(np.float32), dem
    R, n_chup = ma_tran(g['r'].to_numpy())
    KMH, _ = ma_tran(g['kmh'].to_numpy())
    DONG, _ = ma_tran(g['ty_le_dong'].to_numpy())
    DONG = np.nan_to_num(DONG)

    def lui(M, k):
        """M dời k khung về quá khứ (giá trị ở t là M[t-k])."""
        out = np.full_like(M, np.nan)
        out[k:] = M[:-k]
        return out

    def toi(M, k):
        out = np.full_like(M, np.nan)
        out[:-k] = M[k:]
        return out

    with np.errstate(invalid='ignore'):
        cua_so = np.stack([R, lui(R, 1), lui(R, 2), lui(R, 3)])
        r_tb = np.nanmean(cua_so, axis=0)
        r_sd = np.nanstd(cua_so, axis=0)

    # ── Lân cận: đoạn đổ vào (thượng nguồn) và đoạn nhận (hạ nguồn) ──
    d = doan.set_index('doan').loc[co_du_lieu]
    ra_tu = pd.Series(np.arange(N), index=d['u_dau'].to_numpy())     # đoạn bắt đầu ở nút x
    vao_toi = pd.Series(np.arange(N), index=d['v_cuoi'].to_numpy())  # đoạn kết thúc ở nút x
    up = [(i, j) for i, u in enumerate(d['u_dau']) if u in vao_toi.index
          for j in np.atleast_1d(vao_toi.loc[u]) if j != i]
    dn = [(i, j) for i, v in enumerate(d['v_cuoi']) if v in ra_tu.index
          for j in np.atleast_1d(ra_tu.loc[v]) if j != i]

    def tb_lan_can(cap):
        if not cap:
            return np.full((T, N), np.nan, dtype=np.float32)
        a, b = np.array(cap).T
        A = sp.csr_matrix((np.ones(len(a)), (a, b)), shape=(N, N))
        m = ~np.isnan(R)
        tu = (A @ np.nan_to_num(R).T).T
        mau = (A @ m.T.astype(float)).T
        with np.errstate(invalid='ignore'):
            return np.where(mau > 0, tu / np.maximum(mau, 1), np.nan).astype(np.float32)
    R_UP, R_DN = tb_lan_can(up), tb_lan_can(dn)

    # ── Sự cố đang ghi trên đoạn ──
    SU_CO = np.zeros((T, N), dtype=np.float32); TRE = np.zeros((T, N), dtype=np.float32)
    sc = pd.read_parquet(os.path.join(BAC, 'su_co.parquet'), columns=['id', 'canh'])
    sc_doan = sc.explode('canh').dropna()
    sc_doan['doan'] = doan_cua[sc_doan['canh'].astype(int)]
    sc_doan = sc_doan[sc_doan['doan'].isin(co_du_lieu)].drop_duplicates(['id', 'doan'])
    kh = pd.concat([pd.read_parquet(t, columns=['khung', 'id', 'tre_s'])
                    for t in glob.glob(os.path.join(BAC, 'su_co_khung', '*.parquet'))])
    kh = kh.merge(sc_doan[['id', 'doan']], on='id')
    kh['t'] = (kh['khung'] - ngay0) // pd.Timedelta('15min')
    kh = kh[(kh['t'] >= 0) & (kh['t'] < T)]
    kh = kh.groupby(['t', 'doan']).agg(so=('id', 'nunique'), tre=('tre_s', 'max')).reset_index()
    SU_CO[kh['t'], vi_tri[kh['doan']]] = kh['so']
    TRE[kh['t'], vi_tri[kh['doan']]] = kh['tre'].fillna(0)

    # ── Tĩnh theo đoạn ──
    tinh['doan'] = doan_cua
    t_doan = tinh[tinh['doan'].isin(co_du_lieu)].groupby('doan').agg(
        so_lan=('so_lan', 'max'), trung_gian=('trung_gian', 'max'),
        **{c: (c, 'max') for c in tinh.columns if c.startswith('poi_')},
        diem_thoi_tiet=('diem_thoi_tiet', 'first')).loc[co_du_lieu]
    ngap = pd.read_parquet(os.path.join(BAC, 'ngap_canh.parquet'))
    ngap['doan'] = doan_cua[ngap['chi_so']]
    de_mua = np.isin(co_du_lieu, ngap.loc[ngap['nguyen_nhan'] == 'mua', 'doan'])
    de_trieu = np.isin(co_du_lieu, ngap.loc[ngap['nguyen_nhan'] == 'trieu_cuong', 'doan'])

    # ── Thời tiết DỰ BÁO: bản phát hành gần nhất trước t, theo điểm thời tiết của đoạn ──
    db = pd.read_parquet(os.path.join(BAC, 'thoi_tiet_du_bao.parquet'),
                         columns=['phat_hanh', 'diem', 'thoi_gian', 'precipitation', 'precipitation_probability'])
    diem_ten = list(t_doan['diem_thoi_tiet'].cat.categories)
    MUA = np.full((T, len(diem_ten), 2), np.nan, dtype=np.float32)
    KN = np.full((T, len(diem_ten)), np.nan, dtype=np.float32)
    gio_t = moc.floor('h')
    for k, ten in enumerate(diem_ten):
        x = db[db['diem'] == ten]
        for lech in (0, 1):
            muc_tieu = pd.DataFrame({'t': moc, 'gio': gio_t + pd.Timedelta(hours=lech)})
            y = x.rename(columns={'thoi_gian': 'gio'}).sort_values('phat_hanh')
            # Với mỗi (t, giờ đích): bản có phat_hanh <= t, mới nhất.
            m = pd.merge_asof(muc_tieu.sort_values('t'), y, left_on='t', right_on='phat_hanh', by='gio',
                              direction='backward')
            m = m.sort_values('t')
            MUA[:, k, lech] = m['precipitation'].to_numpy()
            if lech == 1:
                KN[:, k] = m['precipitation_probability'].to_numpy()
    di = t_doan['diem_thoi_tiet'].cat.codes.to_numpy()

    # ── Lịch ──
    lich = pd.read_parquet(os.path.join(BAC, 'lich.parquet')).set_index('ngay')
    l = lich.loc[moc.normalize()]
    gio = (moc.hour + moc.minute / 60).to_numpy()
    thu = moc.dayofweek.to_numpy()

    os.makedirs(RA, exist_ok=True)
    cot = None
    for nd in range(so_ngay):
        a, b = nd * K, (nd + 1) * K
        sl = slice(a, b)
        ngay = moc[a].date()
        cot_doc = {
            'khung': np.repeat(moc[sl].to_numpy(), N), 'doan': np.tile(co_du_lieu, K).astype(np.int32),
            'r': R[sl].ravel(), 'kmh': KMH[sl].ravel(), 'n_chup': n_chup[sl].ravel().astype(np.uint8),
            'r_tru_1': lui(R, 1)[sl].ravel(), 'r_tru_2': lui(R, 2)[sl].ravel(), 'r_tru_4': lui(R, 4)[sl].ravel(),
            'r_tb_1h': r_tb[sl].ravel(), 'r_sd_1h': r_sd[sl].ravel(),
            'r_hom_qua': lui(R, K)[sl].ravel() if T > K else np.full((b - a) * N, np.nan, np.float32),
            'r_tuan_truoc': lui(R, 7 * K)[sl].ravel() if T > 7 * K else np.full((b - a) * N, np.nan, np.float32),
            'r_thuong': R_UP[sl].ravel(), 'r_ha': R_DN[sl].ravel(),
            'ty_le_dong': DONG[sl].ravel(), 'su_co': SU_CO[sl].ravel(), 'tre_su_co_s': TRE[sl].ravel(),
            'gio_sin': np.repeat(np.sin(2 * np.pi * gio[sl] / 24), N).astype(np.float32),
            'gio_cos': np.repeat(np.cos(2 * np.pi * gio[sl] / 24), N).astype(np.float32),
            'thu_sin': np.repeat(np.sin(2 * np.pi * thu[sl] / 7), N).astype(np.float32),
            'thu_cos': np.repeat(np.cos(2 * np.pi * thu[sl] / 7), N).astype(np.float32),
            'cuoi_tuan': np.repeat(l['cuoi_tuan'].to_numpy()[sl], N),
            'nghi': np.repeat(l['nghi'].to_numpy()[sl], N),
            'di_hoc': np.repeat(l['di_hoc'].to_numpy()[sl], N),
            'quanh_tet': np.repeat(l['quanh_tet'].to_numpy()[sl], N),
            'mua_db_0': MUA[sl][:, di, 0].ravel(), 'mua_db_1': MUA[sl][:, di, 1].ravel(),
            'kn_mua_db_1': KN[sl][:, di].ravel(),
            'loai': np.tile(d['loai'].to_numpy(), K), 'dai': np.tile(d['dai'].to_numpy(), K).astype(np.float32),
            'so_lan': np.tile(t_doan['so_lan'].to_numpy(), K).astype(np.float32),
            'trung_gian': np.tile(t_doan['trung_gian'].to_numpy(), K).astype(np.float32),
            **{c: np.tile(t_doan[c].to_numpy(), K) for c in t_doan.columns if c.startswith('poi_')},
            'de_ngap_mua': np.tile(de_mua, K), 'de_ngap_trieu': np.tile(de_trieu, K),
            'y_15': toi(R, 1)[sl].ravel(), 'y_30': toi(R, 2)[sl].ravel(), 'y_60': toi(R, 4)[sl].ravel(),
        }
        df = pd.DataFrame(cot_doc)
        df = df[(df['n_chup'] > 0) | df['y_15'].notna()]       # bỏ dòng hoàn toàn trống
        for c in df.columns:
            if df[c].dtype == np.float64:
                df[c] = df[c].astype(np.float32)
        df['loai'] = df['loai'].astype('category')
        df.to_parquet(os.path.join(RA, f'{ngay}.parquet'), index=False, compression='zstd')
        cot = list(df.columns)
        print(f'{ngay}: {len(df):,} dong, {df["doan"].nunique():,} doan, '
              f'co y_15 {df["y_15"].notna().mean():.1%}, co kmh {df["kmh"].notna().mean():.1%}')

    with open(os.path.join(RA, '_mo_ta.json'), 'w', encoding='utf-8') as f:
        json.dump({'cot': cot, 'so_doan': int(N), 'tu': str(ngay0.date()), 'den': str(ngay1.date()),
                   'ma_do_thi': str(pd.read_parquet(os.path.join(BAC, 'su_co.parquet'), columns=['ma_do_thi'])
                                    ['ma_do_thi'].iloc[0]),
                   'tao_luc': time.strftime('%Y-%m-%d %H:%M:%S')}, f, ensure_ascii=False, indent=1)
    print(f'{N:,} doan co du lieu, {so_ngay} ngay, {len(cot)} cot, {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
