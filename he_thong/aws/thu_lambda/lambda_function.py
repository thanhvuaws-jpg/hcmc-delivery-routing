"""
Bộ thu dữ liệu thời gian thực trên AWS Lambda — EventBridge Scheduler gọi 5 phút/lần.

Chỉ lưu BẢN GỐC (tầng đồng) lên S3, không giải mã, không ghép bản đồ:
  dong/tomtom_o/YYYY-MM-DD/HHMM.zip          30 ô Traffic Flow (.pbf) + meta.json   ~200 KB
      <x>_<y>.pbf           kiểu relative: mức = tốc độ hiện tại / tốc độ đường trống (0–1)
      absolute/<x>_<y>.pbf  kiểu absolute: tốc độ hiện tại km/h (bước 5 km/h) — từ 30/10/2026
  dong/tomtom_su_co/YYYY-MM-DD/HHMM.json.gz  sự cố đang diễn ra (JSON gốc)          ~4 KB
  dong/thoi_tiet_du_bao/YYYY-MM-DD/HH.json.gz dự báo Open-Meteo 48 giờ, mỗi giờ một lần

Vì sao chỉ lưu bản gốc: hàm càng ít việc càng ít chỗ hỏng và càng rẻ. Giải mã ô +
ghép vào cạnh đồ thị chạy ở máy (thu_thap/mvt.py, dinh_tuyen/ghep_tomtom.py), lặp lại
được bất cứ lúc nào từ bản gốc — sửa thuật toán không mất dữ liệu.

Chỉ dùng thư viện chuẩn + boto3 (có sẵn trong Lambda): không layer, không gói ngoài.

Biến môi trường:
  TOMTOM_KEY   khóa TomTom — người dùng tự dán trong bảng điều khiển Lambda
  BUCKET       tên bucket S3
  TIEN_TO      (tùy chọn) tiền tố, mặc định "dong"
"""
import datetime as dt
import gzip
import io
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

KHU_VUC = (10.74, 106.62, 10.83, 106.73)        # nam, tây, bắc, đông — trùng thu_thap/tai_osm.py
MUC_PHONG = 14
KIEU = 'relative'
KIEU_THEM = ('absolute',)      # km/h thật -> thời gian đi qua cạnh (QĐ-007)
O_URL = 'https://api.tomtom.com/traffic/map/4/tile/flow/{kieu}/{z}/{x}/{y}.pbf'
SU_CO_URL = 'https://api.tomtom.com/traffic/services/5/incidentDetails'
TRUONG_SU_CO = ('{incidents{type,geometry{type,coordinates},properties{id,iconCategory,'
                'magnitudeOfDelay,events{description,code,iconCategory},startTime,endTime,'
                'from,to,length,delay,roadNumbers,timeValidity,probabilityOfOccurrence,lastReportTime}}}')
THOI_TIET_URL = 'https://api.open-meteo.com/v1/forecast'
DIEM = {                                         # trùng thu_thap/tai_thoi_tiet.py
    'ben_thanh': (10.7725, 106.6980), 'cong_hoa': (10.8010, 106.6530),
    'hang_xanh': (10.8010, 106.7110), 'nga_sau_cho_lon': (10.7560, 106.6590),
    'nguyen_van_linh_q7': (10.7290, 106.7210),
}
BIEN = ['precipitation', 'precipitation_probability', 'rain', 'showers', 'temperature_2m',
        'relative_humidity_2m', 'weather_code', 'cloud_cover', 'wind_speed_10m']

VN = dt.timezone(dt.timedelta(hours=7))
_s3 = None


def s3():
    """Tạo client lúc cần (kiểm thử ở máy thay bằng bản giả, không cần boto3)."""
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client('s3')
    return _s3


def che(s, khoa):
    return str(s).replace(khoa, '***') if khoa else str(s)


def lay(url, tham_so, het_gio=20):
    """GET, xin gzip (Lambda không có brotli), trả về bytes đã giải nén."""
    yeu_cau = urllib.request.Request(url + '?' + urllib.parse.urlencode(tham_so), headers={
        'Accept-Encoding': 'gzip', 'User-Agent': 'thuctaptotnghiep-lambda/1.0'})
    with urllib.request.urlopen(yeu_cau, timeout=het_gio) as r:
        b = r.read()
    return gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b


def cac_o(nam, tay, bac, dong, z):
    def xy(lat, lon):
        n = 2 ** z
        return (int((lon + 180) / 360 * n),
                int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n))
    x0, y0 = xy(bac, tay)
    x1, y1 = xy(nam, dong)
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def ghi(bucket, khoa_s3, du_lieu, loai):
    s3().put_object(Bucket=bucket, Key=khoa_s3, Body=du_lieu, ContentType=loai)


