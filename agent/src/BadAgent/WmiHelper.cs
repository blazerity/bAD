using System.Management;

namespace BadAgent;

internal static class WmiHelper
{
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

    public static IEnumerable<ManagementObject> Query(string wql)
    {
        if (!OperatingSystem.IsWindows())
        {
            yield break;
        }

        using var searcher = new ManagementObjectSearcher(wql);
        foreach (ManagementObject obj in searcher.Get())
        {
            yield return obj;
        }
    }
}
