@echo off
rem Tat bo thu du lieu tu dong (go hen gio Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cai_hen_gio.ps1" -Go
pause
