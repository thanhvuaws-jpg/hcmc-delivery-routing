"""
Mô hình học sâu dự báo tốc độ 12 bước tới (KE_HOACH tuần 6), thử trước trên bộ chuẩn METR-LA / PEMS-BAY
(chuan_metr_la.py) để có số so với bài báo; dữ liệu TP.HCM đủ ngày thì dùng lại đúng mã này.

  gru  GRU 2 tầng × 64, DÙNG CHUNG cho mọi nút, mỗi nút chỉ thấy chuỗi của chính nó (không không gian)
       -> tuyến tính ra 12 bước. Cùng loại với FC-LSTM trong bài báo DCRNN.
  gwn  Graph WaveNet (Wu và cs., IJCAI 2019): 8 tầng TCN có cổng, giãn cách 1,2,1,2,…, sau mỗi tầng là
       tích chập đồ thị khuếch tán K = 2 trên [P_xuôi, P_ngược, A_tự_học]; nối tắt + nối nhảy. Siêu tham số
       đúng bài báo / mã gốc: kênh 32, nhảy 256, cuối 512, dropout 0,3, nhúng nút 10, Adam lr 1e-3,
       weight decay 1e-4, cắt gradient 5, lô 64.
Hàm mất mát: MAE trên đơn vị gốc, BỎ ô thiếu (tốc độ 0) — như bài báo. Chọn trọng số theo MAE kiểm định
tốt nhất; dừng sớm nếu KIEN_NHAN vòng liền không tốt hơn (bài báo chạy đủ 100 vòng — chỉ để đỡ giờ máy).
Mỗi vòng lưu điểm dừng: máy tắt / ngủ giữa chừng thì chạy lại với --tiep.

Chạy:  python hoc_sau.py metr-la gwn [--so-vong=100] [--tiep]
Ra:    mo_hinh/ket_qua/hoc_sau/<bộ>_<mô hình>.json (+ .pt trọng số tốt nhất, _dang.pt điểm dừng)
"""
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from chuan_metr_la import BAI_BAO, BUOC_BAO_CAO, RA as SO_RA, VAO, do_sai, in_bang, nap_bo

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
THU_MUC_RA = os.path.join(GOC, 'mo_hinh', 'ket_qua', 'hoc_sau')
LO = 64
KIEN_NHAN = 20
# Graph WaveNet bảng 2 (đối chiếu bản PDF arXiv 1906.00121, 30/10/2026): (MAE, RMSE, MAPE %) 15/30/60 phút.
BAI_BAO_GWN = {'metr-la': [(2.69, 5.15, 6.90), (3.07, 6.22, 8.37), (3.53, 7.37, 10.01)],
               'pems-bay': [(1.30, 2.74, 2.73), (1.63, 3.70, 3.67), (1.95, 4.52, 4.63)]}


class GRUNut(nn.Module):
    def __init__(self, vao=2, an=64, tang=2, ra=SO_RA):
        super().__init__()
        self.gru = nn.GRU(vao, an, tang, batch_first=True)
        self.ra = nn.Linear(an, ra)

    def forward(self, x):                       # x (B, C, N, T) -> (B, ra, N)
        B, C, N, T = x.shape
        h, _ = self.gru(x.permute(0, 2, 3, 1).reshape(B * N, T, C))
        return self.ra(h[:, -1]).reshape(B, N, -1).transpose(1, 2)


def ma_tran_chuyen(A):
    """D⁻¹A (chuẩn hoá theo hàng) — asym_adj của mã gốc Graph WaveNet."""
    tong = A.sum(1, keepdims=True)
    return np.divide(A, tong, out=np.zeros_like(A), where=tong > 0)


def ma_tran_thua(A):
    """Ma trận numpy -> tensor THƯA của Aᵀ, cho lan_truyen() (đồ thị lớn: TP.HCM ~7 nghìn đoạn)."""
    import scipy.sparse as sp
    T = sp.coo_matrix(A.T)
    return torch.sparse_coo_tensor(np.vstack([T.row, T.col]), T.data.astype(np.float32), T.shape).coalesce()


def lan_truyen(x, A):
    """x (n, c, nút, l) -> out[:, :, w] = Σ_v x[:, :, v] · A[v, w]. A đặc: einsum như mã gốc;
    A thưa (đã là Aᵀ, từ ma_tran_thua): nhân thưa — cùng kết quả, không dựng ma trận N × N."""
    if not A.is_sparse:
        return torch.einsum('ncvl,vw->ncwl', x, A)
    n, c, v, l = x.shape
    y = torch.sparse.mm(A, x.permute(2, 0, 1, 3).reshape(v, -1))
    return y.reshape(v, n, c, l).permute(1, 2, 0, 3)


