using System.Management;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Runtime.Versioning;

namespace BadAgent;

/// <summary>hostname / ip / serial для POST /v1/enrollment-requests (без полного inventory).</summary>
public static class EnrollmentHints
{
    public static (string Hostname, string Ip, string Serial) ForRequest()
    {
        var hostname = Environment.MachineName;
        var ip = TryPrimaryIpv4() ?? "";
        var serial = TryHardwareSerial() ?? "";
        return (hostname, ip, serial);
    }

    private static string? TryPrimaryIpv4()
    {
        try
        {
            foreach (var nic in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (nic.OperationalStatus != OperationalStatus.Up
                    || nic.NetworkInterfaceType is NetworkInterfaceType.Loopback
                        or NetworkInterfaceType.Tunnel)
                {
                    continue;
                }

                foreach (var uni in nic.GetIPProperties().UnicastAddresses)
                {
                    if (uni.Address.AddressFamily != AddressFamily.InterNetwork)
                    {
                        continue;
                    }

                    if (IPAddress.IsLoopback(uni.Address))
                    {
                        continue;
                    }

                    return uni.Address.ToString();
                }
            }
        }
        catch
        {
            // best-effort
        }

        return null;
    }

    /// <summary>SMBIOS UUID. Заглушка, ошибка WMI и не-Windows дают null.</summary>
    public static string? ReadSmbiosUuid()
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        try
        {
            return HardwareMaps.CleanSmbiosUuid(
                WmiHelper.QueryFirst("SELECT UUID FROM Win32_ComputerSystemProduct", "UUID"));
        }
        catch
        {
            return null;
        }
    }

    private static string? TryHardwareSerial()
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        try
        {
            return QueryWmiSerial(
                       "SELECT SerialNumber FROM Win32_BIOS", "SerialNumber")
                   ?? QueryWmiSerial(
                       "SELECT IdentifyingNumber FROM Win32_ComputerSystemProduct", "IdentifyingNumber");
        }
        catch
        {
            return null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static string? QueryWmiSerial(string query, string property)
    {
        using var searcher = new ManagementObjectSearcher(query);
        foreach (ManagementObject obj in searcher.Get())
        {
            using (obj)
            {
                var raw = obj[property]?.ToString();
                var cleaned = HardwareMaps.CleanHardwareSerial(raw);
                if (!string.IsNullOrWhiteSpace(cleaned))
                {
                    return cleaned;
                }
            }
        }

        return null;
    }
}

public readonly record struct EnrollmentRequestResult(
    string Status,
    string? BadId,
    string? ApiKey,
    string? SigningKeyBase64,
    bool RouteMissing);
