using System.Text.RegularExpressions;

namespace BadAgent;

/// <summary>
/// SEC-002 / SEC-009: безопасные имена MSI и URL скачивания обновлений.
/// </summary>
public static class UpdatePathUtil
{
    private static readonly Regex SafeMsiName = new(
        @"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}\.msi$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Compiled);

    /// <summary>
    /// Только basename, без '..' / разделителей; результат обязан остаться внутри <paramref name="tempDir"/>.
    /// </summary>
    public static string ResolveSafeMsiPath(string tempDir, string? msiName, string? versionFallback)
    {
        if (string.IsNullOrWhiteSpace(tempDir))
        {
            throw new ArgumentException("tempDir is required", nameof(tempDir));
        }

        var candidate = string.IsNullOrWhiteSpace(msiName)
            ? $"bad-agent-{(string.IsNullOrWhiteSpace(versionFallback) ? "update" : versionFallback.Trim())}.msi"
            : msiName.Trim();

        // Отсечь абсолютные/UNC и directory pieces — только basename.
        candidate = Path.GetFileName(candidate.Replace('/', Path.DirectorySeparatorChar));

        if (string.IsNullOrWhiteSpace(candidate) || !SafeMsiName.IsMatch(candidate))
        {
            var fb = string.IsNullOrWhiteSpace(versionFallback) ? "update" : versionFallback.Trim();
            // Версия тоже может быть грязной — оставить только semver-like chars.
            fb = Regex.Replace(fb, @"[^0-9A-Za-z._-]", "");
            if (string.IsNullOrWhiteSpace(fb))
            {
                fb = "update";
            }

            candidate = $"bad-agent-{fb}.msi";
            if (!SafeMsiName.IsMatch(candidate))
            {
                candidate = "bad-agent-update.msi";
            }
        }

        var tempFull = Path.GetFullPath(tempDir);
        if (!tempFull.EndsWith(Path.DirectorySeparatorChar)
            && !tempFull.EndsWith(Path.AltDirectorySeparatorChar))
        {
            tempFull += Path.DirectorySeparatorChar;
        }

        var combined = Path.GetFullPath(Path.Combine(tempFull, candidate));
        if (!combined.StartsWith(tempFull, OperatingSystem.IsWindows()
                ? StringComparison.OrdinalIgnoreCase
                : StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"Refusing MSI path outside temp dir: {combined}");
        }

        return combined;
    }

    /// <summary>
    /// Только relative path или absolute URL того же origin, что <paramref name="serverBaseUrl"/>.
    /// Произвольный чужой host — отказ.
    /// </summary>
    public static string ResolveSameOriginUpdateUrl(string serverBaseUrl, string? relativeOrAbsoluteUrl)
    {
        if (string.IsNullOrWhiteSpace(serverBaseUrl))
        {
            throw new ArgumentException("serverBaseUrl is required", nameof(serverBaseUrl));
        }

        if (string.IsNullOrWhiteSpace(relativeOrAbsoluteUrl))
        {
            throw new ArgumentException("update URL is required", nameof(relativeOrAbsoluteUrl));
        }

        var baseUri = new Uri(serverBaseUrl.TrimEnd('/') + "/", UriKind.Absolute);
        var raw = relativeOrAbsoluteUrl.Trim();

        Uri resolved;
        if (Uri.TryCreate(raw, UriKind.Absolute, out var abs))
        {
            resolved = abs;
        }
        else
        {
            // Relative: only path (+ optional query), no scheme-relative //host
            if (raw.StartsWith("//", StringComparison.Ordinal))
            {
                throw new InvalidOperationException("Scheme-relative update URL is not allowed");
            }

            if (raw.Contains("..", StringComparison.Ordinal) || raw.Contains('\\'))
            {
                throw new InvalidOperationException("Update URL must not contain '..' or backslashes");
            }

            var path = raw.StartsWith('/') ? raw : "/" + raw;
            if (!Uri.TryCreate(baseUri, path, out resolved!))
            {
                throw new InvalidOperationException("Invalid relative update URL");
            }
        }

        if (!IsSameOrigin(baseUri, resolved))
        {
            throw new InvalidOperationException(
                "Update download URL must be same-origin as configured server_url; refusing arbitrary absolute URL");
        }

        if (resolved.AbsolutePath.Contains("..", StringComparison.Ordinal))
        {
            throw new InvalidOperationException("Update URL path must not contain '..'");
        }

        // Без fragment; query сохраняем.
        var builder = new UriBuilder(resolved) { Fragment = "" };
        return builder.Uri.ToString();
    }

    private static bool IsSameOrigin(Uri expected, Uri actual)
    {
        return string.Equals(expected.Scheme, actual.Scheme, StringComparison.OrdinalIgnoreCase)
               && string.Equals(expected.Host, actual.Host, StringComparison.OrdinalIgnoreCase)
               && expected.Port == actual.Port;
    }
}
