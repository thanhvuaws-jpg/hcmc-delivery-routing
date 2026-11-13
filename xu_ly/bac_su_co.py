"""
Tầng bạc D10 (TomTom Incidents): gộp các lần chụp sự cố thành
  (1) sự cố theo khung 5 phút  — dùng làm đặc trưng "đang có sự cố gì, trễ bao nhiêu"
  (2) bảng sự cố duy nhất      — mỗi mã sự cố một dòng: thấy lần đầu/cuối, kéo dài bao lâu,
                                  trễ lớn nhất, và các CẠNH đồ thị nó nằm trên.

Đầu vào (tầng đồng):
  du_lieu/tomtom/su_co/YYYY-MM-DD/HHMM.parquet          bộ thu ở máy
  du_lieu/s3/dong/tomtom_su_co/YYYY-MM-DD/HHMM.json.gz  bộ thu AWS (JSON gốc)
Mỗi khung 5 phút giữ một lần chụp, ưu tiên AWS (như bac_tomtom.py).

Đầu ra:
  du_lieu/bac/su_co_khung/YYYY-MM-DD.parquet
      khung, id, hinh_ma (uint64: hình học CỦA LẦN GHI ĐÓ), loai (uint8), muc_tre (uint8), tre_s,
      dai_m (float32), chac_chan (bool), nguon
  du_lieu/bac/su_co_hinh.parquet
      hinh_ma, canh, canh_m, ty_le_ghep, ma_do_thi — mỗi hình học khác nhau ghép vào cạnh một lần.
      Tầng vàng gán sự cố vào đoạn theo bảng này (QĐ-029 mục 5: trước 13/11 dùng hình dài nhất cả đời sự cố
      cho mọi khung = biết trước hàng kẹt sẽ lan tới đâu).
  du_lieu/bac/su_co.parquet
      id, ten_loai, tu, den, mo_ta, lan_dau, lan_cuoi, so_khung, tre_s_max, dai_m_max,
      muc_tre_max, bat_dau, ket_thuc (giờ VN, từ TomTom), canh (list chỉ số cạnh),
      canh_m (mét trùng trên từng cạnh), ty_le_ghep, hinh_hoc (lần dài nhất, [lon, lat]) — chỉ để MÔ TẢ /
      thống kê, không dùng làm đặc trưng theo khung
  du_lieu/bac/su_co_lan_chup.parquet
      khung, nguon — mọi lần chụp sự cố đã có, kể cả lần trống (để biết khung nào THIẾU dữ liệu)

Ghép sự cố vào cạnh: dùng chính BoGhep của dữ liệu kẹt xe, theo ĐÚNG chiều hình học
(sự cố kẹt xe vẽ theo chiều xe chạy; đường đóng hai chiều thì TomTom ghi hai sự cố).

Chạy:  python bac_su_co.py
"""
import glob
import gzip
import json
import os
import sys
import time

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
sys.path.insert(0, os.path.join(GOC, 'thu_thap'))

from bac_tomtom import khung_cua  # noqa: E402

SU_CO_MAY = os.path.join(GOC, 'du_lieu', 'tomtom', 'su_co')
SU_CO_AWS = os.path.join(GOC, 'du_lieu', 's3', 'dong', 'tomtom_su_co')
BAC = os.path.join(GOC, 'du_lieu', 'bac')
RA_KHUNG = os.path.join(BAC, 'su_co_khung')
TEP_HINH = os.path.join(BAC, 'su_co_hinh.parquet')


def ma_hinh(chuoi):
    """Mã 64 bit của chuỗi hình học (giống nhau -> cùng mã); 0 = không có hình."""
    s = pd.Series(chuoi).fillna('')
    ma = pd.util.hash_pandas_object(s, index=False).to_numpy().astype(np.uint64)
    ma[s.to_numpy() == ''] = 0
    return ma


