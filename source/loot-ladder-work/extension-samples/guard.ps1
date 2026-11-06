$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$p=@(tasklist /fo csv|ConvertFrom-Csv|Where-Object {$_.'Image Name' -match '(?i)DeltaForce|AntiCheat|SGuard|^ACE[-_.]'})
$s=@(Get-Service|Where-Object {$_.Name -match '(?i)AntiCheatExpert|^ACE[-_]|^SGuard' -and $_.Status -ne 'Stopped'})
$d=(sc.exe query type= driver state= active|Out-String)
if($p.Count -or $s.Count -or $d -match '(?im)SERVICE_NAME:.*(ACE[-_]|AntiCheat|SGuard)'){Write-Output 'DF/ACE ACTIVE. STOP';exit 4}
if((Get-PSDrive E).Free -lt 20000000000){exit 5}
Write-Output (Get-Date -Format o);exit 0