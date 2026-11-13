"""
Hồ sơ lịch sử làm đặc trưng cho mô hình dự báo: "giờ này, loại ngày này, đoạn này bình thường r bao nhiêu".

Vì sao cần: lần train đầu (06/11/2026) GBM thắng "giữ nguyên" nhưng ở 60 phút THUA mốc trung bình lịch sử —
giao thông lặp lại đều theo giờ mà mô hình không được biết nhịp đó của từng đoạn (QĐ-020).

Chống rò rỉ dữ liệu, hai điều kiện:
  - chỉ các khung trong phần HỌC (trước `cat`) đóng góp vào trung bình; khung kiểm tra không đóng góp;
  - với một khung thuộc phần học, trung bình LOẠI chính khung đó. Nếu không, nhãn của dòng học nằm luôn trong
    đặc trưng của nó, mô hình tin hồ sơ quá mức rồi kém đi trên dữ liệu thật.
Mỗi (ngày, ô 15 phút) có đúng một khung nên loại khung đó cũng là loại ngày đó.

Loại ngày: ngày thường / cuối tuần (chưa tách từng thứ — mới vài tuần dữ liệu, mỗi thứ quá ít mẫu).
"""
import numpy as np
import pandas as pd


def ho_so_mo_rong(R, khung, cat, dau=0, them=4):
    """
    Như ho_so nhưng thêm `them` khung SAU khung cuối: H có T + them dòng, H[:T] trùng ho_so(R, khung, cat, dau).
    Hồ sơ chỉ phụ thuộc loại ngày, ô 15 phút và phần học, nên tính được cả cho giờ chưa có dữ liệu. Nhờ vậy khung MỚI
    NHẤT (dự báo "bây giờ" trên web) vẫn có hồ sơ ở giờ đích. Trước 13/11 chỗ đó là NaN: MAE 60 phút ở khung cuối tăng
    6,8 -> 10,5 (QĐ-029 mục 6). khung phải cách đều 15 phút (chỉ số khung + tầm/15 mới đúng là giờ đích).
    """
    khung = pd.DatetimeIndex(khung)
    if len(khung) > 1 and not ((khung[1:] - khung[:-1]) == pd.Timedelta(minutes=15)).all():
        raise ValueError('khung khong cach deu 15 phut: chi so khung + tam/15 se khong phai gio dich')
    k = pd.date_range(khung[0], periods=len(khung) + them, freq='15min')
    return ho_so(np.concatenate([R, np.full((them, R.shape[1]), np.nan, R.dtype)]), k, cat, dau)


def ho_so(R, khung, cat, dau=0):
    """
    R (T, N): r theo khung × đoạn, NaN = thiếu. khung: pd.DatetimeIndex độ dài T, cách đều 15 phút.
    cat: số khung đầu thuộc phần học. Trả về H (T, N): H[f, n] = TB r của đoạn n ở các khung học CÙNG loại
    ngày và ô 15 phút với khung f, trừ chính f; NaN nếu không có khung nào như vậy.
    dau: chỉ khung [dau, cat) đóng góp (đường cong học: học với ít ngày hơn, hồ sơ cũng chỉ từ chừng đó ngày).
    """
    T, N = R.shape
    cuoi = np.asarray(khung.dayofweek >= 5, dtype=np.int64)
    o = np.asarray(khung.hour * 4 + khung.minute // 15, dtype=np.int64)
    co = ~np.isnan(R)
    gia_tri = np.where(co, R, 0).astype(np.float64)
    tong, dem = np.zeros((2, 96, N)), np.zeros((2, 96, N))
    np.add.at(tong, (cuoi[dau:cat], o[dau:cat]), gia_tri[dau:cat])
    np.add.at(dem, (cuoi[dau:cat], o[dau:cat]), co[dau:cat])
    t, d = tong[cuoi, o], dem[cuoi, o]              # (T, N): tổng, số mẫu của nhóm mà từng khung thuộc về
    t[dau:cat] -= gia_tri[dau:cat]                  # khung học: bỏ chính nó (khung thiếu trừ 0)
    d[dau:cat] -= co[dau:cat]
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(d > 0, t / d, np.nan).astype(np.float32)
