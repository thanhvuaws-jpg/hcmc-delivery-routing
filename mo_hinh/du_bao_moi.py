"""
Dự báo NGOÀI MẪU cho mọi khung từ sau mốc cắt học tới dữ liệu mới nhất (QĐ-029): để lớp dự báo của API / web có số cả
cho những ngày thu về SAU lần train chính, tức dự báo "bây giờ".

Mô hình: GBM + hồ sơ, học trên phần học CỐ ĐỊNH (tới HET_HOC = mốc cắt của lần train chính 12–13/11).
  Từ 14/11 (QĐ-032, chọn trong phần học rồi chấm một lần): 15 / 30 phút mất mát TUYỆT ĐỐI, học y − r; 60 phút mất mát
  tuyệt đối, học y − hồ sơ giờ đích (r_ls_dich, ô chưa có hồ sơ lấy r). MAE tập kiểm tra 5,323 / 5,954 / 6,047
  (cũ 5,475 / 6,167 / 6,292). --cu: như moc_so_sanh (bình phương, y − r), ra du_bao_gbm_v0_<ngày>.parquet. Không học lại khi có dữ liệu mới, nên mọi dự báo sau mốc đều là ngoài mẫu. Hồ sơ và tình trạng chung cũng
chỉ dựng từ phần học. Mô hình lưu bằng joblib, lần sau chỉ cần dự báo (vài phút thay vì ~15 phút).
Tự kiểm: (1) trên các ô trùng với tệp dự báo cũ CÙNG cấu hình phải ra cùng số (bỏ các khung cuối của tệp cũ, nơi dữ liệu
lúc đó chưa đủ); (2) MAE trên tập kiểm tra của lần train chính (nhãn ≤ CUOI_CU) phải ra đúng số đã báo (KY_VONG).

Chạy:  python du_bao_moi.py [--hoc-lai] [--cu]
Ra:    mo_hinh/ket_qua/du_bao_gbm_ls_<ngày cuối dữ liệu>.parquet (API / chấm tuyến đọc tệp này),
       gbm_ls_qd032_hoc_toi_<mốc>.joblib (đều không lên git)
Sau khi kéo dữ liệu mới: he_thong/cap_nhat_du_lieu.sh chạy cả chuỗi.
"""
import glob
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd

from dac_trung import NHAN, BangHoc
from moc_so_sanh import RA, danh_gia, mae_theo_ngay, tao_gbm_chung
from thu_dich_mat_mat import tao_gbm

HET_HOC = '2026-11-08 16:15'            # mốc cắt của lần train chính (QĐ-026)
CUOI_CU = pd.Timestamp('2026-11-12 22:30')
# tầm -> (mất mát, gốc của đích học), QĐ-032; None = như moc_so_sanh (bình phương, gốc r).
CAU_HINH = {'15': ('absolute_error', 'r'), '30': ('absolute_error', 'r'), '60': ('absolute_error', 'ho_so')}
KY_VONG = {'15': 5.323, '30': 5.954, '60': 6.047}
KY_VONG_CU = {'15': 5.475, '30': 6.167, '60': 6.292}


