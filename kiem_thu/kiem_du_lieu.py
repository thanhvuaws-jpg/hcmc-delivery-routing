"""
Kiểm bất biến trên DỮ LIỆU THẬT của mọi tầng (KE_HOACH_DU_LIEU mục 9) — chạy sau mỗi lần
dựng lại tầng bạc/vàng. Mỗi mục in ĐẠT / KHÔNG ĐẠT kèm con số; có mục không đạt thì mã thoát 1.

    python kiem_thu/kiem_du_lieu.py
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BAC = os.path.join(GOC, 'du_lieu', 'bac')
VANG = os.path.join(GOC, 'du_lieu', 'vang')
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))

ket_qua = []


def kiem(ten, dat, chi_tiet=''):
    ket_qua.append(bool(dat))
    print(f'  [{"DAT" if dat else "KHONG DAT"}] {ten}' + (f' — {chi_tiet}' if chi_tiet else ''))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from ghep_tomtom import BoGhep, TEP_CANH
    bo = BoGhep.nap()
    canh = pd.read_parquet(TEP_CANH)
    n_canh = len(canh)

    print('Do thi / chi muc')
    kiem('bang canh khop chi muc', len(bo.xy) == n_canh, f'{n_canh:,} canh, ma {bo.ma_do_thi}')
    kiem('chi_so lien tuc 0..n-1', (canh['chi_so'].to_numpy() == np.arange(n_canh)).all())

    print('Tang bac TomTom')
    tt = json.load(open(os.path.join(BAC, 'tomtom_canh', '_trang_thai.json'), encoding='utf-8'))
    kiem('moi ngay da ghep theo do thi hien tai', all(v['ma_do_thi'] == bo.ma_do_thi for v in tt.values()),
         f'{len(tt)} ngay')
    for tep in sorted(glob.glob(os.path.join(BAC, 'tomtom_canh', '*.parquet'))):
        s = pd.read_parquet(tep)
        ngay = os.path.basename(tep)[:10]
        kiem(f'{ngay}: khoa (khung, chi_so) khong trung', not s.duplicated(['khung', 'chi_so']).any(), f'{len(s):,} dong')
        kiem(f'{ngay}: muc, phu trong 0..100', s['muc'].between(0, 100).all() and s['phu'].between(0, 100).all())
        kiem(f'{ngay}: khung tron 5 phut, dung ngay', (s['khung'].dt.minute % 5 == 0).all()
             and (s['khung'].dt.second == 0).all() and (s['khung'].dt.strftime('%Y-%m-%d') == ngay).all())
        kiem(f'{ngay}: chi_so hop le', s['chi_so'].between(0, n_canh - 1).all())
        kd = s['toc_do'].dropna()
        kiem(f'{ngay}: toc_do (km/h) trong 0..130', kd.between(0, 130).all(),
             f'{len(kd):,} gia tri, max {kd.max() if len(kd) else "-"}')
        kiem(f'{ngay}: dong_duong = (phu_dong > 0)', (s['dong_duong'] == (s['phu_dong'] > 0)).all(),
             f'{int(s["dong_duong"].sum()):,} dong co phan dong, {int((s["phu"] == 0).sum()):,} dong dong het')
        kiem(f'{ngay}: moi dong co phan mo hoac phan dong', ((s['phu'] > 0) | (s['phu_dong'] > 0)).all())
        kiem(f'{ngay}: canh dong het thi muc = 0 (khong co phan mo de tinh)',
             (s.loc[s['phu'] == 0, 'muc'] == 0).all())

    print('Su co')
    sc = pd.read_parquet(os.path.join(BAC, 'su_co.parquet'))
    kiem('ma su co khong trung', sc['id'].is_unique, f'{len(sc):,} su co')
    tat_ca_canh = np.concatenate([np.asarray(c, dtype=np.int64) for c in sc['canh'] if len(c)]) \
        if sc['canh'].map(len).sum() else np.array([], dtype=np.int64)
    kiem('canh cua su co hop le', ((tat_ca_canh >= 0) & (tat_ca_canh < n_canh)).all())
    kiem('lan_dau <= lan_cuoi', (sc['lan_dau'] <= sc['lan_cuoi']).all())

    print('Doan duong')
    cd = pd.read_parquet(os.path.join(BAC, 'canh_doan.parquet'))
    doan = pd.read_parquet(os.path.join(BAC, 'doan.parquet'))
    kiem('moi canh thuoc dung 1 doan', len(cd) == n_canh and (cd['doan'] >= 0).all() and cd['chi_so'].is_unique)
    x = cd.merge(canh[['chi_so', 'u', 'v', 'dai']], on='chi_so').sort_values(['doan', 'thu_tu'])
    lien = (x['v'].shift().to_numpy() == x['u'].to_numpy()) | (x['thu_tu'].to_numpy() == 0)
    kiem('canh trong doan noi lien (v truoc = u sau)', lien.all(), f'{(~lien).sum()} cho dut')
    dem = x.groupby('doan')['thu_tu'].agg(['min', 'max', 'size'])
    kiem('thu_tu lien tuc tu 0', ((dem['min'] == 0) & (dem['max'] == dem['size'] - 1)).all())
    kiem('dai doan = tong dai canh', np.allclose(doan.set_index('doan').loc[dem.index, 'dai'],
                                                 x.groupby('doan')['dai'].sum(), rtol=1e-4))

    print('Tang vang')
    for tep in sorted(glob.glob(os.path.join(VANG, '*.parquet'))):
        v = pd.read_parquet(tep)
        ngay = os.path.basename(tep)[:10]
        kiem(f'{ngay}: khoa (khung, doan) khong trung', not v.duplicated(['khung', 'doan']).any(), f'{len(v):,} dong')
        kiem(f'{ngay}: khung tron 15 phut', (v['khung'].dt.minute % 15 == 0).all())
        for c in ('r', 'y_15', 'y_30', 'y_60', 'r_tru_1', 'ty_le_dong'):
            kiem(f'{ngay}: {c} trong 0..1', v[c].dropna().between(0, 1).all())
        kiem(f'{ngay}: khong con r = 0 do dong duong', not ((v['r'] == 0) & (v['ty_le_dong'] > 0)).any())
        k = v.set_index(['doan', 'khung'])['r']
        a = k.reindex(pd.MultiIndex.from_arrays([v['doan'], v['khung'] + pd.Timedelta('15min')])).to_numpy()
        b = v['y_15'].to_numpy()
        m = ~np.isnan(a) & ~np.isnan(b)
        kiem(f'{ngay}: y_15 = r(t+15) (trong ngay)', np.allclose(a[m], b[m]), f'{m.sum():,} cap')

    print('Lich / thoi tiet')
    li = pd.read_parquet(os.path.join(BAC, 'lich.parquet'))
    kiem('lich lien tuc tung ngay', (li['ngay'].diff().dropna() == pd.Timedelta('1D')).all(), f'{len(li)} ngay')
    tg = pd.read_parquet(os.path.join(BAC, 'thoi_tiet_gio.parquet'))
    kiem('thoi tiet (gio, diem) khong trung', not tg.duplicated(['thoi_gian', 'diem']).any())
    kiem('mua >= 0', (tg['precipitation'].dropna() >= 0).all())
    lt = tg[tg['nguon'] == 'luu_tru']
    gio_du = pd.date_range(lt['thoi_gian'].min(), lt['thoi_gian'].max(), freq='h')
    kiem('luu tru thoi tiet du moi gio', lt.groupby('diem')['thoi_gian'].nunique().eq(len(gio_du)).all(),
         f'{len(gio_du):,} gio x {lt["diem"].nunique()} diem')

    dat = sum(ket_qua)
    print(f'\n{dat}/{len(ket_qua)} muc DAT')
    return 0 if dat == len(ket_qua) else 1


if __name__ == '__main__':
    sys.exit(main())
