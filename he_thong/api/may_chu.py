"""
API định tuyến + web demo giao diện cơ bản (QĐ-018). Hiện chỉ chạy ở máy để test chức năng.

Chỉ nghe 127.0.0.1, chưa có mật khẩu: dữ liệu TomTom gói Evaluation không được mở công khai. Đưa lên VPS (QĐ-017) phải
thêm mật khẩu trước.

  GET  /api/thong-tin           khoảng dữ liệu, vùng bản đồ
  POST /api/tuyen               3 phương án + thực tế đã xảy ra
  POST /api/tuyen-thay-the      các tuyến khác nhau (tốn 1–3 s, gọi khi người dùng bấm)
  GET  /api/hinh-doan           hình các đoạn chính (không đổi, trình duyệt giữ lại)
  GET  /api/tinh-trang?luc=     r từng đoạn ở lần chụp gần thời điểm đó
  GET  /api/du-bao?luc=&tam=30  r dự báo (GBM + hồ sơ, ngoài mẫu) từng đoạn cho 15/30/45/60 phút tới (QĐ-028)
  GET  /api/ngap                điểm dễ ngập đã ghép vào bản đồ
  POST /api/dan-duong           chỉ dẫn từng chặng + xe ảo chạy lại trên số đo thật của một tuyến
  POST /api/tinh-lai            xe đang chạy, có lần chụp mới: giữ tuyến hay đổi tuyến

Chạy:  python he_thong/api/may_chu.py [--cong=8770]
       python he_thong/api/may_chu.py --dung-ho-so    (tính lại hồ sơ tốc độ sau khi kéo dữ liệu mới)
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dich_vu import DichVu, LoiYeuCau, dung_ho_so  # noqa: E402

WEB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web'))
dv = None


@asynccontextmanager
async def vong_doi(_app):
    global dv
    dv = DichVu()
    print('San sang.', flush=True)
    yield


app = FastAPI(title='Dinh tuyen giao hang xe may TP.HCM', lifespan=vong_doi)
app.add_middleware(GZipMiddleware, minimum_size=2000)


class YeuCauTuyen(BaseModel):
    di: tuple[float, float] = Field(description='[vĩ độ, kinh độ] điểm đi')
    den: tuple[float, float] = Field(description='[vĩ độ, kinh độ] điểm đến')
    luc: Optional[str] = Field(None, description='Thời điểm trong dữ liệu đã thu; bỏ trống = lần chụp mới nhất')
    mua_mm: float = Field(0.0, ge=0, le=200)
    trieu_cuong: bool = False


class YeuCauDanDuong(BaseModel):
    canh: list[int] = Field(max_length=20000, description='Các cạnh của tuyến, lấy từ /api/tuyen')
    luc: Optional[str] = None


class YeuCauTinhLai(BaseModel):
    canh_vua_qua: int
    canh_con_lai: list[int] = Field(max_length=20000)
    den: tuple[float, float]
    luc: str
    mua_mm: float = Field(0.0, ge=0, le=200)
    trieu_cuong: bool = False


@app.exception_handler(LoiYeuCau)
async def loi_yeu_cau(_request, loi):
    return JSONResponse(status_code=400, content={'loi': str(loi)})


@app.get('/api/thong-tin')
def thong_tin():
    return dv.thong_tin()


@app.post('/api/tuyen')
def tuyen(y: YeuCauTuyen):
    return dv.tuyen(y.di, y.den, y.luc, y.mua_mm, y.trieu_cuong)


@app.post('/api/tuyen-thay-the')
def tuyen_thay_the(y: YeuCauTuyen):
    return dv.tuyen_thay_the(y.di, y.den, y.luc, y.mua_mm, y.trieu_cuong)


@app.post('/api/dan-duong')
def dan_duong(y: YeuCauDanDuong):
    return dv.dan_duong(y.canh, y.luc)


@app.post('/api/tinh-lai')
def tinh_lai(y: YeuCauTinhLai):
    return dv.tinh_lai(y.canh_vua_qua, y.canh_con_lai, y.den, y.luc, y.mua_mm, y.trieu_cuong)


@app.get('/api/hinh-doan')
def hinh_doan():
    return JSONResponse(dv.hinh_doan(), headers={'Cache-Control': 'max-age=3600'})


@app.get('/api/tinh-trang')
def tinh_trang(luc: Optional[str] = Query(None)):
    return dv.tinh_trang(luc)


@app.get('/api/du-bao')
def du_bao(luc: Optional[str] = Query(None), tam: int = Query(30)):
    return dv.du_bao(luc, tam)


@app.get('/api/ngap')
def ngap():
    return dv.ngap()


@app.get('/')
def trang_chu():
    tep = os.path.join(WEB, 'index.html')
    if not os.path.exists(tep):
        raise HTTPException(404, 'Chua co giao dien')
    return FileResponse(tep)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--dung-ho-so' in sys.argv:
        dung_ho_so()
        print('Da tinh lai ho so toc do')
        sys.exit(0)
    cong = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--cong=')), 8770)
    uvicorn.run(app, host='127.0.0.1', port=cong, log_level='warning')
