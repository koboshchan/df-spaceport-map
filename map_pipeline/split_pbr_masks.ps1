[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Manifest,
    [Parameter(Mandatory = $true)]
    [string]$AddonRoot,
    [Parameter(Mandatory = $true)]
    [string]$ContentRoot,
    [Parameter(Mandatory = $true)]
    [string]$FileList,
    [Parameter(Mandatory = $true)]
    [string]$Report,
    [string]$BackupRoot = ".\map_build\analysis\vmat_pbr_backup"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$drawingAssembly = [System.Drawing.Bitmap].Assembly.Location
$drawingPrimitivesAssembly = [System.Drawing.Rectangle].Assembly.Location
$gdiPlusAssembly = Join-Path (Split-Path -Parent $drawingAssembly) "System.Private.Windows.GdiPlus.dll"
$windowsCoreAssembly = Join-Path (Split-Path -Parent $drawingAssembly) "System.Private.Windows.Core.dll"
Add-Type @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class DfPbrSplit {
    private static Bitmap MakeChannel(Bitmap source, int channel) {
        int width = source.Width;
        int height = source.Height;
        var sourceRect = new Rectangle(0, 0, width, height);
        var sourceData = source.LockBits(sourceRect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        var destination = new Bitmap(width, height, PixelFormat.Format8bppIndexed);
        var palette = destination.Palette;
        for (int i = 0; i < 256; i++) {
            palette.Entries[i] = Color.FromArgb(255, i, i, i);
        }
        destination.Palette = palette;
        var destinationRect = new Rectangle(0, 0, width, height);
        var destinationData = destination.LockBits(destinationRect, ImageLockMode.WriteOnly, PixelFormat.Format8bppIndexed);
        try {
            unsafe {
                byte* sourceBase = (byte*)sourceData.Scan0.ToPointer();
                byte* destinationBase = (byte*)destinationData.Scan0.ToPointer();
                for (int y = 0; y < height; y++) {
                    byte* sourceRow = sourceBase + y * sourceData.Stride;
                    byte* destinationRow = destinationBase + y * destinationData.Stride;
                    for (int x = 0; x < width; x++) {
                        int offset = x * 4 + channel;
                        destinationRow[x] = sourceRow[offset];
                    }
                }
            }
        }
        finally {
            source.UnlockBits(sourceData);
            destination.UnlockBits(destinationData);
        }
        return destination;
    }

    public static void Split(string input, string metalness, string roughness, string ao, bool orm) {
        using (var source = new Bitmap(input)) {
            // Format32bppArgb stores channels in B, G, R, A byte order.
            int metalChannel = orm ? 0 : 2;
            int roughChannel = 1;
            int aoChannel = orm ? 2 : 0;
            using (var metal = MakeChannel(source, metalChannel)) metal.Save(metalness, ImageFormat.Png);
            using (var rough = MakeChannel(source, roughChannel)) rough.Save(roughness, ImageFormat.Png);
            using (var occlusion = MakeChannel(source, aoChannel)) occlusion.Save(ao, ImageFormat.Png);
        }
    }
}
'@ -CompilerOptions "/unsafe" -ReferencedAssemblies @(
    $drawingAssembly,
    $drawingPrimitivesAssembly,
    $gdiPlusAssembly,
    $windowsCoreAssembly
)

$manifestPath = (Resolve-Path -LiteralPath $Manifest).Path
$addonRootPath = (Resolve-Path -LiteralPath $AddonRoot).Path
$contentRootPath = $ContentRoot
$fileListPath = [System.IO.Path]::GetFullPath($FileList)
$reportPath = [System.IO.Path]::GetFullPath($Report)
$backupPath = [System.IO.Path]::GetFullPath($BackupRoot)

$manifestData = Get-Content -LiteralPath $manifestPath -Raw |
    ConvertFrom-Json -AsHashtable
$includeTokens = @(
    "building", "wall", "concrete", "ground", "floor",
    "road", "metal", "trim", "structure", "rock", "terrain"
)
$excludeTokens = @(
    "decal", "glass", "leaf", "leaves", "plant", "tree",
    "window", "lighting", "emissive", "sign", "sticker",
    "banner", "cloth", "water"
)

function Test-ArchitecturalMaterial([string]$Name) {
    $lower = $Name.ToLowerInvariant()
    $included = $false
    foreach ($token in $includeTokens) {
        if ($lower.Contains($token)) {
            $included = $true
            break
        }
    }
    if (-not $included) {
        return $false
    }
    foreach ($token in $excludeTokens) {
        if ($lower.Contains($token)) {
            return $false
        }
    }
    return $true
}

$sourceImages = @{}
$materialRecords = @()
foreach ($entry in $manifestData["materials"].GetEnumerator()) {
    if (-not (Test-ArchitecturalMaterial $entry.Key)) {
        continue
    }
    $record = $entry.Value
    $roles = $record["roles"]
    $packed = $roles["roughness"]
    if (-not $packed -or
        $packed -ne $roles["metalness"] -or
        $packed -ne $roles["occlusion"]) {
        continue
    }
    $lower = $packed.ToLowerInvariant()
    $isOrm = $lower.Contains("_orm")
    if (-not ($lower.Contains("_mra") -or $isOrm)) {
        continue
    }
    $packedPath = $record["images"][$packed]
    if (-not $packedPath) {
        continue
    }
    $sourceImages[$packed] = @{
        Path = $packedPath
        IsOrm = $isOrm
    }
    $materialRecords += ,@{
        Name = $entry.Key
        Vmat = $record["vmat"]
        Packed = $packed
        IsOrm = $isOrm
    }
}

$generated = [ordered]@{}
foreach ($entry in $sourceImages.GetEnumerator()) {
    $relative = $entry.Value.Path.Replace("/", "\")
    $source = Join-Path $addonRootPath $relative
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing packed PBR source: $source"
    }
    $directory = Split-Path -Parent $source
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($source)
    $metalnessPath = Join-Path $directory ($baseName + "_metal.png")
    $roughnessPath = Join-Path $directory ($baseName + "_rough.png")
    $aoPath = Join-Path $directory ($baseName + "_ao.png")
    [DfPbrSplit]::Split(
        $source,
        $metalnessPath,
        $roughnessPath,
        $aoPath,
        [bool]$entry.Value.IsOrm
    )
    $relativeDirectory = Split-Path -Parent $entry.Value.Path
    $generated[$entry.Key] = @{
        Metalness = ($relativeDirectory + "/" + $baseName + "_metal.png")
        Roughness = ($relativeDirectory + "/" + $baseName + "_rough.png")
        Occlusion = ($relativeDirectory + "/" + $baseName + "_ao.png")
    }
}

$compileFiles = New-Object System.Collections.Generic.List[string]
foreach ($material in $materialRecords) {
    $relative = $material.Vmat.Replace("/", "\")
    $source = Join-Path $addonRootPath $relative
    $contentFile = Join-Path $contentRootPath $relative
    $backup = Join-Path $backupPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
    if (-not (Test-Path -LiteralPath $backup)) {
        Copy-Item -LiteralPath $source -Destination $backup -Force
    }
    $text = Get-Content -LiteralPath $source -Raw
    $paths = $generated[$material.Packed]
    $text = [regex]::Replace(
        $text,
        '(?m)^(\s*TextureMetalness\s+).*$',
        ('$1"' + $paths.Metalness + '"')
    )
    $text = [regex]::Replace(
        $text,
        '(?m)^(\s*TextureRoughness\s+).*$',
        ('$1"' + $paths.Roughness + '"')
    )
    $text = [regex]::Replace(
        $text,
        '(?m)^(\s*TextureAmbientOcclusion\s+).*$',
        ('$1"' + $paths.Occlusion + '"')
    )
    Set-Content -LiteralPath $source -Value $text -NoNewline
    $compileFiles.Add($contentFile)
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $fileListPath) | Out-Null
Set-Content -LiteralPath $fileListPath -Value $compileFiles -Encoding utf8
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
@{
    packed_images = $sourceImages.Count
    materials = $materialRecords.Count
    generated = $generated
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8

Write-Output "PACKED_IMAGES=$($sourceImages.Count) MATERIALS=$($materialRecords.Count)"
