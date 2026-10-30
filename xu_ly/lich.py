"""
Lịch D14: mỗi ngày 2020–2027 -> thứ, cuối tuần, âm lịch, ngày lễ, ngày nghỉ chính thức,
khoảng cách tới Tết, giai đoạn bất thường (COVID). Dùng gắn cờ L8 và làm đặc trưng.

Âm lịch tính bằng thuật toán thiên văn của Hồ Ngọc Đức (múi giờ +7 — lịch Việt Nam,
có năm lệch lịch Trung Quốc một ngày). Kiểm bằng ngày Tết và Giỗ Tổ đã biết (kiem_tra()).

Ngày nghỉ chính thức (công chức; khu vực tư thường theo) lấy từ thông báo từng năm, chỉ
ghi những năm dữ liệu cần: 2020–2021 (Kaggle D11) và 11/2026–02/2027 (TomTom D4). Năm
khác suy ra từ Bộ luật Lao động 2019 (Điều 112) + cuối tuần, cột nguon_nghi ghi rõ.

Giai đoạn COVID ở TP.HCM: chỉ ghi mốc có nguồn; cột tin_cay = cao/vua/thap. Đợt 2 năm
2020 (07–09/2020) chưa tìm được văn bản đóng/mở dịch vụ ở TP.HCM → tin_cay thấp, để
phân tích độ nhạy chứ không loại dữ liệu.

Chạy:  python lich.py      -> du_lieu/bac/lich.parquet  (+ in kiểm tra)
"""
import datetime as dt
import math
import os
import sys

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TEP_RA = os.path.join(GOC, 'du_lieu', 'bac', 'lich.parquet')
TU, DEN = dt.date(2020, 1, 1), dt.date(2027, 12, 31)
MUI_GIO = 7

# ───────────── Âm lịch (Hồ Ngọc Đức, amlich.js) ─────────────


def _jd(d, m, y):
    a = (14 - m) // 12
    y2, m2 = y + 4800 - a, m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045


def _soc(k):
    """Thời điểm sóc (trăng mới) thứ k tính từ 1/1/1900, ngày Julius thực."""
    T = k / 1236.85
    T2, T3 = T * T, T * T * T
    dr = math.pi / 180
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
    C1 += -0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(dr * 2 * Mpr)
    C1 += -0.0004 * math.sin(dr * 3 * Mpr)
    C1 += 0.0104 * math.sin(dr * 2 * F) - 0.0051 * math.sin(dr * (M + Mpr))
    C1 += -0.0074 * math.sin(dr * (M - Mpr)) + 0.0004 * math.sin(dr * (2 * F + M))
    C1 += -0.0004 * math.sin(dr * (2 * F - M)) - 0.0006 * math.sin(dr * (2 * F + Mpr))
    C1 += 0.0010 * math.sin(dr * (2 * F - Mpr)) + 0.0005 * math.sin(dr * (2 * Mpr + M))
    if T < -11:
        dt_ = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        dt_ = -0.000278 + 0.000265 * T + 0.000262 * T2
    return jd1 + C1 - dt_


def _ngay_soc(k):
    return math.floor(_soc(k) + 0.5 + MUI_GIO / 24)


def _kinh_do_mat_troi(jdn):
    T = (jdn - 2451545.0) / 36525
    T2 = T * T
    dr = math.pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
    L = (L0 + DL) * dr
    return L - math.pi * 2 * math.floor(L / (math.pi * 2))


def _cung_hoang_dao(ngay):
    return math.floor(_kinh_do_mat_troi(ngay - 0.5 - MUI_GIO / 24) / math.pi * 6)


def _thang_11(nam):
    k = math.floor((_jd(31, 12, nam) - 2415021) / 29.530588853)
    soc = _ngay_soc(k)
    return _ngay_soc(k - 1) if _cung_hoang_dao(soc) >= 9 else soc


