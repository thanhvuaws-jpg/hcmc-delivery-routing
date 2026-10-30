"""
Thu mức kẹt xe thật từ TomTom Traffic Flow (gói Evaluation miễn phí, không cần thẻ).

Hai loại lời gọi:
  - Ô giao thông dạng vector (Vector Flow Tiles): MỘT ô chứa mức kẹt của MỌI
    con đường TomTom có dữ liệu trong ô đó. Hạn mức miễn phí 50.000 ô/ngày.
    Khu trung tâm ở mức phóng 14 cần 30 ô cho một lần chụp.
  - Flow Segment Data: tốc độ hiện tại + tốc độ đường trống (km/h) của đúng một
    đoạn đường tại một điểm. Hạn mức 2.500 lượt/ngày — chỉ dùng để kiểm chứng.

  - Traffic Incident Details v5: sự cố đang diễn ra (tai nạn, công trình, đóng đường,
    ngập, kẹt xe…) trong khu vực — 1 lượt/lần gọi.

Chạy:
  python thu_tomtom.py thu-thu        chụp MỘT lần, in độ phủ + thuộc tính TomTom trả về
  python thu_dinh_ky.py               chụp + lưu (bộ hẹn giờ Windows gọi tệp đó 5 phút/lần)

Lưu (du_lieu/tomtom/):
  tho/YYYY-MM-DD/HHMM.parquet         bản thô mỗi lần chụp (kèm hình học)
  canh/YYYY-MM-DD/HHMM.parquet        mức kẹt theo cạnh cố định của đồ thị xe máy
  su_co/YYYY-MM-DD/HHMM.parquet       mỗi lần chụp: các sự cố đang diễn ra
  (chup/ + doan.parquet: định dạng cũ theo mã băm, chỉ có vài lượt tối 29/10/2026)

Khóa API đọc từ thuctaptotnghiep/.env (TOMTOM_KEY=...). Không in khóa ra màn hình.
"""
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter

import requests

import mvt

GOC =os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
THU_MUC = os.path.join(GOC, 'du_lieu', 'tomtom')
KHU_VUC = (10.74, 106.62, 10.83, 106.73)      # nam, tây, bắc, đông — trùng tai_osm.py
MUC_PHONG = 14
KIEU = 'relative'          # mức kẹt = tốc độ hiện tại / tốc độ đường trống (0..1)

O_GIAO_THONG = 'https://api.tomtom.com/traffic/map/4/tile/flow/{kieu}/{z}/{x}/{y}.pbf'
DOAN_DUONG = 'https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json'


def doc_khoa():
    tep = os.path.join(GOC, '.env')
    if os.path.exists(tep):
        with open(tep, encoding='utf-8') as f:
            for dong in f:
                if dong.strip().startswith('TOMTOM_KEY='):
                    k = dong.split('=', 1)[1].strip().strip('"').strip("'")
                    if k:
                        return k
    k = os.environ.get('TOMTOM_KEY', '').strip()
    if not k:
        sys.exit('Chua co TOMTOM_KEY trong thuctaptotnghiep/.env')
    return k


def o_cua_khu_vuc(nam, tay, bac, dong, z):
    def xy(lat, lon):
        n = 2 ** z
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        return x, y
    x0, y0 = xy(bac, tay)
    x1, y1 = xy(nam, dong)
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def toa_do_that(x, y, z, px, py, extent):
    """Toạ độ trong ô (0..extent) -> (vĩ độ, kinh độ)."""
    n = 2 ** z
    lon = (x + px / extent) / n * 360 - 180
    t = math.pi * (1 - 2 * (y + py / extent) / n)
    return math.degrees(math.atan(math.sinh(t))), lon


