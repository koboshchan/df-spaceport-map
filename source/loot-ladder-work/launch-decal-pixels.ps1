$ErrorActionPreference='Stop'
$a=New-ScheduledTaskAction -Execute 'E:\spaceport-kat-rebuild-20261105\material-venv\Scripts\python.exe' -Argument 'E:\df-v24-build-20261106\loot-ladder-work\decal-pixels-runner.py' -WorkingDirectory 'E:\df-v24-build-20261106'
$p=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value) -LogonType Interactive -RunLevel Limited
$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$t=New-ScheduledTask -Action $a -Principal $p -Settings $s
Register-ScheduledTask -TaskName 'KatDFv24DecalPixels20261106' -InputObject $t | Out-Null
Start-ScheduledTask -TaskName 'KatDFv24DecalPixels20261106'
