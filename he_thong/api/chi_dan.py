"""
Chỉ dẫn từng chặng cho màn hình dẫn đường ("200 m nữa rẽ trái vào Hoàng Văn Thụ"). Hàm thuần, không đọc dữ liệu.

Đồ thị OSM chia đường thành rất nhiều cạnh ngắn, nên phải lọc mới ra chỉ dẫn người đọc được. Nguyên tắc: chỉ báo khi
người lái phải quyết định, hoặc khi cần biết mình vừa sang đường khác.
  - Góc rẽ đo trên TAM_NHIN_M mét trước và sau nút, không đo trên một cạnh (cạnh ngắn làm góc nhiễu).
  - Không có lối nào khác ở nút mà góc nhỏ: không phải quyết định gì, không báo, kể cả khi đổi tên (cầu, đoạn nối).
  - Cùng đường mà tuyến là hướng thẳng nhất, hơn các lối khác ít nhất LE_THANG_NHAT độ: không báo.
    Ngã ba chữ T thì hai lối gần bằng nhau nên vẫn báo.
  - Đi thẳng từ hẻm này sang hẻm khác: không báo, số hẻm đổi liên tục mà người lái chỉ cần đi thẳng.
  - "Đường X" và "X" là một đường. Đoạn không tên kẹp giữa cùng một đường không tính là đổi đường.
  - Các chỗ rẽ cách nhau ≤ GOP_M mét gộp làm một (≤ GOP_CUNG_TEN_M mét nếu cùng tên): rẽ trái hai lần qua dải phân cách
    thành quay đầu, rẽ trái rồi phải lệch làn trên cùng đường thì bỏ.
  - Vòng xoay báo lúc vào, nói luôn đi hướng nào. Vòng ngắn hơn VONG_NGAN_M thì không báo lúc ra.
  - Chỗ rẽ cách đích dưới SAT_DICH_M mét thì bỏ, chỉ báo đến nơi.
"""
import math
import re
import unicodedata

TAM_NHIN_M = 25.0
GOP_M = 30.0
GOP_CUNG_TEN_M = 80.0
VONG_NGAN_M = 60.0
SAT_DICH_M = 15.0
LE_THANG_NHAT = 20.0
GOC_THANG, GOC_RE, GOC_QUAY = 20.0, 45.0, 150.0
# "Ngã tư", "ngã ba" là giao lộ thường, không phải vòng xoay.
VONG_XOAY = re.compile(r'^(vòng xoay|vòng quay|công trường|bùng binh|ngã (năm|sáu|bảy|5|6|7)\b)', re.IGNORECASE)
HUONG = ['bắc', 'đông bắc', 'đông', 'đông nam', 'nam', 'tây nam', 'tây', 'tây bắc']
LOI = {'di_thang': 'Đi thẳng', 'che_trai': 'Chếch trái', 'che_phai': 'Chếch phải', 're_trai': 'Rẽ trái', 're_phai': 'Rẽ phải',
       'quay_dau': 'Quay đầu', 'ra_vong_xoay': 'Ra khỏi vòng xoay'}


def phuong_vi(p, q):
    """Hướng từ p tới q, độ, 0 = bắc, 90 = đông. p, q = (x đông, y bắc) theo mét."""
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360


def goc_giua(a, b):
    """Đổi hướng từ a sang b, trong khoảng −180..180; dương là sang phải."""
    return (b - a + 180) % 360 - 180


def kieu_theo_goc(goc):
    a = abs(goc)
    if a < GOC_THANG:
        return 'di_thang'
    if a >= GOC_QUAY:
        return 'quay_dau'
    return ('che_' if a < GOC_RE else 're_') + ('trai' if goc < 0 else 'phai')


def chuan_ten(t):
    """Khóa so sánh tên đường: OSM lúc ghi "Đường X", lúc ghi "X", khác hoa thường, có cả chữ Ð (U+00D0) thay cho Đ."""
    t = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', t).replace('Ð', 'Đ')).strip().casefold()
    return t[6:] if t.startswith('đường ') else t


def la_hem(t):
    return t.casefold().startswith(('hẻm', 'ngõ', 'ngách'))


def ten_vong_xoay(t):
    return t if t.casefold().startswith(('vòng xoay', 'vòng quay')) else f'vòng xoay {t}'


def ten_theo_doan(ten, dai):
    """[[mét từ đầu tuyến, tên], ...] mỗi khi đổi tên (kể cả không có chỉ dẫn): để hiện "đang đi trên đường nào"."""
    ra, m = [], 0.0
    for t, d in zip(ten, dai):
        if not ra or chuan_ten(ra[-1][1]) != chuan_ten(t):
            ra.append([round(m, 1), t])
        m += d
    return ra


def _buoc(kieu, ten, tai_m, goc, chu=None):
    return {'kieu': kieu, 'ten': ten, 'tai_m': round(tai_m, 1), 'goc': round(goc),
            'chu': chu or (LOI[kieu] + (f' vào {ten}' if ten else ''))}


