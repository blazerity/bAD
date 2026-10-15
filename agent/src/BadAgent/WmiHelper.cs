using System.Management;

namespace BadAgent;

internal static class WmiHelper
{
    /// <summary>Короткая уступка CPU между WMI-запросами (low-impact collect).</summary>
    public static void YieldBriefly()
    {
        try
        {
            Thread.Sleep(0);
        }
        catch
        {
            // ignore
        }
    }

    public static string? QueryFirst(string wql, string property)
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        using var searcher = new ManagementObjectSearcher(wql);
        foreach (ManagementObject obj in searcher.Get())
        {
            using (obj)
            {
                var val = obj[property];
                return val?.ToString();
            }
        }

        return null;
    }

    public static string? QueryFirst(string scope, string wql, string property)
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        using var searcher = new ManagementObjectSearcher(scope, wql);
        foreach (ManagementObject obj in searcher.Get())
        {
            using (obj)
            {
                var val = obj[property];
                return val?.ToString();
            }
        }

        return null;
    }
}
