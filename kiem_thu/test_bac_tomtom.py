"""Tầng bạc TomTom: trung vị trượt, cờ Hampel, khung 5 phút, khoảng trống."""
import numpy as np
import pandas as pd

import bac_tomtom as bt


def test_trung_vi_truot_bang_pandas():
    rng = np.random.default_rng(0)
    M = rng.integers(0, 101, size=(120, 37)).astype(np.float32)
    M[rng.random(M.shape) < 0.15] = np.nan
    mong = pd.DataFrame(M).rolling(13, center=True, min_periods=5).median().to_numpy()
    assert np.allclose(bt.trung_vi_truot(M, khoi=10), mong, equal_nan=True)


def bang(chuoi):
    """Một cạnh, chuỗi mức theo khung 5 phút -> bảng dạng tầng bạc."""
    k = pd.date_range('2026-10-30 07:00', periods=len(chuoi), freq='5min')
    return pd.DataFrame({'khung': k, 'chi_so': 0, 'muc': np.array(chuoi, dtype=np.uint8)})


def test_hampel_bat_diem_nhay_don_le():
    c = [80] * 30
    c[10] = 20
    assert np.flatnonzero(bt.co_hampel(bang(c))).tolist() == [10]


def test_hampel_khong_bat_buoc_nhay_bac_thang():
    assert not bt.co_hampel(bang([80] * 20 + [40] * 20)).any()


def test_hampel_khong_bat_dao_dong_duoi_san():
    rng = np.random.default_rng(1)
    c = np.clip(70 + rng.integers(-6, 7, 60), 0, 100)        # ±6 điểm < sàn 15
    assert not bt.co_hampel(bang(c)).any()


def test_khung_cua_lam_tron_5_phut():
    assert bt.khung_cua('x/2026-10-30/0747.parquet') == pd.Timestamp('2026-10-30 07:45').to_pydatetime()
    assert bt.khung_cua('x/2026-10-30/0001.zip') == pd.Timestamp('2026-10-30 00:00').to_pydatetime()


def test_khoang_trong():
    k = list(pd.date_range('2026-10-30 07:00', periods=4, freq='5min'))
    k += list(pd.date_range('2026-10-30 07:35', periods=2, freq='5min'))   # thiếu 07:20, 07:25, 07:30
    kt = bt.khoang_trong(k)
    assert len(kt) == 1 and kt.iloc[0]['so_khung'] == 3
    assert kt.iloc[0]['tu'] == pd.Timestamp('2026-10-30 07:20')
