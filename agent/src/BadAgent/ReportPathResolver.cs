namespace BadAgent;

/// <summary>
/// Resolves output path for <c>bad -h/--html [path]</c>.
/// Desktop default: <c>bad_report_yyyyMMdd_HHmmss.html</c>.
/// </summary>
public static class ReportPathResolver
{
    public const string DefaultFilePrefix = "bad_report_";

    /// <summary>
    /// Resolve HTML report path.
    /// <paramref name="pathArg"/> null/empty → Desktop + default filename;
    /// existing directory (or trailing slash) → that dir + default filename;
    /// otherwise treat as file path (append <c>.html</c> if missing/wrong).
    /// </summary>
    public static string ResolveHtmlPath(string? pathArg, DateTime utcNow, Func<string>? getDesktop = null)
    {
        var fileName = $"{DefaultFilePrefix}{utcNow:yyyyMMdd_HHmmss}.html";
        if (string.IsNullOrWhiteSpace(pathArg))
        {
            var desktop = getDesktop?.Invoke() ?? GetDesktopDirectory();
            return Path.Combine(desktop, fileName);
        }

        var trimmed = pathArg.Trim();
        if (IsDirectoryTarget(trimmed))
        {
            var dir = trimmed.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (string.IsNullOrEmpty(dir))
            {
                dir = Path.GetPathRoot(trimmed) ?? trimmed;
            }

            return Path.Combine(dir, fileName);
        }

        var full = Path.GetFullPath(trimmed);
        var ext = Path.GetExtension(full);
        if (string.IsNullOrEmpty(ext))
        {
            return full + ".html";
        }

        return full;
    }

    public static string GetDesktopDirectory()
    {
        try
        {
            var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            if (!string.IsNullOrWhiteSpace(desktop))
            {
                return desktop;
            }
        }
        catch
        {
            // fall through
        }

        return Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    }

    private static bool IsDirectoryTarget(string path)
    {
        if (path.EndsWith(Path.DirectorySeparatorChar) || path.EndsWith(Path.AltDirectorySeparatorChar))
        {
            return true;
        }

        try
        {
            return Directory.Exists(path);
        }
        catch
        {
            return false;
        }
    }
}
