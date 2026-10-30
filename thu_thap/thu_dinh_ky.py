"""
Một lượt thu dữ liệu — bộ hẹn giờ Windows gọi 5 phút/lần (xem cai_hen_gio.ps1).

  1. Mức kẹt xe TomTom toàn khu trung tâm (30 ô)          mỗi lượt
  2. Sự cố giao thông TomTom đang diễn ra                 mỗi lượt
  3. Dự báo thời tiết Open-Meteo 48 giờ tới               mỗi giờ một lần

Ba phần độc lập: một phần lỗi (mất mạng, TomTom từ chối…) không làm mất phần kia.
Mọi việc ghi vào du_lieu/nhat_ky/thu_thap_YYYY-MM.log (đã che key).

Chạy tay để thử:   python thu_dinh_ky.py
"""
import logging
import os
import sys
import time

THU_MUC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THU_MUC)

import du_bao_thoi_tiet                                   # noqa: E402
from thu_tomtom import (che_khoa, chup, doc_khoa, gio_vn,  # noqa: E402
                        lay_su_co, luu_chup, luu_su_co)

GOC = os.path.join(THU_MUC, '..')
TEP_KHOA_CHAY = os.path.join(GOC, 'du_lieu', 'nhat_ky', 'dang_chay.lock')


def mo_nhat_ky(luc):
    thu_muc = os.path.join(GOC, 'du_lieu', 'nhat_ky')
    os.makedirs(thu_muc, exist_ok=True)
    logging.basicConfig(filename=os.path.join(thu_muc, f'thu_thap_{luc:%Y-%m}.log'),
                        level=logging.INFO, encoding='utf-8',
                        format='%(asctime)s %(levelname)s %(message)s')
    return logging.getLogger('thu')


def gianh_khoa_chay():
    """Không cho hai lượt chồng nhau (mạng chậm, lượt trước chưa xong). Khóa cũ quá 10 phút coi như bỏ."""
    try:
        if os.path.exists(TEP_KHOA_CHAY) and time.time() - os.path.getmtime(TEP_KHOA_CHAY) < 600:
            return False
        with open(TEP_KHOA_CHAY, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except OSError:
        return False


def main():
    luc = gio_vn()
    nk = mo_nhat_ky(luc)
    if not gianh_khoa_chay():
        nk.warning('Luot truoc chua xong — bo qua luot nay')
        return 0
    khoa = ''
    loi = 0
    try:
        khoa = doc_khoa()
        t0 = time.time()
        try:
            luc_chup, o, doan, so_loi_o, chi_tiet = chup(khoa)
            so_doan, so_canh, ty_le = luu_chup(luc_chup, doan)
            nk.info(f'ket xe: {so_doan} doan TomTom -> {so_canh} canh do thi '
                    f'(ghep {ty_le:.0f}% mau, ke ca phan ngoai ban do), '
                    f'loi o {so_loi_o}/{len(o)}, {time.time() - t0:.1f}s')
            for d in chi_tiet[:3]:
                nk.warning('  ' + d)
            if so_loi_o == len(o):
                loi += 1
        except Exception as e:
            loi += 1
            nk.error(f'ket xe LOI: {che_khoa(e, khoa)}')

        try:
            ds, ngon_ngu = lay_su_co(khoa)
            df = luu_su_co(luc, ds)
            nk.info(f'su co: {len(df)} ({ngon_ngu}) {df["ten_loai"].value_counts().to_dict() if len(df) else {}}')
        except Exception as e:
            loi += 1
            nk.error(f'su co LOI: {che_khoa(e, khoa)}')

        try:
            n = du_bao_thoi_tiet.thu(luc)
            if n is not None:
                nk.info(f'du bao thoi tiet: {n} dong')
        except Exception as e:
            loi += 1
            nk.error(f'du bao thoi tiet LOI: {e}')
    except SystemExit as e:
        nk.error(f'Dung: {e}')
        loi += 1
    finally:
        try:
            os.remove(TEP_KHOA_CHAY)
        except OSError:
            pass
    return 1 if loi else 0


if __name__ == '__main__':
    sys.exit(main())
