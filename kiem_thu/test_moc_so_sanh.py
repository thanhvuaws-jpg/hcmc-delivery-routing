"""Mốc trung bình lịch sử và thước đo của mo_hinh/moc_so_sanh.py — dữ liệu nhỏ tự tạo, không cần tầng vàng."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mo_hinh'))
from dac_trung import chung_toan_mang  # noqa: E402
from ho_so_lich_su import ho_so  # noqa: E402
from moc_so_sanh import LichSu, danh_gia, mae_theo_ngay  # noqa: E402


def _bang(dong):
    return pd.DataFrame([{'doan': d, 'khung': pd.Timestamp(k), 'r': r} for d, k, r in dong])


# 02/11/2026 là thứ Hai, 03/11 thứ Ba, 07/11 thứ Bảy, 09/11 thứ Hai, 10/11 thứ Ba.
HOC = _bang([(1, '2026-11-02 08:00', 0.4), (1, '2026-11-02 08:00', 0.6), (1, '2026-11-03 08:00', 0.8),
             (1, '2026-11-07 08:00', 0.9), (2, '2026-11-02 09:00', np.nan)])


def test_tra_dung_thu_va_gio_dich():
    # Dòng lúc 07:45, tầm 15 phút -> giờ đích 08:00 thứ Hai: TB hai dòng thứ Hai, không lấy thứ Ba.
    du, dung_thu = LichSu(HOC).du_bao(_bang([(1, '2026-11-09 07:45', 0.1)]), 15)
    assert du[0] == pytest.approx(0.5)
    assert dung_thu == 1.0


def test_lui_ve_loai_ngay_khi_chua_co_thu():
    # Thứ Tư chưa có trong phần học -> TB ngày thường (0,4 + 0,6 + 0,8) / 3, không lẫn thứ Bảy.
    du, dung_thu = LichSu(HOC).du_bao(_bang([(1, '2026-11-04 07:45', 0.1)]), 15)
    assert du[0] == pytest.approx(0.6)
    assert dung_thu == 0.0


def test_lui_ve_o_trong_ngay_roi_r_hien_tai():
    # Chủ nhật không có dòng cuối tuần nào lúc 08:15 của đoạn 1, đoạn 3 chưa từng thấy -> r hiện tại.
    du, _ = LichSu(HOC).du_bao(_bang([(3, '2026-11-08 08:00', 0.33)]), 15)
    assert du[0] == pytest.approx(0.33)


def test_bo_dong_r_thieu_khi_tinh_trung_binh():
    du, _ = LichSu(HOC).du_bao(_bang([(2, '2026-11-09 08:45', 0.2)]), 15)
    assert du[0] == pytest.approx(0.2)         # đoạn 2 chỉ có NaN -> coi như chưa có lịch sử


def _chuoi_tuan():
    """Hai đoạn, 14 ngày từ thứ Hai 02/11/2026, một khung lúc 08:00 mỗi ngày trải trên lưới 15 phút."""
    khung = pd.date_range('2026-11-02 00:00', periods=14 * 96, freq='15min')
    R = np.full((len(khung), 2), np.nan, dtype=np.float32)
    o8 = np.flatnonzero((khung.hour == 8) & (khung.minute == 0))
    R[o8, 0] = 0.1 * np.arange(1, 15)          # ngày k có r = 0,1·k (ngày 6, 7, 13, 14 là cuối tuần)
    return khung, R, o8


def test_ho_so_loai_chinh_khung_hoc():
    khung, R, o8 = _chuoi_tuan()
    H = ho_so(R, khung, cat=len(khung))
    # Thứ Hai đầu (r = 0,1): TB các ngày thường CÒN LẠI 2,3,4,5,8,9,10,11,12 — không chứa 0,1.
    assert H[o8[0], 0] == pytest.approx(np.mean([0.2, 0.3, 0.4, 0.5, 0.8, 0.9, 1.0, 1.1, 1.2]), abs=1e-5)
    # Thứ Bảy đầu (r = 0,6): chỉ lấy cuối tuần còn lại 7, 13, 14.
    assert H[o8[5], 0] == pytest.approx(np.mean([0.7, 1.3, 1.4]), abs=1e-5)


def test_ho_so_khung_kiem_tra_khong_dong_gop():
    khung, R, o8 = _chuoi_tuan()
    cat = int(o8[7])                           # 7 ngày đầu là học (ngày 1..7), từ ngày 8 là kiểm tra
    H = ho_so(R, khung, cat=cat)
    ngay_thuong_hoc = [0.1, 0.2, 0.3, 0.4, 0.5]
    # Khung kiểm tra (ngày 9, thứ Ba): TB đủ 5 ngày thường phần học, không bỏ gì, không lấy ngày kiểm tra.
    assert H[o8[8], 0] == pytest.approx(np.mean(ngay_thuong_hoc), abs=1e-5)
    # Giá trị khung kiểm tra đổi thế nào cũng không làm đổi hồ sơ.
    R2 = R.copy()
    R2[cat:, 0] = 0.99
    assert np.array_equal(ho_so(R2, khung, cat=cat), H, equal_nan=True)


def test_ho_so_bo_ngay_dau():
    """Đường cong học (dau > 0): khung trước `dau` không đóng góp; khung học từ `dau` vẫn bỏ chính nó."""
    khung, R, o8 = _chuoi_tuan()
    cat, dau = int(o8[7]), int(o8[2])           # học ngày 3..7, bỏ ngày 1, 2
    H = ho_so(R, khung, cat=cat, dau=dau)
    assert H[o8[8], 0] == pytest.approx(np.mean([0.3, 0.4, 0.5]), abs=1e-5)   # kiểm tra: ngày thường 3, 4, 5
    assert H[o8[2], 0] == pytest.approx(np.mean([0.4, 0.5]), abs=1e-5)        # ngày 3 bỏ chính nó
    R2 = R.copy()
    R2[:dau, 0] = 0.99                                                          # ngày bị bỏ đổi gì cũng vậy
    assert np.array_equal(ho_so(R2, khung, cat=cat, dau=dau)[dau:], H[dau:], equal_nan=True)
    assert np.array_equal(ho_so(R, khung, cat=cat, dau=0), ho_so(R, khung, cat=cat), equal_nan=True)


def test_ho_so_doan_khong_co_lich_su_la_nan():
    khung, R, o8 = _chuoi_tuan()
    H = ho_so(R, khung, cat=len(khung))
    assert np.isnan(H[o8[0], 1])               # đoạn 2 không có số đo nào
    assert np.isnan(H[o8[0] + 1, 0])           # đoạn 1 không có số đo lúc 08:15
    only = np.full_like(R, np.nan)
    only[o8[0], 0] = 0.5
    assert np.isnan(ho_so(only, khung, cat=len(khung))[o8[0], 0])  # chỉ có chính nó -> bỏ đi là hết mẫu


def test_chung_toan_mang_bo_o_thieu():
    R = np.array([[0.5, 0.7, np.nan], [np.nan, np.nan, np.nan]], dtype=np.float32)
    H = np.array([[0.6, 0.6, 0.9], [0.6, 0.6, 0.9]], dtype=np.float32)
    c = chung_toan_mang(R, H)
    assert c[0] == pytest.approx(0.0, abs=1e-6)     # (−0,1 + 0,1) / 2, ô thiếu không tính
    assert np.isnan(c[1])                           # khung không có số đo nào


def test_danh_gia_va_theo_ngay():
    y = np.array([0.2, 0.5, 0.9, 0.9])
    du = np.array([0.3, 0.5, 0.9, 0.7])
    r = np.array([0.2, 0.5, 0.9, 0.9])
    kq = danh_gia(y, du, r, np.array([8, 8, 23, 23]))
    assert kq['mae'] == pytest.approx(7.5)
    assert kq['rmse'] == pytest.approx(np.sqrt((100 + 0 + 0 + 400) / 4), abs=1e-3)
    assert kq['mae_ban_ngay'] == pytest.approx(5.0)
    assert kq['dung_3_muc'] == pytest.approx(0.75)  # dòng 1: kẹt (0,2) dự báo vẫn kẹt (0,3); dòng 4: thông -> đông
    assert kq['f1_ket'] == pytest.approx(1.0)
    ngay = np.array(['a', 'a', 'b', 'b'])
    assert mae_theo_ngay(y, du, ngay) == {'a': pytest.approx(5.0), 'b': pytest.approx(10.0)}
