"""
Bộ đọc ô bản đồ dạng vector (Mapbox Vector Tile, .pbf) viết bằng Python thuần.

Vì sao tự viết: không cài thêm gói ngoài (29/10/2026 lệnh cài mapbox-vector-tile
từ PyPI bị chặn). Định dạng MVT nhỏ và ổn định (đặc tả v2.1), chỉ cần đọc được:

  Tile    { 3: Layer* }
  Layer   { 15: version, 1: name, 2: Feature*, 3: keys*, 4: Value*, 5: extent }
  Feature { 1: id, 2: tags (packed), 3: type, 4: geometry (packed) }
  Value   { 1: string, 2: float, 3: double, 4: int64, 5: uint64, 6: sint64, 7: bool }

Hình học là chuỗi lệnh MoveTo(1) / LineTo(2) / ClosePath(7), mỗi toạ độ là độ lệch
so với điểm trước, mã hoá zigzag.

    giai(noi_dung) -> {ten_lop: {'extent': 4096, 'features': [{'id', 'type',
                                   'properties': {...}, 'lines': [[(x, y), ...], ...]}]}}
"""
import gzip
import struct


def _varint(b, i):
    kq = dich = 0
    while True:
        c = b[i]
        i += 1
        kq |= (c & 0x7F) << dich
        if c < 0x80:
            return kq, i
        dich += 7


def _cac_truong(b):
    """Duyệt (số trường, kiểu dây, giá trị) của một thông điệp protobuf."""
    i, n = 0, len(b)
    while i < n:
        khoa, i = _varint(b, i)
        so, kieu = khoa >> 3, khoa & 7
        if kieu == 0:
            v, i = _varint(b, i)
        elif kieu == 1:
            v, i = b[i:i + 8], i + 8
        elif kieu == 2:
            dai, i = _varint(b, i)
            v, i = b[i:i + dai], i + dai
        elif kieu == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f'Kieu day protobuf khong ho tro: {kieu}')
        yield so, kieu, v


def _packed(b):
    i, ra = 0, []
    while i < len(b):
        v, i = _varint(b, i)
        ra.append(v)
    return ra


def _zigzag(n):
    return (n >> 1) ^ -(n & 1)


def _gia_tri(b):
    for so, kieu, v in _cac_truong(b):
        if so == 1:
            return bytes(v).decode('utf-8', 'replace')
        if so == 2:
            return struct.unpack('<f', v)[0]
        if so == 3:
            return struct.unpack('<d', v)[0]
        if so in (4, 5):
            return v
        if so == 6:
            return _zigzag(v)
        if so == 7:
            return bool(v)
    return None


def _hinh_hoc(lenh):
    """Chuỗi lệnh -> danh sách đường (mỗi đường là list (x, y) trong hệ toạ độ ô)."""
    duong, hien, x, y, i = [], None, 0, 0, 0
    while i < len(lenh):
        ma, so_lan = lenh[i] & 7, lenh[i] >> 3
        i += 1
        if ma in (1, 2):
            for _ in range(so_lan):
                x += _zigzag(lenh[i])
                y += _zigzag(lenh[i + 1])
                i += 2
                if ma == 1:
                    hien = [(x, y)]
                    duong.append(hien)
                else:
                    hien.append((x, y))
        elif ma == 7 and hien:
            hien.append(hien[0])
    return duong


def giai(noi_dung):
    if noi_dung[:2] == b'\x1f\x8b':
        noi_dung = gzip.decompress(noi_dung)
    b = memoryview(noi_dung)
    ket_qua = {}
    for so, _, lop_b in _cac_truong(b):
        if so != 3:
            continue
        ten, extent, khoa, gia_tri, dac_trung = '', 4096, [], [], []
        for s, _, v in _cac_truong(lop_b):
            if s == 1:
                ten = bytes(v).decode('utf-8', 'replace')
            elif s == 5:
                extent = v
            elif s == 3:
                khoa.append(bytes(v).decode('utf-8', 'replace'))
            elif s == 4:
                gia_tri.append(_gia_tri(v))
            elif s == 2:
                dac_trung.append(v)
        ds = []
        for f_b in dac_trung:
            f = {'id': None, 'type': 0, 'properties': {}, 'lines': []}
            the, lenh = [], []
            for s, _, v in _cac_truong(f_b):
                if s == 1:
                    f['id'] = v
                elif s == 2:
                    the = _packed(v)
                elif s == 3:
                    f['type'] = v
                elif s == 4:
                    lenh = _packed(v)
            for k, g in zip(the[0::2], the[1::2]):
                f['properties'][khoa[k]] = gia_tri[g]
            f['lines'] = _hinh_hoc(lenh)
            ds.append(f)
        ket_qua[ten] = {'extent': extent, 'features': ds}
    return ket_qua
