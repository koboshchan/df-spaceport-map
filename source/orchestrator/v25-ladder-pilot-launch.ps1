$ErrorActionPreference='Stop'
$a=New-ScheduledTaskAction -Execute 'E:\spaceport-kat-rebuild-20261105\material-venv\Scripts\python.exe' -Argument '-B E:\df-v25-build-20261106\orchestrator\ladder-pilot.py' -WorkingDirectory 'E:\df-v25-build-20261106\orchestrator'
$p=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value) -LogonType Interactive -RunLevel Limited
$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'KatDFv25LadderPilot20261106' -InputObject (New-ScheduledTask -Action $a -Principal $p -Settings $s) | Out-Null
Start-ScheduledTask -TaskName 'KatDFv25LadderPilot20261106'
