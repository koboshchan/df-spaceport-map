[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputMap,
    [Parameter(Mandatory = $true)]
    [string]$LogPath,
    [string]$Compiler = "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\resourcecompiler.exe",
    [string]$Game = "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo"
)

$ErrorActionPreference = "Stop"
$gameInfo = Join-Path $Game "gameinfo.gi"
$backup = Join-Path ([System.IO.Path]::GetTempPath()) ("gameinfo-{0}.gi" -f [guid]::NewGuid())
$compileExit = 1

Copy-Item -LiteralPath $gameInfo -Destination $backup -Force
try {
    $text = [System.IO.File]::ReadAllText($gameInfo)
    $updated = [regex]::Replace(
        $text,
        '("bakedlighting"\s+")1(")',
        '${1}0${2}',
        1
    )
    if ($updated -eq $text) {
        throw "Could not disable bakedlighting in $gameInfo"
    }

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($gameInfo, $updated, $utf8)

    & $Compiler -nop4 -game $Game -f $InputMap *> $LogPath
    $compileExit = $LASTEXITCODE
}
finally {
    Copy-Item -LiteralPath $backup -Destination $gameInfo -Force
    Remove-Item -LiteralPath $backup -Force
    Write-Output "GAMEINFO_RESTORED=$gameInfo"
}

Write-Output "COMPILE_EXIT=$compileExit"
exit $compileExit
