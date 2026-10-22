using System.Globalization;
using System.Management;

namespace BadAgent;

/// <summary>Локальное отображение времени в ASCII/HTML-отчётах (JSON на сервер — UTC ISO).</summary>
public static class TimeFormat
{
    public const string LocalDisplayPattern = "HH:mm:ss dd.MM.yyyy";

    public static string LocalDisplay(DateTime dateTime)
    {
        var local = dateTime.Kind switch
        {
            DateTimeKind.Utc => dateTime.ToLocalTime(),
            DateTimeKind.Unspecified => dateTime,
            _ => dateTime
        };
        return local.ToString(LocalDisplayPattern, CultureInfo.InvariantCulture);
    }

    /// <summary>UTC ISO, WMI DMTF или исходная строка, если распознать не удалось.</summary>
    public static string FormatForReport(string? raw, string empty = "-")
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return empty;
        }

        return TryParseForDisplay(raw, out var dt) ? LocalDisplay(dt) : raw.Trim();
    }

    private static bool TryParseForDisplay(string raw, out DateTime local)
    {
        var s = raw.Trim();
        if (DateTime.TryParse(
                s,
                CultureInfo.InvariantCulture,
                DateTimeStyles.RoundtripKind,
                out var parsed))
        {
            local = parsed.Kind switch
            {
                DateTimeKind.Utc => parsed.ToLocalTime(),
                DateTimeKind.Local => parsed,
                _ => DateTime.SpecifyKind(parsed, DateTimeKind.Utc).ToLocalTime()
            };
            return true;
        }

        if (OperatingSystem.IsWindows() && s.Length >= 14 && char.IsDigit(s[0]))
        {
            try
            {
                local = ManagementDateTimeConverter.ToDateTime(s);
                return true;
            }
            catch
            {
                // не DMTF
            }
        }

        local = default;
        return false;
    }
}
