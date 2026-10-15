using System.Text.RegularExpressions;

namespace BadAgent;

/// <summary>Pure helpers for WMI hardware field mapping (unit-testable).</summary>
public static class HardwareMaps
{
    private static readonly Regex ChannelRegex = new(
        @"(?:channel[\s\-_]*)([A-Z0-9]+)|(?:^|\b)(?:CHA?N?)[\s\-_]?([A-Z])(?:\b|$)|(?:DIMM\s*)([A-Z])\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Trim and drop WMI placeholder serials like "To Be Filled By O.E.M.".</summary>
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
    /// Prefer SMBIOSMemoryType (modern Windows / Dell) over legacy MemoryType when the latter is 0/Unknown.
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

    /// <summary>Single system-level type when all sticks agree; otherwise null.</summary>
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
    /// Best-effort channel from DeviceLocator / BankLabel (Dell often uses "ChannelA-DIMM0").
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
}
