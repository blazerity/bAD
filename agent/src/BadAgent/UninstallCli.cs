namespace BadAgent;

/// <summary>
/// Локальное снятие агента: <c>bad uninstall</c> / <c>bin\uninstall.cmd</c> → msiexec /x.
/// </summary>
public static class UninstallCli
{
    public static int Run(string[] args)
    {
        var yes = args.Any(a =>
            a is "-y" or "--yes" or "/y" or "/Y");
        var help = args.Any(a =>
            a is "-h" or "--help" or "-?" or "/?" or "help");
        if (help)
        {
            PrintHelp();
            return 0;
        }

        var elevated = WindowsElevation.RequireElevatedOrExit("снятия агента bAD");
        if (elevated != 0)
        {
            return elevated;
        }

        if (!OperatingSystem.IsWindows())
        {
            Console.Error.WriteLine("error: снятие агента поддерживается только на Windows.");
            return 1;
        }

        var productCode = AgentUninstaller.TryFindInstalledProductCode();
        if (productCode is null)
        {
            Console.Error.WriteLine(
                "error: установка MSI bAD не найдена в реестре (уже снята или ставилась не через MSI).");
            return 1;
        }

        if (!yes)
        {
            Console.WriteLine("Будет выполнено снятие агента bAD (служба badagent + файлы в Program Files).");
            Console.WriteLine("Каталог %ProgramData%\\blazerity\\bAD\\ (config, очередь, логи) также будет очищен.");
            Console.Write("Продолжить? [y/N]: ");
            var answer = (Console.ReadLine() ?? "").Trim();
            if (!answer.Equals("y", StringComparison.OrdinalIgnoreCase)
                && !answer.Equals("yes", StringComparison.OrdinalIgnoreCase)
                && !answer.Equals("д", StringComparison.OrdinalIgnoreCase)
                && !answer.Equals("да", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine("Отменено.");
                return 0;
            }
        }

        Console.WriteLine($"Планируется msiexec /x {productCode} …");
        if (!AgentUninstaller.TryStartSilentUninstall(msg => Console.WriteLine(msg)))
        {
            Console.Error.WriteLine("error: не удалось запустить msiexec для снятия.");
            return 1;
        }

        Console.WriteLine(
            "Снятие запланировано через несколько секунд. Закройте это окно или дождитесь выхода " +
            "(не жмите Ctrl+C).");
        Environment.Exit(0);
        return 0;
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""
Использование:
  bad uninstall           Снять агент (нужны права администратора, с подтверждением)
  bad uninstall -y        Без подтверждения
  bad uninstall -h        Эта справка

Также: bin\uninstall.cmd (тот же вызов).
""");
    }
}
