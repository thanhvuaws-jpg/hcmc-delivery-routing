"""
Bảng dữ liệu và đặc trưng dùng chung cho các script dự báo (moc_so_sanh, kiem_doan_mo, ablation): cùng một cách
chia theo thời gian và cùng đặc trưng, để số của các script so được với nhau.

Chia: 70% khung đầu để học, chừa KHOANG_HO khung (nhãn 60 phút của khung học cuối không rơi vào kiểm tra), phần
sau để kiểm tra. Mọi đặc trưng ở khung t chỉ dùng thông tin có tới t.

Đặc trưng thêm ngoài tầng vàng:
  r_ls_dich, ls_tru_r, lech_ls  hồ sơ lịch sử của đoạn ở giờ đích, khoảng cách tới nó, độ lệch hiện tại so với
                                bình thường (ho_so_lich_su.py, đã chống rò rỉ, QĐ-020);
  chung, chung_1h               TÌNH TRẠNG CHUNG TOÀN MẠNG: TB (r − hồ sơ) của mọi đoạn ở khung t và thay đổi so với
                                1 giờ trước. M5 (QĐ-021): phần lớn tương quan giữa các đoạn xa nhau là biến động
                                chung (mưa, ngày vắng…), nên báo thẳng cho mô hình.
"""
import glob
import os
import warnings

import numpy as np
import pandas as pd

from ho_so_lich_su import ho_so_mo_rong

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VANG = os.path.join(GOC, 'du_lieu', 'vang')
TY_LE_HOC = 0.7
KHOANG_HO = 4                   # 4 khung = 60 phút
NHAN = {'15': 'y_15', '30': 'y_30', '60': 'y_60'}

# Nhóm đặc trưng để đo đóng góp (ablation): câu hỏi 3 của đề tài là sự cố và thời tiết.
NHOM = {
    'su_co': ['su_co', 'tre_su_co_s', 'ty_le_dong'],
    'thoi_tiet': ['mua_db_0', 'mua_db_1', 'kn_mua_db_1'],
    'lan_can': ['r_thuong', 'r_ha'],
    'ho_so': ['r_ls_dich', 'ls_tru_r', 'lech_ls'],
    'chung': ['chung', 'chung_1h'],
}


def chung_toan_mang(R, H):
    """TB (r − hồ sơ) trên mọi đoạn ở từng khung; khung không có số đo nào -> NaN."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        return np.nanmean(R - H, axis=1).astype(np.float32)


class BangHoc:
    def __init__(self, het_hoc=None):
        """het_hoc: mốc cắt CỐ ĐỊNH (khung học cuối) thay cho 70% khung đầu — để dự báo dữ liệu mới bằng mô hình đã train
        mà phần học, hồ sơ, tình trạng chung không đổi theo lượng dữ liệu (du_bao_moi.py)."""
        d = pd.concat([pd.read_parquet(t) for t in sorted(glob.glob(os.path.join(VANG, '*.parquet')))],
                      ignore_index=True)
        self.d = d
        self.khung = np.sort(d['khung'].unique())
        self.cat = (int(len(self.khung) * TY_LE_HOC) if het_hoc is None else
                    int(np.searchsorted(self.khung, np.datetime64(pd.Timestamp(het_hoc)), side='right')))
        self.het_hoc = self.khung[self.cat - 1]
        self.dau_kiem = self.khung[min(self.cat + KHOANG_HO, len(self.khung) - 1)]
        self.kiem = d[d['khung'] >= self.dau_kiem]
        doan = np.sort(d['doan'].unique())
        self.fi = np.searchsorted(self.khung, d['khung'].to_numpy())
        self.ni = np.searchsorted(doan, d['doan'].to_numpy())
        self.R = np.full((len(self.khung), len(doan)), np.nan, dtype=np.float32)
        self.R[self.fi, self.ni] = d['r'].to_numpy()
        self.dat_bo_dau(0.0)

    def dat_bo_dau(self, bo_dau):
        """Phần học = khung [dau, cat) với dau = bo_dau × cat: bỏ bớt NGÀY CŨ NHẤT (đường cong học,
        duong_cong_hoc.py). Hồ sơ và tình trạng chung cũng chỉ tính từ phần còn lại. Phần kiểm tra giữ nguyên."""
        d = self.d
        self.dau = int(self.cat * bo_dau)
        self.dau_hoc = self.khung[self.dau]
        self.hoc = d[(d['khung'] >= self.dau_hoc) & (d['khung'] <= self.het_hoc)]
        bo = {'khung', 'doan', *NHAN.values()}
        # Cột chưa có ít nhất 2 giá trị trong phần học (vd r_tuan_truoc khi chưa đủ tuần) thì bỏ —
        # scikit-learn không chia khoảng được, và cột đó cũng chưa có gì để học.
        self.bo_vi_trong = [c for c in d.columns if c not in bo and self.hoc[c].nunique(dropna=True) < 2]
        self.dac_trung = [c for c in d.columns if c not in bo and c not in self.bo_vi_trong]
        # H có thêm KHOANG_HO khung sau khung cuối: khung mới nhất cũng có hồ sơ ở giờ đích (QĐ-029 mục 6).
        self.H = ho_so_mo_rong(self.R, pd.DatetimeIndex(self.khung), self.cat, self.dau, KHOANG_HO)
        self.chung = chung_toan_mang(self.R, self.H[:len(self.khung)])
        self.so_o_chung_co = int(np.isfinite(self.chung).sum())

    def nhan(self, phan, y_cot):
        """Các dòng có r hiện tại và có nhãn y_cot."""
        return phan[phan[y_cot].notna() & phan['r'].notna()]

    def X(self, dong, phut, co_ho_so=True):
        """Ma trận đặc trưng của các dòng (giữ chỉ số gốc của d) cho tầm dự báo `phut` phút, kiểu float32."""
        X = dong[self.dac_trung].copy()
        X['loai'] = X['loai'].cat.codes
        if co_ho_so:
            vt = dong.index.to_numpy()
            dich = self.fi[vt] + phut // 15
            r = dong['r'].to_numpy()
            h_dich = np.where(dich < len(self.H), self.H[np.minimum(dich, len(self.H) - 1), self.ni[vt]], np.nan)
            X['r_ls_dich'] = h_dich
            X['ls_tru_r'] = h_dich - r
            X['lech_ls'] = r - self.H[self.fi[vt], self.ni[vt]]
            f = self.fi[vt]
            X['chung'] = self.chung[f]
            X['chung_1h'] = self.chung[f] - np.where(f >= 4, self.chung[np.maximum(f - 4, 0)], np.nan)
        return X.astype(np.float32)
