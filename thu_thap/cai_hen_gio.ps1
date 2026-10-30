# Cai / go bo hen gio Windows chay thu_dinh_ky.py 5 phut mot lan.
#
#   powershell -ExecutionPolicy Bypass -File cai_hen_gio.ps1          cai (hoac cai lai)
#   powershell -ExecutionPolicy Bypass -File cai_hen_gio.ps1 -Go      go bo
#   Get-ScheduledTask -TaskPath '\ThucTapTotNghiep\' | Get-ScheduledTaskInfo   xem lan chay cuoi
#
# Dung pythonw.exe: khong bat cua so den moi 5 phut.
# Chay ca khi dung pin, may thuc day thi chay bu, khong chay chong hai luot.
# Chi chay khi nguoi dung dang dang nhap — khong can luu mat khau Windows.
param([switch]$Go)

$ten = 'ThuDuLieuGiaoThong'
$thuMuc = '\ThucTapTotNghiep\'

if ($Go) {
    Unregister-ScheduledTask -TaskName $ten -TaskPath $thuMuc -Confirm:$false
    "Da go bo hen gio $thuMuc$ten"
    return
}

$pythonw = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'
$script = Join-Path $PSScriptRoot 'thu_dinh_ky.py'

$hanhDong = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $script + '"') -WorkingDirectory $PSScriptRoot
$kichHoat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
$caiDat = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4)

Register-ScheduledTask -TaskName $ten -TaskPath $thuMuc -Action $hanhDong -Trigger $kichHoat `
    -Settings $caiDat -Description 'Thuc tap tot nghiep: thu muc ket xe + su co TomTom, du bao thoi tiet (5 phut/lan)' `
    -Force | Out-Null

"Da cai hen gio $thuMuc$ten"
"  chay: $pythonw `"$script`""
"  lan dau: $((Get-Date).AddMinutes(1).ToString('HH:mm')), sau do 5 phut/lan"
