"""
Bộ chuẩn METR-LA / PEMS-BAY (D9, KE_HOACH tuần 5–6): kiểm đường ống dự báo và mô hình học sâu trên dữ liệu
CÓ SỐ CÔNG BỐ, trong lúc dữ liệu TP.HCM còn ít ngày. Số của mình lệch xa số bài báo ở mô hình mốc (HA)
nghĩa là đường ống (chia, chuẩn hoá, thước đo) sai — phải sửa trước khi tin mô hình nào.

Nguồn (tải 30/10/2026 vào du_lieu/metr_la/, không lên git):
  metr-la.h5, pems-bay.h5     Google Drive của tác giả DCRNN (Li và cs., ICLR 2018; github.com/liyaguang/DCRNN)
  distances_*.csv, graph_sensor_*   thư mục data/sensor_graph của repo đó (giấy phép MIT)
  KHÔNG dùng adj_mx*.pkl của repo (mở pickle tải từ ngoài về = chạy mã lạ): ma trận kề dựng lại từ
  distances_*.csv đúng công thức bài báo (mục 4): W_ij = exp(−(d_ij/σ)²), σ = độ lệch chuẩn các khoảng
  cách, bỏ W < 0,1. Tệp .h5 đọc thẳng mảng bằng PyTables (đã soát: chỉ có mảng số / chuỗi, không pickle).

Giao thức (giống DCRNN để số so được với bài báo):
  5 phút/bước; vào 12 bước (1 giờ) -> ra 12 bước; mẫu cửa sổ chia THEO THỜI GIAN 70% học / 10% kiểm định /
  20% kiểm tra; z-score theo phần học; tốc độ 0 = thiếu dữ liệu, bị loại khỏi MAE/RMSE/MAPE;
  báo cáo bước 3 / 6 / 12 = 15 / 30 / 60 phút.

Chạy:  python chuan_metr_la.py            (kiểm đường ống: HA + giữ nguyên, so với bảng 1 bài báo)
Dùng:  from chuan_metr_la import nap_bo   (cho mô hình học sâu, mo_hinh/hoc_sau.py)
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import tables

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
THU_MUC = os.path.join(GOC, 'du_lieu', 'metr_la')
BO = {
    'metr-la': {'h5': 'metr-la.h5', 'kc': 'distances_la_2012.csv'},
    'pems-bay': {'h5': 'pems-bay.h5', 'kc': 'distances_bay_2017.csv'},
}
VAO, RA = 12, 12
BUOC_BAO_CAO = {'15': 2, '30': 5, '60': 11}     # chỉ số bước (0 = 5 phút tới)
NGUONG_KE = 0.1

# Bảng 1 bài báo DCRNN (ICLR 2018): (MAE, RMSE, MAPE %) ở 15 / 30 / 60 phút — đối chiếu bản PDF 30/10/2026.
BAI_BAO = {
    'metr-la': {
        'HA': [(4.16, 7.80, 13.0), (4.16, 7.80, 13.0), (4.16, 7.80, 13.0)],
        'FC-LSTM': [(3.44, 6.30, 9.6), (3.77, 7.23, 10.9), (4.37, 8.69, 13.2)],
        'DCRNN': [(2.77, 5.38, 7.3), (3.15, 6.45, 8.8), (3.60, 7.59, 10.5)],
    },
    'pems-bay': {
        'HA': [(2.88, 5.59, 6.8), (2.88, 5.59, 6.8), (2.88, 5.59, 6.8)],
        'FC-LSTM': [(2.05, 4.19, 4.8), (2.20, 4.55, 5.2), (2.37, 4.96, 5.7)],
        'DCRNN': [(1.38, 2.95, 2.9), (1.74, 3.97, 3.9), (2.07, 4.74, 4.9)],
    },
}


def doc_h5(ten):
    """Tốc độ (bước × cảm biến, dặm/giờ; 0 = thiếu), mã cảm biến, mốc thời gian."""
    with tables.open_file(os.path.join(THU_MUC, BO[ten]['h5'])) as f:
        g = f.list_nodes('/')[0]                  # /df (METR-LA) hoặc /speed (PEMS-BAY)
        v = g.block0_values.read().astype(np.float32)
        cot = [c.decode() if isinstance(c, bytes) else str(c) for c in g.block0_items.read()]
        luc = pd.to_datetime(g.axis1.read())
    return v, cot, luc


def ma_tran_ke(ten, cot):
    """Ma trận kề có hướng (n × n) theo khoảng cách đường đi giữa cảm biến — công thức bài báo DCRNN."""
    kc = pd.read_csv(os.path.join(THU_MUC, BO[ten]['kc']), header=None, dtype=str)
    if kc.iloc[0, 0] == 'from':                   # tệp METR-LA có dòng tiêu đề, PEMS-BAY không
        kc = kc.iloc[1:]
    kc.columns = ['tu', 'den', 'kc']
    so = {c: k for k, c in enumerate(cot)}
    kc = kc[kc['tu'].isin(so) & kc['den'].isin(so)]
    D = np.full((len(cot), len(cot)), np.inf)
    D[kc['tu'].map(so).to_numpy(), kc['den'].map(so).to_numpy()] = kc['kc'].astype(float).to_numpy()
    sigma = D[np.isfinite(D)].std()
    W = np.exp(-np.square(D / sigma))
    W[W < NGUONG_KE] = 0
    return W.astype(np.float32)


def chia(so_buoc):
    """Chỉ số mẫu (mẫu s: vào v[s:s+12], ra v[s+12:s+24]) cho học / kiểm định / kiểm tra — đúng cách
    DCRNN (scripts/generate_training_data.py): số mẫu kiểm tra = round(20%), học = round(70%), còn lại kiểm định."""
    S = so_buoc - VAO - RA + 1
    n_kt, n_hoc = round(S * 0.2), round(S * 0.7)
    return np.arange(n_hoc), np.arange(n_hoc, S - n_kt), np.arange(S - n_kt, S)


def nap_bo(ten):
    v, cot, luc = doc_h5(ten)
    hoc, kd, kt = chia(len(v))
    # Thống kê chuẩn hoá lấy trên các bước nằm trong cửa sổ VÀO của mẫu học (như DCRNN: x_train[..., 0]),
    # gồm cả số 0 (thiếu) — giữ y nguyên để số so được với bài báo.
    het_hoc = hoc[-1] + VAO
    tb, ls = float(v[:het_hoc].mean()), float(v[:het_hoc].std())
    gio_ngay = ((luc - luc.normalize()) / pd.Timedelta(days=1)).to_numpy().astype(np.float32)
    return {'ten': ten, 'v': v, 'cot': cot, 'luc': luc, 'gio_ngay': gio_ngay,
            'thu': luc.dayofweek.to_numpy().astype(np.int64), 'ke': ma_tran_ke(ten, cot),
            'hoc': hoc, 'kd': kd, 'kt': kt, 'tb': tb, 'ls': ls}


def do_sai(du, y):
    """MAE, RMSE, MAPE (%) bỏ các ô y = 0 (thiếu) — như masked_mae/rmse/mape của DCRNN."""
    m = y != 0
    e = du[m] - y[m]
    return float(np.abs(e).mean()), float(np.sqrt((e * e).mean())), float(100 * np.abs(e / y[m]).mean())


def ha_kieu_dcrnn(v):
    """
    HA đúng như DCRNN scripts/eval_baseline_methods.py: chia THEO BƯỚC (20% cuối là kiểm tra), dự báo mỗi
    bước kiểm tra = trung bình các bước CÙNG GIỜ CÙNG THỨ (chu kỳ 1 tuần) trong phần trước đó, bỏ số 0.
    Không phụ thuộc tầm dự báo nên 15/30/60 phút như nhau.
    """
    chu_ky = 12 * 24 * 7
    n_kt = round(len(v) * 0.2)
    n_hoc = len(v) - n_kt
    tong = np.zeros((chu_ky, v.shape[1]))
    dem = np.zeros((chu_ky, v.shape[1]))
    for i in range(n_hoc):
        co = v[i] != 0
        tong[i % chu_ky] += np.where(co, v[i], 0)
        dem[i % chu_ky] += co
    tb = np.divide(tong, dem, out=np.zeros_like(tong), where=dem > 0)
    du = tb[np.arange(n_hoc, len(v)) % chu_ky]
    return do_sai(du, v[n_hoc:])


def cua_so(v, mau):
    """(mẫu, 12, n) vào và (mẫu, 12, n) ra cho các chỉ số mẫu."""
    i = mau[:, None]
    return v[i + np.arange(VAO)], v[i + VAO + np.arange(RA)]


def giu_nguyen(d):
    """Mốc ngây thơ: mọi bước tới = số đo KHÁC 0 gần nhất trong cửa sổ vào (0 hết thì 0)."""
    x, y = cua_so(d['v'], d['kt'])
    cuoi = np.zeros(x.shape[::2], dtype=np.float32)
    for k in range(VAO):                          # quét xuôi: giữ giá trị khác 0 muộn nhất
        cuoi = np.where(x[:, k] != 0, x[:, k], cuoi)
    return [do_sai(np.broadcast_to(cuoi, y[:, b].shape), y[:, b]) for b in BUOC_BAO_CAO.values()]


def in_bang(ten, dong):
    """dong: {tên mô hình: [(MAE, RMSE, MAPE) ở 15/30/60]} — in kèm số bài báo."""
    print(f'\n{ten}: MAE / RMSE / MAPE%  (15 | 30 | 60 phut)')
    for mh, so in list(dong.items()) + [(f'{k} (bai bao)', s) for k, s in BAI_BAO[ten].items()]:
        print(f'  {mh:<22}' + ' | '.join(f'{a:5.2f} {b:5.2f} {c:5.1f}%' for a, b, c in so))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for ten in BO:
        t0 = time.time()
        d = nap_bo(ten)
        v = d['v']
        print(f'\n{ten}: {v.shape[0]:,} buoc x {v.shape[1]} cam bien, {d["luc"][0]:%Y-%m-%d} -> {d["luc"][-1]:%Y-%m-%d}; '
              f'thieu (0) {100 * (v == 0).mean():.1f}%; mau hoc/kiem dinh/kiem tra {len(d["hoc"]):,}/{len(d["kd"]):,}/'
              f'{len(d["kt"]):,}; ke: {int((d["ke"] > 0).sum()):,} canh; z-score TB {d["tb"]:.2f} LC {d["ls"]:.2f}')
        ha = ha_kieu_dcrnn(v)
        in_bang(ten, {'HA (cua minh)': [ha] * 3, 'giu nguyen': giu_nguyen(d)})
        print(f'  ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
