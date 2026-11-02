using System.ComponentModel;
using System.Runtime.InteropServices;

namespace BadAgent;

/// <summary>
/// Старт процесса без привязки к консоли вызывающего (DETACHED_PROCESS + CREATE_NO_WINDOW).
/// </summary>
internal static class DetachedProcessStart
{
    private const uint CreateNoWindow = 0x08000000;
    private const uint DetachedProcess = 0x00000008;
    private const int StartfUseShowWindow = 0x00000001;
    private const ushort SwHide = 0;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct StartupInfo
    {
        public int Cb;
        public string? LpReserved;
        public string? LpDesktop;
        public string? LpTitle;
        public int DwX;
        public int DwY;
        public int DwXSize;
        public int DwYSize;
        public int DwXCountChars;
        public int DwYCountChars;
        public int DwFillAttribute;
        public int DwFlags;
        public ushort WShowWindow;
        public ushort CbReserved2;
        public IntPtr LpReserved2;
        public IntPtr HStdInput;
        public IntPtr HStdOutput;
        public IntPtr HStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInformation
    {
        public IntPtr HProcess;
        public IntPtr HThread;
        public int DwProcessId;
        public int DwThreadId;
    }

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool CreateProcessW(
        string? lpApplicationName,
        string lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string? lpCurrentDirectory,
        ref StartupInfo lpStartupInfo,
        out ProcessInformation lpProcessInformation);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr hObject);

    public static bool TryStart(string applicationPath, string arguments, ILogger? logger = null)
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        var commandLine = string.IsNullOrWhiteSpace(arguments)
            ? $"\"{applicationPath}\""
            : $"\"{applicationPath}\" {arguments}";

        var si = new StartupInfo
        {
            Cb = Marshal.SizeOf<StartupInfo>(),
            DwFlags = StartfUseShowWindow,
            WShowWindow = SwHide
        };

        if (!CreateProcessW(
                applicationPath,
                commandLine,
                IntPtr.Zero,
                IntPtr.Zero,
                false,
                CreateNoWindow | DetachedProcess,
                IntPtr.Zero,
                null,
                ref si,
                out var pi))
        {
            var err = Marshal.GetLastWin32Error();
            logger?.LogError(
                "CreateProcess (detached) failed for {App}: {Message}",
                applicationPath,
                new Win32Exception(err).Message);
            return false;
        }

        CloseHandle(pi.HThread);
        CloseHandle(pi.HProcess);
        return true;
    }
}
