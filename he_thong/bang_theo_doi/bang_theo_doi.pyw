"""
Bảng theo dõi hai bộ thu dữ liệu giao thông (AWS Lambda + máy nhà) — ứng dụng cửa sổ Windows.

  Tab "AWS (Lambda)":  đọc CloudWatch Logs (profile chỉ-đọc thuctap-doc)
  Tab "Máy nhà":       đọc du_lieu/nhat_ky/*.log + tác vụ hẹn giờ + dung lượng đã lưu
  Thanh trên:          hạn mức TomTom đã dùng hôm nay, cộng cả hai bộ thu

Mở: bấm đúp MO_BANG_THEO_DOI.bat (chạy bằng pythonw, không hiện cửa sổ dòng lệnh).
Tab AWS chỉ ĐỌC. Tab máy có nút Dừng thu / Bắt đầu thu / Chạy 1 lượt ngay: bật/tắt TÁC VỤ HẸN GIỜ
Windows (schtasks /Change /DISABLE|/ENABLE, /Run) — không xóa tác vụ, không đụng dữ liệu. Dừng phải bấm
2 lần trong 5 giây. Tự làm mới mỗi 60 giây.
"""
import datetime as dt
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.dates                                           # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg   # noqa: E402
from matplotlib.figure import Figure                              # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nguon_aws    # noqa: E402
import nguon_may    # noqa: E402

CHU_KY_MS = 60_000
HAN_MUC_O, HAN_MUC_GOI = 50_000, 2_500          # TomTom Evaluation / ngày

NEN, THE, VIEN = '#0b1220', '#131c2e', '#24324d'
CHU, CHU_PHU = '#e6edf7', '#8a9bb8'
XANH, VANG, DO, LAM = '#2fbf71', '#f2b33d', '#ef5350', '#4aa3ff'
FONT = 'Segoe UI'


def sn(n):
    """Số nguyên kiểu Việt Nam: 4.350"""
    return f'{n:,}'.replace(',', '.')


def tp(x, k=1):
    """Số thập phân kiểu Việt Nam: 99,3"""
    return f'{x:.{k}f}'.replace('.', ',')


KET_QUA_TAC_VU = {'0': 'tốt', '267009': 'đang chạy', '267011': 'chưa chạy lần nào', '267008': 'sẵn sàng',
                  '2147946720': 'bị dừng do quá giờ'}


def phut_truoc(t):
    return (dt.datetime.now() - t).total_seconds() / 60 if t else None


class The(tk.Frame):
    """Ô số liệu: nhãn nhỏ + số lớn + dòng phụ."""

    def __init__(self, cha, nhan):
        super().__init__(cha, bg=THE, highlightbackground=VIEN, highlightthickness=1, padx=14, pady=10)
        tk.Label(self, text=nhan, bg=THE, fg=CHU_PHU, font=(FONT, 9)).pack(anchor='w')
        self.so = tk.Label(self, text='—', bg=THE, fg=CHU, font=(FONT, 20, 'bold'))
        self.so.pack(anchor='w')
        self.phu = tk.Label(self, text='', bg=THE, fg=CHU_PHU, font=(FONT, 9))
        self.phu.pack(anchor='w')

    def dat(self, so, phu='', mau=CHU):
        self.so.config(text=so, fg=mau)
        self.phu.config(text=phu)


