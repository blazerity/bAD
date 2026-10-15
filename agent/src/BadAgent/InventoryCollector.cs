using System.Management;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;

namespace BadAgent;

public sealed class InventoryCollector : IInventoryCollector
{
    public InventorySnapshot Collect(string deviceId, string agentVersion)
    {
        var snap = new InventorySnapshot
        {
            SchemaVersion = 1,
            DeviceId = deviceId,
            CollectedAt = DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"),
            AgentVersion = agentVersion
        };

        snap.Host = CollectHost(snap.CollectorErrors);
        snap.Hardware = CollectHardware(snap.CollectorErrors);
        snap.Network = CollectNetwork(snap.CollectorErrors);
        snap.Users = CollectUsers(snap.CollectorErrors);
        return snap;
    }

    private static HostInfo CollectHost(List<CollectorError> errors)
    {
        var host = new HostInfo
        {
            Hostname = Environment.MachineName,
            Domain = Environment.UserDomainName
        };

        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_OperatingSystem");
                foreach (ManagementObject obj in searcher.Get())
                {
                    using (obj)
                    {
                        host.Os = new OsInfo
                        {
                            Caption = obj["Caption"]?.ToString(),
                            Version = obj["Version"]?.ToString(),
                            Build = obj["BuildNumber"]?.ToString(),
                            Arch = obj["OSArchitecture"]?.ToString(),
                            InstallDate = obj["InstallDate"]?.ToString()
                        };
                        var domain = obj["CSName"]?.ToString();
                        if (!string.IsNullOrWhiteSpace(domain))
                        {
                            host.Hostname = domain;
                        }
                    }
                }

                var dnsDomain = WmiHelper.QueryFirst(
                    "SELECT Domain FROM Win32_ComputerSystem", "Domain");
                if (!string.IsNullOrWhiteSpace(dnsDomain))
                {
                    host.Domain = dnsDomain;
                }
            }
            else
            {
                host.Os = new OsInfo
                {
                    Caption = RuntimeInformation.OSDescription,
                    Version = Environment.OSVersion.VersionString,
                    Arch = RuntimeInformation.OSArchitecture.ToString()
                };
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "host", Error = ex.Message });
            host.Os = null;
        }

        return host;
    }

    private static HardwareInfo CollectHardware(List<CollectorError> errors)
    {
        var hw = new HardwareInfo();

        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var cpuSearcher = new ManagementObjectSearcher("SELECT * FROM Win32_Processor");
                foreach (ManagementObject obj in cpuSearcher.Get())
                {
                    using (obj)
                    {
                        hw.Cpu = new CpuInfo
                        {
                            Name = obj["Name"]?.ToString()?.Trim(),
                            Cores = ToInt(obj["NumberOfCores"]),
                            Logical = ToInt(obj["NumberOfLogicalProcessors"])
                        };
                        break;
                    }
                }

                using var cs = new ManagementObjectSearcher(
                    "SELECT TotalPhysicalMemory FROM Win32_ComputerSystem");
                foreach (ManagementObject obj in cs.Get())
                {
                    using (obj)
                    {
                        hw.RamBytes = ToLong(obj["TotalPhysicalMemory"]);
                    }
                }

                hw.Disks = new List<DiskInfo>();
                using var disks = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive");
                foreach (ManagementObject obj in disks.Get())
                {
                    using (obj)
                    {
                        hw.Disks.Add(new DiskInfo
                        {
                            Model = obj["Model"]?.ToString(),
                            SizeBytes = ToLong(obj["Size"]),
                            MediaType = obj["MediaType"]?.ToString()
                        });
                    }
                }

                hw.Volumes = new List<VolumeInfo>();
                using var vols = new ManagementObjectSearcher(
                    "SELECT * FROM Win32_LogicalDisk WHERE DriveType=3");
                foreach (ManagementObject obj in vols.Get())
                {
                    using (obj)
                    {
                        hw.Volumes.Add(new VolumeInfo
                        {
                            Letter = obj["DeviceID"]?.ToString(),
                            SizeBytes = ToLong(obj["Size"]),
                            FreeBytes = ToLong(obj["FreeSpace"])
                        });
                    }
                }
            }
            else
            {
                hw.Cpu = new CpuInfo
                {
                    Name = "unknown",
                    Cores = Environment.ProcessorCount,
                    Logical = Environment.ProcessorCount
                };
                hw.Disks = new List<DiskInfo>();
                hw.Volumes = DriveInfo.GetDrives()
                    .Where(d => d.IsReady)
                    .Select(d => new VolumeInfo
                    {
                        Letter = d.Name,
                        SizeBytes = d.TotalSize,
                        FreeBytes = d.AvailableFreeSpace
                    })
                    .ToList();
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "hardware", Error = ex.Message });
        }

        return hw;
    }

    private static NetworkInfo CollectNetwork(List<CollectorError> errors)
    {
        var net = new NetworkInfo { Nics = new List<NicInfo>() };
        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var nics = new ManagementObjectSearcher(
                    "SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled=True");
                foreach (ManagementObject obj in nics.Get())
                {
                    using (obj)
                    {
                        var ipv4 = new List<string>();
                        var ipv6 = new List<string>();
                        if (obj["IPAddress"] is string[] addrs)
                        {
                            foreach (var a in addrs)
                            {
                                if (a.Contains(':')) ipv6.Add(a);
                                else ipv4.Add(a);
                            }
                        }

                        net.Nics.Add(new NicInfo
                        {
                            Name = obj["Description"]?.ToString(),
                            Mac = obj["MACAddress"]?.ToString(),
                            Ipv4 = ipv4,
                            Ipv6 = ipv6,
                            Dhcp = obj["DHCPEnabled"] as bool?
                        });
                    }
                }
            }
            else
            {
                foreach (var ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.OperationalStatus != OperationalStatus.Up) continue;
                    if (ni.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;
                    var props = ni.GetIPProperties();
                    var ipv4 = props.UnicastAddresses
                        .Where(a => a.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                        .Select(a => a.Address.ToString())
                        .ToList();
                    var ipv6 = props.UnicastAddresses
                        .Where(a => a.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetworkV6)
                        .Select(a => a.Address.ToString())
                        .ToList();
                    bool? dhcp = null;
                    try
                    {
                        if (OperatingSystem.IsWindows())
                        {
                            dhcp = props.GetIPv4Properties()?.IsDhcpEnabled;
                        }
                    }
                    catch
                    {
                        dhcp = null;
                    }

                    net.Nics.Add(new NicInfo
                    {
                        Name = ni.Name,
                        Mac = FormatMac(ni.GetPhysicalAddress()),
                        Ipv4 = ipv4,
                        Ipv6 = ipv6,
                        Dhcp = dhcp
                    });
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "network", Error = ex.Message });
            net.Nics = null;
        }

        return net;
    }

    private static UsersInfo CollectUsers(List<CollectorError> errors)
    {
        var users = new UsersInfo();
        try
        {
            if (OperatingSystem.IsWindows())
            {
                var user = WmiHelper.QueryFirst(
                    "SELECT UserName FROM Win32_ComputerSystem", "UserName");
                if (!string.IsNullOrWhiteSpace(user))
                {
                    users.LastInteractive = user;
                    users.LoggedOn = new List<string> { user };
                }
                else
                {
                    users.LoggedOn = null;
                    users.LastInteractive = null;
                }
            }
            else
            {
                var name = Environment.UserName;
                users.LoggedOn = string.IsNullOrWhiteSpace(name) ? null : new List<string> { name };
                users.LastInteractive = name;
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "users", Error = ex.Message });
            users.LoggedOn = null;
            users.LastInteractive = null;
        }

        return users;
    }

    private static string? FormatMac(PhysicalAddress address)
    {
        var bytes = address.GetAddressBytes();
        if (bytes.Length == 0) return null;
        return string.Join(":", bytes.Select(b => b.ToString("X2")));
    }

    private static int? ToInt(object? value)
    {
        if (value is null) return null;
        return Convert.ToInt32(value);
    }

    private static long? ToLong(object? value)
    {
        if (value is null) return null;
        return Convert.ToInt64(value);
    }
}
