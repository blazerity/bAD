using Microsoft.Extensions.Logging;

namespace BadAgent;

/// <summary>Один файл из %SystemRoot%\Minidump по запросу heartbeat (без обхода каталога).</summary>
public static class MinidumpUploadHelper
{
    public const long MaxUploadBytes = 8L * 1024 * 1024;

    /// <summary>Возвращает путь к файлу или причину отказа (RU для лога/консоли).</summary>
    public static MinidumpUploadResolveResult TryResolveUploadPath(string? requested)
    {
        if (string.IsNullOrWhiteSpace(requested))
        {
            return new MinidumpUploadResolveResult(null, "minidump: запрос без имени файла");
        }

        if (!OperatingSystem.IsWindows())
        {
            return new MinidumpUploadResolveResult(null, "minidump: только Windows");
        }

        var windowsDir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        if (string.IsNullOrWhiteSpace(windowsDir))
        {
            windowsDir = Environment.GetEnvironmentVariable("SystemRoot") ?? @"C:\Windows";
        }

        var minidumpDir = Path.Combine(windowsDir, "Minidump");
        string name;
        try
        {
            name = Path.GetFileName(requested.Trim());
        }
        catch (ArgumentException)
        {
            return new MinidumpUploadResolveResult(null, "minidump: недопустимое имя файла");
        }

        if (string.IsNullOrEmpty(name)
            || !name.EndsWith(".dmp", StringComparison.OrdinalIgnoreCase))
        {
            return new MinidumpUploadResolveResult(null, "minidump: нужен один .dmp в каталоге Minidump");
        }

        if (string.Equals(name, "memory.dmp", StringComparison.OrdinalIgnoreCase))
        {
            return new MinidumpUploadResolveResult(null, "minidump: отказ — полный дамп памяти (Memory.dmp) не отправляется");
        }

        var fullPath = Path.GetFullPath(Path.Combine(minidumpDir, name));
        var expectedRoot = Path.GetFullPath(minidumpDir);
        if (!fullPath.StartsWith(expectedRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
            && !string.Equals(fullPath, expectedRoot, StringComparison.OrdinalIgnoreCase))
        {
            return new MinidumpUploadResolveResult(null, "minidump: путь вне SystemRoot\\Minidump");
        }

        if (!File.Exists(fullPath))
        {
            return new MinidumpUploadResolveResult(null, $"minidump: файл не найден: {name}");
        }

        long len;
        try
        {
            len = new FileInfo(fullPath).Length;
        }
        catch (Exception ex)
        {
            return new MinidumpUploadResolveResult(null, $"minidump: не удалось прочитать размер: {ex.Message}");
        }

        if (len > MaxUploadBytes)
        {
            return new MinidumpUploadResolveResult(null, $"minidump: отказ — файл больше {MaxUploadBytes / 1024 / 1024} МБ");
        }

        if (len == 0)
        {
            return new MinidumpUploadResolveResult(null, "minidump: пустой файл");
        }

        if (!IsProbablyMinidump(fullPath))
        {
            return new MinidumpUploadResolveResult(null, "minidump: отказ — не похож на минидамп (заголовок не MDMP)");
        }

        return new MinidumpUploadResolveResult(fullPath, null);
    }

    private static bool IsProbablyMinidump(string path)
    {
        var r = MinidumpBugcheck.TryRead(path);
        return r.Code is not null || r.Message is not null;
    }
}

public readonly record struct MinidumpUploadResolveResult(string? FilePath, string? RefusalReason);

public static class MinidumpHeartbeatUpload
{
    /// <summary>Один POST после heartbeat при непустом <paramref name="uploadRequest"/>.</summary>
    public static async Task RunAsync(
        BadApiClient client,
        string apiKey,
        string? uploadRequest,
        ILogger? logger,
        CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(uploadRequest))
        {
            return;
        }

        void LogWarn(string m)
        {
            if (logger is not null)
            {
                logger.LogWarning("{Msg}", m);
            }
            else
            {
                Console.Error.WriteLine(m);
            }
        }

        void LogInfo(string m)
        {
            if (logger is not null)
            {
                logger.LogInformation("{Msg}", m);
            }
            else
            {
                Console.WriteLine(m);
            }
        }

        var resolved = MinidumpUploadHelper.TryResolveUploadPath(uploadRequest);
        if (resolved.FilePath is null)
        {
            LogWarn(resolved.RefusalReason ?? "minidump: отказ");
            return;
        }

        var ok = await client.TryPostMinidumpAsync(apiKey, resolved.FilePath, ct);
        if (ok)
        {
            LogInfo($"minidump: отправлен {System.IO.Path.GetFileName(resolved.FilePath)}");
        }
        else
        {
            LogWarn("minidump: сервер не принял загрузку (404 или ошибка)");
        }
    }
}