class TabBoThu(tk.Frame):
    def __init__(self, cha, ten, la_aws):
        super().__init__(cha, bg=NEN)
        self.ten, self.la_aws = ten, la_aws
        self.luot = []

        dau = tk.Frame(self, bg=NEN)
        dau.pack(fill='x', padx=16, pady=(14, 6))
        self.den = tk.Label(dau, text='●  ĐANG TẢI', bg=NEN, fg=CHU_PHU, font=(FONT, 15, 'bold'))
        self.den.pack(side='left')
        self.dong_cuoi = tk.Label(dau, text='', bg=NEN, fg=CHU_PHU, font=(FONT, 10))
        self.dong_cuoi.pack(side='left', padx=16)
        self.yeu_cau_lam_moi = None              # UngDung gán: gọi sau khi bấm nút điều khiển
        self.dang_bat = None                     # tác vụ hẹn giờ đang bật? (chỉ tab máy)
        if not la_aws:
            self._nut_dieu_khien(dau)

        hang = tk.Frame(self, bg=NEN)
        hang.pack(fill='x', padx=16)
        nhan = ['Lượt chạy hôm nay', 'Thành công', 'Lượt có lỗi', 'Request TomTom hôm nay',
                'Dữ liệu thu hôm nay', 'Thời gian chạy / lượt']
        self.the = [The(hang, n) for n in nhan]
        for i, t in enumerate(self.the):
            t.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 8, 0))
            hang.columnconfigure(i, weight=1)

        self.thong_tin = tk.Label(self, text='', bg=NEN, fg=CHU_PHU, font=(FONT, 9), anchor='w', justify='left')
        self.thong_tin.pack(fill='x', padx=16, pady=(8, 0))

        self.hinh = Figure(figsize=(10, 2.6), dpi=100, facecolor=NEN)
        self.ax1 = self.hinh.add_subplot(1, 2, 1)
        self.ax2 = self.hinh.add_subplot(1, 2, 2)
        self.ve = FigureCanvasTkAgg(self.hinh, master=self)
        self.ve.get_tk_widget().pack(fill='x', padx=10, pady=(6, 0))
        self._trang_tri()

        duoi = tk.Frame(self, bg=NEN)
        duoi.pack(fill='both', expand=True, padx=16, pady=(6, 12))
        cot = (['Thời điểm', 'Ô relative', 'Ô km/h', 'KB', 'Sự cố', 'Giây', 'RAM MB', 'Thời tiết', 'Lỗi']
               if la_aws else ['Thời điểm', 'Ô OK / tổng', 'Đoạn TomTom', 'Cạnh ghép', 'Ghép %', 'Sự cố', 'Giây',
                               'Thời tiết', 'Lỗi'])
        self.bang = ttk.Treeview(duoi, columns=cot, show='headings', height=10, style='Bang.Treeview')
        for c in cot:
            self.bang.heading(c, text=c)
            self.bang.column(c, width=360 if c == 'Lỗi' else 95, anchor='w' if c == 'Lỗi' else 'center')
        cuon = ttk.Scrollbar(duoi, orient='vertical', command=self.bang.yview)
        self.bang.configure(yscrollcommand=cuon.set)
        self.bang.pack(side='left', fill='both', expand=True)
        cuon.pack(side='left', fill='y')
        self.bang.tag_configure('loi', foreground=DO)
        self.bang.tag_configure('chan', background='#101828')

    # ── điều khiển bộ thu ở máy (bật/tắt tác vụ hẹn giờ Windows) ──
    def _nut_dieu_khien(self, cha):
        def nut(chu, mau, lenh):
            return tk.Button(cha, text=chu, command=lenh, bg=mau, fg='#ffffff', activebackground=mau,
                             activeforeground='#ffffff', disabledforeground='#6b7a94', relief='flat',
                             font=(FONT, 10, 'bold'), padx=14, pady=4, cursor='hand2')
        self.nut_chay = nut('Chạy 1 lượt ngay', '#2f6fd6', self._chay_ngay)
        self.nut_bat = nut('▶  Bắt đầu thu', '#1f8a52', self._bat)
        self.nut_dung = nut('■  Dừng thu', '#b83b3b', self._dung)
        for n in (self.nut_chay, self.nut_bat, self.nut_dung):
            n.pack(side='right', padx=(8, 0))
        self.thong_bao = tk.Label(cha, text='', bg=NEN, fg=CHU_PHU, font=(FONT, 9))
        self.thong_bao.pack(side='right', padx=12)
        self._cho_xac_nhan = False

    def _thuc_hien(self, ham, chu_dang_lam):
        self.thong_bao.config(text=chu_dang_lam, fg=CHU_PHU)
        for n in (self.nut_chay, self.nut_bat, self.nut_dung):
            n.config(state='disabled')

        def chay():
            ok, tb = ham()
            self.after(0, lambda: self._xong(ok, tb))
        threading.Thread(target=chay, daemon=True).start()

    def _xong(self, ok, tb):
        self.thong_bao.config(text=('✓ ' if ok else '✗ ') + (tb or ('xong' if ok else 'lỗi')), fg=XANH if ok else DO)
        self._dat_nut()
        if self.yeu_cau_lam_moi:
            self.yeu_cau_lam_moi()

    def _dung(self):
        # Bấm 2 lần trong 5 giây mới dừng: tránh lỡ tay làm thủng dữ liệu.
        if not self._cho_xac_nhan:
            self._cho_xac_nhan = True
            self.nut_dung.config(text='Bấm lần nữa để DỪNG')
            self.after(5000, self._huy_xac_nhan)
            return
        self._cho_xac_nhan = False
        self.nut_dung.config(text='■  Dừng thu')
        self._thuc_hien(nguon_may.tat_tac_vu, 'Đang dừng bộ thu…')

    def _huy_xac_nhan(self):
        if self._cho_xac_nhan:
            self._cho_xac_nhan = False
            self.nut_dung.config(text='■  Dừng thu')

    def _bat(self):
        self._thuc_hien(nguon_may.bat_tac_vu, 'Đang bật bộ thu…')

    def _chay_ngay(self):
        self._thuc_hien(nguon_may.chay_ngay, 'Đang chạy 1 lượt…')

    def _dat_nut(self):
        """Nút nào bấm được tùy tác vụ đang bật hay tắt (chưa biết thì cho bấm cả)."""
        if self.la_aws:
            return
        bat = self.dang_bat
        self.nut_dung.config(state='disabled' if bat is False else 'normal')
        self.nut_bat.config(state='disabled' if bat is True else 'normal')
        self.nut_chay.config(state='disabled' if bat is False else 'normal')

    # ── vẽ ──
    def _trang_tri(self):
        for ax in (self.ax1, self.ax2):
            ax.clear()
            ax.set_facecolor(THE)
            ax.tick_params(colors=CHU_PHU, labelsize=8)
            for vien in ax.spines.values():
                vien.set_color(VIEN)
        self.ve.draw_idle()

    def bao_loi(self, chu, mau=DO):
        self.den.config(text=f'●  {chu}', fg=mau)

    def cap_nhat(self, luot, phu):
        self.luot = luot
        if not self.la_aws:
            trang_thai = phu.get('tac_vu', {}).get('Scheduled Task State')
            self.dang_bat = {'Enabled': True, 'Disabled': False}.get(trang_thai)
            self._dat_nut()
        if not luot:
            self.bao_loi('CHƯA CÓ DỮ LIỆU', VANG)
            return
        thuc = [x for x in luot if not x.get('chi_loi') and not x.get('bo_qua')]
        cuoi = thuc[-1]['t'] if thuc else luot[-1]['t']
        p = phut_truoc(cuoi)
        if self.dang_bat is False:
            self.den.config(text='●  ĐÃ DỪNG (tác vụ hẹn giờ đang tắt)', fg=VANG)
        elif p <= 7:
            self.den.config(text='●  ĐANG CHẠY', fg=XANH)
        elif p <= 15:
            self.den.config(text='●  CHẬM', fg=VANG)
        else:
            self.den.config(text='●  NGỪNG?', fg=DO)
        self.dong_cuoi.config(text=f'Lượt cuối {cuoi:%H:%M:%S} ({p:.0f} phút trước) · 5 phút/lượt')

        hom_nay = dt.date.today()
        hn = [x for x in luot if x['t'].date() == hom_nay]
        hn_thuc = [x for x in hn if not x.get('chi_loi') and not x.get('bo_qua')]
        co_loi = [x for x in hn if x['loi'] or (self.la_aws and x['o_loi']) or (not self.la_aws and x['o_loi'])]
        tc = 100 * (1 - len(co_loi) / max(len(hn), 1))
        self.the[0].dat(f'{len(hn_thuc)}', f'24 giờ qua: {len([x for x in luot if not x.get("chi_loi")])}')
        self.the[1].dat(f'{tp(tc)}%', 'lượt không lỗi', XANH if tc >= 99 else VANG if tc >= 95 else DO)
        self.the[2].dat(f'{len(co_loi)}', 'hôm nay', XANH if not co_loi else DO)
        giay = [x['giay'] for x in hn_thuc if x.get('giay')]
        if self.la_aws:
            o = sum(x['o_duoc'] + x['o_loi'] + x['o_them_duoc'] for x in hn)
            goi = len(hn_thuc)
            self.the[3].dat(sn(o + goi), f'{sn(o)} ô bản đồ + {sn(goi)} lượt sự cố')
            mb = sum(x['kb'] for x in hn) / 1024
            self.the[4].dat(f'{tp(mb)} MB', f'{len(hn_thuc)} zip + sự cố lên S3')
            ram = [x['mb_ram'] for x in hn if x.get('mb_ram')]
            tien = [x['ms_tinh_tien'] for x in hn if x.get('ms_tinh_tien')]
            self.thong_tin.config(text=(
                f'RAM tối đa {max(ram) if ram else "—"} MB / 256 MB   ·   thời gian tính tiền TB '
                f'{tp(sum(tien) / len(tien) / 1000 if tien else 0)} s   ·   dự báo thời tiết hôm nay: '
                f'{sum(1 for x in hn if x["thoi_tiet"])} lần   ·   sự cố TB '
                f'{(sum(x["su_co"] or 0 for x in hn_thuc) / max(len(hn_thuc), 1)):.0f}/lượt'))
        else:
            o = sum(x['o_tong'] for x in hn)
            goi = len(hn_thuc)
            self.the[3].dat(sn(o + goi), f'{sn(o)} ô bản đồ + {sn(goi)} lượt sự cố')
            dl = phu.get('dung_luong', {})
            mb = sum(v[1] for v in dl.values())
            self.the[4].dat(f'{tp(mb)} MB', ' · '.join(f'{k} {v[0]}' for k, v in dl.items()) + ' tệp')
            tv = phu.get('tac_vu', {})
            self.thong_tin.config(text=(
                f'Tác vụ hẹn giờ: {tv.get("Status", tv.get("loi", "?"))}   ·   lần chạy kế '
                f'{tv.get("Next Run Time", "?")}   ·   lần trước: '
                f'{KET_QUA_TAC_VU.get(tv.get("Last Result", ""), "LỖI mã " + tv.get("Last Result", "?"))}   ·   '
                f'ghép TB {(sum(x["ghep_pt"] for x in hn_thuc) / max(len(hn_thuc), 1)):.0f}% mẫu'))
        if giay:
            self.the[5].dat(f'{tp(sum(giay) / len(giay))} s', f'nhanh nhất {tp(min(giay))} · chậm nhất {tp(max(giay))}')

        # Biểu đồ 24 giờ.
        self._trang_tri()
        t = [x['t'] for x in thuc]
        self.ax1.plot(t, [x.get('giay') or 0 for x in thuc], color=LAM, lw=1.2)
        loi_t = [x['t'] for x in luot if x['loi'] or x.get('o_loi')]
        if loi_t:
            self.ax1.scatter(loi_t, [0] * len(loi_t), color=DO, s=18, zorder=3, label='lượt lỗi')
            self.ax1.legend(fontsize=8, facecolor=THE, labelcolor=CHU, edgecolor=VIEN)
        self.ax1.set_title('Thời gian mỗi lượt (giây) — 24 giờ', color=CHU, fontsize=9)
        self.ax2.plot(t, [x.get('su_co') or 0 for x in thuc], color=VANG, lw=1.2)
        self.ax2.set_title('Sự cố TomTom đang ghi nhận mỗi lượt', color=CHU, fontsize=9)
        for ax in (self.ax1, self.ax2):
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
        self.hinh.tight_layout()
        self.ve.draw_idle()

        # Bảng 40 lượt gần nhất (mới ở trên).
        self.bang.delete(*self.bang.get_children())
        for i, x in enumerate(reversed(luot[-40:])):
            loi = '; '.join(x['loi'])
            if self.la_aws:
                gt = (f'{x["t"]:%d/%m %H:%M:%S}', f'{x["o_duoc"]}/{x["o_duoc"] + x["o_loi"]}', x['o_them_duoc'],
                      x['kb'], x['su_co'] if x['su_co'] is not None else '—', tp(x['giay']) if x['giay'] else '—',
                      x['mb_ram'] or '—', 'có' if x['thoi_tiet'] else '', loi)
            else:
                gt = (f'{x["t"]:%d/%m %H:%M:%S}', f'{x["o_tong"] - x["o_loi"]}/{x["o_tong"]}', x['doan'], x['canh'],
                      x['ghep_pt'], x['su_co'] if x['su_co'] is not None else '—', tp(x['giay']) if x['giay'] else '—',
                      'có' if x['thoi_tiet'] else '', loi)
            the = ['loi'] if (loi or x.get('o_loi')) else (['chan'] if i % 2 else [])
            self.bang.insert('', 'end', values=gt, tags=the)


