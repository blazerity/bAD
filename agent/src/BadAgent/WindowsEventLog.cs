using System.Diagnostics;
using System.Runtime.Versioning;

namespace BadAgent;

/// <summary>
/// Пишет крупные сбои агента в журнал Application (Windows Event Log).
/// Soft-fail вне Windows / без прав на создание source.
/// </summary>
public static class WindowsEventLog
{
    public const string Source = "bAD Agent";
    public const string LogName = "Application";

    public static void WriteError(string message, Exception? ex = null)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        WriteWindows(EventLogEntryType.Error, message, ex);
    }

    public static void WriteWarning(string message, Exception? ex = null)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        WriteWindows(EventLogEntryType.Warning, message, ex);
    }

    public static void WriteInfo(string message)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        WriteWindows(EventLogEntryType.Information, message, null);
    }

    [SupportedOSPlatform("windows")]
    private static void WriteWindows(EventLogEntryType type, string message, Exception? ex)
    {
        try
        {
            EnsureSource();
            var text = ex is null ? message : $"{message}{Environment.NewLine}{ex}";
            if (text.Length > 30000)
            {
                text = text[..30000];
            }

            EventLog.WriteEntry(Source, text, type);
        }
        catch
        {
            // Нет прав на Event Log / source — не валить службу.
        }
    }

    [SupportedOSPlatform("windows")]
    private static void EnsureSource()
    {
        if (EventLog.SourceExists(Source))
        {
            return;
        }

        EventLog.CreateEventSource(Source, LogName);
    }
}