def goc(bang, d, h, X=None, cau_hinh=None):
    """Gốc của đích học / dự báo: r hiện tại, hoặc hồ sơ giờ đích (ô chưa có hồ sơ -> r)."""
    if cau_hinh is None or cau_hinh[h][1] == 'r':
        return d['r'].to_numpy()
    X = bang.X(d, int(h)) if X is None else X
    hs = X['r_ls_dich'].to_numpy()
    return np.where(np.isnan(hs), d['r'].to_numpy(), hs)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bang = BangHoc(het_hoc=HET_HOC)
    print(f'hoc toi {bang.het_hoc}, kiem tu {bang.dau_kiem}, du lieu toi {bang.khung[-1]}; {len(bang.dac_trung)} dac trung',
          flush=True)
    cu = '--cu' in sys.argv
    cau_hinh = None if cu else CAU_HINH
    ky_vong = KY_VONG_CU if cu else KY_VONG
    ten_mh = 'gbm_ls' if cu else 'gbm_ls_qd032'
    tep_mh = os.path.join(RA, f'{ten_mh}_hoc_toi_{pd.Timestamp(HET_HOC):%Y%m%d_%H%M}.joblib')
    mh = joblib.load(tep_mh) if os.path.exists(tep_mh) and '--hoc-lai' not in sys.argv else None
    if mh is not None and mh['dac_trung'] != bang.dac_trung:
        print('dac trung khac luc luu mo hinh -> hoc lai')
        mh = None
    if mh is None:
        mh = {'dac_trung': bang.dac_trung, 'het_hoc': HET_HOC, 'cau_hinh': cau_hinh}
        for h, y in NHAN.items():
            t = time.time()
            a = bang.nhan(bang.hoc, y)
            Xa = bang.X(a, int(h))
            m = (tao_gbm_chung(bang.dac_trung.index('loai')) if cu else
                 tao_gbm(cau_hinh[h][0], bang.dac_trung.index('loai')))
            m.fit(Xa, a[y].to_numpy() - goc(bang, a, h, Xa, cau_hinh))
            mh[h] = m
            del a, Xa
            print(f'hoc GBM + ho so {h} phut: {time.time() - t:.0f}s', flush=True)
        joblib.dump(mh, tep_mh)
    b = bang.kiem[bang.kiem['r'].notna()]
    ra = pd.DataFrame({'khung': b['khung'].to_numpy(), 'doan': b['doan'].to_numpy(), 'r': b['r'].to_numpy()})
    for h, y in NHAN.items():
        Xb = bang.X(b, int(h))
        ra[f'du_{h}'] = np.clip(goc(bang, b, h, Xb, cau_hinh) + mh[h].predict(Xb), 0, 1).astype(np.float32)
        ra[y] = b[y].to_numpy()
    cuoi = pd.Timestamp(bang.khung[-1])
    tien_to = 'du_bao_gbm_v0_' if cu else 'du_bao_gbm_ls_'
    tep = os.path.join(RA, f'{tien_to}{cuoi:%Y-%m-%d}.parquet')

    # Tự kiểm với tệp cũ (bỏ 2 giờ cuối của tệp cũ: lúc đó khung cuối có thể chưa đủ lần chụp).
    for tep_cu in sorted(glob.glob(os.path.join(RA, f'{tien_to}*.parquet'))):
        if os.path.abspath(tep_cu) == os.path.abspath(tep):
            continue
        c = pd.read_parquet(tep_cu, columns=['khung', 'doan', 'du_15', 'du_30', 'du_60'])
        c = c[c['khung'] <= c['khung'].max() - pd.Timedelta(hours=2)]
        m = c.merge(ra, on=['khung', 'doan'], suffixes=('_cu', ''))
        lech = max(float((m[f'du_{h}_cu'] - m[f'du_{h}']).abs().max()) for h in NHAN)
        print(f'tu kiem voi {os.path.basename(tep_cu)}: {len(m):,}/{len(c):,} o trung, lech lon nhat {lech:.2e}')
    for h, y in NHAN.items():
        x = ra[ra[y].notna() & (ra['khung'] + pd.Timedelta(minutes=int(h)) <= CUOI_CU)]
        mae = danh_gia(x[y].to_numpy(), x[f'du_{h}'].to_numpy(), x['r'].to_numpy(), x['khung'].dt.hour.to_numpy())['mae']
        print(f'tu kiem MAE tap kiem tra {h} phut: {mae:.3f} (da bao {ky_vong[h]}'
              f'{", KHONG KHOP" if abs(mae - ky_vong[h]) > 0.002 else ""})')

    ra.to_parquet(tep, index=False)
    print(f'{len(ra):,} o, khung {ra["khung"].min()} -> {ra["khung"].max()} -> {tep}')
    for h, y in NHAN.items():
        x = ra[ra[y].notna()]
        ngay = x['khung'].dt.strftime('%Y-%m-%d').to_numpy()
        print(f'  {h} phut (o co nhan): MAE {danh_gia(x[y].to_numpy(), x[f"du_{h}"].to_numpy(), x["r"].to_numpy(), x["khung"].dt.hour.to_numpy())["mae"]:.3f}'
              f' | theo ngay {mae_theo_ngay(x[y].to_numpy(), x[f"du_{h}"].to_numpy(), ngay)}')
    print(f'({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
