"""
Dự báo NGOÀI MẪU cho mọi khung từ sau mốc cắt học tới dữ liệu mới nhất (QĐ-029): để lớp dự báo của API / web có số cả
cho những ngày thu về SAU lần train chính, tức dự báo "bây giờ".

Mô hình: GBM + hồ sơ y như moc_so_sanh / so_sanh_du_bao, học trên phần học CỐ ĐỊNH (tới HET_HOC = mốc cắt của lần train
chính 12–13/11). Không học lại khi có dữ liệu mới, nên mọi dự báo sau mốc đều là ngoài mẫu. Hồ sơ và tình trạng chung cũng
chỉ dựng từ phần học. Mô hình lưu bằng joblib, lần sau chỉ cần dự báo (vài phút thay vì ~15 phút).
Tự kiểm: trên các ô trùng với tệp dự báo cũ của so_sanh_du_bao.py phải ra cùng số (bỏ các khung cuối của tệp cũ, nơi
dữ liệu lúc đó chưa đủ).

Chạy:  python du_bao_moi.py [--hoc-lai]
Ra:    mo_hinh/ket_qua/du_bao_gbm_ls_<ngày cuối dữ liệu>.parquet, gbm_ls_hoc_toi_<mốc>.joblib (đều không lên git)
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

HET_HOC = '2026-11-08 16:15'            # mốc cắt của lần train chính (QĐ-026)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    bang = BangHoc(het_hoc=HET_HOC)
    print(f'hoc toi {bang.het_hoc}, kiem tu {bang.dau_kiem}, du lieu toi {bang.khung[-1]}; {len(bang.dac_trung)} dac trung',
          flush=True)
    tep_mh = os.path.join(RA, f'gbm_ls_hoc_toi_{pd.Timestamp(HET_HOC):%Y%m%d_%H%M}.joblib')
    mh = joblib.load(tep_mh) if os.path.exists(tep_mh) and '--hoc-lai' not in sys.argv else None
    if mh is not None and mh['dac_trung'] != bang.dac_trung:
        print('dac trung khac luc luu mo hinh -> hoc lai')
        mh = None
    if mh is None:
        mh = {'dac_trung': bang.dac_trung, 'het_hoc': HET_HOC}
        for h, y in NHAN.items():
            t = time.time()
            a = bang.nhan(bang.hoc, y)
            m = tao_gbm_chung(bang.dac_trung.index('loai'))
            m.fit(bang.X(a, int(h)), (a[y] - a['r']).to_numpy())
            mh[h] = m
            print(f'hoc GBM + ho so {h} phut: {time.time() - t:.0f}s', flush=True)
        joblib.dump(mh, tep_mh)
    b = bang.kiem[bang.kiem['r'].notna()]
    ra = pd.DataFrame({'khung': b['khung'].to_numpy(), 'doan': b['doan'].to_numpy(), 'r': b['r'].to_numpy()})
    for h, y in NHAN.items():
        ra[f'du_{h}'] = np.clip(b['r'].to_numpy() + mh[h].predict(bang.X(b, int(h))), 0, 1).astype(np.float32)
        ra[y] = b[y].to_numpy()
    cuoi = pd.Timestamp(bang.khung[-1])
    tep = os.path.join(RA, f'du_bao_gbm_ls_{cuoi:%Y-%m-%d}.parquet')

    # Tự kiểm với tệp cũ (bỏ 2 giờ cuối của tệp cũ: lúc đó khung cuối có thể chưa đủ lần chụp).
    for cu in sorted(glob.glob(os.path.join(RA, 'du_bao_gbm_ls_*.parquet'))):
        if os.path.abspath(cu) == os.path.abspath(tep):
            continue
        c = pd.read_parquet(cu, columns=['khung', 'doan', 'du_15', 'du_30', 'du_60'])
        c = c[c['khung'] <= c['khung'].max() - pd.Timedelta(hours=2)]
        m = c.merge(ra, on=['khung', 'doan'], suffixes=('_cu', ''))
        lech = max(float((m[f'du_{h}_cu'] - m[f'du_{h}']).abs().max()) for h in NHAN)
        print(f'tu kiem voi {os.path.basename(cu)}: {len(m):,}/{len(c):,} o trung, lech lon nhat {lech:.2e}')

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
