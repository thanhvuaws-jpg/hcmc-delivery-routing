"""
Tổng hợp chấm tuyến bằng tốc độ thật qua NHIỀU NGÀY (kế hoạch tuần 10: thống kê, kiểm định ý nghĩa).

Đọc danh_gia/ket_qua/cham_tuyen_<ngày>[_zenodo].csv do cham_tuyen_that.py tạo; hai bộ điểm báo riêng:
  dia_danh  10 địa danh chọn tay, 90 cặp;
  zenodo    90 cặp điểm giao hàng thật (D13).
So tuyến tối ưu D, tính lại giữa đường E, nhanh nhất C với tuyến ngắn nhất A và bản đồ thường B.

Một chuyến KHÔNG độc lập với chuyến khác cùng cặp điểm hay cùng ngày, nên:
  khoảng tin cậy  bootstrap 95% lấy mẫu lại theo CẶP ĐIỂM (giữ nguyên mọi chuyến của cặp đó);
  kiểm định       Wilcoxon dấu–hạng trên chênh lệch TB của từng cặp điểm, không phải từng chuyến;
  ổn định         tiêu chí kế hoạch kiểm trên TỪNG ngày và từng khung giờ, không chỉ con số gộp.
Tiêu chí kế hoạch: D không chậm hơn A ở ≥ 80% chuyến, nhanh hơn trung bình ≥ 5%.

Chạy:  python tong_hop_cham.py
Ra:    danh_gia/ket_qua/tong_hop_<bộ điểm>.csv, tong_hop_tom_tat.json, tong_hop_theo_gio.png
"""
import glob
import json
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from scipy.stats import wilcoxon                      # noqa: E402

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RA = os.path.join(GOC, 'danh_gia', 'ket_qua')
BOOT = 2000
SAI_SO_BANG = 0.05              # chênh dưới 0,05 phút (3 giây) coi như bằng nhau, như cham_tuyen_that.py
THU = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']


def nap(bo):
    mau = re.compile(r'cham_tuyen_(\d{4}-\d\d-\d\d)' + ('_zenodo' if bo == 'zenodo' else '') + r'\.csv$')
    phan = []
    for t in sorted(glob.glob(os.path.join(RA, 'cham_tuyen_*.csv'))):
        m = mau.search(os.path.basename(t))
        if m:
            x = pd.read_csv(t, encoding='utf-8-sig')
            if 'phut_kk_A' in x.columns:        # bỏ các tệp của phiên bản cũ (chưa có giờ chiều, chưa có khắt khe)
                phan.append(x.assign(ngay=m[1]))
    return pd.concat(phan, ignore_index=True) if phan else None


def nhanh_hon(g, a='A', b='D', tien_to='phut_'):
    """% tổng thời gian b nhanh hơn a."""
    return 100 * (1 - g[f'{tien_to}{b}'].sum() / g[f'{tien_to}{a}'].sum())


def khong_cham(g, a='A', b='D', tien_to='phut_'):
    return float((g[f'{tien_to}{b}'] <= g[f'{tien_to}{a}'] + SAI_SO_BANG).mean())


def hang_tom_tat(g):
    return {'so_chuyen': len(g), 'phut_A': round(g['phut_A'].mean(), 1), 'phut_D': round(g['phut_D'].mean(), 1),
            'D_nhanh_hon_A_pct': round(nhanh_hon(g), 1), 'D_khong_cham_A': round(khong_cham(g), 3),
            'E_nhanh_hon_A_pct': round(nhanh_hon(g, 'A', 'E'), 1), 'C_nhanh_hon_B_pct': round(nhanh_hon(g, 'B', 'C'), 1),
            'D_nhanh_hon_B_pct': round(nhanh_hon(g, 'B', 'D'), 1),
            'kk_D_nhanh_hon_A_pct': round(nhanh_hon(g, tien_to='phut_kk_'), 1),
            'kk_D_khong_cham_A': round(khong_cham(g, tien_to='phut_kk_'), 3),
            'vao_dong_A': int(g['vao_dong_A'].sum()), 'vao_dong_D': int(g['vao_dong_D'].sum()),
            'vao_dong_E': int(g['vao_dong_E'].sum()), 'do_that_D': round(g['do_that_D'].mean(), 3)}


def dat(h):
    return h['D_nhanh_hon_A_pct'] >= 5 and h['D_khong_cham_A'] >= 0.8


