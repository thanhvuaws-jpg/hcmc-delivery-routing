@echo off
chcp 65001 >nul
rem Kéo dữ liệu gốc mà bộ thu AWS đã lưu trên S3 về máy, rồi dựng lại tầng bạc.
rem  - Chỉ TẢI tệp mới/khác, không xóa gì ở máy, không ghi gì lên S3.
rem  - Cần profile AWS "thuctap-doc" (user IAM CHỈ ĐỌC bucket) — cách tạo: note/CAN_NHO.md, mục AWS.
rem  - Không ghi khóa vào tệp này: khóa nằm trong %%USERPROFILE%%\.aws\credentials do "aws configure" tạo.
rem  - Tên bucket đọc từ .env (dòng S3_BUCKET=...): repo GitHub công khai nên không ghi tên ở đây.
cd /d "%~dp0.."
set S3_BUCKET=
for /f "usebackq tokens=1,* delims==" %%a in (".env") do if "%%a"=="S3_BUCKET" set S3_BUCKET=%%b
if "%S3_BUCKET%"=="" (
  echo LOI: chua co dong S3_BUCKET=... trong .env
  pause
  exit /b 1
)
echo Dang keo du lieu tu S3 ve du_lieu\s3\dong ...
aws s3 sync s3://%S3_BUCKET%/dong du_lieu\s3\dong --profile thuctap-doc --only-show-errors
if errorlevel 1 (
  echo LOI: chua keo duoc. Kiem tra profile thuctap-doc ^(aws configure --profile thuctap-doc^).
  pause
  exit /b 1
)
echo Dang dung tang bac ...
python xu_ly\bac_tomtom.py
python xu_ly\bac_su_co.py
python xu_ly\bac_thoi_tiet.py
python xu_ly\vang.py
echo Xong.
pause
