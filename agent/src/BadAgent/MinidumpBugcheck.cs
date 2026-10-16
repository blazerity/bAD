using System.Globalization;

namespace BadAgent;

/// <summary>
/// Читает BugCheck из <b>заголовка</b> minidump (prefix файла). Тело дампа не отправляется.
/// </summary>
public static class MinidumpBugcheck
{
    public const int MaxHeaderBytes = 64 * 1024;
    public const int MaxMessageChars = 200;

    private const uint MdmpSignature = 0x504D444D; // 'MDMP'
    private const uint ExceptionStreamType = 6;

    public readonly record struct Result(
        string? Code,
        IReadOnlyList<string>? Parameters,
        string? Message);

    public static Result TryRead(string path)
    {
        try
        {
            using var fs = new FileStream(
                path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            var toRead = (int)Math.Min(MaxHeaderBytes, fs.Length);
            if (toRead < 32)
            {
                return default;
            }

            var buf = new byte[toRead];
            var n = fs.Read(buf, 0, toRead);
            if (n < 32)
            {
                return default;
            }

            return TryParseHeader(buf.AsSpan(0, n));
        }
        catch
        {
            return default;
        }
    }

    public static Result TryParseHeader(ReadOnlySpan<byte> data)
    {
        if (data.Length < 32)
        {
            return default;
        }

        var sig = BitConverter.ToUInt32(data);
        if (sig != MdmpSignature)
        {
            return default;
        }

        // MINIDUMP_HEADER: NumberOfStreams @8, StreamDirectoryRva @12
        var numberOfStreams = BitConverter.ToUInt32(data.Slice(8));
        var directoryRva = BitConverter.ToUInt32(data.Slice(12));
        if (numberOfStreams == 0 || numberOfStreams > 256)
        {
            return default;
        }

        // MINIDUMP_DIRECTORY: StreamType(4) + DataSize(4) + RVA(4) = 12
        long dirEnd = (long)directoryRva + (long)numberOfStreams * 12;
        if (directoryRva > data.Length || dirEnd > data.Length)
        {
            return default;
        }

        for (uint i = 0; i < numberOfStreams; i++)
        {
            var off = (int)(directoryRva + i * 12);
            var streamType = BitConverter.ToUInt32(data.Slice(off));
            var dataSize = BitConverter.ToUInt32(data.Slice(off + 4));
            var rva = BitConverter.ToUInt32(data.Slice(off + 8));
            if (streamType != ExceptionStreamType || dataSize < 24)
            {
                continue;
            }

            if (rva > data.Length || (long)rva + 4 + 20 > data.Length)
            {
                continue;
            }

            // MINIDUMP_EXCEPTION_STREAM: ThreadId(4) + alignment(4) + EXCEPTION_RECORD64
            // EXCEPTION_RECORD64 starts at rva+8: ExceptionCode(4)...
            var exOff = (int)rva + 8;
            if (exOff + 4 + 4 + 8 + 8 + 4 + 4 + 32 > data.Length)
            {
                // Need at least code + flags + record + address + numParams + align + 4*8 params
                if (exOff + 4 > data.Length)
                {
                    continue;
                }
            }

            var code = BitConverter.ToUInt32(data.Slice(exOff));
            var codeStr = $"0x{code:X8}";

            uint numParams = 0;
            if (exOff + 4 + 4 + 8 + 8 + 4 <= data.Length)
            {
                numParams = BitConverter.ToUInt32(data.Slice(exOff + 4 + 4 + 8 + 8));
            }

            numParams = Math.Min(numParams, 4u);
            List<string>? parameters = null;
            var paramsOff = exOff + 4 + 4 + 8 + 8 + 4 + 4; // after NumberParameters + __unusedAlignment
            if (numParams > 0 && paramsOff + numParams * 8 <= data.Length)
            {
                parameters = new List<string>((int)numParams);
                for (uint p = 0; p < numParams; p++)
                {
                    var val = BitConverter.ToUInt64(data.Slice(paramsOff + (int)(p * 8)));
                    parameters.Add($"0x{val:X}");
                }
            }

            var message = HardwareMaps.BugcheckMessage(code);
            if (message is { Length: > MaxMessageChars })
            {
                message = message[..MaxMessageChars];
            }

            return new Result(codeStr, parameters, message);
        }

        return default;
    }

    /// <summary>Fallback: System Event Log BugCheck около mtime файла (без копирования dump).</summary>
    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    public static Result TryFromEventLog(DateTime fileMtimeUtc)
    {
        if (!OperatingSystem.IsWindows())
        {
            return default;
        }

        try
        {
            using var log = new System.Diagnostics.EventLog("System");
            var from = fileMtimeUtc.ToLocalTime().AddMinutes(-30);
            var to = fileMtimeUtc.ToLocalTime().AddMinutes(30);
            // Идём с конца — свежие записи.
            for (var i = log.Entries.Count - 1; i >= 0 && i >= log.Entries.Count - 400; i--)
            {
                System.Diagnostics.EventLogEntry entry;
                try
                {
                    entry = log.Entries[i];
                }
                catch
                {
                    continue;
                }

                if (entry.TimeGenerated < from)
                {
                    break;
                }

                if (entry.TimeGenerated > to)
                {
                    continue;
                }

                // BugCheck / event id 1001
                var isBugcheck = string.Equals(entry.Source, "BugCheck", StringComparison.OrdinalIgnoreCase)
                                 || (entry.InstanceId & 0xFFFF) == 1001;
                if (!isBugcheck)
                {
                    continue;
                }

                var parsed = TryParseBugcheckEventMessage(entry.Message);
                if (parsed.Code is not null)
                {
                    return parsed;
                }
            }
        }
        catch
        {
            // soft-fail
        }

        return default;
    }

    public static Result TryParseBugcheckEventMessage(string? message)
    {
        if (string.IsNullOrWhiteSpace(message))
        {
            return default;
        }

        // Типичный текст: "The computer has rebooted from a bugcheck.  The bugcheck was: 0x0000009f (0xa, 0xb, 0xc, 0xd)."
        var m = System.Text.RegularExpressions.Regex.Match(
            message,
            @"0x([0-9a-fA-F]{1,8})\s*\(\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*\)",
            System.Text.RegularExpressions.RegexOptions.CultureInvariant);
        if (!m.Success)
        {
            m = System.Text.RegularExpressions.Regex.Match(
                message,
                @"bugcheck\s*(?:was)?\s*:?\s*0x([0-9a-fA-F]{1,8})",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase
                | System.Text.RegularExpressions.RegexOptions.CultureInvariant);
            if (!m.Success)
            {
                return default;
            }

            var codeOnly = uint.Parse(m.Groups[1].Value, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            var codeStr = $"0x{codeOnly:X8}";
            var msgOnly = HardwareMaps.BugcheckMessage(codeOnly);
            return new Result(codeStr, null, TruncateMsg(msgOnly));
        }

        var code = uint.Parse(m.Groups[1].Value, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
        var parameters = new List<string>
        {
            NormalizeHexToken(m.Groups[2].Value),
            NormalizeHexToken(m.Groups[3].Value),
            NormalizeHexToken(m.Groups[4].Value),
            NormalizeHexToken(m.Groups[5].Value),
        };
        return new Result($"0x{code:X8}", parameters, TruncateMsg(HardwareMaps.BugcheckMessage(code)));
    }

    private static string NormalizeHexToken(string raw)
    {
        var t = raw.Trim();
        if (!t.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
        {
            t = "0x" + t;
        }

        return t;
    }

    private static string? TruncateMsg(string? msg)
    {
        if (msg is null)
        {
            return null;
        }

        return msg.Length <= MaxMessageChars ? msg : msg[..MaxMessageChars];
    }
}
