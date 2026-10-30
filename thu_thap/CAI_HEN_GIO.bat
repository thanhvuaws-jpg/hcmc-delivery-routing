@echo off
rem Bam dup tep nay MOT LAN de bat bo thu du lieu tu chay 5 phut/lan.
rem Go bo: chay  GO_HEN_GIO.bat
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cai_hen_gio.ps1"
echo.
echo Kiem tra: mo Task Scheduler ^> Task Scheduler Library ^> ThucTapTotNghiep
pause
