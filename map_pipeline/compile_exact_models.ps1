[CmdletBinding()]
param(
    [string]$Manifest = "C:\Users\Administrator\Documents\ChatGPT\DF CS2\map_build\analysis\exact_cells_v2_all.json",
    [string]$ContentRoot = "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\df_spaceport",
    [string]$Compiler = "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\resourcecompiler.exe",
    [string]$Game = "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo",
    [string]$LogRoot = "C:\Users\Administrator\Documents\ChatGPT\DF CS2\map_build\analysis\model_compile_logs",
    [int]$ChunkSize = 128,
    [int]$StartChunk = 1
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$data = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json -AsHashtable
$models = @(
    $data["cells"] | ForEach-Object {
        Join-Path $ContentRoot (($_["vmdl"]) -replace "/", "\")
    }
)
$chunkCount = [math]::Ceiling($models.Count / $ChunkSize)
$failedChunks = @()

for ($chunkIndex = $StartChunk; $chunkIndex -le $chunkCount; $chunkIndex++) {
    $offset = ($chunkIndex - 1) * $ChunkSize
    $chunk = @($models[$offset..([math]::Min($offset + $ChunkSize - 1, $models.Count - 1))])
    $listPath = Join-Path $LogRoot ("chunk_{0:D3}.txt" -f $chunkIndex)
    $logPath = Join-Path $LogRoot ("chunk_{0:D3}.log" -f $chunkIndex)
    $chunk | Set-Content -LiteralPath $listPath -Encoding utf8

    Write-Host ("CHUNK {0}/{1} MODELS={2}" -f $chunkIndex, $chunkCount, $chunk.Count)
    & $Compiler -nop4 -game $Game -filelist $listPath *> $logPath
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $failedChunks += [pscustomobject]@{
            Chunk = $chunkIndex
            ExitCode = $exitCode
            Log = $logPath
        }
    }
    Write-Host ("CHUNK_EXIT={0}" -f $exitCode)
}

$reportPath = Join-Path $LogRoot "summary.json"
@{
    model_count = $models.Count
    chunk_size = $ChunkSize
    chunk_count = $chunkCount
    start_chunk = $StartChunk
    failed_chunks = $failedChunks
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $reportPath -Encoding utf8

Write-Host ("SUMMARY={0}" -f $reportPath)
if ($failedChunks.Count -gt 0) {
    exit 1
}
