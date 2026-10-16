using System.DirectoryServices;
using System.Management;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Microsoft.Win32;

namespace BadAgent;

public sealed class InventoryCollector : IInventoryCollector
{
    /// <summary>Макс. число установленных программ (Uninstall registry бывает огромным).</summary>
    public const int MaxSoftwarePrograms = 500;

    /// <summary>Макс. GPU из Win32_VideoController.</summary>
    public const int MaxGpus = 16;

    /// <summary>Макс. физических модулей RAM из Win32_PhysicalMemory.</summary>
    public const int MaxRamModules = 32;

    /// <summary>Макс. мониторов из WmiMonitorID.</summary>
    public const int MaxMonitors = 8;

    /// <summary>Макс. метаданных minidump-файлов в inventory (тела не читаем).</summary>
    public const int MaxMinidumpFiles = 20;

    /// <summary>Макс. продуктов AV из SecurityCenter2.</summary>
    public const int MaxAntivirusProducts = 8;

    public InventorySnapshot Collect(string deviceId, string agentVersion, CollectorOptions? options = null)
    {
        options ??= new CollectorOptions();
        var snap = new InventorySnapshot
        {
            SchemaVersion = 2,
            DeviceId = deviceId,
            CollectedAt = DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"),
            AgentVersion = agentVersion
        };

        var prevPriority = Thread.CurrentThread.Priority;
        try
        {
            // Низкий приоритет потока сбора — не подвешивать интерактив.
            Thread.CurrentThread.Priority = ThreadPriority.BelowNormal;

            snap.Host = CollectHost(snap.CollectorErrors);
            WmiHelper.YieldBriefly();
            snap.Network = CollectNetwork(snap.CollectorErrors);
            WmiHelper.YieldBriefly();

            if (options.CollectHardware)
            {
                snap.Hardware = CollectHardware(snap.CollectorErrors);
            }
            // Выключено: оставить null, без спама collector_errors.

            WmiHelper.YieldBriefly();
            if (options.CollectUsers)
            {
                snap.Users = CollectUsers(snap.CollectorErrors);
            }

            WmiHelper.YieldBriefly();
            if (options.CollectSoftware)
            {
                snap.Software = CollectSoftware(snap.CollectorErrors);
            }

            WmiHelper.YieldBriefly();
            snap.Security = CollectSecurity(snap.CollectorErrors);

            WmiHelper.YieldBriefly();
            snap.Minidumps = CollectMinidumps(snap.CollectorErrors);
        }
        finally
        {
            try
            {
                Thread.CurrentThread.Priority = prevPriority;
            }
            catch
            {
                // ignore
            }
        }

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
                using var searcher = new ManagementObjectSearcher(
                    "SELECT Caption, Version, BuildNumber, OSArchitecture, InstallDate, CSName, LastBootUpTime FROM Win32_OperatingSystem");
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
                        host.LastBootAt = TryWmiDateToUtcIso(obj["LastBootUpTime"]?.ToString());
                        var domain = obj["CSName"]?.ToString();
                        if (!string.IsNullOrWhiteSpace(domain))
                        {
                            host.Hostname = domain;
                        }
                    }
                }

                try
                {
                    var tz = TimeZoneInfo.Local;
                    host.Timezone = string.IsNullOrWhiteSpace(tz.Id) ? tz.DisplayName : tz.Id;
                }
                catch
                {
                    // soft-fail timezone
                }

                host.PendingReboot = TryDetectPendingReboot(errors);

                string? dnsDomain = null;
                string? partOfDomain = null;
                using (var cs = new ManagementObjectSearcher(
                           "SELECT Domain, PartOfDomain FROM Win32_ComputerSystem"))
                {
                    foreach (ManagementObject obj in cs.Get())
                    {
                        using (obj)
                        {
                            dnsDomain = obj["Domain"]?.ToString();
                            partOfDomain = obj["PartOfDomain"]?.ToString();
                            break;
                        }
                    }
                }

                if (!string.IsNullOrWhiteSpace(dnsDomain))
                {
                    host.Domain = dnsDomain;
                }

                CollectAdComputerOu(host, errors, partOfDomain);
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

            if (host.Timezone is null)
            {
                try
                {
                    var tz = TimeZoneInfo.Local;
                    host.Timezone = string.IsNullOrWhiteSpace(tz.Id) ? tz.DisplayName : tz.Id;
                }
                catch
                {
                    // ignore
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "host", Error = ex.Message });
            host.Os = null;
        }

        return host;
    }

    /// <summary>AD distinguishedName / OU path; soft-fail для workgroup.</summary>
    [SupportedOSPlatform("windows")]
    private static void CollectAdComputerOu(HostInfo host, List<CollectorError> errors, string? partOfDomain)
    {
        try
        {
            if (!string.Equals(partOfDomain, "True", StringComparison.OrdinalIgnoreCase)
                && partOfDomain != "1")
            {
                // Workgroup — не ошибка.
                return;
            }

            WmiHelper.YieldBriefly();
            var sam = Environment.MachineName + "$";
            using var root = new DirectoryEntry("LDAP://RootDSE");
            var defaultNc = root.Properties["defaultNamingContext"]?.Value as string;
            if (string.IsNullOrWhiteSpace(defaultNc))
            {
                return;
            }

            using var searchRoot = new DirectoryEntry("LDAP://" + defaultNc);
            using var searcher = new DirectorySearcher(searchRoot)
            {
                Filter = $"(&(objectCategory=computer)(sAMAccountName={EscapeLdapFilter(sam)}))",
                SearchScope = SearchScope.Subtree,
                PageSize = 1
            };
            searcher.PropertiesToLoad.Add("distinguishedName");
            var result = searcher.FindOne();
            var dn = result?.Properties["distinguishedName"]?[0]?.ToString();
            if (string.IsNullOrWhiteSpace(dn))
            {
                return;
            }

            host.AdDistinguishedName = dn;
            host.AdOu = OuPathFromDn(dn);
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "host.ad_ou",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    private static string EscapeLdapFilter(string value)
    {
        return value
            .Replace("\\", "\\5c")
            .Replace("*", "\\2a")
            .Replace("(", "\\28")
            .Replace(")", "\\29")
            .Replace("\0", "\\00");
    }

    /// <summary>CN=PC,OU=Laptops,DC=x → OU=Laptops,DC=x</summary>
    private static string? OuPathFromDn(string dn)
    {
        var idx = dn.IndexOf(',');
        if (idx < 0 || idx + 1 >= dn.Length)
        {
            return null;
        }

        return dn[(idx + 1)..];
    }

    private static HardwareInfo CollectHardware(List<CollectorError> errors)
    {
        var hw = new HardwareInfo();

        if (!OperatingSystem.IsWindows())
        {
            try
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
            catch (Exception ex)
            {
                errors.Add(new CollectorError { Section = "hardware", Error = Truncate(ex.Message, 200) });
            }

            return hw;
        }

        CollectHardwareCpu(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareRamTotal(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareSystemIdentity(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareChassis(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareBattery(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareMonitors(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareDisks(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareVolumes(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareGpus(hw, errors);
        WmiHelper.YieldBriefly();
        CollectHardwareRamModules(hw, errors);
        return hw;
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareCpu(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            using var cpuSearcher = new ManagementObjectSearcher(
                "SELECT Name, NumberOfCores, NumberOfLogicalProcessors FROM Win32_Processor");
            foreach (ManagementObject obj in cpuSearcher.Get())
            {
                using (obj)
                {
                    hw.Cpu = new CpuInfo
                    {
                        Name = HardwareMaps.CleanWmiString(obj["Name"]?.ToString()),
                        Cores = ToInt(obj["NumberOfCores"]),
                        Logical = ToInt(obj["NumberOfLogicalProcessors"])
                    };
                    break;
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "hardware.cpu", Error = Truncate(ex.Message, 200) });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareRamTotal(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            using var cs = new ManagementObjectSearcher(
                "SELECT TotalPhysicalMemory FROM Win32_ComputerSystem");
            foreach (ManagementObject obj in cs.Get())
            {
                using (obj)
                {
                    hw.RamBytes = ToLong(obj["TotalPhysicalMemory"]);
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "hardware.ram", Error = Truncate(ex.Message, 200) });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareSystemIdentity(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            string? biosSerial = null;
            string? productSerial = null;
            string? productName = null;
            string? productVendor = null;
            string? csModel = null;
            string? csManufacturer = null;
            string? boardSerial = null;

            using (var bios = new ManagementObjectSearcher(
                       "SELECT SerialNumber, SMBIOSBIOSVersion, Version, Manufacturer, ReleaseDate FROM Win32_BIOS"))
            {
                foreach (ManagementObject obj in bios.Get())
                {
                    using (obj)
                    {
                        biosSerial = obj["SerialNumber"]?.ToString();
                        hw.BiosVersion = HardwareMaps.PreferFirst(
                            HardwareMaps.CleanWmiString(obj["SMBIOSBIOSVersion"]?.ToString()),
                            HardwareMaps.CleanWmiString(obj["Version"]?.ToString()));
                        hw.BiosManufacturer = HardwareMaps.CleanWmiString(obj["Manufacturer"]?.ToString());
                        hw.BiosReleaseDate = HardwareMaps.CleanWmiString(obj["ReleaseDate"]?.ToString());
                        break;
                    }
                }
            }

            using (var product = new ManagementObjectSearcher(
                       "SELECT Name, IdentifyingNumber, Vendor, UUID FROM Win32_ComputerSystemProduct"))
            {
                foreach (ManagementObject obj in product.Get())
                {
                    using (obj)
                    {
                        productName = obj["Name"]?.ToString();
                        productSerial = obj["IdentifyingNumber"]?.ToString();
                        productVendor = obj["Vendor"]?.ToString();
                        // Отдельное поле для duplicates; не device_id / не PK.
                        hw.SmbiosUuid = HardwareMaps.CleanSmbiosUuid(obj["UUID"]?.ToString());
                        break;
                    }
                }
            }

            using (var cs = new ManagementObjectSearcher(
                       "SELECT Model, Manufacturer FROM Win32_ComputerSystem"))
            {
                foreach (ManagementObject obj in cs.Get())
                {
                    using (obj)
                    {
                        csModel = obj["Model"]?.ToString();
                        csManufacturer = obj["Manufacturer"]?.ToString();
                        break;
                    }
                }
            }

            using (var board = new ManagementObjectSearcher("SELECT SerialNumber FROM Win32_BaseBoard"))
            {
                foreach (ManagementObject obj in board.Get())
                {
                    using (obj)
                    {
                        boardSerial = obj["SerialNumber"]?.ToString();
                        break;
                    }
                }
            }

            // Отдельные сигналы «та же железка» (не PK). Пустые/placeholder не шлём.
            hw.BiosSerial = HardwareMaps.CleanHardwareSerial(biosSerial);
            hw.IdentifyingNumber = HardwareMaps.CleanHardwareSerial(productSerial);
            hw.BaseboardSerial = HardwareMaps.CleanHardwareSerial(boardSerial);
            // Совместимость: прежнее одно поле — PreferFirst из очищенных.
            hw.SerialNumber = HardwareMaps.PreferFirst(
                hw.BiosSerial, hw.IdentifyingNumber, hw.BaseboardSerial);
            hw.Model = HardwareMaps.PreferFirst(csModel, productName);
            hw.Manufacturer = HardwareMaps.PreferFirst(csManufacturer, productVendor);
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.system",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareChassis(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            var raw = new List<int>();
            using var searcher = new ManagementObjectSearcher(
                "SELECT ChassisTypes FROM Win32_SystemEnclosure");
            foreach (ManagementObject obj in searcher.Get())
            {
                using (obj)
                {
                    if (obj["ChassisTypes"] is ushort[] codes)
                    {
                        foreach (var c in codes)
                        {
                            raw.Add(c);
                        }
                    }
                    else if (obj["ChassisTypes"] is Array arr)
                    {
                        foreach (var item in arr)
                        {
                            if (item is null)
                            {
                                continue;
                            }

                            try
                            {
                                raw.Add(Convert.ToInt32(item));
                            }
                            catch
                            {
                                // skip
                            }
                        }
                    }

                    break;
                }
            }

            hw.ChassisTypesRaw = raw.Count > 0 ? raw : null;
            hw.ChassisType = HardwareMaps.NormalizeChassisType(
                hw.ChassisTypesRaw, hw.Manufacturer, hw.Model);
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.chassis",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareBattery(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            // Win32_Battery; на десктопах без батареи коллекция пустая — не ошибка.
            using var searcher = new ManagementObjectSearcher(
                "SELECT Name, EstimatedChargeRemaining, BatteryStatus, EstimatedRunTime FROM Win32_Battery");
            foreach (ManagementObject obj in searcher.Get())
            {
                using (obj)
                {
                    var charge = ToInt(obj["EstimatedChargeRemaining"]);
                    var statusCode = ToInt(obj["BatteryStatus"]);
                    var runtime = ToInt(obj["EstimatedRunTime"]);
                    // 71582788 — «unknown» sentinel в WMI EstimatedRunTime.
                    if (runtime is >= 71582788 or <= 0)
                    {
                        runtime = null;
                    }

                    hw.Battery = new BatteryInfo
                    {
                        Name = HardwareMaps.CleanWmiString(obj["Name"]?.ToString()),
                        ChargePercent = charge is >= 0 and <= 100 ? charge : null,
                        StatusCode = statusCode,
                        Status = MapBatteryStatus(statusCode),
                        EstimatedRuntimeMinutes = runtime
                    };
                    break;
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.battery",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    private static string? MapBatteryStatus(int? code) => code switch
    {
        1 => "other",
        2 => "unknown",
        3 => "full",
        4 => "low",
        5 => "critical",
        6 => "charging",
        7 => "charging",
        8 => "charging",
        9 => "charging",
        10 => "undefined",
        11 => "partial",
        _ => code is null ? null : "unknown"
    };

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareMonitors(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            var monitors = new List<MonitorInfo>();
            // EDID через root\wmi; soft-fail если класс недоступен.
            using (var searcher = new ManagementObjectSearcher(
                       @"root\wmi",
                       "SELECT InstanceName, ManufacturerName, ProductCodeID, SerialNumberID, " +
                       "UserFriendlyName, UserFriendlyNameLength, WeekOfManufacture, YearOfManufacture " +
                       "FROM WmiMonitorID WHERE Active=TRUE"))
            {
                foreach (ManagementObject obj in searcher.Get())
                {
                    using (obj)
                    {
                        if (monitors.Count >= MaxMonitors)
                        {
                            break;
                        }

                        var name = DecodeWmiMonitorString(obj["UserFriendlyName"] as ushort[], obj["UserFriendlyNameLength"]);
                        var mfg = DecodeWmiMonitorString(obj["ManufacturerName"] as ushort[], null);
                        var serial = DecodeWmiMonitorString(obj["SerialNumberID"] as ushort[], null);
                        if (name is null && mfg is null && serial is null)
                        {
                            continue;
                        }

                        monitors.Add(new MonitorInfo
                        {
                            Name = name,
                            Manufacturer = mfg,
                            SerialNumber = serial,
                            Year = ToInt(obj["YearOfManufacture"]),
                            Week = ToInt(obj["WeekOfManufacture"])
                        });
                    }
                }
            }

            WmiHelper.YieldBriefly();
            // Best-effort разрешение с активного видеоадаптера (одно на все, если один монитор).
            try
            {
                using var vc = new ManagementObjectSearcher(
                    "SELECT CurrentHorizontalResolution, CurrentVerticalResolution FROM Win32_VideoController " +
                    "WHERE CurrentHorizontalResolution IS NOT NULL");
                foreach (ManagementObject obj in vc.Get())
                {
                    using (obj)
                    {
                        var w = ToInt(obj["CurrentHorizontalResolution"]);
                        var h = ToInt(obj["CurrentVerticalResolution"]);
                        if (w is null or 0 || h is null or 0)
                        {
                            continue;
                        }

                        if (monitors.Count == 0)
                        {
                            monitors.Add(new MonitorInfo { Width = w, Height = h, Name = "display" });
                        }
                        else if (monitors.Count == 1)
                        {
                            monitors[0].Width = w;
                            monitors[0].Height = h;
                        }

                        break;
                    }
                }
            }
            catch
            {
                // resolution optional
            }

            hw.Monitors = monitors.Count > 0 ? monitors : null;
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.monitors",
                Error = Truncate(ex.Message, 200)
            });
            hw.Monitors = null;
        }
    }

    /// <summary>WmiMonitorID хранит строки как UInt16[] (UTF-16 code units).</summary>
    private static string? DecodeWmiMonitorString(ushort[]? data, object? lengthObj)
    {
        if (data is null || data.Length == 0)
        {
            return null;
        }

        var len = data.Length;
        if (lengthObj is not null)
        {
            try
            {
                var reported = Convert.ToInt32(lengthObj);
                if (reported > 0 && reported <= data.Length)
                {
                    len = reported;
                }
            }
            catch
            {
                // use full array
            }
        }

        var chars = new char[len];
        var n = 0;
        for (var i = 0; i < len; i++)
        {
            var c = (char)data[i];
            if (c == '\0')
            {
                break;
            }

            chars[n++] = c;
        }

        if (n == 0)
        {
            return null;
        }

        var s = new string(chars, 0, n).Trim();
        return string.IsNullOrWhiteSpace(s) ? null : s;
    }

    private static MinidumpInfo? CollectMinidumps(List<CollectorError> errors)
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        try
        {
            var info = new MinidumpInfo { Files = new List<MinidumpFileInfo>() };
            var windowsDir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            if (string.IsNullOrWhiteSpace(windowsDir))
            {
                windowsDir = Environment.GetEnvironmentVariable("SystemRoot") ?? @"C:\Windows";
            }

            var memoryDmp = Path.Combine(windowsDir, "Memory.dmp");
            if (File.Exists(memoryDmp))
            {
                info.MemoryDmpPresent = true;
                info.MemoryDmpPath = memoryDmp;
                try
                {
                    info.MemoryDmpModifiedAt = File.GetLastWriteTimeUtc(memoryDmp)
                        .ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
                }
                catch
                {
                    // ignore
                }
            }

            var minidumpDir = Path.Combine(windowsDir, "Minidump");
            if (Directory.Exists(minidumpDir))
            {
                // Top-N по mtime без полной материализации всех FileInfo.
                var top = new List<(DateTime Mtime, string Path)>(MaxMinidumpFiles);
                var count = 0;
                foreach (var path in Directory.EnumerateFiles(minidumpDir, "*.dmp"))
                {
                    count++;
                    DateTime mtime;
                    try
                    {
                        mtime = File.GetLastWriteTimeUtc(path);
                    }
                    catch
                    {
                        continue;
                    }

                    if (top.Count < MaxMinidumpFiles)
                    {
                        top.Add((mtime, path));
                        if (top.Count == MaxMinidumpFiles)
                        {
                            top.Sort((a, b) => b.Mtime.CompareTo(a.Mtime));
                        }

                        continue;
                    }

                    if (mtime <= top[^1].Mtime)
                    {
                        continue;
                    }

                    top[^1] = (mtime, path);
                    top.Sort((a, b) => b.Mtime.CompareTo(a.Mtime));
                }

                info.Count = count;
                if (top.Count > 0 && top.Count < MaxMinidumpFiles)
                {
                    top.Sort((a, b) => b.Mtime.CompareTo(a.Mtime));
                }

                foreach (var (mtime, path) in top)
                {
                    try
                    {
                        var f = new FileInfo(path);
                        var file = new MinidumpFileInfo
                        {
                            Name = f.Name,
                            SizeBytes = f.Exists ? f.Length : null,
                            ModifiedAt = f.LastWriteTimeUtc.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
                        };
                        // Только заголовок / Event Log — тело .dmp не читаем целиком и не upload.
                        var bug = MinidumpBugcheck.TryRead(path);
                        if (bug.Code is null)
                        {
                            bug = MinidumpBugcheck.TryFromEventLog(mtime);
                        }

                        if (bug.Code is not null)
                        {
                            file.BugcheckCode = bug.Code;
                            file.BugcheckParameters = bug.Parameters is { Count: > 0 }
                                ? bug.Parameters.ToList()
                                : null;
                            file.BugcheckMessage = bug.Message;
                        }

                        info.Files.Add(file);
                    }
                    catch
                    {
                        // skip unreadable entry
                    }
                }
            }

            if (!info.MemoryDmpPresent && info.Count == 0)
            {
                return info; // пустой блок — полезно знать, что дампов нет
            }

            return info;
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "minidumps",
                Error = Truncate(ex.Message, 200)
            });
            return null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareDisks(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            hw.Disks = new List<DiskInfo>();
            using var disks = new ManagementObjectSearcher(
                "SELECT Model, Size, MediaType, SerialNumber, InterfaceType FROM Win32_DiskDrive");
            foreach (ManagementObject obj in disks.Get())
            {
                using (obj)
                {
                    hw.Disks.Add(new DiskInfo
                    {
                        Model = HardwareMaps.CleanWmiString(obj["Model"]?.ToString()),
                        SizeBytes = ToLong(obj["Size"]),
                        MediaType = HardwareMaps.CleanWmiString(obj["MediaType"]?.ToString()),
                        // Уже disks[].serial_number (inventory-plus); не дублировать top-level.
                        SerialNumber = HardwareMaps.CleanHardwareSerial(obj["SerialNumber"]?.ToString()),
                        InterfaceType = HardwareMaps.CleanWmiString(obj["InterfaceType"]?.ToString())
                    });
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "hardware.disks", Error = Truncate(ex.Message, 200) });
            hw.Disks = null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareVolumes(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            hw.Volumes = new List<VolumeInfo>();
            using var vols = new ManagementObjectSearcher(
                "SELECT DeviceID, Size, FreeSpace FROM Win32_LogicalDisk WHERE DriveType=3");
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
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.volumes",
                Error = Truncate(ex.Message, 200)
            });
            hw.Volumes = null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareGpus(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            var gpus = new List<GpuInfo>();
            using var searcher = new ManagementObjectSearcher(
                "SELECT Name, AdapterCompatibility, DriverVersion, AdapterRAM, PNPDeviceID " +
                "FROM Win32_VideoController");
            foreach (ManagementObject obj in searcher.Get())
            {
                using (obj)
                {
                    if (gpus.Count >= MaxGpus)
                    {
                        break;
                    }

                    var name = HardwareMaps.CleanWmiString(obj["Name"]?.ToString());
                    if (name is null)
                    {
                        continue;
                    }

                    // Пропускать placeholder / remote display stubs, если дальше есть реальное имя адаптера.
                    if (name.Contains("Microsoft Basic Display", StringComparison.OrdinalIgnoreCase)
                        || name.Contains("Remote Desktop", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    gpus.Add(new GpuInfo
                    {
                        Name = name,
                        Vendor = HardwareMaps.CleanWmiString(obj["AdapterCompatibility"]?.ToString()),
                        DriverVersion = HardwareMaps.CleanWmiString(obj["DriverVersion"]?.ToString()),
                        AdapterRamBytes = ToLong(obj["AdapterRAM"]),
                        PnpDeviceId = HardwareMaps.CleanWmiString(obj["PNPDeviceID"]?.ToString())
                    });
                }
            }

            hw.Gpus = gpus.Count > 0 ? gpus : new List<GpuInfo>();
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "hardware.gpus", Error = Truncate(ex.Message, 200) });
            hw.Gpus = null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectHardwareRamModules(HardwareInfo hw, List<CollectorError> errors)
    {
        try
        {
            // Предпочитать SMBIOSMemoryType; старые хосты могут отвергнуть колонку — fallback.
            const string withSmbios =
                "SELECT Capacity, Speed, Manufacturer, PartNumber, SerialNumber, FormFactor, " +
                "MemoryType, SMBIOSMemoryType, BankLabel, DeviceLocator FROM Win32_PhysicalMemory";
            const string legacy =
                "SELECT Capacity, Speed, Manufacturer, PartNumber, SerialNumber, FormFactor, " +
                "MemoryType, BankLabel, DeviceLocator FROM Win32_PhysicalMemory";

            List<RamModuleInfo> modules;
            try
            {
                modules = ReadPhysicalMemoryModules(withSmbios);
            }
            catch (ManagementException)
            {
                modules = ReadPhysicalMemoryModules(legacy);
            }

            hw.RamModules = modules;
            hw.RamMemoryType = HardwareMaps.ConsensusMemoryType(modules.Select(m => m.MemoryType));
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "hardware.ram_modules",
                Error = Truncate(ex.Message, 200)
            });
            hw.RamModules = null;
        }
    }

    private static NetworkInfo CollectNetwork(List<CollectorError> errors)
    {
        var net = new NetworkInfo { Nics = new List<NicInfo>() };
        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var nics = new ManagementObjectSearcher(
                    "SELECT Description, MACAddress, IPAddress, DHCPEnabled FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled=True");
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

                    net.Nics.Add(new NicInfo
                    {
                        Name = ni.Name,
                        Mac = FormatMac(ni.GetPhysicalAddress()),
                        Ipv4 = ipv4,
                        Ipv6 = ipv6,
                        Dhcp = null
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

    /// <summary>
    /// Лёгкий список установленных программ из Uninstall registry (views 64-bit + 32-bit).
    /// </summary>
    private static SoftwareInfo CollectSoftware(List<CollectorError> errors)
    {
        var software = new SoftwareInfo { Programs = new List<InstalledProgram>() };
        try
        {
            if (!OperatingSystem.IsWindows())
            {
                // Opt-in, но нет Windows registry — опустить programs без спама ошибок.
                software.Programs = null;
                return software;
            }

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            ReadUninstallHive(RegistryHive.LocalMachine, RegistryView.Registry64, software.Programs!, seen);
            ReadUninstallHive(RegistryHive.LocalMachine, RegistryView.Registry32, software.Programs!, seen);

            software.Programs = software.Programs!
                .OrderBy(p => p.Name, StringComparer.OrdinalIgnoreCase)
                .Take(MaxSoftwarePrograms)
                .ToList();
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError { Section = "software", Error = Truncate(ex.Message, 200) });
            software.Programs = null;
        }

        return software;
    }

    [SupportedOSPlatform("windows")]
    private static void ReadUninstallHive(
        RegistryHive hive,
        RegistryView view,
        List<InstalledProgram> dest,
        HashSet<string> seen)
    {
        using var baseKey = RegistryKey.OpenBaseKey(hive, view);
        using var uninstall = baseKey.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall");
        if (uninstall is null)
        {
            return;
        }

        foreach (var subName in uninstall.GetSubKeyNames())
        {
            if (dest.Count >= MaxSoftwarePrograms)
            {
                break;
            }

            using var sub = uninstall.OpenSubKey(subName);
            if (sub is null)
            {
                continue;
            }

            // Пропускать quiet/system записи без display name.
            var name = sub.GetValue("DisplayName") as string;
            if (string.IsNullOrWhiteSpace(name))
            {
                continue;
            }

            name = name.Trim();
            if (sub.GetValue("SystemComponent") is int sc && sc == 1)
            {
                continue;
            }

            var version = (sub.GetValue("DisplayVersion") as string)?.Trim();
            var publisher = (sub.GetValue("Publisher") as string)?.Trim();
            var dedupeKey = $"{name}|{version}";
            if (!seen.Add(dedupeKey))
            {
                continue;
            }

            dest.Add(new InstalledProgram
            {
                Name = name,
                Version = string.IsNullOrWhiteSpace(version) ? null : version,
                Publisher = string.IsNullOrWhiteSpace(publisher) ? null : publisher,
            });
        }
    }

    private static string? FormatMac(PhysicalAddress address)
    {
        var bytes = address.GetAddressBytes();
        if (bytes.Length == 0) return null;
        return string.Join(":", bytes.Select(b => b.ToString("X2")));
    }

    [SupportedOSPlatform("windows")]
    private static List<RamModuleInfo> ReadPhysicalMemoryModules(string wql)
    {
        var modules = new List<RamModuleInfo>();
        using var searcher = new ManagementObjectSearcher(wql);
        foreach (ManagementObject obj in searcher.Get())
        {
            using (obj)
            {
                if (modules.Count >= MaxRamModules)
                {
                    break;
                }

                var capacity = ToLong(obj["Capacity"]);
                var speed = ToInt(obj["Speed"]);
                var manufacturer = HardwareMaps.CleanWmiString(obj["Manufacturer"]?.ToString());
                var partNumber = HardwareMaps.CleanWmiString(obj["PartNumber"]?.ToString());
                var serial = HardwareMaps.CleanWmiString(obj["SerialNumber"]?.ToString());
                var bank = HardwareMaps.CleanWmiString(obj["BankLabel"]?.ToString());
                var locator = HardwareMaps.CleanWmiString(obj["DeviceLocator"]?.ToString());
                var formFactor = HardwareMaps.FormFactorName(ToInt(obj["FormFactor"]));
                // Legacy MemoryType на современном Dell часто 0; SMBIOSMemoryType даёт DDR4/DDR5/LPDDR*.
                var memoryType = HardwareMaps.ResolveMemoryType(
                    ToInt(SafeWmiProperty(obj, "MemoryType")),
                    ToInt(SafeWmiProperty(obj, "SMBIOSMemoryType")));

                // Пропускать пустые строки без полезного identity/size.
                if (capacity is null or 0
                    && speed is null
                    && manufacturer is null
                    && partNumber is null
                    && locator is null
                    && bank is null
                    && memoryType is null)
                {
                    continue;
                }

                modules.Add(new RamModuleInfo
                {
                    CapacityBytes = capacity,
                    SpeedMhz = speed,
                    Manufacturer = manufacturer,
                    PartNumber = partNumber,
                    SerialNumber = serial,
                    FormFactor = formFactor,
                    MemoryType = memoryType,
                    BankLabel = bank,
                    DeviceLocator = locator,
                    Channel = HardwareMaps.InferChannel(locator, bank)
                });
            }
        }

        return modules;
    }

    private static SecurityInfo? CollectSecurity(List<CollectorError> errors)
    {
        if (!OperatingSystem.IsWindows())
        {
            return null;
        }

        var sec = new SecurityInfo();
        CollectSecurityTpm(sec, errors);
        WmiHelper.YieldBriefly();
        CollectSecuritySecureBoot(sec, errors);
        WmiHelper.YieldBriefly();
        CollectSecurityAntivirus(sec, errors);
        return sec;
    }

    [SupportedOSPlatform("windows")]
    private static void CollectSecurityTpm(SecurityInfo sec, List<CollectorError> errors)
    {
        try
        {
            var scope = new ManagementScope(@"\\.\root\cimv2\Security\MicrosoftTpm");
            scope.Connect();
            using var searcher = new ManagementObjectSearcher(
                scope, new ObjectQuery("SELECT SpecVersion, IsEnabled_InitialValue FROM Win32_Tpm"));
            foreach (ManagementObject obj in searcher.Get())
            {
                using (obj)
                {
                    sec.TpmPresent = true;
                    sec.TpmSpecVersion = HardwareMaps.CleanWmiString(obj["SpecVersion"]?.ToString());
                    break;
                }
            }

            if (sec.TpmPresent is null)
            {
                sec.TpmPresent = false;
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "security.tpm",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectSecuritySecureBoot(SecurityInfo sec, List<CollectorError> errors)
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(
                @"SYSTEM\CurrentControlSet\Control\SecureBoot\State");
            if (key?.GetValue("UEFISecureBootEnabled") is int v)
            {
                sec.SecureBoot = v != 0;
            }
            else if (key?.GetValue("UEFISecureBootEnabled") is long lv)
            {
                sec.SecureBoot = lv != 0;
            }
            else
            {
                sec.SecureBoot = null;
            }
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "security.secure_boot",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CollectSecurityAntivirus(SecurityInfo sec, List<CollectorError> errors)
    {
        try
        {
            var list = new List<AntivirusProductInfo>();
            var scope = new ManagementScope(@"\\.\root\SecurityCenter2");
            scope.Connect();
            using var searcher = new ManagementObjectSearcher(
                scope, new ObjectQuery("SELECT displayName, productState FROM AntiVirusProduct"));
            foreach (ManagementObject obj in searcher.Get())
            {
                using (obj)
                {
                    if (list.Count >= MaxAntivirusProducts)
                    {
                        break;
                    }

                    var name = HardwareMaps.CleanWmiString(obj["displayName"]?.ToString());
                    if (name is null)
                    {
                        continue;
                    }

                    list.Add(new AntivirusProductInfo
                    {
                        Name = name,
                        ProductState = ToInt(obj["productState"])
                    });
                }
            }

            sec.Antivirus = list.Count > 0 ? list : null;
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "security.antivirus",
                Error = Truncate(ex.Message, 200)
            });
        }
    }

    [SupportedOSPlatform("windows")]
    private static bool? TryDetectPendingReboot(List<CollectorError> errors)
    {
        try
        {
            if (RegistryKeyExists(
                    @"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending")
                || RegistryKeyExists(
                    @"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootInProgress")
                || RegistryKeyExists(
                    @"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired")
                || RegistryValueExists(
                    @"SYSTEM\CurrentControlSet\Control\Session Manager",
                    "PendingFileRenameOperations"))
            {
                return true;
            }

            return false;
        }
        catch (Exception ex)
        {
            errors.Add(new CollectorError
            {
                Section = "host.pending_reboot",
                Error = Truncate(ex.Message, 200)
            });
            return null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static bool RegistryKeyExists(string relativePath)
    {
        using var key = Registry.LocalMachine.OpenSubKey(relativePath);
        return key is not null;
    }

    [SupportedOSPlatform("windows")]
    private static bool RegistryValueExists(string relativePath, string valueName)
    {
        using var key = Registry.LocalMachine.OpenSubKey(relativePath);
        if (key is null)
        {
            return false;
        }

        return key.GetValue(valueName) is not null;
    }

    [SupportedOSPlatform("windows")]
    private static string? TryWmiDateToUtcIso(string? dmtf)
    {
        if (string.IsNullOrWhiteSpace(dmtf))
        {
            return null;
        }

        try
        {
            var dt = ManagementDateTimeConverter.ToDateTime(dmtf).ToUniversalTime();
            return dt.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Читать опциональное WMI-свойство; отсутствующие → null (без throw).</summary>
    [SupportedOSPlatform("windows")]
    private static object? SafeWmiProperty(ManagementBaseObject obj, string name)
    {
        try
        {
            return obj[name];
        }
        catch (ManagementException)
        {
            return null;
        }
        catch (System.Runtime.InteropServices.COMException)
        {
            return null;
        }
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

    private static string Truncate(string text, int max)
    {
        if (string.IsNullOrEmpty(text) || text.Length <= max)
        {
            return text;
        }

        return text[..max];
    }
}
