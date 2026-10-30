"""Cho pytest tìm thấy các mô-đun của dự án (chạy: python -m pytest kiem_thu -q)."""
import os
import sys

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for thu_muc in ('dinh_tuyen', 'thu_thap', 'xu_ly', 'khai_pha', 'mo_hinh'):
    sys.path.insert(0, os.path.join(GOC, thu_muc))
