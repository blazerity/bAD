using System.Text;

namespace BadAgent;

/// <summary>
/// Запуск msiexec вне консоли <c>bad.cmd</c>.
/// Helper через .cmd + <c>Process.Start(UseShellExecute)</c> оставался в той же консоли —
/// Restart Manager → Ctrl+C → «Завершить выполнение пакетного файла».
/// </summary>
internal static class MsiexecLauncher
{
    private const int DelayMs = 3500;

    /// <summary>
    /// Пишет короткий .vbs в %TEMP%, стартует wscript detached, пауза, msiexec с /norestart.
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

        var dir = Path.Combine(Path.GetTempPath(), "bADagent-update");
        Directory.CreateDirectory(dir);
        var scriptPath = Path.Combine(dir, $"msiexec-{Guid.NewGuid():N}.vbs");

        var runCommand = BuildMsiexecRunCommand(msiexec, msiexecArguments);
        var vbs = new StringBuilder();
        vbs.AppendLine("' bAD: отложенный msiexec — консоль bad.cmd должна закрыться до установки");
        vbs.Append("WScript.Sleep ").Append(DelayMs).AppendLine();
        vbs.Append("CreateObject(\"WScript.Shell\").Run \"")
            .Append(EscapeVbsString(runCommand))
            .AppendLine("\", 0, False");
        vbs.AppendLine("On Error Resume Next");
        vbs.AppendLine("CreateObject(\"Scripting.FileSystemObject\").DeleteFile WScript.ScriptFullName, True");
        File.WriteAllText(scriptPath, vbs.ToString(), Encoding.ASCII);

        var wscript = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.System),
            "wscript.exe");
        var wscriptArgs = $"//B //Nologo \"{scriptPath}\"";

        if (!DetachedProcessStart.TryStart(wscript, wscriptArgs, logger))
        {
            logger?.LogError("Не удалось запустить detached wscript: {Script}", scriptPath);
            QuietFiles.TryDelete(scriptPath);
            return false;
        }

        logger?.LogInformation(
            "Запланирован отложенный msiexec (detached VBS {Script}): {Args}",
            scriptPath,
            msiexecArguments);
        return true;
    }

    private static string BuildMsiexecRunCommand(string msiexecPath, string msiexecArguments)
    {
        var args = msiexecArguments.Trim();
        if (!args.Contains("/norestart", StringComparison.OrdinalIgnoreCase)
            && !args.Contains("/promptrestart", StringComparison.OrdinalIgnoreCase))
        {
            args += " /norestart";
        }

        return $"\"{msiexecPath}\" {args}";
    }

    private static string EscapeVbsString(string value) =>
        value.Replace("\"", "\"\"");
}
