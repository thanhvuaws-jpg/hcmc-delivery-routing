"""Chỉ dẫn từng chặng: trái phải phải đúng và không báo thừa ở đường cong, cạnh ngắn."""
from chi_dan import chi_dan, chuan_ten, goc_giua, kieu_theo_goc, phuong_vi, ten_theo_doan


def tuyen(*diem):
    """Dãy (x, y) -> xy, dài từng cạnh."""
    dai = [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(diem, diem[1:])]
    return list(diem), dai


def giua(buoc):
    """Bỏ bước xuất phát và đến nơi."""
    return [(b['kieu'], b['ten']) for b in buoc[1:-1]]


def test_phuong_vi_va_chieu_re():
    assert round(phuong_vi((0, 0), (0, 10))) == 0
    assert round(phuong_vi((0, 0), (10, 0))) == 90
    assert goc_giua(0, 270) == -90           # đang đi bắc, ra hướng tây: sang trái
    assert goc_giua(350, 10) == 20
    assert kieu_theo_goc(-90) == 're_trai' and kieu_theo_goc(90) == 're_phai'
    assert kieu_theo_goc(-30) == 'che_trai' and kieu_theo_goc(30) == 'che_phai'
    assert kieu_theo_goc(5) == 'di_thang' and kieu_theo_goc(170) == 'quay_dau'


def test_di_bac_re_tay_la_re_trai_re_dong_la_re_phai():
    xy, dai = tuyen((0, 0), (0, 100), (-100, 100))
    assert giua(chi_dan(xy, ['A', 'B'], dai, lambda j: [(0, 200)])) == [('re_trai', 'B')]
    xy, dai = tuyen((0, 0), (0, 100), (100, 100))
    assert giua(chi_dan(xy, ['A', 'B'], dai, lambda j: [(0, 200)])) == [('re_phai', 'B')]


def test_vi_tri_chi_dan_la_met_tu_dau_tuyen():
    xy, dai = tuyen((0, 0), (0, 100), (-100, 100), (-100, 300))
    buoc = chi_dan(xy, ['A', 'B', 'B'], dai, lambda j: [(0, 200)] if j == 1 else [])
    assert buoc[1]['tai_m'] == 100 and buoc[-1]['tai_m'] == 400
    assert buoc[0]['kieu'] == 'xuat_phat' and buoc[-1]['kieu'] == 'den_noi'


def test_duong_cong_khong_co_loi_khac_thi_khong_bao():
    xy, dai = tuyen((0, 0), (0, 100), (-100, 100))
    assert giua(chi_dan(xy, ['A', 'A'], dai)) == []


def test_duong_cong_co_hem_ngang_ma_van_la_huong_thang_nhat_thi_khong_bao():
    # Đi bắc, đường lượn 40° sang phải, có hẻm vuông góc sang trái.
    xy, dai = tuyen((0, 0), (0, 100), (64, 177))
    assert giua(chi_dan(xy, ['A', 'A'], dai, lambda j: [(-100, 100)])) == []


def test_nga_ba_chu_t_cung_ten_van_bao():
    xy, dai = tuyen((0, 0), (0, 100), (-100, 100))
    assert giua(chi_dan(xy, ['A', 'A'], dai, lambda j: [(100, 100)])) == [('re_trai', 'A')]


def test_doi_ten_khi_di_thang_o_nga_tu_thi_bao():
    xy, dai = tuyen((0, 0), (0, 100), (0, 200))
    assert giua(chi_dan(xy, ['A', 'B'], dai, lambda j: [(-100, 100)])) == [('di_thang', 'B')]


def test_doi_ten_ma_khong_co_lua_chon_thi_khong_bao():
    xy, dai = tuyen((0, 0), (0, 100), (0, 200), (0, 300))
    assert giua(chi_dan(xy, ['A', 'Cầu A', 'A'], dai)) == []


def test_doi_ten_khong_co_lua_chon_nhung_goc_lon_van_bao_re():
    # Đường nối một chiều nhập vào trục lớn, góc 123°: không được ghi là đi tiếp.
    xy, dai = tuyen((0, 0), (0, 100), (84, 45))
    assert giua(chi_dan(xy, ['A', 'B'], dai)) == [('re_phai', 'B')]


def test_duong_x_va_x_la_mot_duong():
    xy, dai = tuyen((0, 0), (0, 100), (0, 200))
    assert giua(chi_dan(xy, ['Hòa Bình', 'Đường Hòa Bình'], dai, lambda j: [(-100, 100)])) == []
    assert giua(chi_dan(xy, ['Hẻm 686 Cách Mạng', 'Hẻm 686  cách mạng'], dai, lambda j: [(-100, 100)])) == []
    assert chuan_ten('Nguyễn Ðình Chiểu') == chuan_ten('Nguyễn Đình Chiểu')


def test_di_thang_tu_hem_sang_hem_thi_khong_bao():
    xy, dai = tuyen((0, 0), (0, 100), (0, 200))
    assert giua(chi_dan(xy, ['Hẻm 404', 'Hẻm 390'], dai, lambda j: [(-100, 100)])) == []
    # Rẽ vào hẻm khác thì vẫn báo.
    xy, dai = tuyen((0, 0), (0, 100), (100, 100))
    assert giua(chi_dan(xy, ['Hẻm 404', 'Hẻm 390'], dai, lambda j: [(0, 200)])) == [('re_phai', 'Hẻm 390')]


