param([string]$ProcessName = "cs2")

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class WindowEnumerator
{
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@

$rows = [System.Collections.Generic.List[object]]::new()
[WindowEnumerator]::EnumWindows({
    param($hWnd, $lParam)
    if (-not [WindowEnumerator]::IsWindowVisible($hWnd)) {
        return $true
    }
    [uint32]$processId = 0
    [void][WindowEnumerator]::GetWindowThreadProcessId($hWnd, [ref]$processId)
    try {
        $process = Get-Process -Id $processId -ErrorAction Stop
    }
    catch {
        return $true
    }
    if ($process.ProcessName -eq $ProcessName) {
        $text = [System.Text.StringBuilder]::new(512)
        [void][WindowEnumerator]::GetWindowText($hWnd, $text, $text.Capacity)
        $rows.Add([pscustomobject]@{
            ProcessId = $processId
            Handle = $hWnd.ToInt64()
            Title = $text.ToString()
        })
    }
    return $true
}, [IntPtr]::Zero) | Out-Null

$rows | Format-Table -AutoSize