class UngDung(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Bảng theo dõi thu dữ liệu giao thông TP.HCM')
        self.geometry('1320x860')
        self.minsize(1100, 720)
        self.configure(bg=NEN)
        self._kieu()
        self.hang_doi = queue.Queue()

        dau = tk.Frame(self, bg=NEN)
        dau.pack(fill='x', padx=16, pady=(12, 0))
        tk.Label(dau, text='Thu dữ liệu giao thông TP.HCM', bg=NEN, fg=CHU, font=(FONT, 17, 'bold')).pack(side='left')
        self.gio = tk.Label(dau, text='', bg=NEN, fg=CHU_PHU, font=(FONT, 10))
        self.gio.pack(side='right')
        nut = tk.Button(dau, text='Làm mới', command=self.lam_moi, bg=VIEN, fg=CHU, activebackground=LAM,
                        activeforeground=CHU, relief='flat', font=(FONT, 10, 'bold'), padx=14, pady=4, cursor='hand2')
        nut.pack(side='right', padx=12)

        hm = tk.Frame(self, bg=THE, highlightbackground=VIEN, highlightthickness=1, padx=14, pady=8)
        hm.pack(fill='x', padx=16, pady=10)
        tk.Label(hm, text='Hạn mức TomTom hôm nay (cả hai bộ thu)', bg=THE, fg=CHU_PHU, font=(FONT, 9)).grid(
            row=0, column=0, columnspan=4, sticky='w')
        self.hm_o_chu = tk.Label(hm, text='', bg=THE, fg=CHU, font=(FONT, 10, 'bold'))
        self.hm_o_chu.grid(row=1, column=0, sticky='w')
        self.hm_o = ttk.Progressbar(hm, length=380, maximum=HAN_MUC_O, style='HanMuc.Horizontal.TProgressbar')
        self.hm_o.grid(row=1, column=1, padx=(10, 30))
        self.hm_goi_chu = tk.Label(hm, text='', bg=THE, fg=CHU, font=(FONT, 10, 'bold'))
        self.hm_goi_chu.grid(row=1, column=2, sticky='w')
        self.hm_goi = ttk.Progressbar(hm, length=380, maximum=HAN_MUC_GOI, style='HanMuc.Horizontal.TProgressbar')
        self.hm_goi.grid(row=1, column=3, padx=10)

        so = ttk.Notebook(self, style='Tab.TNotebook')
        so.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.tab_aws = TabBoThu(so, 'AWS', True)
        self.tab_may = TabBoThu(so, 'May', False)
        self.tab_may.yeu_cau_lam_moi = lambda: self.after(1500, self.lam_moi)
        so.add(self.tab_aws, text='   AWS (Lambda, 24/7)   ')
        so.add(self.tab_may, text='   Máy nhà (local)   ')

        self._dang_tai = False
        self.after(200, self._tu_dong)
        self.after(300, self._nhan)
        self._dong_ho()

    def _kieu(self):
        s = ttk.Style(self)
        s.theme_use('clam')
        s.configure('Tab.TNotebook', background=NEN, borderwidth=0)
        s.configure('Tab.TNotebook.Tab', background=THE, foreground=CHU_PHU, padding=(10, 6), font=(FONT, 10, 'bold'),
                    borderwidth=0)
        s.map('Tab.TNotebook.Tab', background=[('selected', VIEN)], foreground=[('selected', CHU)])
        s.configure('Bang.Treeview', background=THE, fieldbackground=THE, foreground=CHU, rowheight=24,
                    font=(FONT, 9), borderwidth=0)
        s.configure('Bang.Treeview.Heading', background=VIEN, foreground=CHU, font=(FONT, 9, 'bold'), relief='flat')
        s.map('Bang.Treeview', background=[('selected', '#2b4a7a')])
        s.configure('HanMuc.Horizontal.TProgressbar', troughcolor=NEN, background=XANH, bordercolor=VIEN,
                    lightcolor=XANH, darkcolor=XANH)

    def _dong_ho(self):
        self.gio.config(text=dt.datetime.now().strftime('%H:%M:%S  %d/%m/%Y'))
        self.after(1000, self._dong_ho)

    def lam_moi(self):
        """Nút Làm mới: đọc lại ngay (bỏ qua nếu lượt đọc trước chưa xong)."""
        if not self._dang_tai:
            self._dang_tai = True
            threading.Thread(target=self._tai, daemon=True).start()

    def _tu_dong(self):
        self.lam_moi()
        self.after(CHU_KY_MS, self._tu_dong)

    def _tai(self):
        """Chạy ở luồng phụ: đọc cả hai nguồn rồi gửi kết quả về luồng giao diện."""
        try:
            self._tai_hai_nguon()
        finally:
            self._dang_tai = False

    def _tai_hai_nguon(self):
        try:
            self.hang_doi.put(('may', nguon_may.doc_luot(24),
                               {'tac_vu': nguon_may.tac_vu(), 'dung_luong': nguon_may.dung_luong_hom_nay()}))
        except Exception as e:                                  # noqa: BLE001
            self.hang_doi.put(('may_loi', str(e)[:200], None))
        try:
            self.hang_doi.put(('aws', nguon_aws.doc_luot(24), {}))
        except nguon_aws.ChuaCoQuyen:
            self.hang_doi.put(('aws_loi', 'CHƯA CÓ QUYỀN ĐỌC LOG AWS — cần bấm Create policy (note/CAN_NHO.md)', None))
        except Exception as e:                                  # noqa: BLE001
            self.hang_doi.put(('aws_loi', f'LỖI ĐỌC LOG: {str(e)[:120]}', None))

    def _nhan(self):
        try:
            while True:
                loai, du, phu = self.hang_doi.get_nowait()
                if loai == 'may':
                    self.tab_may.cap_nhat(du, phu)
                elif loai == 'aws':
                    self.tab_aws.cap_nhat(du, phu)
                elif loai == 'may_loi':
                    self.tab_may.bao_loi(du)
                elif loai == 'aws_loi':
                    self.tab_aws.bao_loi(du, VANG)
                self._han_muc()
        except queue.Empty:
            pass
        self.after(300, self._nhan)

    def _han_muc(self):
        hn = dt.date.today()
        o = goi = 0
        for x in self.tab_aws.luot:
            if x['t'].date() == hn and not x.get('chi_loi'):
                o += x['o_duoc'] + x['o_loi'] + x['o_them_duoc']
                goi += 1
        for x in self.tab_may.luot:
            if x['t'].date() == hn and not x.get('bo_qua'):
                o += x['o_tong']
                goi += 1
        self.hm_o['value'] = min(o, HAN_MUC_O)
        self.hm_goi['value'] = min(goi, HAN_MUC_GOI)
        self.hm_o_chu.config(text=f'Ô bản đồ: {sn(o)} / {sn(HAN_MUC_O)} ({100 * o / HAN_MUC_O:.0f}%)')
        self.hm_goi_chu.config(text=f'Lượt gọi sự cố: {sn(goi)} / {sn(HAN_MUC_GOI)} ({100 * goi / HAN_MUC_GOI:.0f}%)')


if __name__ == '__main__':
    UngDung().mainloop()
