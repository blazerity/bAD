using System.Globalization;
using System.Management;
using System.Net;
using System.Text;

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

    /// <summary>Относительная «свежесть» + локальное время (как панель: <c>time.local-time</c> + muted).</summary>
    public static string FormatFreshnessHtml(string? rawUtcIso, string empty = "—")
    {
        if (string.IsNullOrWhiteSpace(rawUtcIso))
        {
            return WebUtility.HtmlEncode(empty);
        }

        if (!TryParseUtcInstant(rawUtcIso, out var instantUtc))
        {
            return WebUtility.HtmlEncode(rawUtcIso.Trim());
        }

        var rel = FormatRelativeRussian(DateTime.UtcNow, instantUtc);
        var local = LocalDisplay(instantUtc.ToLocalTime());
        var iso = rawUtcIso.Trim();
        var sb = new StringBuilder();
        sb.Append("<time class=\"local-time\" datetime=\"");
        sb.Append(WebUtility.HtmlEncode(iso));
        sb.Append("\" title=\"");
        sb.Append(WebUtility.HtmlEncode(local));
        sb.Append("\">");
        sb.Append(WebUtility.HtmlEncode(rel));
        sb.Append("</time><span class=\"muted freshness-abs\"> (");
        sb.Append(WebUtility.HtmlEncode(local));
        sb.Append(")</span>");
        return sb.ToString();
    }

    /// <summary>Текст для ASCII: относительное + локальное в скобках.</summary>
    public static string FormatFreshnessPlain(string? rawUtcIso, string empty = "-")
    {
        if (string.IsNullOrWhiteSpace(rawUtcIso))
        {
            return empty;
        }

        if (!TryParseUtcInstant(rawUtcIso, out var instantUtc))
        {
            return rawUtcIso.Trim();
        }

        var rel = FormatRelativeRussian(DateTime.UtcNow, instantUtc);
        var local = LocalDisplay(instantUtc.ToLocalTime());
        return $"{rel} ({local})";
    }

    public static string FormatRelativeRussian(DateTime nowUtc, DateTime instantUtc)
    {
        if (instantUtc.Kind != DateTimeKind.Utc)
        {
            instantUtc = instantUtc.Kind switch
            {
                DateTimeKind.Local => instantUtc.ToUniversalTime(),
                _ => DateTime.SpecifyKind(instantUtc, DateTimeKind.Utc)
            };
        }

        if (nowUtc.Kind != DateTimeKind.Utc)
        {
            nowUtc = nowUtc.ToUniversalTime();
        }

        var delta = nowUtc - instantUtc;
        if (delta < TimeSpan.Zero)
        {
            delta = TimeSpan.Zero;
        }

        if (delta < TimeSpan.FromSeconds(45))
        {
            return "только что";
        }

        if (delta < TimeSpan.FromMinutes(1))
        {
            return "меньше минуты назад";
        }

        if (delta < TimeSpan.FromHours(1))
        {
            var m = (int)delta.TotalMinutes;
            return m == 1 ? "1 мин. назад" : $"{m} мин. назад";
        }

        if (delta < TimeSpan.FromHours(24))
        {
            var h = (int)delta.TotalHours;
            return h == 1 ? "1 ч. назад" : $"{h} ч. назад";
        }

        if (delta < TimeSpan.FromHours(48))
        {
            return "вчера";
        }

        if (delta < TimeSpan.FromDays(7))
        {
            var d = (int)delta.TotalDays;
            return d == 1 ? "1 дн. назад" : $"{d} дн. назад";
        }

        if (delta < TimeSpan.FromDays(30))
        {
            var w = Math.Max(1, (int)(delta.TotalDays / 7));
            return w == 1 ? "1 нед. назад" : $"{w} нед. назад";
        }

        var mo = Math.Max(1, (int)(delta.TotalDays / 30));
        return mo == 1 ? "1 мес. назад" : $"{mo} мес. назад";
    }

    public static bool TryParseUtcInstant(string? raw, out DateTime instantUtc)
    {
        instantUtc = default;
        if (string.IsNullOrWhiteSpace(raw))
        {
            return false;
        }

        var s = raw.Trim();
        if (DateTime.TryParse(
                s,
                CultureInfo.InvariantCulture,
                DateTimeStyles.RoundtripKind,
                out var parsed))
        {
            instantUtc = parsed.Kind switch
            {
                DateTimeKind.Utc => parsed,
                DateTimeKind.Local => parsed.ToUniversalTime(),
                _ => DateTime.SpecifyKind(parsed, DateTimeKind.Utc)
            };
            return true;
        }

        if (OperatingSystem.IsWindows() && s.Length >= 14 && char.IsDigit(s[0]))
        {
            try
            {
                instantUtc = ManagementDateTimeConverter.ToDateTime(s).ToUniversalTime();
                return true;
            }
            catch
            {
                // не DMTF
            }
        }

        return false;
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
