"""
Chạy thử hàm Lambda NGAY Ở MÁY trước khi đưa lên AWS: gọi TomTom/Open-Meteo thật,
nhưng thay S3 bằng thư mục tạm — không cần boto3, không đụng tới AWS.
Rồi đọc lại kết quả bằng chính bộ đọc ô của dự án để chắc bản gốc dùng được.

    python thu_o_may.py
"""
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile

THU_MUC = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(THU_MUC, '..', '..', '..'))
sys.path.insert(0, THU_MUC)
sys.path.insert(0, os.path.join(GOC, 'thu_thap'))

import lambda_function as hl          # noqa: E402
import mvt                            # noqa: E402
from thu_tomtom import doc_khoa       # noqa: E402


class S3Gia:
    def __init__(self, goc):
        self.goc = goc

    def put_object(self, Bucket, Key, Body, ContentType):
        p = os.path.join(self.goc, Bucket, *Key.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(Body)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tam = tempfile.mkdtemp(prefix='thu_lambda_')
    try:
        hl._s3 = S3Gia(tam)
        os.environ['TOMTOM_KEY'] = doc_khoa()
        os.environ['BUCKET'] = 'bucket-gia'
        # Ép chạy cả phần thời tiết dù đang không ở phút 0–4.
        that = hl.dt.datetime
        class Luc(that):
            @classmethod
            def now(cls, tz=None):
                return that.now(tz).replace(minute=1)
        hl.dt.datetime = Luc
        kq = hl.lambda_handler({}, None)
        hl.dt.datetime = that
        print('Ket qua handler:', json.dumps(kq, ensure_ascii=False))

        tep = []
        for r, _, fs in os.walk(tam):
            tep += [os.path.relpath(os.path.join(r, f), tam) for f in fs]
        print('Tep "S3":', sorted(tep))
        z = [t for t in tep if t.endswith('.zip')][0]
        with zipfile.ZipFile(os.path.join(tam, z)) as zz:
            meta = json.loads(zz.read('meta.json'))
            # Đếm ĐOẠN (đường gấp khúc) như thu_tomtom.giai_o, không đếm đặc trưng: một đặc
            # trưng có thể gồm nhiều đoạn. Về đêm TomTom cắt ít đoạn hơn (22:57 còn ~3.700).
            ten = [n for n in zz.namelist() if n.endswith('.pbf')]
            goc = [n for n in ten if '/' not in n]          # kiểu relative, tên cũ ở gốc zip
            dem = sum(len(f['lines']) for n in goc
                      for lop in mvt.giai(zz.read(n)).values() for f in lop['features'] if f['type'] == 2)
            # Kiểu absolute: mức = km/h, phải nằm trong 0–130 (không phải tỉ lệ 0–1).
            kmh = [f['properties'].get('traffic_level') for n in ten if n.startswith('absolute/')
                   for lop in mvt.giai(zz.read(n)).values() for f in lop['features'] if f['type'] == 2]
            kmh = [v for v in kmh if isinstance(v, (int, float))]
        print(f'Doc lai zip: {len(goc)} o relative, {len(ten) - len(goc)} o absolute, {dem:,} doan, '
              f'km/h {min(kmh):.0f}-{max(kmh):.0f} (trung vi {sorted(kmh)[len(kmh) // 2]:.0f}), '
              f'meta thoi_diem={meta["thoi_diem"]}, loi={meta["loi"]}')
        ok = (kq['o_duoc'] == 30 and kq.get('o_them_duoc') == 30 and dem > 1000 and max(kmh) > 5
              and 'su_co' in kq and kq.get('thoi_tiet') == 'ok' and not kq['loi'])
        print('DAT' if ok else 'CHUA DAT')
        return 0 if ok else 1
    finally:
        shutil.rmtree(tam, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