class GCN(nn.Module):
    """Tích chập đồ thị khuếch tán bậc 2 trên nhiều ma trận (công thức 4 bài báo Graph WaveNet)."""

    def __init__(self, c_vao, c_ra, so_ma_tran, bac=2, dropout=0.3):
        super().__init__()
        self.bac, self.dropout = bac, dropout
        self.mlp = nn.Conv2d((bac * so_ma_tran + 1) * c_vao, c_ra, (1, 1))

    def forward(self, x, cac_A):
        ra = [x]
        for A in cac_A:
            x1 = lan_truyen(x, A)
            ra.append(x1)
            for _ in range(2, self.bac + 1):
                x1 = lan_truyen(x1, A)
                ra.append(x1)
        return F.dropout(self.mlp(torch.cat(ra, dim=1)), self.dropout, training=self.training)


class GraphWaveNet(nn.Module):
    """tu_hoc=False: bỏ ma trận kề tự học (N × N đặc — không vừa GPU khi N lớn); bảng 3 bài báo: chỉ
    [P_xuôi, P_ngược] kém [P_xuôi, P_ngược, A_tự_học] 3,08 so với 3,04 MAE trung bình.
    khoi: số khối (mỗi khối 2 tầng giãn cách 1, 2 -> vùng nhìn 1 + 3·khoi bước); chuỗi vào ngắn thì giảm."""

    def __init__(self, cac_A, so_nut, vao=2, ra=SO_RA, kenh=32, nhay=256, cuoi=512, khoi=4, tang=2, nhung=10,
                 tu_hoc=True):
        super().__init__()
        self.cac_A = cac_A
        self.tu_hoc = tu_hoc
        if tu_hoc:
            self.nv1 = nn.Parameter(torch.randn(so_nut, nhung))
            self.nv2 = nn.Parameter(torch.randn(nhung, so_nut))
        self.dau = nn.Conv2d(vao, kenh, (1, 1))
        self.loc, self.cong, self.nhay, self.gcn, self.bn = (nn.ModuleList() for _ in range(5))
        self.vung_nhin = 1
        for _ in range(khoi):
            gian = 1
            for _ in range(tang):
                self.loc.append(nn.Conv2d(kenh, kenh, (1, 2), dilation=gian))
                self.cong.append(nn.Conv2d(kenh, kenh, (1, 2), dilation=gian))
                self.nhay.append(nn.Conv2d(kenh, nhay, (1, 1)))
                self.gcn.append(GCN(kenh, kenh, len(cac_A) + int(tu_hoc)))
                self.bn.append(nn.BatchNorm2d(kenh))
                self.vung_nhin += gian
                gian *= 2
        self.cuoi1 = nn.Conv2d(nhay, cuoi, (1, 1))
        self.cuoi2 = nn.Conv2d(cuoi, ra, (1, 1))

    def forward(self, x):                       # x (B, C, N, T) -> (B, ra, N)
        if x.shape[3] < self.vung_nhin:         # đệm trái cho đủ vùng nhìn (12 -> 13): ra đúng 1 bước thời gian
            x = F.pad(x, (self.vung_nhin - x.shape[3], 0, 0, 0))
        x = self.dau(x)
        cac_A = list(self.cac_A)
        if self.tu_hoc:
            cac_A.append(F.softmax(F.relu(self.nv1 @ self.nv2), dim=1))
        bo_qua = 0
        for i in range(len(self.loc)):
            du = x
            x = torch.tanh(self.loc[i](du)) * torch.sigmoid(self.cong[i](du))
            s = self.nhay[i](x)
            bo_qua = s + (bo_qua[..., -s.shape[3]:] if torch.is_tensor(bo_qua) else 0)
            x = self.gcn[i](x, cac_A) + du[..., -x.shape[3]:]
            x = self.bn[i](x)
        x = F.relu(self.cuoi1(F.relu(bo_qua)))
        return self.cuoi2(x)[..., -1]


