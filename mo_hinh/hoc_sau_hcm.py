"""
Học sâu dự báo mức kẹt trên dữ liệu THẬT TP.HCM (tầng vàng: đoạn đường × khung 15 phút), dùng lại mã mô hình
đã tái lập đúng bài báo trên METR-LA (hoc_sau.py, QĐ-014).

Khác METR-LA:
  - Nút = ĐOẠN đường có dữ liệu TomTom (~7,4 nghìn); giá trị = r (tốc độ / đường trống); thiếu = NaN.
    Vào 4 kênh: r chuẩn hoá (thiếu -> 0 = trung bình), "có số đo" 0/1, giờ trong ngày, cuối tuần 0/1.
  - Đồ thị: đoạn i -> j khi j bắt đầu ở nút cuối của i (xe đi tiếp được), cộng vòng tự thân. Ma trận THƯA;
    Graph WaveNet bỏ ma trận tự học (N × N không vừa GPU 4 GB).
  - Khung 15 phút: vào 8 khung (2 giờ) -> ra 4 khung; báo cáo 15 / 30 / 60 phút = khung 1 / 2 / 4.
  - Chia và thước đo GIỐNG moc_so_sanh.py để so thẳng với giữ nguyên / TB 1h / GBM: 70% khung đầu để học
    (10% cuối của phần học làm kiểm định để dừng sớm — không dùng để cập nhật trọng số), chừa 4 khung, phần sau
    kiểm tra; chỉ chấm ô có r(t) và có nhãn; MAE theo điểm % (toàn bộ, ban ngày, đang đông/kẹt), đúng 3 mức.
Dữ liệu còn ít ngày thì số chỉ để KIỂM ĐƯỜNG ỐNG, chưa kết luận mô hình nào hơn.

Mỗi vòng lưu điểm dừng: máy tắt / ngủ giữa chừng thì chạy lại với --tiep (cùng dữ liệu).

Chạy:  python hoc_sau_hcm.py [gwn|gru] [--ho-so] [--so-vong=200] [--tiep]
       --ho-so: học phần chênh so với hồ sơ lịch sử của đoạn ở giờ đích (ho_so_lich_su.py, QĐ-020).
Ra:    mo_hinh/ket_qua/hoc_sau/hcm_<mô hình>_<ngày cuối của dữ liệu>.json + .pt — giữ lại từng lần train để
       so độ ổn định qua các tuần (tính từ dữ liệu TomTom — không lên git)
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch
import torch.nn as nn

from ho_so_lich_su import ho_so
from hoc_sau import GRUNut, GraphWaveNet, ma_tran_thua
from moc_so_sanh import KHOANG_HO, TY_LE_HOC, danh_gia, mae_theo_ngay

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VANG = os.path.join(GOC, 'du_lieu', 'vang')
RA_THU_MUC = os.path.join(GOC, 'mo_hinh', 'ket_qua', 'hoc_sau')
VAO, RA = 8, 4
BUOC = {'15': 0, '30': 1, '60': 3}              # chỉ số khung ra (0 = 15 phút tới)
LO = 4                                          # N lớn: lô nhỏ cho vừa GPU 4 GB
KIEN_NHAN = 20
TY_LE_KIEM_DINH = 0.1


def nap_vang():
    """Ma trận r (khung × đoạn), mốc khung, mã đoạn — khung = mọi khung có dòng trong tầng vàng (như moc_so_sanh)."""
    d = pd.concat([pd.read_parquet(t, columns=['khung', 'doan', 'r'])
                   for t in sorted(glob.glob(os.path.join(VANG, '*.parquet')))], ignore_index=True)
    khung = np.sort(d['khung'].unique())
    doan = np.sort(d['doan'].unique())
    R = np.full((len(khung), len(doan)), np.nan, dtype=np.float32)
    R[np.searchsorted(khung, d['khung'].to_numpy()), np.searchsorted(doan, d['doan'].to_numpy())] = d['r'].to_numpy()
    return pd.DatetimeIndex(khung), doan, R


def do_thi(doan):
    """Đồ thị thưa giữa các đoạn: i -> j khi đoạn j bắt đầu ở nút cuối đoạn i; + vòng tự thân."""
    d = pd.read_parquet(os.path.join(GOC, 'du_lieu', 'bac', 'doan.parquet'),
                        columns=['doan', 'u_dau', 'v_cuoi']).set_index('doan').loc[doan]
    N = len(doan)
    cap = pd.DataFrame({'i': np.arange(N), 'nut': d['v_cuoi'].to_numpy()}).merge(
        pd.DataFrame({'j': np.arange(N), 'nut': d['u_dau'].to_numpy()}), on='nut')
    cap = cap[cap['i'] != cap['j']]
    A = sp.csr_matrix((np.ones(len(cap)), (cap['i'], cap['j'])), shape=(N, N)) + sp.identity(N, format='csr')
    return A, len(cap)


def chuyen(A):
    """D⁻¹A cho ma trận thưa (cùng ý nghĩa hoc_sau.ma_tran_chuyen)."""
    tong = np.asarray(A.sum(1)).ravel()
    return sp.diags(np.divide(1.0, tong, out=np.zeros_like(tong), where=tong > 0)) @ A


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    thong_so = [a for a in sys.argv[1:] if not a.startswith('--')]
    ten_mh = thong_so[0] if thong_so else 'gwn'
    so_vong = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--so-vong=')), 200)
    dung_ho_so = '--ho-so' in sys.argv
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    tb_ = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    t_bat_dau = time.time()

    khung, doan, R = nap_vang()
    T, N = R.shape
    A, so_canh = do_thi(doan)
    cat = int(T * TY_LE_HOC)
    het_hoc, dau_kiem = cat - 1, min(cat + KHOANG_HO, T - 1)
    co = ~np.isnan(R)
    tb, ls = float(np.nanmean(R[:cat])), float(np.nanstd(R[:cat]))
    print(f'{T} khung ({khung[0]} -> {khung[-1]}), {N:,} doan, {so_canh:,} cap doan noi tiep; co so do '
          f'{co.mean():.1%}; hoc toi {khung[het_hoc]} | kiem tu {khung[dau_kiem]}; r TB {tb:.3f} LC {ls:.3f}')

    # Đệm NaN trước (VAO−1 khung) và sau (RA khung): mẫu t = khung hiện tại; vào Rp[t:t+VAO] = khung t−7..t,
    # ra Rp[t+VAO:t+VAO+RA] = khung t+1..t+4.
    Rp = np.concatenate([np.full((VAO - 1, N), np.nan, np.float32), R, np.full((RA, N), np.nan, np.float32)])
    gio = ((khung - khung.normalize()) / pd.Timedelta(days=1)).to_numpy().astype(np.float32)
    Gp = np.concatenate([np.zeros(VAO - 1, np.float32), gio, np.zeros(RA, np.float32)])
    cuoi = np.asarray(khung.dayofweek >= 5, dtype=np.float32)
    Cp = np.concatenate([np.zeros(VAO - 1, np.float32), cuoi, np.zeros(RA, np.float32)])
    V = torch.tensor(Rp, device=tb_)
    G = torch.tensor(Gp, device=tb_)
    C = torch.tensor(Cp, device=tb_)
    buoc = torch.arange(VAO + RA, device=tb_)

    # --ho-so: thêm kênh "độ lệch so với mức bình thường", và mô hình học PHẦN CHÊNH so với hồ sơ ở giờ đích
    # (hồ sơ đã chống rò rỉ, ho_so_lich_su.py) thay vì học từ mức trung bình chung.
    Hv = None
    if dung_ho_so:
        Hp = np.concatenate([np.full((VAO - 1, N), np.nan, np.float32), ho_so(R, khung, cat),
                             np.full((RA, N), np.nan, np.float32)])
        Hv = torch.tensor(Hp, device=tb_)

    def lo(mau):
        """Mẫu (khung t) -> vào (B, số kênh, N, VAO); ra (B, RA, N) theo r (NaN = thiếu); mức nền cộng vào đầu ra."""
        s = torch.as_tensor(mau, device=tb_)[:, None] + buoc
        x, y = V[s[:, :VAO]], V[s[:, VAO:]]
        m = ~torch.isnan(x)
        z = torch.where(m, (x - tb) / ls, torch.zeros_like(x))
        g = G[s[:, :VAO]][:, :, None].expand_as(x)
        c = C[s[:, :VAO]][:, :, None].expand_as(x)
        kenh, nen = [z, m.float(), g, c], tb
        if dung_ho_so:
            kenh.append(torch.nan_to_num((x - Hv[s[:, :VAO]]) / ls, nan=0.0))
            nen = torch.nan_to_num(Hv[s[:, VAO:]], nan=tb)
        return torch.stack(kenh, dim=1).transpose(2, 3), y, nen

    def mae_co_nhan(du, y):
        m = ~torch.isnan(y)
        return torch.abs(du[m] - y[m]).mean() if m.any() else du.sum() * 0

    # Mẫu học: có ít nhất một nhãn; 10% cuối (theo thời gian) làm kiểm định.
    co_nhan = np.array([co[t + 1:t + 1 + RA].any() for t in range(T)])
    hoc_tat = np.arange(het_hoc + 1)[co_nhan[:het_hoc + 1]]
    # Ít nhất 96 khung = trọn một ngày: lần train 06/11 kiểm định 54 khung, phần lớn là đêm dễ đoán, nên dừng
    # sớm theo số quá lạc quan (kiểm định 5,10 so với kiểm tra 6,24–6,73).
    so_kd = min(max(96, int(len(hoc_tat) * TY_LE_KIEM_DINH)), len(hoc_tat) // 2)
    mau_hoc, mau_kd = hoc_tat[:-so_kd], hoc_tat[-so_kd:]
    mau_kt = np.arange(dau_kiem, T)

    so_kenh = 5 if dung_ho_so else 4
    if ten_mh == 'gru':
        mh = GRUNut(vao=so_kenh, ra=RA)
    else:
        cac_A = [ma_tran_thua(chuyen(A)).to(tb_), ma_tran_thua(chuyen(A.T.tocsr())).to(tb_)]
        mh = GraphWaveNet(cac_A, N, vao=so_kenh, ra=RA, khoi=3, tu_hoc=False)
    if dung_ho_so:
        ten_mh += '_ho_so'
    mh = mh.to(tb_)
    toi_uu = torch.optim.Adam(mh.parameters(), lr=1e-3, weight_decay=1e-4)
    print(f'{ten_mh}: {sum(p.numel() for p in mh.parameters()):,} tham so; mau hoc/kiem dinh/kiem tra '
          f'{len(mau_hoc)}/{len(mau_kd)}/{len(mau_kt)}; thiet bi {tb_}', flush=True)

    def du_doan(mau):
        mh.eval()
        ra = []
        with torch.no_grad():
            for k in range(0, len(mau), LO):
                x, _, nen = lo(mau[k:k + LO])
                ra.append(mh(x) * ls + nen)
        mh.train()
        return torch.cat(ra)

    tep = os.path.join(RA_THU_MUC, f'hcm_{ten_mh}_{khung[-1]:%Y-%m-%d}')
    os.makedirs(RA_THU_MUC, exist_ok=True)
    vong0, tot_nhat, chua_tot, lich_su = 0, float('inf'), 0, []
    if '--tiep' in sys.argv and os.path.exists(tep + '_dang.pt'):
        dd = torch.load(tep + '_dang.pt', map_location=tb_, weights_only=False)
        mh.load_state_dict(dd['mh'])
        toi_uu.load_state_dict(dd['toi_uu'])
        vong0, tot_nhat, chua_tot, lich_su, rng = dd['vong'], dd['tot_nhat'], dd['chua_tot'], dd['lich_su'], dd['rng']
        print(f'Chay tiep tu vong {vong0}', flush=True)
    for vong in range(vong0, so_vong):
        t = time.time()
        mat = []
        tron = rng.permutation(mau_hoc)
        for k in range(0, len(tron), LO):
            x, y, nen = lo(tron[k:k + LO])
            loss = mae_co_nhan(mh(x) * ls + nen, y)
            toi_uu.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(mh.parameters(), 5)
            toi_uu.step()
            mat.append(loss.item())
        kd = float(mae_co_nhan(du_doan(mau_kd), lo(mau_kd)[1]))
        lich_su.append({'vong': vong + 1, 'mae_hoc': round(100 * float(np.mean(mat)), 3),
                        'mae_kiem_dinh': round(100 * kd, 3), 'giay': round(time.time() - t, 1)})
        if kd < tot_nhat:
            tot_nhat, chua_tot = kd, 0
            torch.save(mh.state_dict(), tep + '.pt')
        else:
            chua_tot += 1
        torch.save({'mh': mh.state_dict(), 'toi_uu': toi_uu.state_dict(), 'vong': vong + 1, 'tot_nhat': tot_nhat,
                    'chua_tot': chua_tot, 'lich_su': lich_su, 'rng': rng}, tep + '_dang.pt')
        if vong == 0 or chua_tot == 0 or (vong + 1) % 10 == 0:
            print(f'vong {vong + 1:3d}: MAE hoc {100 * np.mean(mat):.2f}, kiem dinh {100 * kd:.2f}'
                  f'{" *" if chua_tot == 0 else ""} ({time.time() - t:.1f}s'
                  f'{f", GPU {torch.cuda.max_memory_allocated() / 2**30:.2f} GB" if vong == 0 and tb_.type == "cuda" else ""})',
                  flush=True)
        if chua_tot >= KIEN_NHAN:
            print(f'Dung som o vong {vong + 1}')
            break

    mh.load_state_dict(torch.load(tep + '.pt', map_location=tb_))
    du = du_doan(mau_kt).cpu().numpy()
    kq = {}
    print(f'\nKiem tra ({len(mau_kt)} khung tu {khung[dau_kiem]}), MAE diem %:')
    for p, b in BUOC.items():
        h = b + 1
        tt = mau_kt[mau_kt + h < T]
        r, y = R[tt], R[tt + h]
        m = ~np.isnan(r) & ~np.isnan(y)
        gio_t = np.broadcast_to(khung[tt].hour.to_numpy()[:, None], r.shape)[m]
        dd = np.clip(du[:len(tt), b][m], 0, 1)
        ngay = np.broadcast_to(khung[tt].strftime('%Y-%m-%d').to_numpy()[:, None], r.shape)[m]
        kq[p] = {'giu_nguyen': danh_gia(y[m], r[m], r[m], gio_t), ten_mh: danh_gia(y[m], dd, r[m], gio_t),
                 'mae_theo_ngay': {'giu_nguyen': mae_theo_ngay(y[m], r[m], ngay), ten_mh: mae_theo_ngay(y[m], dd, ngay)}}
        g, n = kq[p]['giu_nguyen'], kq[p][ten_mh]
        print(f'{p:>2} phut | giu nguyen {g["mae"]:.2f} -> {ten_mh} {n["mae"]:.2f} | RMSE {g["rmse"]} -> {n["rmse"]} | '
              f'ban ngay {g["mae_ban_ngay"]} -> {n["mae_ban_ngay"]} | dang dong/ket {g["mae_dang_dong_ket"]} -> '
              f'{n["mae_dang_dong_ket"]} | dung 3 muc {g["dung_3_muc"]:.1%} -> {n["dung_3_muc"]:.1%} | '
              f'F1 3 muc {g["f1_3_muc"]} -> {n["f1_3_muc"]} | F1 ket {g["f1_ket"]} -> {n["f1_ket"]} | {n["n"]:,} o')
        print(f'        theo ngay {kq[p]["mae_theo_ngay"][ten_mh]}', flush=True)
    with open(tep + '.json', 'w', encoding='utf-8') as f:
        json.dump({'mo_hinh': ten_mh, 'khung': [str(khung[0]), str(khung[-1])], 'hoc_toi': str(khung[het_hoc]),
                   'kiem_tu': str(khung[dau_kiem]), 'so_doan': N, 'so_vong': len(lich_su),
                   'ket_qua': kq, 'lich_su': lich_su}, f, ensure_ascii=False, indent=1)
    print(f'-> {tep}.json ({(time.time() - t_bat_dau) / 60:.1f} phut)')


if __name__ == '__main__':
    main()