def giai_o(noi_dung, x, y, z):
    # Toạ độ MVT tính từ góc TRÊN-trái của ô, khớp với công thức ở toa_do_that.
    du_lieu = mvt.giai(noi_dung)
    ra = []
    for ten_lop, lop in du_lieu.items():
        extent = lop.get('extent', 4096)
        for f in lop['features']:
            if f['type'] != 2:          # chỉ lấy đường (LineString)
                continue
            for net in f['lines']:
                if len(net) < 2:
                    continue
                diem = [toa_do_that(x, y, z, px, py, extent) for px, py in net]
                # Mã đoạn = băm hình học (làm tròn ~1 m): cùng con đường ở các lần
                # chụp khác nhau ra cùng mã, nên chỉ cần lưu hình học một lần.
                ma = hashlib.md5(json.dumps([(round(a, 5), round(b, 5)) for a, b in diem]).encode()).hexdigest()[:16]
                ra.append({'lop': ten_lop, 'ma': ma, 'diem': diem, 'tt': dict(f['properties'])})
    return ra


def che_khoa(s, khoa):
    """Lỗi của requests có thể chứa nguyên URL kèm key — che trước khi in/ghi nhật ký."""
    return str(s).replace(khoa, '***') if khoa else str(s)


def gio_vn():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).replace(microsecond=0)


def chup(khoa, in_chi_tiet=False):
    o = o_cua_khu_vuc(*KHU_VUC, MUC_PHONG)
    luc = gio_vn()
    tat_ca, loi, chi_tiet_loi = [], 0, []
    for x, y in o:
        url = O_GIAO_THONG.format(kieu=KIEU, z=MUC_PHONG, x=x, y=y)
        try:
            r = requests.get(url, params={'key': khoa}, timeout=30)
            if r.status_code != 200:
                loi += 1
                chi_tiet_loi.append(f'o {x},{y}: HTTP {r.status_code} {che_khoa(r.text[:120], khoa)}')
                continue
            tat_ca += giai_o(r.content, x, y, MUC_PHONG)
        except requests.RequestException as e:
            loi += 1
            chi_tiet_loi.append(f'o {x},{y}: {che_khoa(e, khoa)}')
    if in_chi_tiet:
        for d in chi_tiet_loi:
            print('  ' + d)
    return luc, o, tat_ca, loi, chi_tiet_loi


def _luu_parquet(df, tep):
    """
    Ghi ra tệp tạm rồi đổi tên: máy tắt giữa chừng không để lại tệp hỏng.
    zstd mức 19: một lượt (thô + cạnh) ~240 KB thay vì ~480 KB của snappy mặc định
    → ~70 MB/ngày, ~6,3 GB cho 3 tháng (đo 29/10/2026).
    """
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    tam = tep + '.tam'
    df.to_parquet(tam, index=False, compression='zstd', compression_level=19)
    os.replace(tam, tep)


def luu_chup(luc, doan):
    """
    tho/YYYY-MM-DD/HHMM.parquet  : bản thô TomTom (mức, loại đường, phủ, đóng đường, hình học)
                                   — để ghép lại được nếu sau này sửa đồ thị/cách ghép
    canh/YYYY-MM-DD/HHMM.parquet : mức kẹt theo CẠNH CỐ ĐỊNH của đồ thị xe máy
                                   (chi_so, muc % phần mở, phu_m, dong_m, dong_duong) — dùng cho mô hình

    Vì sao không lưu theo "mã đoạn TomTom": TomTom cắt đoạn theo chỗ mức kẹt thay đổi,
    nên cùng con đường có hình học khác nhau giữa các lần chụp (28% đoạn đổi sau 5 phút,
    đo 29/10/2026). Xem dinh_tuyen/ghep_tomtom.py.

    Mỗi lần chụp một tệp nhỏ thay vì ghi nối vào một tệp lớn: không phải đọc lại cả
    ngày mỗi 5 phút, và hỏng một tệp chỉ mất một lần chụp.
    """
    import pandas as pd
    sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
    from ghep_tomtom import BoGhep, bang_canh

    ngay, gio = f'{luc:%Y-%m-%d}', f'{luc:%H%M}'
    tg = pd.Timestamp(luc.replace(tzinfo=None))
    tho = pd.DataFrame({
        'muc': pd.array([d['tt'].get('traffic_level') for d in doan], dtype='Float32'),
        'loai_duong': pd.Categorical([d['tt'].get('road_type') for d in doan]),
        'phu': pd.Categorical([d['tt'].get('traffic_road_coverage') for d in doan]),
        'dong_duong': [bool(d['tt'].get('road_closure', False)) for d in doan],
        'hinh_hoc': [json.dumps([(round(a, 6), round(b, 6)) for a, b in d['diem']]) for d in doan],
    })
    tho.insert(0, 'thoi_diem', tg)
    _luu_parquet(tho, os.path.join(THU_MUC, 'tho', ngay, f'{gio}.parquet'))

    cong, khong_ghep = BoGhep.nap().ghep(doan)
    canh = bang_canh(cong)
    canh.insert(0, 'thoi_diem', tg)
    _luu_parquet(canh, os.path.join(THU_MUC, 'canh', ngay, f'{gio}.parquet'))
    da_ghep = sum(v[1] + v[2] for v in cong.values())
    return len(tho), len(canh), 100 * da_ghep / max(da_ghep + khong_ghep, 1)


