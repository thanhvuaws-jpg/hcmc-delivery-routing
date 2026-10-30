"""
Tải mạng lưới đường OpenStreetMap cho khu vực thử nghiệm (mặc định: trung tâm TP.HCM).

Nguồn: Overpass API (overpass-api.de). Dữ liệu OSM theo giấy phép ODbL — dùng tự do
cho đồ án, chỉ cần ghi "© OpenStreetMap contributors" trên bản đồ và trong báo cáo.

Lấy:
  - mọi đường (way có thẻ highway) kèm thẻ: oneway, access, motorcycle, maxspeed,
    junction, lanes… — đủ để dựng đồ thị tìm đường cho XE MÁY có tính luật.
  - quan hệ cấm rẽ (relation type=restriction).

Chạy:   python tai_osm.py                 (khu vực mặc định: vùng ô TomTom)
        python tai_osm.py poi             (điểm thu hút giao thông: trường, chợ, bệnh viện…)
        python tai_osm.py 10.74 106.62 10.83 106.73 trung_tam
Kết quả: ../du_lieu/ban_do/osm_<ten>.json  +  in thống kê.

Overpass là máy chủ miễn phí dùng chung: tải MỘT lần rồi dùng tệp đã lưu,
không gọi lặp lại trong vòng lặp.
"""
import json
import os
import sys
import time
from collections import Counter

import requests

THU_MUC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'du_lieu', 'ban_do')
# Máy chủ chính hay trả 504 với khu vực lớn (29/10/2026) — có danh sách dự phòng.
MAY_CHU = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
]
TAC_NHAN = 'thuctaptotnghiep-dinh-tuyen-giao-hang/0.1 (do an sinh vien)'

# Trung tâm TP.HCM cũ: Q1, Q3, Q4, Q5, Q10, Q11, Phú Nhuận, một phần Tân Bình, Bình Thạnh.
# (osm_trung_tam.json, tải 29/10/2026 — giữ nguyên làm bản gốc, không dùng dựng đồ thị nữa.)
TRUNG_TAM = (10.74, 106.62, 10.83, 106.73, 'trung_tam')

# Toàn vùng 30 ô TomTom (mức phóng 14) quanh khu trung tâm: ô phủ 10,7254–10,8333 /
# 106,6113–106,7432, đoạn TomTom thò ra tới 10,7232–10,8355 / 106,6091–106,7454; nới thêm
# ~200 m để cạnh ở mép không bị cắt cụt. Bản đồ cũ hẹp hơn nên ~15–22% dữ liệu kẹt xe
# rơi ra ngoài, không ghép được (QĐ-006, 30/10/2026).
VUNG_TOMTOM = (10.721, 106.607, 10.838, 106.748, 'vung_tomtom')
MAC_DINH = VUNG_TOMTOM

# Chia khu vực thành LUOI x LUOI ô để mỗi truy vấn nhỏ, máy chủ không cắt giữa chừng.
# Mỗi ô tải xong ghi ngay vào ban_do/o_tam/<ten>/ — máy chủ hỏng giữa chừng thì chạy lại
# chỉ tải tiếp ô còn thiếu (30/10/2026: 8/9 ô xong rồi ô cuối 504 liên tục, mất hết).
LUOI = 4


def goi_overpass(truy_van, nhan):
    loi = None
    for lan in range(2):
        for may in MAY_CHU:
            try:
                r = requests.post(may, data={'data': truy_van}, headers={'User-Agent': TAC_NHAN}, timeout=240)
                r.raise_for_status()
                return r.json()['elements']
            except Exception as e:
                loi = e
                print(f'    {may.split("/")[2]}: {str(e)[:80]} — thu may khac', flush=True)
                time.sleep(5)
        time.sleep(30)
    raise RuntimeError(f'Khong tai duoc {nhan}: {loi}')


def tai_mot_o(hop):
    return goi_overpass(f"""
[out:json][timeout:180];
(
  way["highway"]({hop});
  relation["type"="restriction"]({hop});
);
(._;>;);
out body qt;
""", f'o {hop}')


# Điểm thu hút giao thông: trường học (giờ tan trường), chợ, bệnh viện, trung tâm thương
# mại, siêu thị, trạm xe buýt, bãi xe. Lấy toạ độ tâm (out center) — đủ để tính khoảng
# cách / mật độ quanh mỗi cạnh, không cần hình học đầy đủ.
POI = [
    'nwr["amenity"~"^(school|university|college|kindergarten|hospital|clinic|marketplace|'
    'place_of_worship|bus_station|parking)$"]',
    'nwr["shop"~"^(mall|supermarket|department_store)$"]',
    'node["highway"="bus_stop"]',
    'nwr["railway"="station"]',
]


