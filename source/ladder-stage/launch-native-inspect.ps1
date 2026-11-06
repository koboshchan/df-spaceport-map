$ErrorActionPreference='Stop'
$a=New-ScheduledTaskAction -Execute 'E:\spaceport-kat-rebuild-20261105\material-venv\Scripts\python.exe' -Argument 'E:\df-v25-build-20261106\ladder-stage\inspect-native-compiled.py' -WorkingDirectory 'E:\df-v25-build-20261106\ladder-stage'
$p=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value) -LogonType Interactive -RunLevel Limited
$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'KatV25NativeInspect' -InputObject (New-ScheduledTask -Action $a -Principal $p -Settings $s) -Force | Out-Null
Start-ScheduledTask -TaskName 'KatV25NativeInspect'