# ─────────────── Sự cố giao thông (Traffic Incident Details v5) ───────────────

SU_CO = 'https://api.tomtom.com/traffic/services/5/incidentDetails'
LOAI_SU_CO = {0: 'khong_ro', 1: 'tai_nan', 2: 'suong_mu', 3: 'nguy_hiem', 4: 'mua', 5: 'bang',
              6: 'ket_xe', 7: 'dong_lan', 8: 'dong_duong', 9: 'cong_trinh', 10: 'gio',
              11: 'ngap', 14: 'xe_hong'}
TRUONG_SU_CO = ('{incidents{type,geometry{type,coordinates},properties{id,iconCategory,'
                'magnitudeOfDelay,events{description,code,iconCategory},startTime,endTime,'
                'from,to,length,delay,roadNumbers,timeValidity,probabilityOfOccurrence,lastReportTime}}}')
COT_SU_CO = ['thoi_diem', 'id', 'loai', 'ten_loai', 'muc_tre', 'tre_s', 'dai_m', 'tu', 'den',
             'mo_ta', 'bat_dau', 'ket_thuc', 'hieu_luc', 'kha_nang', 'bao_cuoi', 'hinh_hoc']


def lay_su_co(khoa):
    """Sự cố ĐANG diễn ra trong khu vực. Một lời gọi = 1 lượt trong hạn mức 2.500/ngày."""
    nam, tay, bac, dong = KHU_VUC
    for ngon_ngu in ('vi-VN', 'en-GB'):
        r = requests.get(SU_CO, params={
            'key': khoa, 'bbox': f'{tay},{nam},{dong},{bac}', 'fields': TRUONG_SU_CO,
            'language': ngon_ngu, 'timeValidityFilter': 'present'}, timeout=30)
        if r.status_code == 400 and ngon_ngu == 'vi-VN':
            continue        # thử lại bằng tiếng Anh nếu TomTom không nhận vi-VN
        if r.status_code != 200:
            raise RuntimeError(f'su co HTTP {r.status_code} {che_khoa(r.text[:150], khoa)}')
        return r.json().get('incidents', []), ngon_ngu
    return [], None


def luu_su_co(luc, ds):
    """Luôn ghi tệp, kể cả 0 sự cố: phân biệt "không có sự cố" với "không thu được"."""
    df = bang_su_co(luc, ds)
    _luu_parquet(df, os.path.join(THU_MUC, 'su_co', f'{luc:%Y-%m-%d}', f'{luc:%H%M}.parquet'))
    return df


