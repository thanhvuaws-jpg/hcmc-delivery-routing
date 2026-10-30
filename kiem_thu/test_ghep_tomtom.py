"""Bộ ghép TomTom -> cạnh trên bản đồ giả nhỏ, đáp án tính tay."""
import numpy as np
import pandas as pd
import pytest

from ghep_tomtom import BUOC_M, MX, MY, BoGhep, bang_canh, doan_tu_tho

LAT0, LON0 = 10.78, 106.70


def m_sang_latlon(x, y):
    """Toạ độ mét tương đối (x đông, y bắc) -> (lat, lon), cùng phép chiếu với ghep_tomtom."""
    return (LAT0 * MY + y) / MY, (LON0 * MX + x) / MX


def canh_m(*ds):
    """[(x1, y1, x2, y2), ...] mét tương đối -> mảng xy tuyệt đối như BoGhep dùng."""
    return np.array([(LON0 * MX + a, LAT0 * MY + b, LON0 * MX + c, LAT0 * MY + d) for a, b, c, d in ds])


@pytest.fixture
def bo():
    # e0: đông 0->200 m; e1: tây 200->0 (chiều ngược của e0); e2: bắc, cắt ngang ở x = 100.
    return BoGhep.tu_toa_do(canh_m((0, 0, 200, 0), (200, 0, 0, 0), (100, -100, 100, 100)))


def doan(diem_m, muc=1.0, phu='one_side', dong=False):
    return {'diem': [m_sang_latlon(x, y) for x, y in diem_m],
            'tt': {'traffic_level': muc, 'traffic_road_coverage': phu, 'road_closure': dong}}


def test_lay_mau_duong_thang():
    x, y, h = BoGhep._lay_mau(np.array([[0.0, 0.0], [100.0, 0.0]]))
    assert np.allclose(x, np.arange(5, 100, 10)) and np.allclose(y, 0)
    assert np.allclose(h, 90)                     # đi về phía đông


def test_lay_mau_bo_khuc_ngan_hon_nua_met():
    # Khúc 0,3 m ở giữa bị bỏ, không tính vào quãng đường: tổng 20 m -> 2 mẫu.
    x, _, _ = BoGhep._lay_mau(np.array([[0.0, 0.0], [10.0, 0.0], [10.3, 0.0], [20.3, 0.0]]))
    assert len(x) == 2


def test_ghep_dung_chieu(bo):
    cong, khong = bo.ghep([doan([(0, 3), (200, 3)], muc=0.5)])
    assert set(cong) == {0}                       # không nhận e1 (ngược chiều) hay e2 (vuông góc)
    assert cong[0][1] == pytest.approx(200) and khong == 0
    assert cong[0][0] / cong[0][1] == pytest.approx(0.5)


def test_ghep_nguoc_chieu_vao_canh_nguoc(bo):
    cong, _ = bo.ghep([doan([(200, -3), (0, -3)])])
    assert set(cong) == {1}


def test_xa_qua_15m_khong_ghep(bo):
    cong, khong = bo.ghep([doan([(0, 20), (200, 20)])])
    assert cong == {} and khong == pytest.approx(200)


def test_muc_trung_binh_theo_chieu_dai(bo):
    cong, _ = bo.ghep([doan([(0, 2), (100, 2)], muc=0.4), doan([(100, 2), (200, 2)], muc=0.8)])
    b = bang_canh(cong).set_index('chi_so')
    assert b.loc[0, 'muc'] == 60 and b.loc[0, 'phu_m'] == 200


def test_phan_dong_tach_khoi_muc(bo):
    # Nửa đầu cạnh đang ĐÓNG (TomTom ghi 0), nửa sau mở với mức 0,8: mức cạnh phải là 80,
    # không phải 40 do trộn số 0 của phần đóng.
    cong, _ = bo.ghep([doan([(0, 2), (100, 2)], muc=0.0, dong=True), doan([(100, 2), (200, 2)], muc=0.8)])
    b = bang_canh(cong).set_index('chi_so').loc[0]
    assert b['muc'] == 80 and b['phu_m'] == 100 and b['dong_m'] == 100 and b['dong_duong']


def test_canh_dong_het(bo):
    cong, _ = bo.ghep([doan([(0, 2), (200, 2)], muc=0.0, dong=True)])
    b = bang_canh(cong).set_index('chi_so').loc[0]
    assert b['phu_m'] == 0 and b['dong_m'] == 200 and b['dong_duong']


def test_doan_thieu_muc_bi_bo(bo):
    cong, khong = bo.ghep([doan([(0, 2), (200, 2)], muc=None)])
    assert cong == {} and khong == 0


def test_doan_tu_tho_doi_kieu_float():
    # Parquet trả numpy.float32 — isinstance(x, float) sai, bộ ghép cũ từng bỏ hết đoạn vì vậy.
    df = pd.DataFrame({'muc': pd.array([0.5, None], dtype='Float32'), 'phu': ['full', 'one_side'],
                       'dong_duong': [False, True], 'hinh_hoc': ['[[10.78, 106.7], [10.781, 106.7]]'] * 2})
    d = doan_tu_tho(df)
    assert type(d[0]['tt']['traffic_level']) is float and d[1]['tt']['traffic_level'] is None
    assert d[1]['tt']['road_closure'] is True


def test_buoc_lay_mau_la_10m():
    assert BUOC_M == 10.0
