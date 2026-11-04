[CmdletBinding()]
param(
    [string]$Cs2Root,
    [ValidateSet("df_spaceport_player_scale_raytrace", "df_spaceport_player_scale_clear", "df_spaceport_player_scale_noflicker", "df_spaceport_player_scale", "df_spaceport_full40_open", "df_spaceport_full40_open_lit")]
    [string]$Map = "df_spaceport_player_scale_raytrace"
)

$ErrorActionPreference = "Stop"
$PackageRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$SourceAddon = Join-Path $PackageRoot "addon"

function Find-Cs2Root {
    if ($Cs2Root) {
        $candidate = (Resolve-Path -LiteralPath $Cs2Root).Path
        if (Test-Path -LiteralPath (Join-Path $candidate "game\bin\win64\cs2.exe")) {
            return $candidate
        }
        throw "The supplied Cs2Root does not contain game\bin\win64\cs2.exe."
    }

    $steamExe = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction SilentlyContinue).SteamExe
    if (-not $steamExe) {
        $steamExe = Join-Path ${env:ProgramFiles(x86)} "Steam\steam.exe"
    }
    if (-not (Test-Path -LiteralPath $steamExe)) {
        throw "Steam was not found. Pass -Cs2Root with the CS2 installation folder."
    }

    $steamRoot = Split-Path -Parent $steamExe
    $libraryRoots = @($steamRoot)
    $libraryFile = Join-Path $steamRoot "steamapps\libraryfolders.vdf"
    if (Test-Path -LiteralPath $libraryFile) {
        $libraryText = Get-Content -LiteralPath $libraryFile -Raw
        foreach ($match in [regex]::Matches($libraryText, '"path"\s+"([^"]+)"')) {
            $libraryRoots += $match.Groups[1].Value.Replace("\\", "\")
        }
    }

    foreach ($libraryRoot in $libraryRoots | Select-Object -Unique) {
        $candidate = Join-Path $libraryRoot "steamapps\common\Counter-Strike Global Offensive"
        if (Test-Path -LiteralPath (Join-Path $candidate "game\bin\win64\cs2.exe")) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Counter-Strike 2 was not found in a Steam library."
}

$Cs2Root = Find-Cs2Root
$CompilerPath = Join-Path $Cs2Root "game\bin\win64\resourcecompiler.exe"
if (-not (Test-Path -LiteralPath $CompilerPath)) {
    throw "CS2 Workshop Tools are not installed. Install DLC 2279721 in Steam first."
}

$AddonRoot = Join-Path $Cs2Root "game\csgo_addons\df_spaceport"
New-Item -ItemType Directory -Force -Path $AddonRoot | Out-Null
try {
    Copy-Item -Path (Join-Path $SourceAddon "*") -Destination $AddonRoot -Recurse -Force
}
catch {
    throw "Could not install the addon. Close Counter-Strike 2 and run the script again."
}

$steamExe = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction SilentlyContinue).SteamExe
if (-not $steamExe) {
    $steamExe = Join-Path ${env:ProgramFiles(x86)} "Steam\steam.exe"
}

Write-Host "Installed $Map to $AddonRoot"
Write-Host "Starting CS2 Workshop Tools..."
Start-Process -FilePath $steamExe -ArgumentList @(
    "-applaunch",
    "730",
    "-tools",
    "-console",
    "-condebug",
    "+map_workshop",
    "df_spaceport",
    $Map
)
