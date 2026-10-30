"""
Đọc tình trạng BỘ THU AWS từ CloudWatch Logs của Lambda, bằng AWS CLI với profile chỉ-đọc
`thuctap-doc` (quyền: S3 dong/* + đọc log của đúng log group này — note/CAN_NHO.md).
Không cần boto3, không ghi gì lên AWS. Đọc log (FilterLogEvents) không tính tiền.

Mỗi lượt Lambda in một dòng JSON (he_thong/aws/thu_lambda/lambda_function.py):
  {"thoi_diem": ..., "o_duoc": 30, "o_loi": 0, "o_them_duoc": 30, "kb": 199, "su_co": 21,
   "thoi_tiet": "ok", "loi": [], "giay": 11.5}
và AWS thêm dòng REPORT: "Duration: 7493.11 ms  Billed Duration: ...  Max Memory Used: 98 MB".
"""
import datetime as dt
import json
import re
import subprocess

NHOM_LOG = '/aws/lambda/thu-du-lieu-giao-thong'
PROFILE = 'thuctap-doc'
KHONG_HIEN = 0x08000000
VN = dt.timezone(dt.timedelta(hours=7))
REPORT = re.compile(r'Duration: ([\d.]+) ms.*?Billed Duration: (\d+) ms.*?Max Memory Used: (\d+) MB')


class ChuaCoQuyen(Exception):
    pass


def _goi(tham_so, het_gio=90):
    r = subprocess.run(['aws'] + tham_so + ['--profile', PROFILE, '--output', 'json'], capture_output=True,
                       text=True, timeout=het_gio, creationflags=KHONG_HIEN, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        loi = (r.stderr or r.stdout).strip()
        if 'AccessDenied' in loi or 'not authorized' in loi:
            raise ChuaCoQuyen(loi[:300])
        raise RuntimeError(loi[:300])
    return json.loads(r.stdout or '{}')


def doc_luot(gio=24):
    """Danh sách lượt Lambda trong `gio` giờ gần nhất (cũ -> mới), giờ VN không múi giờ."""
    tu_ms = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=gio)).timestamp() * 1000)
    su_kien = _goi(['logs', 'filter-log-events', '--log-group-name', NHOM_LOG, '--start-time', str(tu_ms),
                    '--filter-pattern', '?"o_duoc" ?REPORT ?ERROR ?"Task timed out" ?Traceback'])
    su_kien = sorted(su_kien.get('events', []), key=lambda e: e['timestamp'])
    luot, cho_report = [], {}
    for e in su_kien:
        t = dt.datetime.fromtimestamp(e['timestamp'] / 1000, VN).replace(tzinfo=None)
        msg = e['message'].strip()
        luong = e.get('logStreamName', '')
        if msg.startswith('{') and '"o_duoc"' in msg:
            try:
                j = json.loads(msg)
            except json.JSONDecodeError:
                continue
            x = {'t': t, 'o_duoc': j.get('o_duoc', 0), 'o_loi': j.get('o_loi', 0),
                 'o_them_duoc': j.get('o_them_duoc', 0), 'kb': j.get('kb', 0), 'su_co': j.get('su_co'),
                 'thoi_tiet': j.get('thoi_tiet') == 'ok', 'loi': list(j.get('loi') or []), 'giay': j.get('giay'),
                 'ms_tinh_tien': None, 'mb_ram': None}
            luot.append(x)
            cho_report[luong] = x
        elif msg.startswith('REPORT'):
            m = REPORT.search(msg)
            x = cho_report.pop(luong, None)
            if m and x is not None and (t - x['t']).total_seconds() < 120:
                x['ms_tinh_tien'], x['mb_ram'] = int(m[2]), int(m[3])
        elif any(k in msg for k in ('ERROR', 'Task timed out', 'Traceback')):
            luot.append({'t': t, 'o_duoc': 0, 'o_loi': 0, 'o_them_duoc': 0, 'kb': 0, 'su_co': None,
                         'thoi_tiet': False, 'loi': [msg[:300]], 'giay': None, 'ms_tinh_tien': None, 'mb_ram': None,
                         'chi_loi': True})
    return luot
