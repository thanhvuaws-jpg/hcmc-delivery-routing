"""
Tải bộ dữ liệu Kaggle bằng API, không cần cài gói `kaggle` (gọi thẳng REST API).

Mặc định: "Traffic Flow data in Ho Chi Minh City, Viet Nam" (thanhnguyen2612),
CC0, nhóm nghiên cứu ĐH Bách Khoa TP.HCM — dữ liệu D11 trong note/KE_HOACH.md.

Khóa đọc từ thuctaptotnghiep/.env, một trong hai cách:
  KAGGLE_USERNAME + KAGGLE_KEY      (khóa cũ, tệp kaggle.json)
  KAGGLE_API_TOKEN                  (token mới)
Không bao giờ in khóa ra màn hình.

Chạy:   python tai_kaggle.py
        python tai_kaggle.py <chu_so_huu>/<ten_bo_du_lieu> <thu_muc_con>
Kết quả: du_lieu/<thu_muc_con>/ (giải nén) + in danh sách tệp, số dòng, vài dòng đầu.

Dữ liệu tải về là dữ liệu từ bên ngoài: giải nén vào thư mục riêng, chặn tên tệp
đi ra ngoài thư mục đích (zip slip), và chỉ đọc bằng pandas — không chạy gì trong đó.
"""
import io
import os
import sys
import zipfile

import requests

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAC_DINH = ('thanhnguyen2612/traffic-flow-data-in-ho-chi-minh-city-viet-nam', 'kaggle_hcmc')
API = 'https://www.kaggle.com/api/v1/datasets/download/{bo}'
TOI_DA_BYTE = 500 * 1024 * 1024      # chặn tải nhầm bộ quá lớn


def doc_env():
    gt = {}
    tep = os.path.join(GOC, '.env')
    if os.path.exists(tep):
        for dong in open(tep, encoding='utf-8'):
            dong = dong.strip()
            if '=' in dong and not dong.startswith('#'):
                k, v = dong.split('=', 1)
                gt[k.strip()] = v.strip().strip('"').strip("'")
    return gt


def che(s, bi_mat):
    s = str(s)
    for b in bi_mat:
        if b:
            s = s.replace(b, '***')
    return s


def tai(bo, thu_muc_con):
    env = doc_env()
    token, ten, khoa = env.get('KAGGLE_API_TOKEN'), env.get('KAGGLE_USERNAME'), env.get('KAGGLE_KEY')
    bi_mat = [token, khoa]
    phien = requests.Session()
    if token:
        phien.headers['Authorization'] = f'Bearer {token}'
    elif ten and khoa:
        phien.auth = (ten, khoa)
    else:
        sys.exit('Chua co khoa Kaggle trong .env (KAGGLE_USERNAME + KAGGLE_KEY, hoac KAGGLE_API_TOKEN).')

    print(f'Tai {bo} ...')
    r = phien.get(API.format(bo=bo), stream=True, timeout=120, allow_redirects=True)
    if r.status_code != 200:
        sys.exit(f'Kaggle tu choi: HTTP {r.status_code} {che(r.text[:200], bi_mat)}\n'
                 '  401 = khoa sai/het han; 403 = chua bam dong y dieu khoan bo du lieu tren web; 404 = sai ten bo.')
    du_lieu = io.BytesIO()
    for khoi in r.iter_content(1 << 20):
        du_lieu.write(khoi)
        if du_lieu.tell() > TOI_DA_BYTE:
            sys.exit('Bo du lieu lon hon 500 MB — dung lai, kiem tra lai truoc khi tai.')
    print(f'  da tai {du_lieu.tell() / 1e6:.1f} MB')

    dich = os.path.abspath(os.path.join(GOC, 'du_lieu', thu_muc_con))
    os.makedirs(dich, exist_ok=True)
    with zipfile.ZipFile(du_lieu) as z:
        for m in z.infolist():
            duong = os.path.abspath(os.path.join(dich, m.filename))
            if not duong.startswith(dich + os.sep):
                sys.exit(f'Tep nen co duong dan la ({m.filename!r}) — khong giai nen.')
        z.extractall(dich)
        ds = [(m.filename, m.file_size) for m in z.infolist() if not m.is_dir()]
    print(f'  giai nen vao {dich}')
    return dich, ds


def xem_nhanh(dich, ds):
    import pandas as pd
    pd.set_option('display.width', 200)
    pd.set_option('display.max_columns', 20)
    for ten, co in ds:
        print(f'\n== {ten}  ({co / 1e6:.1f} MB)')
        if ten.lower().endswith('.csv'):
            p = os.path.join(dich, ten)
            so_dong = sum(1 for _ in open(p, 'rb')) - 1
            print(f'   {so_dong:,} dong')
            print(pd.read_csv(p, nrows=4).to_string())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    bo, con = (sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else MAC_DINH
    dich, ds = tai(bo, con)
    xem_nhanh(dich, ds)