def _thang_nhuan(a11):
    k = math.floor((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    i, cung = 1, _cung_hoang_dao(_ngay_soc(k + 1))
    while True:
        truoc = cung
        i += 1
        cung = _cung_hoang_dao(_ngay_soc(k + i))
        if not (cung != truoc and i < 14):
            break
    return i - 1


def am_lich(d):
    """date -> (ngày, tháng, năm âm, nhuận?)."""
    so = _jd(d.day, d.month, d.year)
    k = math.floor((so - 2415021.076998695) / 29.530588853)
    dau_thang = _ngay_soc(k + 1)
    if dau_thang > so:
        dau_thang = _ngay_soc(k)
    a11 = _thang_11(d.year)
    b11 = a11
    if a11 >= dau_thang:
        nam = d.year
        a11 = _thang_11(d.year - 1)
    else:
        nam = d.year + 1
        b11 = _thang_11(d.year + 1)
    ngay = so - dau_thang + 1
    lech = math.floor((dau_thang - a11) / 29)
    nhuan, thang = False, lech + 11
    if b11 - a11 > 365:
        tn = _thang_nhuan(a11)
        if lech >= tn:
            thang = lech + 10
            nhuan = lech == tn
    if thang > 12:
        thang -= 12
    if thang >= 11 and lech < 4:
        nam -= 1
    return ngay, thang, nam, nhuan


# ───────────── Ngày nghỉ chính thức đã công bố ─────────────

def _khoang(a, b):
    a, b = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    return [a + dt.timedelta(n) for n in range((b - a).days + 1)]


# (từ, đến, tên, nguồn). Gồm cả ngày nghỉ bù / hoán đổi.
NGHI_DA_CONG_BO = [
    ('2020-01-01', '2020-01-01', 'tet_duong_lich', 'thong bao 2020'),
    ('2020-01-23', '2020-01-29', 'tet_nguyen_dan', 'thong bao 2020 (28 Chap - mung 5)'),
    ('2020-04-02', '2020-04-02', 'gio_to', 'thong bao 2020'),
    ('2020-04-30', '2020-05-03', 'giai_phong_lao_dong', 'thong bao 2020'),
    ('2020-09-02', '2020-09-02', 'quoc_khanh', 'BLLD 2012: 1 ngay'),
    ('2021-01-01', '2021-01-03', 'tet_duong_lich', 'thong bao 2021'),
    ('2021-02-10', '2021-02-16', 'tet_nguyen_dan', 'thong bao 2021 (29 Chap - mung 5)'),
    ('2021-04-21', '2021-04-21', 'gio_to', 'thong bao 2021'),
    ('2021-04-30', '2021-05-03', 'giai_phong_lao_dong', 'thong bao 2021 (3/5 nghi bu)'),
    ('2021-09-02', '2021-09-05', 'quoc_khanh', 'thong bao 2021'),
    # 24/11/2026: NQ 28/2026/QH16. Bộ Nội vụ đề xuất nghỉ đúng 1 ngày, không hoán đổi
    # (Tờ trình 10033/TTr-BNV 14/9/2026) — chưa thấy quyết định cuối, kiểm lại khi tới.
    ('2026-11-24', '2026-11-24', 'van_hoa_viet_nam', 'NQ 28/2026/QH16; de xuat BNV 14/9/2026'),
    ('2027-01-01', '2027-01-03', 'tet_duong_lich', 'bao chi 10/2026'),
    ('2027-02-04', '2027-02-10', 'tet_nguyen_dan', 'thong bao BNV 10/2026; HN 1732/TB-UBND'),
]
NAM_DA_CONG_BO = {2020, 2021}           # năm đã ghi ĐỦ mọi đợt nghỉ

# (từ, đến, tên, tin cậy, ghi chú) — TP.HCM. Chồng nhau thì dòng SAU (cụ thể hơn) thắng.
GIAI_DOAN = [
    ('2020-02-03', '2020-05-03', 'covid_hs_nghi_hoc_2020', 'vua', 'hoc sinh nghi den truong tu sau Tet 2020'),
    ('2020-03-15', '2020-03-31', 'covid_dong_giai_tri_2020', 'cao', 'dung bar/karaoke/rap tu 18h 15/3'),
    ('2020-04-01', '2020-04-22', 'covid_ct16_2020', 'cao', 'cach ly xa hoi Chi thi 16; TP.HCM nhom nguy co cao toi 22/4'),
    ('2020-04-23', '2020-05-07', 'covid_noi_long_2020', 'vua', 'noi long dan, bar mo lai 8/5'),
    ('2020-07-28', '2020-09-15', 'covid_dot2_2020', 'thap', 'dot dich Da Nang; chua tim duoc van ban dong/mo dich vu o TP.HCM'),
    ('2021-02-02', '2021-02-28', 'covid_tsn_2021', 'cao', 'hoc sinh hoc truc tuyen, dung dich vu khong thiet yeu; mo lai 1/3 (CV 546/UBND-VX)'),
    ('2021-05-31', '2021-06-19', 'covid_ct15_2021', 'cao', 'gian cach Chi thi 15'),
    ('2021-06-20', '2021-07-08', 'covid_ct10_2021', 'cao', 'gian cach Chi thi 10 + 15'),
    ('2021-07-09', '2021-09-30', 'covid_ct16_2021', 'cao', 'Chi thi 16; 23/8-15/9 "ai o dau o yen do"'),
]

# Năm học TP.HCM (từ, đến, nguồn) — chỉ các năm dữ liệu cần. Ngày đi học = trong năm học,
# thứ 2–6, không phải ngày nghỉ chính thức, không trong đợt học sinh nghỉ vì COVID.
# Nghỉ Tết của học sinh thường dài hơn công chức: ngoài khoảng Tết đã công bố, mọi ngày
# trong [-7, +7] quanh mùng 1 cũng coi là không đi học (tin cậy vừa, chờ đối chiếu).
NAM_HOC = [
    ('2019-08-19', '2020-07-15', 'nam hoc 2019-20 keo dai toi 15/7/2020 vi COVID (tin cay vua)'),
    ('2020-09-01', '2021-05-31', 'nam hoc 2020-21 (tin cay vua)'),
    ('2026-08-24', '2027-05-31', 'QD 5067/QD-UBND: tuu truong 24/8, khai giang 5/9/2026, HK1 ket thuc truoc 18/1/2027'),
]
GIAI_DOAN_HS_NGHI = {'covid_hs_nghi_hoc_2020', 'covid_ct16_2020', 'covid_dong_giai_tri_2020', 'covid_tsn_2021'}

TET_DA_BIET = {2020: '2020-01-25', 2021: '2021-02-12', 2022: '2022-02-01', 2023: '2023-01-22',
               2024: '2024-02-10', 2025: '2025-01-29', 2026: '2026-02-17', 2027: '2027-02-06'}
GIO_TO_DA_BIET = {2020: '2020-04-02', 2021: '2021-04-21', 2022: '2022-04-10', 2023: '2023-04-29',
                  2024: '2024-04-18', 2025: '2025-04-07', 2026: '2026-04-26'}


def le_theo_luat(d, am):
    """Tên ngày lễ theo Bộ luật Lao động (Điều 112) — đúng NGÀY lễ, chưa tính nghỉ bù."""
    a_ngay, a_thang, _, nhuan = am
    if (d.month, d.day) == (1, 1):
        return 'tet_duong_lich'
    if not nhuan and a_thang == 1 and a_ngay <= 3:
        return 'tet_nguyen_dan'
    if not nhuan and (a_thang, a_ngay) == (3, 10):
        return 'gio_to'
    if (d.month, d.day) == (4, 30):
        return 'giai_phong'
    if (d.month, d.day) == (5, 1):
        return 'lao_dong'
    if (d.month, d.day) == (9, 2):
        return 'quoc_khanh'
    if d.year >= 2026 and (d.month, d.day) == (11, 24):
        return 'van_hoa_viet_nam'
    return ''


def dung():
    import pandas as pd
    ngay = [TU + dt.timedelta(n) for n in range((DEN - TU).days + 1)]
    am = [am_lich(d) for d in ngay]
    tet = sorted(d for d, a in zip(ngay, am) if a[:2] == (1, 1) and not a[3])
    # Giao thừa = ngày trước mùng 1 (29 hoặc 30 tháng Chạp).
    giao_thua = {t - dt.timedelta(1) for t in tet}

    nghi_cb = {}
    for a, b, ten, nguon in NGHI_DA_CONG_BO:
        for d in _khoang(a, b):
            nghi_cb[d] = (ten, nguon)
    gd = {}
    for a, b, ten, tin, _ in GIAI_DOAN:
        for d in _khoang(a, b):
            gd[d] = (ten, tin)
    nam_hoc = {d for a, b, _ in NAM_HOC for d in _khoang(a, b)}

    hang = []
    for d, a in zip(ngay, am):
        le = le_theo_luat(d, a) or ('giao_thua' if d in giao_thua else '')
        gan = min(tet, key=lambda t: abs((d - t).days))
        cach = (d - gan).days
        if d in nghi_cb:
            nghi, nguon = True, nghi_cb[d][1]
        elif d.year in NAM_DA_CONG_BO or d.year >= 2027 and d < dt.date(2027, 2, 11) or \
                dt.date(2026, 11, 1) <= d <= dt.date(2026, 12, 31):
            nghi = d.weekday() >= 5
            nguon = 'cuoi_tuan' if nghi else ''
        else:
            nghi = d.weekday() >= 5 or le not in ('', 'giao_thua')
            nguon = 'suy_tu_luat' if le not in ('', 'giao_thua') else ('cuoi_tuan' if nghi else '')
        hang.append({
            'ngay': pd.Timestamp(d), 'thu': d.weekday(), 'cuoi_tuan': d.weekday() >= 5,
            'am_ngay': a[0], 'am_thang': a[1], 'am_nam': a[2], 'am_nhuan': a[3],
            'le': le, 'nghi': nghi, 'nguon_nghi': nguon,
            'di_hoc': (d in nam_hoc and d.weekday() < 5 and not nghi and abs(cach) > 7
                       and gd.get(d, ('', ''))[0] not in GIAI_DOAN_HS_NGHI),
            'cach_tet': cach if abs(cach) <= 30 else None,
            'quanh_tet': -7 <= cach <= 10,
            'giai_doan': gd.get(d, ('', ''))[0], 'tin_cay_giai_doan': gd.get(d, ('', ''))[1],
        })
    df = pd.DataFrame(hang)
    df['cach_tet'] = df['cach_tet'].astype('Int16')
    os.makedirs(os.path.dirname(TEP_RA), exist_ok=True)
    df.to_parquet(TEP_RA, index=False)
    return df


def kiem_tra(df):
    ok = True
    tet = {d.year: str(d.date()) for d in df.loc[(df.am_ngay == 1) & (df.am_thang == 1) & ~df.am_nhuan, 'ngay']}
    for nam, ngay in TET_DA_BIET.items():
        dung_ = tet.get(nam) == ngay
        ok &= dung_
        print(f'  Tet {nam}: tinh {tet.get(nam)} / biet {ngay} {"OK" if dung_ else "SAI"}')
    gio_to = {d.year: str(d.date()) for d in df.loc[df['le'] == 'gio_to', 'ngay']}
    for nam, ngay in GIO_TO_DA_BIET.items():
        dung_ = gio_to.get(nam) == ngay
        ok &= dung_
        print(f'  Gio To {nam}: tinh {gio_to.get(nam)} / biet {ngay} {"OK" if dung_ else "SAI"}')
    print(f'  Gio To 2027 (chua co moc doi chieu): {gio_to.get(2027)}')
    return ok


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    df = dung()
    print(f'{len(df)} ngay {df.ngay.min().date()} -> {df.ngay.max().date()} -> {TEP_RA}')
    dat = kiem_tra(df)
    print('Ngay nghi (khong ke cuoi tuan) 11/2026-02/2027:')
    m = df[(df.ngay >= '2026-11-01') & (df.ngay <= '2027-02-28') & df.nghi & ~df.cuoi_tuan]
    print('  ' + ', '.join(f'{d.date()} {le or ""}' for d, le in zip(m['ngay'], m['le'])))
    print('DAT' if dat else 'KHONG DAT')
    sys.exit(0 if dat else 1)