def thu_o(khoa, bucket, tien_to, luc):
    o = cac_o(*KHU_VUC, MUC_PHONG)
    viec = [(KIEU, xy) for xy in o] + [(k, xy) for k in KIEU_THEM for xy in o]

    def mot_o(v):
        kieu, (x, y) = v
        try:
            return v, lay(O_URL.format(kieu=kieu, z=MUC_PHONG, x=x, y=y), {'key': khoa}), None
        except Exception as e:                       # noqa: BLE001 — ghi lỗi từng ô, không dừng cả lượt
            return v, None, che(e, khoa)[:200]

    # 5 luồng: 30 ô ~4 giây (đo 29/10/2026), vẫn nhẹ nhàng với máy chủ TomTom.
    with ThreadPoolExecutor(5) as ex:
        kq = list(ex.map(mot_o, viec))
    duoc = [(v, b) for v, b, _ in kq if b]
    loi = [{'kieu': v[0], 'o': list(v[1]), 'loi': e} for v, _, e in kq if e]
    if any(k == KIEU for (k, _), _ in duoc):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for (kieu, (x, y)), b in duoc:
                # Kiểu chính giữ tên cũ ở gốc zip để bộ đọc cũ vẫn đọc được.
                z.writestr(f'{x}_{y}.pbf' if kieu == KIEU else f'{kieu}/{x}_{y}.pbf', b)
            z.writestr('meta.json', json.dumps({
                'thoi_diem': luc.isoformat(), 'khu_vuc': KHU_VUC, 'muc_phong': MUC_PHONG,
                'kieu': KIEU, 'kieu_them': list(KIEU_THEM), 'so_o': len(o), 'loi': loi}, ensure_ascii=False))
        ghi(bucket, f'{tien_to}/tomtom_o/{luc:%Y-%m-%d}/{luc:%H%M}.zip', buf.getvalue(), 'application/zip')
    chinh = [b for (k, _), b in duoc if k == KIEU]
    return {'o_duoc': len(chinh), 'o_loi': sum(1 for x in loi if x['kieu'] == KIEU),
            'o_them_duoc': len(duoc) - len(chinh), 'kb': round(sum(len(b) for _, b in duoc) / 1024)}


def thu_su_co(khoa, bucket, tien_to, luc):
    nam, tay, bac, dong = KHU_VUC
    b = lay(SU_CO_URL, {'key': khoa, 'bbox': f'{tay},{nam},{dong},{bac}', 'fields': TRUONG_SU_CO,
                        'language': 'en-GB', 'timeValidityFilter': 'present'})
    goi = json.dumps({'thoi_diem': luc.isoformat(), 'tra_ve': json.loads(b)}, ensure_ascii=False).encode()
    ghi(bucket, f'{tien_to}/tomtom_su_co/{luc:%Y-%m-%d}/{luc:%H%M}.json.gz', gzip.compress(goi, 9),
        'application/gzip')
    return {'su_co': len(json.loads(b).get('incidents', []))}


def thu_thoi_tiet(bucket, tien_to, luc):
    ten = list(DIEM)
    b = lay(THOI_TIET_URL, {
        'latitude': ','.join(str(DIEM[t][0]) for t in ten),
        'longitude': ','.join(str(DIEM[t][1]) for t in ten),
        'hourly': ','.join(BIEN), 'forecast_days': 2, 'timezone': 'Asia/Ho_Chi_Minh'}, het_gio=30)
    goi = json.dumps({'phat_hanh': luc.isoformat(), 'diem': ten, 'tra_ve': json.loads(b)},
                     ensure_ascii=False).encode()
    ghi(bucket, f'{tien_to}/thoi_tiet_du_bao/{luc:%Y-%m-%d}/{luc:%H}.json.gz', gzip.compress(goi, 9),
        'application/gzip')
    return {'thoi_tiet': 'ok'}


def lambda_handler(event, context):
    t0 = time.time()
    khoa = os.environ.get('TOMTOM_KEY', '').strip()
    bucket = os.environ['BUCKET']
    tien_to = os.environ.get('TIEN_TO', 'dong')
    luc = dt.datetime.now(VN).replace(second=0, microsecond=0)
    if not khoa:
        raise RuntimeError('Chua dat bien moi truong TOMTOM_KEY')

    tom_tat, loi = {'thoi_diem': luc.isoformat()}, []
    for ten, viec in (('o', lambda: thu_o(khoa, bucket, tien_to, luc)),
                      ('su_co', lambda: thu_su_co(khoa, bucket, tien_to, luc))):
        try:
            tom_tat.update(viec())
        except Exception as e:                       # noqa: BLE001
            loi.append(f'{ten}: {che(e, khoa)[:200]}')
    # Dự báo thời tiết: lượt đầu mỗi giờ (phút 0–4).
    if luc.minute < 5:
        try:
            tom_tat.update(thu_thoi_tiet(bucket, tien_to, luc))
        except Exception as e:                       # noqa: BLE001
            loi.append(f'thoi_tiet: {str(e)[:200]}')
    tom_tat['loi'] = loi
    tom_tat['giay'] = round(time.time() - t0, 1)
    print(json.dumps(tom_tat, ensure_ascii=False))   # một dòng / lượt trong CloudWatch Logs

    # Hỏng hết thì báo lỗi để CloudWatch ghi nhận (Errors > 0); hỏng một phần thì vẫn coi là chạy.
    if tom_tat.get('o_duoc', 0) == 0 and 'su_co' not in tom_tat:
        raise RuntimeError('Luot thu hong hoan toan: ' + '; '.join(loi))
    return tom_tat
