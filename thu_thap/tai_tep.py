"""
Tải một tệp dữ liệu công khai về thư mục riêng, kiểm tra MD5, giải nén an toàn.

Dùng cho các bộ dữ liệu mở có giấy phép rõ ràng (ghi trong note/KE_HOACH.md, mục 3).
Dữ liệu tải về là dữ liệu bên ngoài: mỗi bộ một thư mục riêng dưới du_lieu/,
chặn tên tệp đi ra ngoài thư mục đích (zip slip), KHÔNG chạy mã nằm trong gói.

    python tai_tep.py <url> <thu_muc_con> [md5]
"""
import hashlib
import os
import sys
import zipfile

import requests

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TOI_DA_BYTE = 500 * 1024 * 1024


def tai(url, thu_muc_con, md5=None):
    dich = os.path.abspath(os.path.join(GOC, 'du_lieu', thu_muc_con))
    os.makedirs(dich, exist_ok=True)
    ten = url.split('?')[0].rstrip('/').split('/')[-1]
    tep = os.path.join(dich, ten)
    h = hashlib.md5()
    with requests.get(url, stream=True, timeout=120,
                      headers={'User-Agent': 'thuctaptotnghiep/0.1 (do an sinh vien)'}) as r:
        r.raise_for_status()
        co = 0
        with open(tep + '.tam', 'wb') as f:
            for khoi in r.iter_content(1 << 20):
                co += len(khoi)
                if co > TOI_DA_BYTE:
                    sys.exit('Tep lon hon 500 MB — dung lai.')
                f.write(khoi)
                h.update(khoi)
    if md5 and h.hexdigest() != md5:
        os.remove(tep + '.tam')
        sys.exit(f'MD5 khong khop ({h.hexdigest()} != {md5}) — bo tep.')
    os.replace(tep + '.tam', tep)
    print(f'Da tai {ten}: {co / 1e6:.1f} MB, md5 {"khop" if md5 else h.hexdigest()}')

    if zipfile.is_zipfile(tep):
        with zipfile.ZipFile(tep) as z:
            for m in z.infolist():
                if not os.path.abspath(os.path.join(dich, m.filename)).startswith(dich + os.sep):
                    sys.exit(f'Duong dan la trong tep nen: {m.filename!r} — khong giai nen.')
            z.extractall(dich)
            print(f'Giai nen {len(z.infolist())} muc vao {dich}')
    return dich


if __name__ == '__main__':
    tai(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
