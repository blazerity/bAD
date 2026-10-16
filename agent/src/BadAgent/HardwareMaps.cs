using System.Text.RegularExpressions;

namespace BadAgent;

/// <summary>Чистые хелперы маппинга WMI-полей железа (удобно для unit-тестов).</summary>
public static class HardwareMaps
{
    private static readonly Regex ChannelRegex = new(
        @"(?:channel[\s\-_]*)([A-Z0-9]+)|(?:^|\b)(?:CHA?N?)[\s\-_]?([A-Z])(?:\b|$)|(?:DIMM\s*)([A-Z])\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Trim и отбрасывание placeholder-строк WMI вроде "To Be Filled By O.E.M.".</summary>
    public static string? CleanWmiString(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        var text = value.Trim();
        if (text.Length == 0)
        {
            return null;
        }

        var lower = text.ToLowerInvariant();
        if (lower is "none" or "n/a" or "na" or "default string" or "system serial number"
            or "system product name" or "system manufacturer" or "to be filled by o.e.m."
            or "o.e.m." or "oem" or "unknown" or "not specified" or "not available")
        {
            return null;
        }

        if (lower.StartsWith("to be filled", StringComparison.Ordinal)
            || lower.StartsWith("fill by oem", StringComparison.Ordinal))
        {
            return null;
        }

        return text;
    }

    public static string? FormFactorName(int? code) => code switch
    {
        null => null,
        0 => "Unknown",
        1 => "Other",
        2 => "SIP",
        3 => "DIP",
        4 => "ZIP",
        5 => "SOJ",
        6 => "Proprietary",
        7 => "SIMM",
        8 => "DIMM",
        9 => "TSOP",
        10 => "PGA",
        11 => "RIMM",
        12 => "SODIMM",
        13 => "SRIMM",
        14 => "SMD",
        15 => "SSMP",
        16 => "QFP",
        17 => "TQFP",
        18 => "SOIC",
        19 => "LCC",
        20 => "PLCC",
        21 => "BGA",
        22 => "FPBGA",
        23 => "LGA",
        _ => $"code_{code.Value}"
    };

    public static string? MemoryTypeName(int? code) => code switch
    {
        null => null,
        0 => "Unknown",
        1 => "Other",
        2 => "DRAM",
        3 => "Synchronous DRAM",
        4 => "Cache DRAM",
        5 => "EDO",
        6 => "EDRAM",
        7 => "VRAM",
        8 => "SRAM",
        9 => "RAM",
        10 => "ROM",
        11 => "Flash",
        12 => "EEPROM",
        13 => "FEPROM",
        14 => "EPROM",
        15 => "CDRAM",
        16 => "3DRAM",
        17 => "SDRAM",
        18 => "SGRAM",
        19 => "RDRAM",
        20 => "DDR",
        21 => "DDR2",
        22 => "DDR2 FB-DIMM",
        24 => "DDR3",
        25 => "FBD2",
        26 => "DDR4",
        27 => "LPDDR",
        28 => "LPDDR2",
        29 => "LPDDR3",
        30 => "LPDDR4",
        31 => "Logical non-volatile device",
        32 => "HBM",
        33 => "HBM2",
        34 => "DDR5",
        35 => "LPDDR5",
        36 => "HBM3",
        37 => "LPDDR5X",
        _ => $"code_{code.Value}"
    };

    /// <summary>
    /// Предпочитать SMBIOSMemoryType (современный Windows / Dell) вместо legacy MemoryType, если тот 0/Unknown.
    /// </summary>
    public static string? ResolveMemoryType(int? memoryType, int? smbiosMemoryType)
    {
        var smbios = MeaningfulMemoryType(smbiosMemoryType);
        if (smbios is not null)
        {
            return smbios;
        }

        return MeaningfulMemoryType(memoryType);
    }

    /// <summary>Единый тип на уровне системы, если все планки совпадают; иначе null.</summary>
    public static string? ConsensusMemoryType(IEnumerable<string?> stickTypes)
    {
        var distinct = stickTypes
            .Select(CleanWmiString)
            .Where(t => t is not null)
            .Where(t => !string.Equals(t, "Unknown", StringComparison.OrdinalIgnoreCase))
            .Where(t => !string.Equals(t, "Other", StringComparison.OrdinalIgnoreCase))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        return distinct.Count == 1 ? distinct[0] : null;
    }

    private static string? MeaningfulMemoryType(int? code)
    {
        var name = MemoryTypeName(code);
        if (name is null
            || string.Equals(name, "Unknown", StringComparison.OrdinalIgnoreCase)
            || string.Equals(name, "Other", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        return name;
    }

    /// <summary>
    /// Best-effort канал из DeviceLocator / BankLabel (Dell часто пишет "ChannelA-DIMM0").
    /// </summary>
    public static string? InferChannel(string? deviceLocator, string? bankLabel)
    {
        foreach (var raw in new[] { deviceLocator, bankLabel })
        {
            var text = CleanWmiString(raw);
            if (text is null)
            {
                continue;
            }

            var m = ChannelRegex.Match(text);
            if (!m.Success)
            {
                continue;
            }

            var token = m.Groups[1].Success ? m.Groups[1].Value
                : m.Groups[2].Success ? m.Groups[2].Value
                : m.Groups[3].Value;
            token = token.Trim().ToUpperInvariant();
            if (token.Length == 0)
            {
                continue;
            }

            return token.Length == 1 ? $"Channel {token}" : $"Channel {token}";
        }

        return null;
    }

    public static string? PreferFirst(params string?[] values)
    {
        foreach (var v in values)
        {
            var cleaned = CleanWmiString(v);
            if (cleaned is not null)
            {
                return cleaned;
            }
        }

        return null;
    }

    /// <summary>
    /// Серийники железа для inventory: CleanWmiString + отсев <c>0</c> / all-zero / all-F.
    /// </summary>
    public static string? CleanHardwareSerial(string? value)
    {
        var text = CleanWmiString(value);
        if (text is null)
        {
            return null;
        }

        if (text == "0")
        {
            return null;
        }

        var compact = text.Replace("-", "", StringComparison.Ordinal)
            .Replace(" ", "", StringComparison.Ordinal);
        if (compact.Length == 0)
        {
            return null;
        }

        if (compact.All(c => c == '0') || compact.All(c => c is 'F' or 'f'))
        {
            return null;
        }

        return text;
    }

    /// <summary>
    /// SMBIOS UUID для inventory / fallback id: trim; отсев all-F и all-zero.
    /// Не primary <c>device_id</c> (MachineGuid остаётся ключом установки).
    /// </summary>
    public static string? CleanSmbiosUuid(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return null;
        }

        var uuid = raw.Trim();
        if (uuid.Length == 0)
        {
            return null;
        }

        if (uuid.Equals("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", StringComparison.OrdinalIgnoreCase)
            || uuid.Equals("00000000-0000-0000-0000-000000000000", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        // Без дефисов — тоже отсечь однородный мусор.
        var compact = uuid.Replace("-", "", StringComparison.Ordinal);
        if (compact.Length > 0
            && (compact.All(c => c is 'F' or 'f') || compact.All(c => c == '0')))
        {
            return null;
        }

        return uuid;
    }

    /// <summary>
    /// Нормализация SMBIOS ChassisTypes → laptop|desktop|server|vm|other.
    /// VM hint из manufacturer/model перекрывает, если похоже на гипервизор.
    /// </summary>
    public static string NormalizeChassisType(
        IReadOnlyList<int>? chassisTypesRaw,
        string? manufacturer,
        string? model)
    {
        if (LooksLikeVirtualMachine(manufacturer, model))
        {
            return "vm";
        }

        if (chassisTypesRaw is null || chassisTypesRaw.Count == 0)
        {
            return "other";
        }

        foreach (var code in chassisTypesRaw)
        {
            if (code is 8 or 9 or 10 or 14 or 30 or 31 or 32)
            {
                return "laptop";
            }
        }

        foreach (var code in chassisTypesRaw)
        {
            if (code is 17 or 23 or 28 or 29)
            {
                return "server";
            }
        }

        foreach (var code in chassisTypesRaw)
        {
            if (code is 3 or 4 or 5 or 6 or 7 or 13 or 15 or 16 or 24 or 34 or 35 or 36)
            {
                return "desktop";
            }
        }

        return "other";
    }

    public static bool LooksLikeVirtualMachine(string? manufacturer, string? model)
    {
        var blob = $"{manufacturer} {model}".ToLowerInvariant();
        return blob.Contains("vmware", StringComparison.Ordinal)
               || blob.Contains("virtualbox", StringComparison.Ordinal)
               || blob.Contains("vbox", StringComparison.Ordinal)
               || blob.Contains("hyper-v", StringComparison.Ordinal)
               || blob.Contains("virtual machine", StringComparison.Ordinal)
               || blob.Contains("kvm", StringComparison.Ordinal)
               || blob.Contains("qemu", StringComparison.Ordinal)
               || blob.Contains("xen", StringComparison.Ordinal)
               || blob.Contains("parallels", StringComparison.Ordinal)
               || blob.Contains("bochs", StringComparison.Ordinal);
    }

    /// <summary>Короткие имена известных bugcheck; иначе null (код всё равно отдаём).</summary>
    public static string? BugcheckMessage(uint code) => code switch
    {
        0x0000000A => "IRQL_NOT_LESS_OR_EQUAL",
        0x0000001A => "MEMORY_MANAGEMENT",
        0x0000001E => "KMODE_EXCEPTION_NOT_HANDLED",
        0x0000003B => "SYSTEM_SERVICE_EXCEPTION",
        0x00000050 => "PAGE_FAULT_IN_NONPAGED_AREA",
        0x0000007E => "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
        0x0000007F => "UNEXPECTED_KERNEL_MODE_TRAP",
        0x0000009F => "DRIVER_POWER_STATE_FAILURE",
        0x000000C2 => "BAD_POOL_CALLER",
        0x000000D1 => "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
        0x000000D8 => "DRIVER_VERIFIER_DETECTED_VIOLATION",
        0x000000EA => "THREAD_STUCK_IN_DEVICE_DRIVER",
        0x000000F4 => "CRITICAL_OBJECT_TERMINATION",
        0x00000109 => "CRITICAL_STRUCTURE_CORRUPTION",
        0x00000133 => "DPC_WATCHDOG_VIOLATION",
        0x00000139 => "KERNEL_SECURITY_CHECK_FAILURE",
        0x00000144 => "BUGCODE_USB_DRIVER",
        0x000001C4 => "DRIVER_VERIFIER_DETECTED_VIOLATION",
        _ => null
    };
}
