"""
Vẽ mạng đường xe máy + các tuyến tìm được thành ảnh PNG — không cần ảnh nền
từ máy chủ bản đồ nào, dùng được cho báo cáo.

Chạy:   python ve_tuyen.py
Kết quả: ket_qua/tuan1_tuyen.png
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from kiem_tra_tuan1 import DIA_DIEM, THU_MUC_RA
from tim_duong import BanDo

NET = {'trunk': 1.6, 'primary': 1.3, 'secondary': 1.0, 'tertiary': 0.8}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    bd = BanDo.nap()
    G = bd.G
    nhom = {'lon': [], 'nho': [], 'hem': []}
    for a, b, d in G.edges(data=True):
        doan = [(G.nodes[a]['x'], G.nodes[a]['y']), (G.nodes[b]['x'], G.nodes[b]['y'])]
        loai = d['loai'].replace('_link', '')
        nhom['lon' if loai in NET else ('hem' if loai == 'service' else 'nho')].append(doan)

    fig, ax = plt.subplots(figsize=(13, 11), dpi=110)
    ax.add_collection(LineCollection(nhom['hem'], colors='#e2ddd3', linewidths=0.35))
    ax.add_collection(LineCollection(nhom['nho'], colors='#cfc8bb', linewidths=0.5))
    ax.add_collection(LineCollection(nhom['lon'], colors='#a99f8f', linewidths=1.1))

    cap = [('Chợ Bến Thành', 'Ngã tư Hàng Xanh'), ('Ngã tư Hàng Xanh', 'Chợ Bến Thành'),
           ('Lăng Cha Cả', 'Chợ Bến Thành'), ('Chợ Bình Tây', 'Thảo Cầm Viên')]
    mau = ['#c0392b', '#e67e22', '#1f6feb', '#2e7d32']
    for (a, b), m in zip(cap, mau):
        kq = bd.tim(DIA_DIEM[a], DIA_DIEM[b], 'dai')
        xs = [p[1] for p in kq['toa_do']]
        ys = [p[0] for p in kq['toa_do']]
        ax.plot(xs, ys, color=m, linewidth=3.2, alpha=.9,
                label=f'{a} → {b}: {kq["dai_m"] / 1000:.2f} km, ~{kq["tg_s"] / 60:.0f} phút')
    for ten, (y, x) in DIA_DIEM.items():
        ax.plot(x, y, 'o', color='#222', markersize=5)
        ax.annotate(ten, (x, y), xytext=(4, 4), textcoords='offset points', fontsize=8.5)

    ax.set_xlim(106.635, 106.725)
    ax.set_ylim(10.742, 10.815)
    ax.set_aspect(1 / 0.983)       # cos(10.78°): giữ đúng tỉ lệ ngang–dọc
    ax.set_xticks([]); ax.set_yticks([])
    ax.legend(loc='lower right', fontsize=9, framealpha=.95)
    ax.set_title('Tuần 1 — đường ngắn nhất cho xe máy (một chiều, cấm xe máy, cấm rẽ)\n'
                 'Nền: mạng đường từ OpenStreetMap (© OpenStreetMap contributors)', fontsize=11)
    os.makedirs(THU_MUC_RA, exist_ok=True)
    tep = os.path.join(THU_MUC_RA, 'tuan1_tuyen.png')
    fig.savefig(tep, bbox_inches='tight')
    print('->', tep)


if __name__ == '__main__':
    main()
