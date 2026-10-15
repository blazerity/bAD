using System.Management;

namespace BadAgent;

internal static class WmiHelper
{
    /// <summary>Короткая уступка CPU между WMI-запросами (low-impact collect).</summary>
    public static void YieldBriefly() => Thread.Sleep(0);

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
}