def tai_poi(nam, tay, bac, dong, ten):
    hop = f'{nam},{tay},{bac},{dong}'
    truy_van = '[out:json][timeout:180];\n(\n' + ''.join(f'  {q}({hop});\n' for q in POI) + ');\nout center tags qt;\n'
    el = goi_overpass(truy_van, f'poi {hop}')
    tep = os.path.join(THU_MUC, f'osm_poi_{ten}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump({'khu_vuc': {'ten': ten, 'nam': nam, 'tay': tay, 'bac': bac, 'dong': dong},
                   'nguon': 'OpenStreetMap contributors (ODbL), qua Overpass API',
                   'tai_luc': time.strftime('%Y-%m-%d %H:%M:%S'), 'elements': el}, f, ensure_ascii=False)
    loai = Counter(e.get('tags', {}).get('amenity') or e.get('tags', {}).get('shop')
                   or e.get('tags', {}).get('highway') or e.get('tags', {}).get('railway') for e in el)
    print(f'POI: {len(el):,} diem -> {tep}')
    for k, v in loai.most_common(16):
        print(f'  {k:<18} {v:,}')


def tai(nam, tay, bac, dong, ten):
    hop_tong = f'{nam},{tay},{bac},{dong}'
    print(f'Tai OSM khu vuc {ten} [{hop_tong}], chia {LUOI}x{LUOI} o ...')
    t0 = time.time()
    gop = {}
    tam = os.path.join(THU_MUC, 'o_tam', ten)
    os.makedirs(tam, exist_ok=True)
    buoc_vd, buoc_kd = (bac - nam) / LUOI, (dong - tay) / LUOI
    for i in range(LUOI):
        for j in range(LUOI):
            hop = f'{nam + i * buoc_vd:.5f},{tay + j * buoc_kd:.5f},{nam + (i + 1) * buoc_vd:.5f},{tay + (j + 1) * buoc_kd:.5f}'
            tep_o = os.path.join(tam, hop.replace(',', '_') + '.json')
            if os.path.exists(tep_o):
                with open(tep_o, encoding='utf-8') as f:
                    el = json.load(f)
                nhan = 'da co'
            else:
                el = tai_mot_o(hop)
                with open(tep_o + '.tam', 'w', encoding='utf-8') as f:
                    json.dump(el, f, ensure_ascii=False)
                os.replace(tep_o + '.tam', tep_o)
                nhan = 'tai moi'
                time.sleep(3)
            # Đường vắt qua ranh giới ô xuất hiện ở cả hai ô: gộp theo (loại, id).
            for e in el:
                gop[(e['type'], e['id'])] = e
            print(f'  o {i},{j} ({nhan}): {len(el):,} phan tu (tong da gop {len(gop):,})', flush=True)
    du_lieu = {'elements': list(gop.values())}
    os.makedirs(THU_MUC, exist_ok=True)
    tep = os.path.join(THU_MUC, f'osm_{ten}.json')
    with open(tep, 'w', encoding='utf-8') as f:
        json.dump({'khu_vuc': {'ten': ten, 'nam': nam, 'tay': tay, 'bac': bac, 'dong': dong, 'luoi': LUOI},
                   'nguon': 'OpenStreetMap contributors (ODbL), qua Overpass API',
                   'tai_luc': time.strftime('%Y-%m-%d %H:%M:%S'),
                   'elements': du_lieu['elements']}, f, ensure_ascii=False)
    print(f'  xong sau {time.time() - t0:.0f}s, {os.path.getsize(tep) / 1e6:.1f} MB -> {tep}')
    return du_lieu['elements']


def thong_ke(el):
    nut = [e for e in el if e['type'] == 'node']
    duong = [e for e in el if e['type'] == 'way']
    cam_re = [e for e in el if e['type'] == 'relation']
    loai = Counter(e.get('tags', {}).get('highway') for e in duong)
    mot_chieu = sum(1 for e in duong if e.get('tags', {}).get('oneway') in ('yes', '1', '-1'))
    cam_xe_may = sum(1 for e in duong if e.get('tags', {}).get('motorcycle') == 'no')
    print(f'  nut: {len(nut):,} | duong: {len(duong):,} | quan he cam re: {len(cam_re):,}')
    print(f'  duong mot chieu: {mot_chieu:,} | ghi ro cam xe may: {cam_xe_may:,}')
    print('  theo loai highway:')
    for k, v in loai.most_common(14):
        print(f'    {k:<16} {v:,}')


if __name__ == '__main__':
    if sys.argv[1:] == ['poi']:
        tai_poi(*MAC_DINH)
    elif len(sys.argv) == 6:
        a = sys.argv[1:]
        thong_ke(tai(float(a[0]), float(a[1]), float(a[2]), float(a[3]), a[4]))
    else:
        thong_ke(tai(*MAC_DINH))
