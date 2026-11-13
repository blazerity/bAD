using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text;

namespace BadAgent;

/// <summary>Проверка elevated (Administrator) для CLI, меняющего config или службу.</summary>
public static class WindowsElevation
{
    [SupportedOSPlatform("windows")]
    public static bool IsElevated()
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        using var identity = WindowsIdentity.GetCurrent();
        var principal = new WindowsPrincipal(identity);
        return principal.IsInRole(WindowsBuiltInRole.Administrator);
    }

    /// <summary>Вопрос, при согласии — перезапуск с runas. Саму команду не выполняет.</summary>
    public static int OfferRunAsAdmin()
    {
        Console.Write("Запустить от администратора? [y/N]: ");
        var answer = (Console.ReadLine() ?? "").Trim();
        if (!IsAffirmative(answer))
        {
            CliColumns.Write("Запуск", "отменено", "без изменений");
            return 0;
        }

        if (!OperatingSystem.IsWindows())
        {
            Console.Error.WriteLine(
                "error: изменение конфигурации поддерживается только на Windows с правами администратора.");
            return 1;
        }

        try
        {
            var exe = Environment.ProcessPath;
            if (string.IsNullOrWhiteSpace(exe))
            {
                CliColumns.Write("Запуск", "не найден путь к исполняемому файлу", "ошибка");
                return 1;
            }

            var args = Environment.GetCommandLineArgs();
            var argumentLine = args.Length > 1
                ? string.Join(" ", args.Skip(1).Select(QuoteWin32Argument))
                : "";

            var psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = argumentLine,
                UseShellExecute = true,
                Verb = "runas"
            };

            using var process = Process.Start(psi);
            if (process is null)
            {
                CliColumns.Write("Запуск", "не удалось запустить процесс", "ошибка");
                return 1;
            }

            process.WaitForExit();
            return process.ExitCode;
        }
        catch (Win32Exception ex) when (ex.NativeErrorCode == 1223)
        {
            CliColumns.Write("Запуск", "отменено", "без изменений");
            return 0;
        }
        catch (Win32Exception ex)
        {
            CliColumns.Write("Запуск", ex.Message, "ошибка");
            return 1;
        }
    }

    private static bool IsAffirmative(string answer) =>
        answer.Equals("y", StringComparison.OrdinalIgnoreCase)
        || answer.Equals("yes", StringComparison.OrdinalIgnoreCase)
        || answer.Equals("д", StringComparison.OrdinalIgnoreCase)
        || answer.Equals("да", StringComparison.OrdinalIgnoreCase);

    private static string QuoteWin32Argument(string arg)
    {
        if (arg.Length == 0)
        {
            return "\"\"";
        }

        if (!arg.Contains(' ') && !arg.Contains('"') && !arg.Contains('\t'))
        {
            return arg;
        }

        var sb = new StringBuilder();
        sb.Append('"');
        foreach (var ch in arg)
        {
            sb.Append(ch == '"' ? "\\\"" : ch);
        }

        sb.Append('"');
        return sb.ToString();
    }
}