def test_ba_lan_chech_cung_ten_gop_lai():
    # Đường cong có lối thẳng hơn ở mỗi nút, cùng tên, cách nhau 60 m.
    xy, dai = tuyen((0, 0), (0, 100), (21, 157), (64, 200), (121, 221), (300, 221))
    def khac(j):
        return [(xy[j][0] - 5, xy[j][1] + 100)]
    assert giua(chi_dan(xy, ['A', 'B', 'B', 'B', 'B'], dai, khac)) == [('re_phai', 'B')]


def test_cho_re_sat_dich_thi_bo():
    xy, dai = tuyen((0, 0), (0, 100), (10, 100))
    assert giua(chi_dan(xy, ['A', 'B'], dai, lambda j: [(0, 200)])) == []


def test_doan_khong_ten_kep_giua_cung_duong_thi_khong_bao():
    xy, dai = tuyen((0, 0), (0, 100), (0, 200), (0, 300))
    assert giua(chi_dan(xy, ['A', '', 'A'], dai, lambda j: [(-100, 100)])) == []


def test_re_vao_hem_khong_ten_van_bao():
    xy, dai = tuyen((0, 0), (0, 100), (100, 100))
    assert giua(chi_dan(xy, ['A', ''], dai, lambda j: [(0, 200)])) == [('re_phai', '')]


def test_hai_lan_re_trai_qua_dai_phan_cach_gop_thanh_quay_dau():
    xy, dai = tuyen((0, 0), (0, 100), (-15, 100), (-15, 0))
    assert giua(chi_dan(xy, ['A', 'A', 'A'], dai, lambda j: [(0, 200)])) == [('quay_dau', 'A')]


def test_lech_lan_tren_cung_duong_thi_bo():
    # Cả hai nút đều có lối thẳng hơn tuyến: chếch trái rồi chếch phải ngay, gộp lại thành đi thẳng.
    xy, dai = tuyen((0, 0), (0, 100), (-10, 110), (-10, 300))
    assert giua(chi_dan(xy, ['A', 'A', 'A'], dai, lambda j: [(0, 200)] if j == 1 else [(-30, 130)])) == []


def test_chech_vao_nhanh_khi_co_loi_di_thang():
    xy, dai = tuyen((0, 0), (0, 100), (-10, 110), (-10, 300))
    assert giua(chi_dan(xy, ['A', 'A', 'A'], dai, lambda j: [(0, 200)] if j == 1 else [(100, 110)])) == [('che_trai', 'A')]


def test_vong_xoay_bao_luc_vao_va_luc_ra_neu_vong_dai():
    xy, dai = tuyen((0, 0), (0, 100), (30, 130), (60, 100), (60, 0))
    ten = ['A', 'Vòng xoay Mũi Tàu', 'Vòng xoay Mũi Tàu', 'B']
    buoc = chi_dan(xy, ten, dai, lambda j: [(0, 200)])
    assert giua(buoc) == [('vong_xoay', 'Vòng xoay Mũi Tàu'), ('ra_vong_xoay', 'B')]
    assert buoc[1]['chu'] == 'Vào Vòng xoay Mũi Tàu, quay đầu ra B'


def test_vong_xoay_ngan_chi_bao_luc_vao_va_noi_huong_ra():
    xy, dai = tuyen((0, 0), (0, 100), (20, 120), (120, 120))
    buoc = chi_dan(xy, ['A', 'Công trường Dân Chủ', 'B'], dai, lambda j: [(0, 200)])
    assert giua(buoc) == [('vong_xoay', 'Công trường Dân Chủ')]
    assert buoc[1]['chu'] == 'Vào vòng xoay Công trường Dân Chủ, rẽ phải ra B'


def test_nga_tu_khong_phai_vong_xoay():
    xy, dai = tuyen((0, 0), (0, 100), (100, 100))
    assert giua(chi_dan(xy, ['A', 'Ngã tư Hàng Xanh'], dai, lambda j: [(0, 200)])) == [('re_phai', 'Ngã tư Hàng Xanh')]
    xy, dai = tuyen((0, 0), (0, 100), (0, 200))
    buoc = chi_dan(xy, ['Rạch Bùng Binh', 'Rạch Bùng Binh'], dai)
    assert giua(buoc) == []


def test_ten_theo_doan():
    assert ten_theo_doan(['A', 'A', 'Đường A', '', 'B'], [10, 10, 10, 10, 10]) == [[0.0, 'A'], [30.0, ''], [40.0, 'B']]


def test_tuyen_rong_va_mot_canh():
    assert [b['kieu'] for b in chi_dan([(0, 0)], [], [])] == ['den_noi']
    xy, dai = tuyen((0, 0), (0, 100))
    buoc = chi_dan(xy, ['A'], dai)
    assert [b['kieu'] for b in buoc] == ['xuat_phat', 'den_noi']
    assert buoc[0]['chu'] == 'Đi về hướng bắc trên A'
