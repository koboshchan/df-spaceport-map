param(
    [Parameter(Mandatory = $true)]
    [int]$VirtualKey,
    [string]$WindowTitle = "Counter-Strike 2"
)

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class KeyboardInput
{
    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT
    {
        public uint type;
        public InputUnion U;
    }

    [StructLayout(LayoutKind.Explicit)]
    public struct InputUnion
    {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
        [FieldOffset(0)] public HARDWAREINPUT hi;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT
    {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct HARDWAREINPUT
    {
        public uint uMsg;
        public ushort wParamL;
        public ushort wParamH;
    }

    [DllImport("user32.dll")]
    public static extern uint MapVirtualKey(uint code, uint mapType);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint SendInput(
        uint count,
        INPUT[] inputs,
        int size
    );

    public static void Press(ushort virtualKey)
    {
        const uint KEYEVENTF_SCANCODE = 0x0008;
        const uint KEYEVENTF_KEYUP = 0x0002;
        ushort scanCode = (ushort)MapVirtualKey(virtualKey, 0);
        var inputs = new INPUT[2];
        inputs[0].type = 1;
        inputs[0].U.ki.wScan = scanCode;
        inputs[0].U.ki.dwFlags = KEYEVENTF_SCANCODE;
        inputs[1].type = 1;
        inputs[1].U.ki.wScan = scanCode;
        inputs[1].U.ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP;
        if (SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT))) != 2)
        {
            throw new InvalidOperationException(
                "SendInput failed: " + Marshal.GetLastWin32Error()
            );
        }
    }
}
"@

$shell = New-Object -ComObject WScript.Shell
if (-not $shell.AppActivate($WindowTitle)) {
    throw "Target window not found: $WindowTitle"
}
Start-Sleep -Milliseconds 250
[KeyboardInput]::Press([System.UInt16]$VirtualKey)
Write-Output "SENT=$VirtualKey"