def bang_su_co(luc, ds):
    """JSON sự cố TomTom (danh sách 'incidents') -> bảng COT_SU_CO. Dùng chung cho bản ở máy
    và bản AWS (xu_ly/bac_su_co.py) để hai nguồn ra cùng một dạng."""
    import pandas as pd
    hang = []
    for i in ds:
        p, g = i.get('properties', {}) or {}, i.get('geometry', {}) or {}
        hang.append({
            'thoi_diem': pd.Timestamp(luc.replace(tzinfo=None)), 'id': p.get('id'),
            'loai': p.get('iconCategory'), 'ten_loai': LOAI_SU_CO.get(p.get('iconCategory'), 'khac'),
            'muc_tre': p.get('magnitudeOfDelay'), 'tre_s': p.get('delay'), 'dai_m': p.get('length'),
            'tu': p.get('from'), 'den': p.get('to'),
            'mo_ta': '; '.join((e or {}).get('description', '') for e in (p.get('events') or [])),
            'bat_dau': p.get('startTime'), 'ket_thuc': p.get('endTime'),
            'hieu_luc': p.get('timeValidity'), 'kha_nang': p.get('probabilityOfOccurrence'),
            'bao_cuoi': p.get('lastReportTime'),
            'hinh_hoc': json.dumps(g.get('coordinates')),
        })
    return pd.DataFrame(hang, columns=COT_SU_CO)


def thu_thu():
    sys.stdout.reconfigure(encoding='utf-8')
    khoa = doc_khoa()
    t0 = time.time()
    luc, o, doan, loi, _ = chup(khoa, in_chi_tiet=True)
    print(f'Chup luc {luc:%H:%M} — {len(o)} o (loi {loi}), {len(doan):,} doan co du lieu, {time.time() - t0:.1f}s')
    if not doan:
        return
    print('Lop:', Counter(d['lop'] for d in doan).most_common())
    khoa_tt = Counter(k for d in doan for k in d['tt'])
    print('Thuoc tinh TomTom tra ve:', khoa_tt.most_common())
    for k in ('road_category', 'road_subcategory', 'traffic_road_coverage'):
        if k in khoa_tt:
            print(f'  {k}:', Counter(d['tt'].get(k) for d in doan).most_common(10))
    muc = [d['tt'].get('traffic_level') for d in doan if isinstance(d['tt'].get('traffic_level'), (int, float))]
    if muc:
        nhom = Counter('ket (<0.4)' if m < 0.4 else 'dong (0.4-0.75)' if m < 0.75 else 'thong (>=0.75)' for m in muc)
        print('Muc ket xe luc nay:', nhom.most_common())
    dai = 0.0
    for d in doan:
        for (a1, b1), (a2, b2) in zip(d['diem'], d['diem'][1:]):
            dai += math.hypot((a2 - a1) * 111_320, (b2 - b1) * 111_320 * math.cos(math.radians(a1)))
    print(f'Tong chieu dai duong co du lieu: {dai / 1000:.0f} km')
    print('Mau 2 doan:', json.dumps([{'tt': d['tt'], 'diem_dau': d['diem'][0]} for d in doan[:2]], ensure_ascii=False))

    # Kiểm chứng bằng số km/h thật ở 3 điểm (3 lượt trong hạn mức 2.500/ngày).
    for ten, (a, b) in {'Dien Bien Phu (Q3)': (10.7795, 106.6880),
                        'Cach Mang Thang 8': (10.7770, 106.6850),
                        'Nguyen Thi Minh Khai': (10.7860, 106.6950)}.items():
        r = requests.get(DOAN_DUONG, params={'point': f'{a},{b}', 'unit': 'KMPH', 'key': khoa}, timeout=30)
        if r.ok:
            f = r.json().get('flowSegmentData', {})
            print(f'  {ten:<22} hien tai {f.get("currentSpeed")} km/h | duong trong {f.get("freeFlowSpeed")} km/h'
                  f' | do tin cay {f.get("confidence")} | {f.get("frc")}')
        else:
            print(f'  {ten}: HTTP {r.status_code} {r.text[:100]}')


if __name__ == '__main__':
    lenh = sys.argv[1] if len(sys.argv) > 1 else 'thu-thu'
    if lenh == 'thu-thu':
        thu_thu()
    else:
        sys.exit('Thu dinh ky: chay thu_dinh_ky.py (bo hen gio Windows goi tep do).')
