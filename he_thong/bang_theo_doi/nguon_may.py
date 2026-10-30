"""
Đọc tình trạng BỘ THU Ở MÁY: nhật ký du_lieu/nhat_ky/thu_thap_YYYY-MM.log (thu_thap/thu_dinh_ky.py
ghi), tác vụ hẹn giờ Windows, dung lượng đã lưu. Chỉ đọc, không ghi gì.

Một lượt trong nhật ký có dạng:
  2026-10-30 11:47:42,315 INFO ket xe: 4761 doan TomTom -> 33112 canh do thi (ghep 96% mau, ...), loi o 0/30, 19.9s
  2026-10-30 11:47:44,085 INFO su co: 182 (en-GB) {'ket_xe': 166, 'dong_duong': 16}
  2026-10-30 12:02:44,030 INFO du bao thoi tiet: 240 dong          (mỗi giờ một lần)
  ... WARNING Luot truoc chua xong — bo qua luot nay
  ... ERROR ket xe LOI: ...
"""
import datetime as dt
import os
import re
import subprocess

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
NHAT_KY = os.path.join(GOC, 'du_lieu', 'nhat_ky')
TEN_TAC_VU = r'\ThucTapTotNghiep\ThuDuLieuGiaoThong'
O_MOI_LUOT = 30                 # ô TomTom relative mỗi lượt (thu_tomtom.KHU_VUC, mức phóng 14)

DONG = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (\w+) (.*)$')
KET_XE = re.compile(r'ket xe: (\d+) doan TomTom -> (\d+) canh do thi \(ghep (\d+)% mau.*loi o (\d+)/(\d+), ([\d.]+)s')
SU_CO = re.compile(r'su co: (\d+) \(([\w-]+)\) (.*)$')
KHONG_HIEN = 0x08000000         # CREATE_NO_WINDOW: không bật cửa sổ đen khi gọi lệnh


def _tep_log(gio):
    """Tệp log của tháng hiện tại và tháng trước nếu cửa sổ thời gian vắt qua đầu tháng."""
    bay_gio = dt.datetime.now()
    thang = {bay_gio.strftime('%Y-%m'), (bay_gio - dt.timedelta(hours=gio)).strftime('%Y-%m')}
    return [os.path.join(NHAT_KY, f'thu_thap_{t}.log') for t in sorted(thang)]


def doc_luot(gio=24):
    """Danh sách lượt thu trong `gio` giờ gần nhất (cũ -> mới)."""
    tu = dt.datetime.now() - dt.timedelta(hours=gio)
    luot, cuoi = [], None
    for tep in _tep_log(gio):
        if not os.path.exists(tep):
            continue
        with open(tep, encoding='utf-8', errors='replace') as f:
            for dong in f:
                m = DONG.match(dong.rstrip('\n'))
                if not m:
                    continue
                t = dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                if t < tu:
                    continue
                muc, noi_dung = m.group(2), m.group(3)
                k = KET_XE.search(noi_dung)
                if k:
                    cuoi = {'t': t, 'doan': int(k[1]), 'canh': int(k[2]), 'ghep_pt': int(k[3]),
                            'o_loi': int(k[4]), 'o_tong': int(k[5]), 'giay': float(k[6]),
                            'su_co': None, 'thoi_tiet': False, 'loi': []}
                    luot.append(cuoi)
                    continue
                if noi_dung.startswith('ket xe LOI'):
                    cuoi = {'t': t, 'doan': 0, 'canh': 0, 'ghep_pt': 0, 'o_loi': O_MOI_LUOT, 'o_tong': O_MOI_LUOT,
                            'giay': None, 'su_co': None, 'thoi_tiet': False, 'loi': [noi_dung[:200]]}
                    luot.append(cuoi)
                    continue
                if cuoi is None or (t - cuoi['t']).total_seconds() > 120:
                    if muc in ('WARNING', 'ERROR'):
                        luot.append({'t': t, 'doan': 0, 'canh': 0, 'ghep_pt': 0, 'o_loi': 0, 'o_tong': 0,
                                     'giay': None, 'su_co': None, 'thoi_tiet': False,
                                     'loi': [f'{muc}: {noi_dung[:200]}'], 'bo_qua': 'bo qua luot' in noi_dung})
                    continue
                s = SU_CO.search(noi_dung)
                if s:
                    cuoi['su_co'] = int(s[1])
                elif noi_dung.startswith('du bao thoi tiet'):
                    cuoi['thoi_tiet'] = True
                elif muc in ('WARNING', 'ERROR'):
                    cuoi['loi'].append(f'{muc}: {noi_dung[:200]}')
    return luot


def tac_vu():
    """Trạng thái tác vụ hẹn giờ Windows (schtasks), dạng {Status, Last Run Time, Last Result, Next Run Time}."""
    try:
        r = subprocess.run(['schtasks', '/Query', '/TN', TEN_TAC_VU, '/FO', 'LIST', '/V'], capture_output=True,
                           text=True, timeout=15, creationflags=KHONG_HIEN)
    except Exception as e:                                      # noqa: BLE001
        return {'loi': str(e)}
    if r.returncode != 0:
        return {'loi': (r.stderr or r.stdout).strip()[:200] or 'khong tim thay tac vu'}
    kq = {}
    for dong in r.stdout.splitlines():
        if ':' in dong:
            k, v = dong.split(':', 1)
            if k.strip() in ('Status', 'Last Run Time', 'Last Result', 'Next Run Time', 'Scheduled Task State'):
                kq[k.strip()] = v.strip()
    return kq


def _schtasks(*tham_so):
    try:
        r = subprocess.run(['schtasks', *tham_so, '/TN', TEN_TAC_VU], capture_output=True, text=True, timeout=20,
                           creationflags=KHONG_HIEN)
    except Exception as e:                                      # noqa: BLE001
        return False, str(e)[:200]
    thong_bao = (r.stdout or r.stderr).strip().splitlines()
    return r.returncode == 0, (thong_bao[-1] if thong_bao else '')[:200]


def tat_tac_vu():
    """DỪNG thu ở máy: tắt tác vụ hẹn giờ (không xóa — bật lại được). Lượt đang chạy dở vẫn chạy nốt."""
    return _schtasks('/Change', '/DISABLE')


def bat_tac_vu():
    """BẮT ĐẦU thu lại: bật tác vụ hẹn giờ, chạy tiếp mỗi 5 phút."""
    return _schtasks('/Change', '/ENABLE')


def chay_ngay():
    """Chạy MỘT lượt ngay (tác vụ phải đang bật). Bộ thu có khóa chống chạy chồng lượt."""
    return _schtasks('/Run')


def dung_luong_hom_nay():
    """Số tệp + MB đã lưu hôm nay ở du_lieu/tomtom/{tho,canh,su_co}."""
    hom_nay = dt.date.today().isoformat()
    kq = {}
    for loai in ('tho', 'canh', 'su_co'):
        thu_muc = os.path.join(GOC, 'du_lieu', 'tomtom', loai, hom_nay)
        so, byte = 0, 0
        if os.path.isdir(thu_muc):
            for e in os.scandir(thu_muc):
                if e.is_file() and e.name.endswith('.parquet'):
                    so += 1
                    byte += e.stat().st_size
        kq[loai] = (so, byte / 1e6)
    return kq
