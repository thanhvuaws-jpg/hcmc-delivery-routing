"""
Gộp cạnh đồ thị thành ĐOẠN ĐƯỜNG: chuỗi cạnh có hướng nối liền nhau giữa hai nút giao.

Vì sao: tầng vàng và mô hình cần đơn vị gọn hơn cạnh OSM (350.839 cạnh, phần lớn là các
khúc ngắn vài chục mét do OSM thêm nút để vẽ đường cong). Đoạn đường ~ "cảm biến" như các
bộ dữ liệu giao thông chuẩn (METR-LA, PEMS-BAY), và mức kẹt TomTom trên các cạnh liền nhau
của cùng một đoạn gần như luôn bằng nhau.

Nút "giữa đoạn" (không phải nút giao): có đúng 2 nút kề (tính cả hai chiều) và bậc vào/ra
là (1,1) — đường một chiều — hoặc (2,2) — đường hai chiều. Mọi nút khác là đầu đoạn.
Với ĐƯỜNG CHÍNH (trunk … tertiary) chỉ tính cạnh đường chính khi xét nút kề, và cắt đoạn khi
đổi tên đường: hẻm đâm ngang (cứ vài chục mét một hẻm ở TP.HCM) không cắt đoạn. Lần đầu (tính
mọi cạnh) ra 177.212 đoạn, trung vị 38 m — vụn quá, không dùng làm "cảm biến" được.
Mỗi chiều đi của đường hai chiều là một đoạn riêng (kẹt mỗi chiều khác nhau).

Đầu ra:
  du_lieu/bac/doan.parquet       doan (int32), u_dau, v_cuoi, so_canh, dai (m), loai (loại chiếm
                                 nhiều chiều dài nhất), ten, trung_gian (max các cạnh)
  du_lieu/bac/canh_doan.parquet  chi_so -> doan, thu_tu (vị trí cạnh trong đoạn)

Chạy:  python doan_duong.py   (sau khi dựng lại đồ thị / BoGhep.dung())
"""
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(GOC, 'dinh_tuyen'))
from ghep_tomtom import TEP_CANH  # noqa: E402

