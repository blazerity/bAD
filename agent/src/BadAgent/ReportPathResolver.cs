namespace BadAgent;

/// <summary>
/// Резолвит путь вывода для <c>bad -h/--html [path]</c>.
/// По умолчанию на Desktop: <c>bad_report_yyyyMMdd_HHmmss.html</c>.
/// </summary>
public static class ReportPathResolver
{
    public const string DefaultFilePrefix = "bad_report_";

    /// <summary>
    /// Резолвит путь HTML-отчёта.
    /// <paramref name="pathArg"/> null/empty → Desktop + имя по умолчанию;
    /// существующий каталог (или слэш в конце) → этот каталог + имя по умолчанию;
    /// иначе — путь к файлу (добавить <c>.html</c>, если нет/не тот).
    /// <paramref name="now"/> только для timestamp в имени по умолчанию (local или UTC — решает вызывающий).
    /// </summary>
    public static string ResolveHtmlPath(string? pathArg, DateTime now, Func<string>? getDesktop = null)
    {
        var fileName = $"{DefaultFilePrefix}{now:yyyyMMdd_HHmmss}.html";
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
            // дальше — UserProfile
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
