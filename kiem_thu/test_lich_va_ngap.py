"""Âm lịch, ngày lễ, chuẩn hóa tên đường (ghép điểm ngập)."""
import datetime as dt
from collections import namedtuple

import pytest

import bac_ngap as bn
import lich


@pytest.mark.parametrize('nam,ngay', list(lich.TET_DA_BIET.items()))
def test_tet(nam, ngay):
    assert lich.am_lich(dt.date.fromisoformat(ngay))[:2] == (1, 1)


@pytest.mark.parametrize('ngay,mong', [
    ('2020-05-23', (1, 4, 2020, True)),       # năm 2020 nhuận tháng 4
    ('2023-03-22', (1, 2, 2023, True)),       # năm 2023 nhuận tháng 2
    ('2026-04-26', (10, 3, 2026, False)),     # Giỗ Tổ 2026
])
def test_am_lich_thang_nhuan(ngay, mong):
    assert lich.am_lich(dt.date.fromisoformat(ngay)) == mong


def test_ngay_van_hoa_tu_2026():
    d = dt.date(2026, 11, 24)
    assert lich.le_theo_luat(d, lich.am_lich(d)) == 'van_hoa_viet_nam'
    d = dt.date(2025, 11, 24)
    assert lich.le_theo_luat(d, lich.am_lich(d)) == ''


@pytest.mark.parametrize('a,b', [('Đường số 32', 'Đường 32'), ('Đường Võ Văn Kiệt', 'võ văn kiệt'),
                                 ('Cách Mạng Tháng Tám', 'Cách Mạng Tháng 8')])
def test_chuan_ten(a, b):
    assert bn.chuan(a) == bn.chuan(b)


def test_ten_chung_chung():
    assert bn.chung_chung('Đường số 2') and bn.chung_chung('Đường 35')
    assert not bn.chung_chung('Đường 3 Tháng 2') and not bn.chung_chung('Đường D1')


def test_chi_ten_duong_moi_danh_ca_tuyen():
    R = namedtuple('R', 'duong khu_vuc mo_ta')
    assert bn.chi_ten_duong(R('Cao Đạt', '', 'Đường Cao Đạt.'))
    assert not bn.chi_ten_duong(R('Lê Văn Lương', 'xã Nhà Bè', 'Đường Lê Văn Lương: đoạn qua xã Nhà Bè.'))
    assert not bn.chi_ten_duong(R('Bến Nghé', '', 'Đường Bến Nghé, số 4 (Tân Thuận).'))
