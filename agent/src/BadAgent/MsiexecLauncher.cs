using System.Diagnostics;
using System.Text;

namespace BadAgent;

/// <summary>
/// Запуск msiexec вне консоли <c>bad.cmd</c>.
/// Иначе Restart Manager шлёт CTRL+C в консоль → «Завершить выполнение пакетного файла (Y/N)?»
/// и установка обрывается.
/// </summary>
internal static class MsiexecLauncher
{
    /// <summary>
    /// Пишет короткий .cmd в %TEMP%, стартует его скрыто (без привязки к текущей консоли),
    /// ждёт несколько секунд, затем вызывает msiexec — чтобы BadAgent / bad.cmd успели выйти.
    /// </summary>
    public static bool StartDelayedDetached(string msiexecArguments, ILogger? logger = null)
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        var msiexec = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.System),
            "msiexec.exe");
        if (!File.Exists(msiexec))
        {
            logger?.LogError("msiexec.exe не найден: {Path}", msiexec);
            return false;
        }

        var dir = Path.Combine(Path.GetTempPath(), "bad-agent-update");
        Directory.CreateDirectory(dir);
        var helperPath = Path.Combine(dir, $"msiexec-{Guid.NewGuid():N}.cmd");

        // ping ≈ пауза без timeout.exe (есть не везде / может ждать подтверждения).
        var sb = new StringBuilder();
        sb.AppendLine("@echo off");
        sb.AppendLine("rem bAD: отложенный msiexec — bad.cmd должен завершиться до замены файлов");
        sb.AppendLine("ping -n 4 127.0.0.1 >nul");
        sb.AppendLine($"\"{msiexec}\" {msiexecArguments}");
        sb.AppendLine("del \"%~f0\" >nul 2>&1");
        File.WriteAllText(helperPath, sb.ToString(), Encoding.ASCII);

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.System),
                    "cmd.exe"),
                Arguments = $"/d /c \"{helperPath}\"",
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Hidden,
                WorkingDirectory = dir,
                ErrorDialog = false
            };

            if (Process.Start(psi) is null)
            {
                logger?.LogError("Не удалось запустить helper msiexec: {Helper}", helperPath);
                TryDelete(helperPath);
                return false;
            }

            logger?.LogInformation(
                "Запланирован отложенный msiexec через {Helper}: {Args}",
                helperPath,
                msiexecArguments);
            return true;
        }
        catch (Exception ex)
        {
            logger?.LogError(ex, "Ошибка запуска helper msiexec");
            TryDelete(helperPath);
            return false;
        }
    }

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch
        {
            // best-effort
        }
    }
}
