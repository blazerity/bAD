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

    /// <summary>Assembly version as major.minor.patch, or <paramref name="fallback"/>.</summary>
    public static string GetAgentVersion(string fallback = "0.5.0") =>
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

    /// <summary>True when <paramref name="candidate"/> is a higher semver than <paramref name="current"/>.</summary>
    public static bool IsNewer(string? candidate, string? current)
    {
        if (!TryParseSemVer(candidate, out var a))
        {
            return false;
        }

        if (!TryParseSemVer(current, out var b))
        {
            return true;
        }

        return a > b;
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