def ghep_hinh(bo, hh):
    """Hình học (chuỗi JSON [[lon, lat], ...]) -> (cạnh, mét trùng từng cạnh, tỉ lệ ghép được)."""
    toa_do = json.loads(hh) if isinstance(hh, str) and hh else None
    if not toa_do or not isinstance(toa_do[0], list) or len(toa_do) < 2:
        return [], [], 0.0
    cong, khong = bo.ghep([{'diem': [(b, a) for a, b in toa_do],
                            'tt': {'traffic_level': 1.0, 'traffic_road_coverage': 'one_side'}}])
    c = sorted(cong)
    da = sum(v[1] for v in cong.values())
    return np.array(c, dtype=np.int32).tolist(), [round(cong[i][1]) for i in c], round(da / max(da + khong, 1), 3)


def doc(nguon, tep):
    if nguon == 'may':
        return pd.read_parquet(tep)
    from thu_tomtom import bang_su_co
    with gzip.open(tep, 'rt', encoding='utf-8') as f:
        goi = json.load(f)
    luc = pd.Timestamp(goi['thoi_diem']).tz_localize(None).to_pydatetime()
    return bang_su_co(luc, goi['tra_ve'].get('incidents', []))


def gio_vn(chuoi):
    """'2026-10-29T11:39:00Z' -> giờ VN không múi giờ (NaT nếu trống)."""
    t = pd.to_datetime(chuoi, utc=True, errors='coerce')
    return t.dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from ghep_tomtom import BoGhep
    khung = {}
    for nguon, mau in (('may', os.path.join(SU_CO_MAY, '*', '*.parquet')),
                       ('aws', os.path.join(SU_CO_AWS, '*', '*.json.gz'))):
        for tep in glob.glob(mau):
            khung.setdefault(khung_cua(tep), {})[nguon] = tep

    # Danh sách lần chụp ĐÃ CÓ, kể cả lần không có sự cố nào: tầng vàng cần biết khung nào thiếu hẳn lần chụp
    # để ghi NaN thay vì 0 (09/11 23:26 → 11/11 16:56 TomTom từ chối vì hết credit, NHAT_KY 11/11).
    os.makedirs(BAC, exist_ok=True)
    pd.DataFrame({'khung': pd.to_datetime(sorted(khung)),
                  'nguon': ['aws' if 'aws' in khung[k] else 'may' for k in sorted(khung)]}
                 ).to_parquet(os.path.join(BAC, 'su_co_lan_chup.parquet'), index=False)

    phan = []
    for k in sorted(khung):
        nguon = 'aws' if 'aws' in khung[k] else 'may'
        df = doc(nguon, khung[k][nguon])
        df.insert(0, 'khung', pd.Timestamp(k))
        df['nguon'] = nguon
        phan.append(df)
    tat_ca = pd.concat(phan, ignore_index=True)
    print(f'{len(khung)} khung, {len(tat_ca):,} dong su co, {tat_ca["id"].nunique()} ma su co')

    # (1) Theo khung, chia tệp theo ngày. hinh_ma = hình học CỦA ĐÚNG LẦN GHI ĐÓ (QĐ-029 mục 5): tầng vàng gán sự cố vào
    # đoạn theo hình của từng lần ghi, không theo hình dài nhất cả đời sự cố (hàng kẹt về sau mới dài ra = thông tin
    # tương lai). Hình giống nhau chỉ ghép một lần: su_co_hinh.parquet (hinh_ma -> cạnh).
    tat_ca['hinh_ma'] = ma_hinh(tat_ca['hinh_hoc'])
    gon = pd.DataFrame({
        'khung': tat_ca['khung'], 'id': tat_ca['id'], 'hinh_ma': tat_ca['hinh_ma'],
        'loai': tat_ca['loai'].astype('uint8'), 'muc_tre': tat_ca['muc_tre'].fillna(0).astype('uint8'),
        'tre_s': tat_ca['tre_s'].astype('float32'), 'dai_m': tat_ca['dai_m'].astype('float32'),
        'chac_chan': tat_ca['kha_nang'].eq('certain'),
        'nguon': pd.Categorical(tat_ca['nguon'], categories=['aws', 'may']),
    })
    os.makedirs(RA_KHUNG, exist_ok=True)
    for ngay, g in gon.groupby(gon['khung'].dt.date):
        g.sort_values(['khung', 'id']).to_parquet(os.path.join(RA_KHUNG, f'{ngay}.parquet'), index=False)

    # (2) Mỗi mã sự cố một dòng.
    tat_ca['bat_dau_vn'] = gio_vn(tat_ca['bat_dau'])
    tat_ca['ket_thuc_vn'] = gio_vn(tat_ca['ket_thuc'])
    g = tat_ca.sort_values('khung').groupby('id')
    bang = g.agg(ten_loai=('ten_loai', 'last'), tu=('tu', 'last'), den=('den', 'last'), mo_ta=('mo_ta', 'last'),
                 lan_dau=('khung', 'min'), lan_cuoi=('khung', 'max'), so_khung=('khung', 'nunique'),
                 tre_s_max=('tre_s', 'max'), dai_m_max=('dai_m', 'max'), muc_tre_max=('muc_tre', 'max'),
                 bat_dau=('bat_dau_vn', 'min'), ket_thuc=('ket_thuc_vn', 'last'))
    dai_nhat = tat_ca.loc[tat_ca.groupby('id')['dai_m'].idxmax().dropna().astype(int)]
    bang['hinh_hoc'] = dai_nhat.set_index('id')['hinh_hoc']

    bo = BoGhep.nap()
    # Mỗi hình học khác nhau ghép một lần (dùng cho cả bảng theo khung lẫn bảng mỗi sự cố).
    hinh = tat_ca.loc[tat_ca['hinh_ma'] != 0, ['hinh_ma', 'hinh_hoc']].drop_duplicates('hinh_ma')
    t_ghep = time.time()
    ket = [ghep_hinh(bo, hh) for hh in hinh['hinh_hoc']]
    hinh = pd.DataFrame({'hinh_ma': hinh['hinh_ma'].to_numpy(), 'canh': [k[0] for k in ket],
                         'canh_m': [k[1] for k in ket], 'ty_le_ghep': [k[2] for k in ket]})
    hinh['ma_do_thi'] = bo.ma_do_thi
    hinh.to_parquet(TEP_HINH, index=False)
    print(f'{len(hinh):,} hinh hoc khac nhau, ghep {time.time() - t_ghep:.0f}s -> {TEP_HINH}')
    # Bảng mỗi sự cố: hình DÀI NHẤT, chỉ để mô tả / thống kê — KHÔNG dùng làm đặc trưng theo khung.
    theo_ma = hinh.set_index('hinh_ma')
    ma_dai = ma_hinh(bang['hinh_hoc'])
    bang['canh'] = [theo_ma.at[m, 'canh'] if m in theo_ma.index else [] for m in ma_dai]
    bang['canh_m'] = [theo_ma.at[m, 'canh_m'] if m in theo_ma.index else [] for m in ma_dai]
    bang['ty_le_ghep'] = [float(theo_ma.at[m, 'ty_le_ghep']) if m in theo_ma.index else 0.0 for m in ma_dai]
    bang = bang.reset_index()
    bang['ma_do_thi'] = bo.ma_do_thi
    bang.to_parquet(os.path.join(BAC, 'su_co.parquet'), index=False)

    bang['keo_dai_phut'] = (bang['lan_cuoi'] - bang['lan_dau']).dt.total_seconds() / 60 + 5
    print(bang.groupby('ten_loai').agg(so=('id', 'size'), keo_dai_tb_phut=('keo_dai_phut', 'mean'),
                                       tre_tb_s=('tre_s_max', 'mean'), ghep_tb=('ty_le_ghep', 'mean'),
                                       canh_tb=('canh', lambda s: np.mean([len(x) for x in s]))).round(2).to_string())


if __name__ == '__main__':
    main()