def mae_bo_thieu(du, y):
    m = (y != 0).float()
    return (torch.abs(du - y) * m).sum() / m.sum().clamp(min=1)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    thong_so = [a for a in sys.argv[1:] if not a.startswith('--')]
    ten_bo, ten_mh = (thong_so + ['metr-la', 'gwn'][len(thong_so):])[:2]
    so_vong = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--so-vong=')), 100)
    os.makedirs(THU_MUC_RA, exist_ok=True)
    goc_ten = os.path.join(THU_MUC_RA, f'{ten_bo}_{ten_mh}')
    torch.manual_seed(0)
    torch.backends.cudnn.benchmark = True        # kích thước lô cố định -> cuDNN chọn sẵn thuật toán nhanh nhất
    rng = np.random.default_rng(0)
    tb_ = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    d = nap_bo(ten_bo)
    V = torch.tensor(d['v'], device=tb_)
    GIO = torch.tensor(d['gio_ngay'], device=tb_)
    tb, ls = d['tb'], d['ls']
    buoc = torch.arange(VAO + SO_RA, device=tb_)

    def lo(mau):
        """Mẫu -> vào (B, 2, N, 12): [tốc độ z-score, giờ trong ngày]; ra (B, 12, N) đơn vị gốc."""
        s = torch.as_tensor(mau, device=tb_)[:, None] + buoc
        x, y = V[s[:, :VAO]], V[s[:, VAO:]]
        g = GIO[s[:, :VAO]][:, :, None].expand_as(x)
        return torch.stack([(x - tb) / ls, g], dim=1).transpose(2, 3), y

    if ten_mh == 'gru':
        mh = GRUNut()
    else:
        A = d['ke']
        cac_A = [torch.tensor(ma_tran_chuyen(A), device=tb_), torch.tensor(ma_tran_chuyen(A.T), device=tb_)]
        mh = GraphWaveNet(cac_A, A.shape[0])
    mh = mh.to(tb_)
    toi_uu = torch.optim.Adam(mh.parameters(), lr=1e-3, weight_decay=1e-4)
    so_tham_so = sum(p.numel() for p in mh.parameters())

    def du_doan(mau):
        mh.eval()
        ra = []
        with torch.no_grad():
            for k in range(0, len(mau), LO):
                x, _ = lo(mau[k:k + LO])
                ra.append(mh(x) * ls + tb)
        mh.train()
        return torch.cat(ra)

    def mae_kiem_dinh():
        du = du_doan(d['kd'])
        return float(mae_bo_thieu(du, lo(d['kd'])[1]))

    vong0, tot_nhat, lich_su, chua_tot = 0, float('inf'), [], 0
    if '--tiep' in sys.argv and os.path.exists(goc_ten + '_dang.pt'):
        dd = torch.load(goc_ten + '_dang.pt', map_location=tb_, weights_only=False)
        mh.load_state_dict(dd['mh'])
        toi_uu.load_state_dict(dd['toi_uu'])
        vong0, tot_nhat, lich_su, chua_tot = dd['vong'], dd['tot_nhat'], dd['lich_su'], dd['chua_tot']
        rng = dd['rng']
        print(f'Chay tiep tu vong {vong0}')
    print(f'{ten_bo} {ten_mh}: {so_tham_so:,} tham so, thiet bi {tb_}, mau hoc {len(d["hoc"]):,}', flush=True)

    t_bat_dau = time.time()
    for vong in range(vong0, so_vong):
        t = time.time()
        tron = rng.permutation(d['hoc'])
        mat = []
        for k in range(0, len(tron), LO):
            x, y = lo(tron[k:k + LO])
            loss = mae_bo_thieu(mh(x) * ls + tb, y)
            toi_uu.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(mh.parameters(), 5)
            toi_uu.step()
            mat.append(loss.item())
        kd = mae_kiem_dinh()
        lich_su.append({'vong': vong + 1, 'mae_hoc': round(float(np.mean(mat)), 4), 'mae_kiem_dinh': round(kd, 4),
                        'giay': round(time.time() - t, 1)})
        if kd < tot_nhat:
            tot_nhat, chua_tot = kd, 0
            torch.save(mh.state_dict(), goc_ten + '.pt')
        else:
            chua_tot += 1
        torch.save({'mh': mh.state_dict(), 'toi_uu': toi_uu.state_dict(), 'vong': vong + 1, 'tot_nhat': tot_nhat,
                    'lich_su': lich_su, 'chua_tot': chua_tot, 'rng': rng}, goc_ten + '_dang.pt')
        print(f'vong {vong + 1:3d}: MAE hoc {np.mean(mat):.3f}, kiem dinh {kd:.3f}'
              f'{" *" if chua_tot == 0 else ""} ({time.time() - t:.0f}s)', flush=True)
        if chua_tot >= KIEN_NHAN:
            print(f'Dung som: {KIEN_NHAN} vong khong tot hon')
            break

    mh.load_state_dict(torch.load(goc_ten + '.pt', map_location=tb_))
    du = du_doan(d['kt']).cpu().numpy()
    y = lo(d['kt'])[1].cpu().numpy()
    so = [do_sai(du[:, b], y[:, b]) for b in BUOC_BAO_CAO.values()]
    trung_binh = do_sai(du, y)
    bang = {f'{ten_mh} (cua minh)': so}
    if ten_mh == 'gwn':
        bang['Graph WaveNet (bai bao)'] = BAI_BAO_GWN[ten_bo]
    in_bang(ten_bo, bang)
    print(f'TB 12 buoc: MAE {trung_binh[0]:.2f}, RMSE {trung_binh[1]:.2f}, MAPE {trung_binh[2]:.2f}%; '
          f'MAE kiem dinh tot nhat {tot_nhat:.3f}; hoc {(time.time() - t_bat_dau) / 60:.0f} phut')
    with open(goc_ten + '.json', 'w', encoding='utf-8') as f:
        json.dump({'bo': ten_bo, 'mo_hinh': ten_mh, 'tham_so': so_tham_so, 'so_vong': len(lich_su),
                   'mae_kiem_dinh_tot_nhat': tot_nhat,
                   'kiem_tra': {p: dict(zip(('mae', 'rmse', 'mape'), s)) for p, s in zip(BUOC_BAO_CAO, so)},
                   'kiem_tra_tb_12_buoc': dict(zip(('mae', 'rmse', 'mape'), trung_binh)),
                   'bai_bao': BAI_BAO[ten_bo], 'lich_su': lich_su}, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