def kiem_dinh(k, a='A', b='D', hat=42):
    """Bootstrap theo cặp điểm cho % nhanh hơn, Wilcoxon trên chênh TB từng cặp."""
    k = k.assign(cap=k['di'] + '|' + k['den'])
    tong = k.groupby('cap')[[f'phut_{a}', f'phut_{b}']].sum().to_numpy()
    rng = np.random.default_rng(hat)
    chon = rng.integers(0, len(tong), (BOOT, len(tong)))
    pct = 100 * (1 - tong[chon, 1].sum(axis=1) / tong[chon, 0].sum(axis=1))
    lech = k.groupby('cap')[[f'phut_{a}', f'phut_{b}']].mean().to_numpy()
    w = wilcoxon(lech[:, 0], lech[:, 1])
    return {'so_cap': len(tong), 'pct': round(nhanh_hon(k, a, b), 2), 'ci95': [round(float(x), 2) for x in np.percentile(pct, [2.5, 97.5])],
            'wilcoxon_p': float(w.pvalue), 'cap_b_nhanh_hon': round(float((lech[:, 1] < lech[:, 0]).mean()), 3)}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tom_tat = {}
    fig, truc = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for bo, ax in zip(('zenodo', 'dia_danh'), truc):
        k = nap(bo)
        if k is None:
            print(f'{bo}: chua co du lieu')
            continue
        k['thu'] = pd.to_datetime(k['ngay']).dt.dayofweek
        k['cuoi_tuan'] = k['thu'] >= 5
        print(f'\n===== {bo}: {len(k):,} chuyen, {k["ngay"].nunique()} ngay, {k[["di", "den"]].drop_duplicates().shape[0]} cap =====')
        cot = ['so_chuyen', 'phut_A', 'phut_D', 'D_nhanh_hon_A_pct', 'D_khong_cham_A', 'E_nhanh_hon_A_pct', 'D_nhanh_hon_B_pct',
               'kk_D_nhanh_hon_A_pct', 'kk_D_khong_cham_A', 'vao_dong_A', 'vao_dong_D', 'vao_dong_E']
        theo_ngay = pd.DataFrame({n: hang_tom_tat(g) for n, g in k.groupby('ngay')}).T
        theo_ngay.insert(0, 'thu', [THU[pd.Timestamp(n).dayofweek] for n in theo_ngay.index])
        theo_ngay['dat'] = [dat(h) for _, h in theo_ngay.iterrows()]
        print(theo_ngay[['thu', *cot, 'dat']].to_string())
        theo_gio = pd.DataFrame({(ct, gio): hang_tom_tat(g) for (ct, gio), g in k.groupby(['cuoi_tuan', 'gio'])}).T
        theo_gio['dat'] = [dat(h) for _, h in theo_gio.iterrows()]
        print('\nTheo gio (False = ngay thuong, True = cuoi tuan):')
        print(theo_gio[cot + ['dat']].to_string())
        toan_bo = hang_tom_tat(k)
        kd = {'D_so_A': kiem_dinh(k), 'E_so_A': kiem_dinh(k, 'A', 'E'), 'D_so_B': kiem_dinh(k, 'B', 'D'), 'C_so_B': kiem_dinh(k, 'B', 'C'),
              'E_so_D': kiem_dinh(k, 'D', 'E')}
        print('\nToan bo:', json.dumps(toan_bo, ensure_ascii=False))
        for ten, x in kd.items():
            print(f'  {ten}: nhanh hon {x["pct"]:+.2f}% (95% CI {x["ci95"][0]:+.2f} .. {x["ci95"][1]:+.2f}), Wilcoxon p = {x["wilcoxon_p"]:.2e}, '
                  f'{x["cap_b_nhanh_hon"]:.0%} cap nhanh hon')
        print(f'TIEU CHI: dat {int(theo_ngay["dat"].sum())}/{len(theo_ngay)} ngay; khat khe dat '
              f'{int(((theo_ngay["kk_D_nhanh_hon_A_pct"] >= 5) & (theo_ngay["kk_D_khong_cham_A"] >= 0.8)).sum())}/{len(theo_ngay)} ngay; '
              f'{int(theo_gio["dat"].sum())}/{len(theo_gio)} khung gio')
        tom_tat[bo] = {'toan_bo': toan_bo, 'kiem_dinh': kd, 'so_ngay': int(k['ngay'].nunique()),
                       'ngay_dat': int(theo_ngay['dat'].sum()), 'gio_dat': int(theo_gio['dat'].sum()), 'so_gio': len(theo_gio)}
        theo_ngay.to_csv(os.path.join(RA, f'tong_hop_{bo}_theo_ngay.csv'), encoding='utf-8-sig')
        theo_gio.to_csv(os.path.join(RA, f'tong_hop_{bo}_theo_gio.csv'), encoding='utf-8-sig')
        for ct, nhan, mau in ((False, 'Ngày thường', '#2a78d6'), (True, 'Cuối tuần', '#eb6834')):
            x = theo_gio.loc[ct]
            ax.plot(x.index, x['D_nhanh_hon_A_pct'].astype(float), color=mau, lw=2, marker='o', ms=5, label=nhan)
        ax.axhline(5, color='#52514e', lw=1, ls='--')
        ax.text(0.1, 5.6, 'Tiêu chí 5%', color='#52514e', fontsize=9)
        ax.set_title(f'{"Điểm giao hàng thật" if bo == "zenodo" else "10 địa danh"}: tuyến tối ưu nhanh hơn tuyến ngắn nhất', fontsize=10)
        ax.set_xlabel('Giờ xuất phát')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', color='#e4e3df', lw=0.8)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
    truc[0].set_ylabel('Nhanh hơn (%)')
    fig.tight_layout()
    fig.savefig(os.path.join(RA, 'tong_hop_theo_gio.png'), dpi=150)
    with open(os.path.join(RA, 'tong_hop_tom_tat.json'), 'w', encoding='utf-8') as f:
        json.dump(tom_tat, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
