using System.Globalization;

namespace BadAgent;

/// <summary>Общее форматирование для локальных ASCII/HTML-отчётов inventory.</summary>
public static class ReportFormat
{
    private static readonly string[] ByteUnits = ["B", "KiB", "MiB", "GiB", "TiB"];

    public static string FormatOs(OsInfo? os, string empty = "-")
    {
        if (os is null) return empty;
        var parts = new[] { os.Caption, os.Version, os.Arch }
            .Where(s => !string.IsNullOrWhiteSpace(s));
        var text = string.Join(" / ", parts);
        return string.IsNullOrEmpty(text) ? empty : text;
    }

    public static string FormatCores(CpuInfo? cpu, string empty = "-")
    {
        if (cpu is null) return empty;
        return $"{cpu.Cores ?? 0} cores / {cpu.Logical ?? 0} logical";
    }

    public static string FormatBytes(long? bytes, string empty = "-")
    {
        if (bytes is null or < 0) return empty;
        double v = bytes.Value;
        var i = 0;
        while (v >= 1024 && i < ByteUnits.Length - 1)
        {
            v /= 1024;
            i++;
        }

        return i == 0
            ? $"{bytes.Value} {ByteUnits[i]}"
            : string.Format(CultureInfo.InvariantCulture, "{0:0.##} {1}", v, ByteUnits[i]);
    }
}