def chi_dan(xy, ten, dai, loi_khac=lambda j: ()):
    """
    xy:  (x, y) mét của các nút trên tuyến, n + 1 phần tử
    ten: tên đường của từng cạnh, n phần tử; '' nếu không có tên
    dai: chiều dài từng cạnh, n phần tử (mét)
    loi_khac(j): (x, y) các nút kề khác có thể đi tiếp từ nút j, trừ nút sau trên tuyến và nút vừa rời
    Trả về các bước theo thứ tự, luôn mở đầu bằng 'xuat_phat' và kết thúc bằng 'den_noi'; tai_m là số mét kể từ đầu tuyến.
    """
    n = len(dai)
    if n == 0:
        return [_buoc('den_noi', '', 0.0, 0.0, 'Đến nơi')]
    lk = [0.0]
    for d in dai:
        lk.append(lk[-1] + d)

    def nhin(j, chieu):
        """Điểm trên tuyến cách nút j TAM_NHIN_M mét, về trước (chieu = −1) hoặc về sau (+1)."""
        con, a, k = TAM_NHIN_M, xy[j], j
        while 0 <= k + chieu <= n:
            b = xy[k + chieu]
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            if d >= con:
                return (a[0] + (b[0] - a[0]) * con / d, a[1] + (b[1] - a[1]) * con / d)
            con, a, k = con - d, b, k + chieu
        return a

    ung_vien = []
    ten_hien = ten[0]
    vong = None                 # bước vào vòng xoay đang đi
    tren_vong = bool(VONG_XOAY.match(ten[0]))
    for j in range(1, n):
        moi = ten[j]
        vao, ra = phuong_vi(nhin(j, -1), xy[j]), phuong_vi(xy[j], nhin(j, 1))
        goc = goc_giua(vao, ra)
        c = {'j': j, 'vao': vao, 'ra': ra, 'goc': goc, 'ten': moi, 'ten_cu': ten_hien, 'co_dinh': None}
        if tren_vong:
            if chuan_ten(moi) == chuan_ten(ten[j - 1]):
                continue
            tren_vong = False
            ten_hien = moi
            if vong:
                vong.update(ra_ten=moi, ra_goc=goc_giua(vong['vao'], ra))
            if not vong or lk[j] - lk[vong['j']] >= VONG_NGAN_M:
                ung_vien.append({**c, 'co_dinh': 'ra_vong_xoay'})
            vong = None
            continue
        if moi and VONG_XOAY.match(moi) and chuan_ten(moi) != chuan_ten(ten_hien):
            tren_vong = True
            ten_hien = moi
            vong = {**c, 'co_dinh': 'vong_xoay', 'ra_ten': '', 'ra_goc': None}
            ung_vien.append(vong)
            continue
        goc_khac = [abs(goc_giua(vao, phuong_vi(xy[j], k))) for k in loi_khac(j)]
        thang_nhat = all(abs(goc) + LE_THANG_NHAT <= g for g in goc_khac)
        if moi and chuan_ten(moi) != chuan_ten(ten_hien):
            khong_phai_chon = not goc_khac and abs(goc) < GOC_RE
            di_thang_qua_hem = abs(goc) < GOC_THANG and thang_nhat and la_hem(moi)
            if not (khong_phai_chon or di_thang_qua_hem):
                ung_vien.append(c)
        elif goc_khac and abs(goc) >= GOC_THANG and not thang_nhat:
            ung_vien.append(c)
        else:
            continue
        ten_hien = moi

    gop = []
    for c in ung_vien:
        t = gop[-1] if gop else None
        if t and not t['co_dinh'] and not c['co_dinh']:
            gan = lk[c['j']] - lk[t['j_cuoi']]
            if gan <= GOP_M or (gan <= GOP_CUNG_TEN_M and chuan_ten(c['ten']) == chuan_ten(t['ten'])):
                t.update(ra=c['ra'], j_cuoi=c['j'], ten=c['ten'] or t['ten'], goc=goc_giua(t['vao'], c['ra']))
                continue
        gop.append({**c, 'j_cuoi': c['j']})

    huong = phuong_vi(xy[0], nhin(0, 1))
    ten_dau = next((t for t, m in zip(ten, lk) if t and m <= 50), '')
    buoc = [_buoc('xuat_phat', ten_dau, 0.0, huong,
                  f'Đi về hướng {HUONG[round(huong / 45) % 8]}' + (f' trên {ten_dau}' if ten_dau else ''))]
    for t in gop:
        if lk[-1] - lk[t['j']] < SAT_DICH_M:
            continue
        kieu = t['co_dinh'] or kieu_theo_goc(t['goc'])
        if kieu == 'di_thang' and (not t['ten'] or chuan_ten(t['ten']) == chuan_ten(t['ten_cu'])):
            continue
        if kieu == 'vong_xoay':
            chu = 'Vào ' + ten_vong_xoay(t['ten'])
            if t['ra_goc'] is not None:
                chu += ', ' + LOI[kieu_theo_goc(t['ra_goc'])].lower() + (f' ra {t["ra_ten"]}' if t['ra_ten'] else '')
            buoc.append(_buoc(kieu, t['ten'], lk[t['j']], t['goc'], chu))
        else:
            buoc.append(_buoc(kieu, t['ten'], lk[t['j']], t['goc']))
    buoc.append(_buoc('den_noi', '', lk[-1], 0.0, 'Đến nơi'))
    return buoc
