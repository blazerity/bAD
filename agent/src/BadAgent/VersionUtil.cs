using System.Globalization;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace BadAgent;

public static class VersionUtil
{
    private static readonly Regex SemVerPrefix = new(
        @"^\s*v?(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Версия сборки как major.minor.patch или <paramref name="fallback"/>.</summary>
    public static string GetAgentVersion(string fallback = "0.12.0") =>
        Assembly.GetExecutingAssembly().GetName().Version?.ToString(3) ?? fallback;

    public static bool TryParseSemVer(string? value, out Version version)
    {
        version = new Version(0, 0, 0);
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        var m = SemVerPrefix.Match(value);
        if (!m.Success)
        {
            return false;
        }

        var major = int.Parse(m.Groups["major"].Value, CultureInfo.InvariantCulture);
        var minor = int.Parse(m.Groups["minor"].Value, CultureInfo.InvariantCulture);
        var patch = int.Parse(m.Groups["patch"].Value, CultureInfo.InvariantCulture);
        version = new Version(major, minor, patch);
        return true;
    }

    /// <summary>Нормализовать desired: null/пусто/`latest` → <c>latest</c>; иначе major.minor.patch или null если мусор.</summary>
    public static string? NormalizeDesiredAgentVersion(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "latest";
        }

        var t = value.Trim();
        if (string.Equals(t, "latest", StringComparison.OrdinalIgnoreCase))
        {
            return "latest";
        }

        if (!TryParseSemVer(t, out var v))
        {
            return null;
        }

        return $"{v.Major}.{v.Minor}.{v.Build}";
    }

    /// <summary>-1 если a&lt;b, 0 если равны, 1 если a&gt;b; null если непарсибельно.</summary>
    public static int? CompareSemVer(string? a, string? b)
    {
        if (!TryParseSemVer(a, out var va) || !TryParseSemVer(b, out var vb))
        {
            return null;
        }

        return va.CompareTo(vb);
    }

    public static bool IsSameVersion(string? a, string? b) => CompareSemVer(a, b) == 0;

    /// <summary>True, если <paramref name="candidate"/> новее по semver, чем <paramref name="current"/>.</summary>
    public static bool IsNewer(string? candidate, string? current)
    {
        var cmp = CompareSemVer(candidate, current);
        if (cmp is null)
        {
            // Старое поведение: битый candidate → false; битый current → true если candidate ок.
            if (!TryParseSemVer(candidate, out _))
            {
                return false;
            }

            return !TryParseSemVer(current, out _);
        }

        return cmp > 0;
    }

    public static bool IsOlder(string? candidate, string? current)
    {
        var cmp = CompareSemVer(candidate, current);
        return cmp < 0;
    }

    public static string Sha256Hex(Stream stream)
    {
        using var sha = SHA256.Create();
        var hash = sha.ComputeHash(stream);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    public static string Sha256HexFile(string path)
    {
        using var fs = File.OpenRead(path);
        return Sha256Hex(fs);
    }

    public static bool VerifySha256File(string path, string expectedHex)
    {
        if (string.IsNullOrWhiteSpace(expectedHex))
        {
            return false;
        }

        var actual = Sha256HexFile(path);
        return string.Equals(actual, expectedHex.Trim(), StringComparison.OrdinalIgnoreCase);
    }
}
