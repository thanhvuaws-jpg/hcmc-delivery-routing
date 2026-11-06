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


def ho_so(R, khung, cat):
    """
    R (T, N): r theo khung × đoạn, NaN = thiếu. khung: pd.DatetimeIndex độ dài T, cách đều 15 phút.
    cat: số khung đầu thuộc phần học. Trả về H (T, N): H[f, n] = TB r của đoạn n ở các khung học CÙNG loại
    ngày và ô 15 phút với khung f, trừ chính f; NaN nếu không có khung nào như vậy.
    """
    T, N = R.shape
    cuoi = np.asarray(khung.dayofweek >= 5, dtype=np.int64)
    o = np.asarray(khung.hour * 4 + khung.minute // 15, dtype=np.int64)
    co = ~np.isnan(R)
    gia_tri = np.where(co, R, 0).astype(np.float64)
    tong, dem = np.zeros((2, 96, N)), np.zeros((2, 96, N))
    np.add.at(tong, (cuoi[:cat], o[:cat]), gia_tri[:cat])
    np.add.at(dem, (cuoi[:cat], o[:cat]), co[:cat])
    t, d = tong[cuoi, o], dem[cuoi, o]              # (T, N): tổng, số mẫu của nhóm mà từng khung thuộc về
    t[:cat] -= gia_tri[:cat]                        # khung học: bỏ chính nó (khung thiếu trừ 0)
    d[:cat] -= co[:cat]
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(d > 0, t / d, np.nan).astype(np.float32)