BAC = os.path.join(GOC, 'du_lieu', 'bac')
CHINH = {'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
         'tertiary', 'tertiary_link'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t0 = time.time()
    from do_thi import TEP_RA
    with open(TEP_RA, 'rb') as f:
        G = pickle.load(f)['G']
    canh = pd.read_parquet(TEP_CANH)
    chi_so = {(u, v): int(i) for i, u, v in zip(canh['chi_so'], canh['u'], canh['v'])}

    loai_e = {(u, v): d['loai'] for u, v, d in G.edges(data=True)}
    ten_e = {(u, v): d['ten'] for u, v, d in G.edges(data=True)}

    def la_chinh(u, v):
        return loai_e[(u, v)] in CHINH

    def ke(n, chinh):
        """(nút trước, nút sau) của n, chỉ tính cạnh cùng cấp (đường chính / mọi đường)."""
        tr = [p for p in G.predecessors(n) if not chinh or la_chinh(p, n)]
        sa = [s for s in G.successors(n) if not chinh or la_chinh(n, s)]
        return tr, sa

    def giua_doan(n, chinh):
        tr, sa = ke(n, chinh)
        if len(set(tr) | set(sa)) != 2 or (len(tr), len(sa)) not in ((1, 1), (2, 2)):
            return False
        # Đường chính đổi tên ở nút này (vd hết Lê Lợi sang Lê Duẩn) thì cắt đoạn.
        return not chinh or len({ten_e[(p, n)] for p in tr} | {ten_e[(n, s)] for s in sa}) == 1

    giua = {False: {n for n in G.nodes if giua_doan(n, False)},
            True: {n for n in G.nodes if giua_doan(n, True)}}
    da_dung = np.zeros(len(canh), dtype=bool)
    doan_cua = np.full(len(canh), -1, dtype=np.int32)
    thu_tu = np.zeros(len(canh), dtype=np.int16)
    ds = []

    def di_tiep(u, v):
        """Từ cạnh (u, v) đi tiếp qua các nút giữa đoạn (cùng cấp đường), không quay đầu."""
        chinh = la_chinh(u, v)
        chuoi, da = [(u, v)], {chi_so[(u, v)]}
        while v in giua[chinh]:
            tiep = [w for w in ke(v, chinh)[1] if w != u]
            # Dừng trước cạnh đã thuộc đoạn khác: không đi tiếp thì không ghi đè đoạn cũ
            # (30/10/2026: thiếu điều kiện này làm 3 đoạn mất cạnh đầu — kiem_du_lieu.py bắt được).
            if len(tiep) != 1 or chi_so[(v, tiep[0])] in da or da_dung[chi_so[(v, tiep[0])]]:
                break
            u, v = v, tiep[0]
            chuoi.append((u, v))
            da.add(chi_so[(u, v)])
        return chuoi

    # Bắt đầu từ cạnh rời một đầu đoạn; vòng kín toàn nút giữa đoạn xử lý ở lượt sau.
    for luot in (0, 1):
        for u, v in G.edges():
            i = chi_so[(u, v)]
            if da_dung[i] or (luot == 0 and u in giua[la_chinh(u, v)]):
                continue
            chuoi = di_tiep(u, v)
            d = len(ds)
            idx = [chi_so[e] for e in chuoi]
            da_dung[idx] = True
            doan_cua[idx] = d
            thu_tu[idx] = np.arange(len(idx))
            ds.append((d, chuoi[0][0], chuoi[-1][1], idx))

    assert da_dung.all(), 'còn cạnh chưa vào đoạn nào'
    dai = canh['dai'].to_numpy()
    loai, ten = canh['loai'].to_numpy(), canh['ten'].to_numpy()
    tg = None
    tep_tinh = os.path.join(BAC, 'canh_tinh.parquet')
    if os.path.exists(tep_tinh):
        tg = pd.read_parquet(tep_tinh, columns=['trung_gian'])['trung_gian'].to_numpy()
    hang = []
    for d, u, v, idx in ds:
        dl = pd.Series(dai[idx]).groupby(loai[idx]).sum()
        ten_d = next((t for t in ten[idx] if t), '')
        hang.append({'doan': d, 'u_dau': u, 'v_cuoi': v, 'so_canh': len(idx), 'dai': float(dai[idx].sum()),
                     'loai': dl.idxmax(), 'ten': ten_d,
                     'trung_gian': float(tg[idx].max()) if tg is not None else np.nan})
    doan = pd.DataFrame(hang).astype({'doan': np.int32, 'so_canh': np.int32, 'dai': np.float32,
                                      'trung_gian': np.float32})
    doan.to_parquet(os.path.join(BAC, 'doan.parquet'), index=False)
    pd.DataFrame({'chi_so': canh['chi_so'].astype(np.int32), 'doan': doan_cua, 'thu_tu': thu_tu}).to_parquet(
        os.path.join(BAC, 'canh_doan.parquet'), index=False)

    print(f'{len(canh):,} canh -> {len(doan):,} doan ({len(canh) / len(doan):.1f} canh/doan), {time.time() - t0:.0f}s')
    print(f'  dai doan: trung vi {doan["dai"].median():.0f} m, p90 {doan["dai"].quantile(.9):.0f} m, max {doan["dai"].max():.0f} m')
    chinh = doan[doan['loai'].isin(['trunk', 'primary', 'secondary', 'tertiary', 'trunk_link', 'primary_link'])]
    print(f'  doan tren duong chinh (trunk..tertiary): {len(chinh):,}, tong {chinh["dai"].sum() / 1000:.0f} km')


if __name__ == '__main__':
    main()
