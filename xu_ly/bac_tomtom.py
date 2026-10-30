"""
Tầng bạc D4 (TomTom Flow): mỗi khung 5 phút -> mức kẹt theo CẠNH CỐ ĐỊNH của đồ thị,
gắn cờ chất lượng. Tái lập hoàn toàn từ tầng đồng (không sửa bản gốc).

Đầu vào:
  du_lieu/tomtom/tho/YYYY-MM-DD/HHMM.parquet        bộ thu ở máy (từ 29/10/2026 19:07)
  du_lieu/s3/dong/tomtom_o/YYYY-MM-DD/HHMM.zip      bộ thu AWS, kéo về bằng keo_s3.bat
                                                     (từ 29/10/2026 23:57)

Mỗi khung 5 phút giữ MỘT lần chụp: ưu tiên AWS (chạy 24/7, giờ chụp đều), thiếu thì lấy
bản ở máy. Khung có cả hai thì so hai bản với nhau — chênh lệch đó là "độ nhiễu" của
nguồn trong khoảng ~1 phút, ghi vào chat_luong_ngay để làm mốc cho mô hình.

Đầu ra:
  du_lieu/bac/tomtom_canh/YYYY-MM-DD.parquet
      khung       datetime  đầu khung 5 phút (giờ VN)
      chi_so      int32     cạnh trong du_lieu/do_thi/canh.parquet
      muc         uint8     % tốc độ đường trống (r = muc / 100)
      toc_do      UInt8     km/h (kiểu absolute, chỉ có ở lần chụp AWS từ 30/10/2026 04:11;
                            TomTom làm tròn bước 5 km/h; trống nếu không có)
      phu         uint8     % chiều dài cạnh có mẫu TomTom ĐANG MỞ (0–100, cắt ở 100); muc chỉ tính
                            từ phần này — phu = 0 nghĩa là cạnh chỉ có phần đóng, bỏ qua muc
      phu_dong    uint8     % chiều dài cạnh thuộc đoạn ĐÓNG (TomTom road_closure, ghi mức 0)
      dong_duong  bool      phu_dong > 0
      co          uint16    cờ chất lượng, bit (n-1) = Ln trong note/KE_HOACH_DU_LIEU.md
      nguon       'aws' | 'may'
  du_lieu/bac/khoang_trong.parquet      khung không có lần chụp nào (L6)
  du_lieu/bac/chat_luong_ngay.parquet   mỗi ngày: số khung, % cạnh có dữ liệu, số cờ, nhiễu hai nguồn

Cờ:
  L4  bit 3  nhảy bất thường: bộ lọc Hampel theo từng cạnh, cửa sổ 13 khung (±30 phút),
             |x − trung vị| > max(3 × 1,4826 × MAD, 15 điểm %). Ngưỡng sàn = nhiễu đo thật:
             hai bộ thu chụp cách nhau ~1 phút lệch nhau p95 = 13–14 điểm ban ngày (đo 30/10/2026,
             1,45 triệu cặp; ban đêm ~0) — dưới mức đó là dao động bình thường của nguồn (QĐ-009).
  L7  bit 6  ghép kém: phu + phu_dong < 30%.
  L8  bit 7  ngày thuộc giai đoạn bất thường (COVID, quanh Tết) theo du_lieu/bac/lich.parquet.
  (L1 không áp: TomTom kiểu relative luôn trong 0–1. L2 trùng lặp xử lý ở mức khung.)

Chạy:  python bac_tomtom.py              các ngày chưa xử lý hoặc có thêm lần chụp mới
       python bac_tomtom.py --lam-lai    xử lý lại tất cả (vd sau khi dựng lại đồ thị)
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
sys.path.insert(0, os.path.join(GOC, 'thu_thap'))

THO_MAY = os.path.join(GOC, 'du_lieu', 'tomtom', 'tho')
THO_AWS = os.path.join(GOC, 'du_lieu', 's3', 'dong', 'tomtom_o')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA = os.path.join(BAC, 'tomtom_canh')
TEP_TRANG_THAI = os.path.join(RA, '_trang_thai.json')

CO_L4, CO_L7, CO_L8 = 1 << 3, 1 << 6, 1 << 7
PHU_TOI_THIEU = 30
HAMPEL_CUA_SO, HAMPEL_K, HAMPEL_SAN = 13, 3.0, 15.0

_bo = None


def _bo_ghep():
    global _bo
    if _bo is None:
        from ghep_tomtom import BoGhep
        _bo = BoGhep.nap()
    return _bo


# ───────────── Đọc lần chụp ─────────────

def doan_tu_zip(tep, kieu='relative'):
    """
    Zip AWS -> list đoạn cùng dạng thu_tomtom.giai_o. Ô relative nằm ở gốc zip; từ
    30/10/2026 04:11 zip có thêm absolute/<x>_<y>.pbf (traffic_level = km/h).
    """
    from thu_tomtom import MUC_PHONG, giai_o
    doan = []
    with zipfile.ZipFile(tep) as z:
        for ten in z.namelist():
            thu_muc, _, goc = ten.rpartition('/')
            if goc.endswith('.pbf') and thu_muc == ('' if kieu == 'relative' else kieu):
                x, y = map(int, goc[:-4].split('_'))
                doan += giai_o(z.read(ten), x, y, MUC_PHONG)
    return doan


def doc_lan_chup(nguon, tep):
    from ghep_tomtom import doan_tu_tho
    if nguon == 'aws':
        return doan_tu_zip(tep)
    return doan_tu_tho(pd.read_parquet(tep, columns=['muc', 'phu', 'dong_duong', 'hinh_hoc']))


def ghep_mot(viec):
    """(nguon, tep) -> (bảng cạnh của lần chụp, số mét không ghép được). Chạy trong tiến trình con."""
    from ghep_tomtom import bang_canh
    nguon, tep = viec
    bo = _bo_ghep()
    cong, khong = bo.ghep(doc_lan_chup(nguon, tep))
    bang = bang_canh(cong)
    bang['toc_do'] = pd.array([pd.NA] * len(bang), dtype='UInt8')
    if nguon == 'aws':
        kmh, _ = bo.ghep(doan_tu_zip(tep, 'absolute'))
        if kmh:
            k = np.fromiter(kmh.keys(), dtype=np.int64)
            k = k[[kmh[i][1] > 0 for i in k]]                  # bỏ cạnh chỉ có phần đóng
            v = np.array([kmh[i][0] / kmh[i][1] for i in k])     # km/h trung bình theo chiều dài
            toc = pd.Series(np.clip(np.round(v), 0, 254).astype(np.uint8), index=k)
            bang['toc_do'] = pd.array(bang['chi_so'].map(toc), dtype='UInt8')
    return bang, khong


def khung_cua(tep):
    """.../YYYY-MM-DD/HHMM.ext -> đầu khung 5 phút."""
    ngay = os.path.basename(os.path.dirname(tep))
    hhmm = os.path.basename(tep).split('.')[0]
    t = dt.datetime.strptime(ngay + hhmm, '%Y-%m-%d%H%M')
    return t.replace(minute=t.minute - t.minute % 5)


def liet_ke():
    """ngày -> {khung: {'aws': tệp, 'may': tệp}}"""
    theo_ngay = {}
    for nguon, mau in (('may', os.path.join(THO_MAY, '*', '*.parquet')),
                       ('aws', os.path.join(THO_AWS, '*', '*.zip'))):
        for tep in glob.glob(mau):
            k = khung_cua(tep)
            theo_ngay.setdefault(k.date(), {}).setdefault(k, {})[nguon] = tep
    return theo_ngay


# ───────────── Cờ ─────────────

def trung_vi_truot(M, w=HAMPEL_CUA_SO, toi_thieu=5, khoi=8000):
    """
    Trung vị trượt theo trục 0, cửa sổ w đặt giữa, bỏ NaN; ít hơn toi_thieu giá trị thì NaN.
    Cho đúng kết quả pandas rolling(w, center=True, min_periods).median() (kiểm 30/10/2026)
    nhưng nhanh hơn nhiều: sắp xếp mọi cửa sổ cùng lúc (NaN tự xếp cuối) rồi lấy phần tử giữa.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    h = w // 2
    ra = np.full(M.shape, np.nan, dtype=np.float32)
    for c in range(0, M.shape[1], khoi):
        P = np.pad(M[:, c:c + khoi], ((h, h), (0, 0)), constant_values=np.nan)
        W = np.sort(sliding_window_view(P, w, axis=0), axis=2)
        n = (~np.isnan(W)).sum(axis=2)
        duoi = np.take_along_axis(W, np.maximum((n - 1) // 2, 0)[..., None], axis=2)[..., 0]
        tren = np.take_along_axis(W, (n // 2)[..., None], axis=2)[..., 0]
        m = (duoi + tren) / 2
        m[n < toi_thieu] = np.nan
        ra[:, c:c + khoi] = m
    return ra


def co_hampel(df):
    """Trả mảng bool: dòng nào là điểm nhảy bất thường theo chuỗi thời gian của cạnh đó."""
    ti, khung = pd.factorize(df['khung'], sort=True)
    ei, canh = pd.factorize(df['chi_so'], sort=True)
    M = np.full((len(khung), len(canh)), np.nan, dtype=np.float32)
    muc = df['muc'].to_numpy().astype(np.float32)
    if 'phu' in df:                                     # cạnh chỉ có phần đóng: muc vô nghĩa
        muc[df['phu'].to_numpy() == 0] = np.nan
    M[ti, ei] = muc
    lech = np.abs(M - trung_vi_truot(M))
    mad = trung_vi_truot(lech)
    with np.errstate(invalid='ignore'):
        la = lech > np.maximum(HAMPEL_K * 1.4826 * mad, HAMPEL_SAN)
    return la[ti, ei]


def ngay_bat_thuong(ngay):
    tep = os.path.join(BAC, 'lich.parquet')
    if not os.path.exists(tep):
        return False
    lich = pd.read_parquet(tep, columns=['ngay', 'giai_doan', 'quanh_tet']).set_index('ngay')
    d = pd.Timestamp(ngay)
    return d in lich.index and (lich.at[d, 'giai_doan'] != '' or bool(lich.at[d, 'quanh_tet']))


# ───────────── Xử lý một ngày ─────────────

def xu_ly_ngay(ngay, khung, ex, dai_canh):
    viec, chon, doi = [], {}, []
    for k in sorted(khung):
        c = khung[k]
        nguon = 'aws' if 'aws' in c else 'may'
        chon[k] = (nguon, c[nguon])
        viec.append((nguon, c[nguon]))
        if 'aws' in c and 'may' in c:
            doi.append(k)
            viec.append(('may', c['may']))
    kq = dict(zip(viec, ex.map(ghep_mot, viec, chunksize=4)))

    phan = []
    for k, (nguon, tep) in chon.items():
        bang, _ = kq[(nguon, tep)]
        bang = bang.copy()
        bang.insert(0, 'khung', pd.Timestamp(k))
        bang['nguon'] = nguon
        phan.append(bang)
    df = pd.concat(phan, ignore_index=True)
    dai = dai_canh[df['chi_so']]
    df['phu'] = np.minimum(100, np.round(100 * df.pop('phu_m') / dai)).astype(np.uint8)
    df['phu_dong'] = np.minimum(100, np.round(100 * df.pop('dong_m') / dai)).astype(np.uint8)
    df['co'] = np.uint16(0)
    df.loc[df['phu'].astype(int) + df['phu_dong'] < PHU_TOI_THIEU, 'co'] |= CO_L7
    df.loc[co_hampel(df), 'co'] |= CO_L4
    if ngay_bat_thuong(ngay):
        df['co'] |= CO_L8
    df['co'] = df['co'].astype(np.uint16)
    df['nguon'] = pd.Categorical(df['nguon'], categories=['aws', 'may'])
    df = df[['khung', 'chi_so', 'muc', 'toc_do', 'phu', 'phu_dong', 'dong_duong', 'co', 'nguon']].sort_values(
        ['khung', 'chi_so'], ignore_index=True)

    # Nhiễu giữa hai nguồn ở các khung có cả hai.
    lech = []
    for k in doi:
        a = kq[('aws', khung[k]['aws'])][0].set_index('chi_so')['muc'].astype(int)
        b = kq[('may', khung[k]['may'])][0].set_index('chi_so')['muc'].astype(int)
        chung = a.index.intersection(b.index)
        lech.append((len(chung) / max(len(a.index.union(b.index)), 1), (a[chung] - b[chung]).abs().mean()))
    return df, lech


def khoang_trong(tat_ca_khung):
    """Các khung 5 phút bị thiếu giữa lần chụp đầu và cuối (L6)."""
    if not tat_ca_khung:
        return pd.DataFrame(columns=['tu', 'den', 'so_khung'])
    k = pd.DatetimeIndex(sorted(tat_ca_khung))
    du = pd.date_range(k[0], k[-1], freq='5min')
    thieu = du.difference(k)
    if not len(thieu):
        return pd.DataFrame(columns=['tu', 'den', 'so_khung'])
    nhom = (pd.Series(thieu).diff() != pd.Timedelta('5min')).cumsum()
    g = pd.Series(thieu).groupby(nhom.values)
    return pd.DataFrame({'tu': g.min().values, 'den': g.max().values, 'so_khung': g.size().values})


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from ghep_tomtom import TEP_CANH
    lam_lai = '--lam-lai' in sys.argv
    os.makedirs(RA, exist_ok=True)
    trang_thai = {}
    if os.path.exists(TEP_TRANG_THAI) and not lam_lai:
        with open(TEP_TRANG_THAI, encoding='utf-8') as f:
            trang_thai = json.load(f)
    bo = _bo_ghep()
    dai_canh = pd.read_parquet(TEP_CANH, columns=['dai'])['dai'].to_numpy()
    theo_ngay = liet_ke()
    chat_luong = []
    tep_cl = os.path.join(BAC, 'chat_luong_ngay.parquet')
    cu = pd.read_parquet(tep_cl) if os.path.exists(tep_cl) and not lam_lai else None

    with ProcessPoolExecutor(max(1, min(8, (os.cpu_count() or 2) - 2))) as ex:
        for ngay in sorted(theo_ngay):
            khung = theo_ngay[ngay]
            dau_van_tay = {'so_tep': sum(len(v) for v in khung.values()), 'ma_do_thi': bo.ma_do_thi}
            if trang_thai.get(str(ngay)) == dau_van_tay:
                continue
            t0 = time.time()
            df, lech = xu_ly_ngay(ngay, khung, ex, dai_canh)
            tep = os.path.join(RA, f'{ngay}.parquet')
            df.to_parquet(tep + '.tam', index=False, compression='zstd', compression_level=9)
            os.replace(tep + '.tam', tep)
            so_khung = df['khung'].nunique()
            moi_khung = df.groupby('khung').size()
            dong = {
                'ngay': pd.Timestamp(ngay), 'so_khung': so_khung,
                'khung_aws': int(df.drop_duplicates('khung')['nguon'].eq('aws').sum()),
                'canh_tb_moi_khung': round(float(moi_khung.mean())),
                'ty_le_canh_co_du_lieu': round(float(moi_khung.mean()) / len(dai_canh), 4),
                'ty_le_L4': round(float(((df['co'] & CO_L4) > 0).mean()), 5),
                'ty_le_L7': round(float(((df['co'] & CO_L7) > 0).mean()), 4),
                'khung_ca_hai_nguon': len(lech),
                'trung_canh_hai_nguon': round(float(np.mean([a for a, _ in lech])), 4) if lech else None,
                'lech_muc_tb_hai_nguon': round(float(np.mean([b for _, b in lech])), 2) if lech else None,
                'ma_do_thi': bo.ma_do_thi,
            }
            chat_luong.append(dong)
            trang_thai[str(ngay)] = dau_van_tay
            print(f'{ngay}: {so_khung} khung ({dong["khung_aws"]} AWS), {len(df):,} dong, '
                  f'{os.path.getsize(tep) / 1e6:.1f} MB, L4 {dong["ty_le_L4"]:.2%}, L7 {dong["ty_le_L7"]:.1%}, '
                  f'{time.time() - t0:.0f}s')

    with open(TEP_TRANG_THAI, 'w', encoding='utf-8') as f:
        json.dump(trang_thai, f, ensure_ascii=False, indent=1)
    if chat_luong:
        moi = pd.DataFrame(chat_luong)
        if cu is not None:
            moi = pd.concat([cu[~cu['ngay'].isin(moi['ngay'])], moi], ignore_index=True)
        moi.sort_values('ngay').to_parquet(tep_cl, index=False)
    kt = khoang_trong([k for v in theo_ngay.values() for k in v])
    kt.to_parquet(os.path.join(BAC, 'khoang_trong.parquet'), index=False)
    print(f'Khoang trong (L6): {len(kt)} doan, {int(kt["so_khung"].sum()) if len(kt) else 0} khung thieu')
    if len(kt):
        print(kt.sort_values('so_khung', ascending=False).head(5).to_string(index=False))


if __name__ == '__main__':
    main()
