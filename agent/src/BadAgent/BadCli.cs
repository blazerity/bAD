namespace BadAgent;

/// <summary>
/// Локальный интерактивный CLI (<c>bad</c> / BadAgent.exe вне Windows Service).
/// Сбор inventory локально — сервер не нужен.
/// </summary>
public static class BadCli
{
    public static int Run(string[] args, IInventoryCollector? collector = null)
    {
        try
        {
            if (IsHelp(args))
            {
                PrintHelp();
                return 0;
            }

            if (IsInteractiveConfig(args))
            {
                return ConfigCli.RunInteractive();
            }

            if (IsConfigCommand(args, out var configArgs))
            {
                return ConfigCli.Run(configArgs);
            }

            if (IsHtml(args, out var htmlPathArg))
            {
                return RunHtml(htmlPathArg, collector);
            }

            if (IsPushCommand(args, out var pushRest))
            {
                return PushCli.Run(pushRest);
            }

            if (IsUpdateCommand(args, out var updateRest))
            {
                return UpdateCli.Run(updateRest);
            }

            if (IsUninstallCommand(args, out var uninstallRest))
            {
                return UninstallCli.Run(uninstallRest);
            }

            if (args.Length == 0 || IsAsciiCommand(args[0]))
            {
                return RunAscii(collector);
            }

            Console.Error.WriteLine($"error: неизвестная команда '{args[0]}'");
            PrintHelp();
            return 2;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"error: {ex.Message}");
            return 1;
        }
    }

    /// <summary>Глаголы/флаги первого аргумента: всегда локальный report CLI (не service host).</summary>
    public static bool IsExplicitCliArg(string arg) =>
        arg is "-?" or "--help" or "help" or "/?" or "-h"
            or "-c" or "--configure"
            or "-r" or "--report" or "--html" or "html"
            or "report" or "info" or "ascii"
            or "config" or "settings"
            or "push"
            or "update"
            or "uninstall" or "unistall";

    private static bool IsHelp(string[] args) =>
        args.Length > 0 && args[0] is "-?" or "--help" or "help" or "/?" or "-h";

    private static bool IsInteractiveConfig(string[] args) =>
        args.Length > 0 && args[0] is "-c" or "--configure";

    private static bool IsAsciiCommand(string cmd) =>
        cmd is "report" or "info" or "ascii";

    private static bool IsConfigCommand(string[] args, out string[] rest)
    {
        if (args.Length > 0 && args[0] is "config" or "settings")
        {
            rest = args.AsSpan(1).ToArray();
            return true;
        }

        rest = [];
        return false;
    }

    private static bool IsPushCommand(string[] args, out string[] rest)
    {
        if (args.Length > 0 && string.Equals(args[0], "push", StringComparison.OrdinalIgnoreCase))
        {
            rest = args.AsSpan(1).ToArray();
            return true;
        }

        rest = [];
        return false;
    }

    private static bool IsUpdateCommand(string[] args, out string[] rest)
    {
        if (args.Length > 0 && string.Equals(args[0], "update", StringComparison.OrdinalIgnoreCase))
        {
            rest = args.AsSpan(1).ToArray();
            return true;
        }

        rest = [];
        return false;
    }

    private static bool IsUninstallCommand(string[] args, out string[] rest)
    {
        // unistall — частая опечатка
        if (args.Length > 0
            && (string.Equals(args[0], "uninstall", StringComparison.OrdinalIgnoreCase)
                || string.Equals(args[0], "unistall", StringComparison.OrdinalIgnoreCase)))
        {
            rest = args.AsSpan(1).ToArray();
            return true;
        }

        rest = [];
        return false;
    }

    private static bool IsHtml(string[] args, out string? pathArg)
    {
        // -r/--report — канон; --html/html — совместимость со старыми примерами
        if (args.Length > 0 && args[0] is "-r" or "--report" or "--html" or "html")
        {
            pathArg = args.Length > 1 ? args[1] : null;
            return true;
        }

        pathArg = null;
        return false;
    }

    private static int RunAscii(IInventoryCollector? collector)
    {
        var (snap, config) = Collect(collector);
        Console.Write(AsciiReportWriter.Write(snap, config));
        return 0;
    }

    private static int RunHtml(string? pathArg, IInventoryCollector? collector)
    {
        var (snap, config) = Collect(collector);
        var html = HtmlReportWriter.Write(snap, config);
        var path = ReportPathResolver.ResolveHtmlPath(pathArg, DateTime.Now);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        File.WriteAllText(path, html);
        Console.WriteLine($"HTML-отчёт записан: {path}");
        return 0;
    }

    private static (InventorySnapshot Snap, AgentConfig Config) Collect(IInventoryCollector? collector)
    {
        var config = ConfigStore.LoadForReport();
        var deviceId = string.IsNullOrWhiteSpace(config.DeviceId)
            ? DeviceIdentity.ResolveDeviceId()
            : config.DeviceId;
        config.DeviceId = deviceId;

        var version = VersionUtil.GetAgentVersion();
        var options = CollectorOptions.FromConfig(config);
        var c = collector ?? new InventoryCollector();
        var snap = c.Collect(deviceId, version, options);
        return (snap, config);
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""
Использование:
  bad                      Локальный ASCII-отчёт inventory
  bad -r [path]            HTML-отчёт
  bad -c                   Интерактивная настройка агента
  bad -h                   Справка
  bad config               Показать настройки (api_key / enrollment_token не печатаются)
  bad config set <k> <v>   Один параметр (server_url в бою — https://)
  bad push                 Синхронизация с сервером: очередь → inventory → heartbeat
  bad update               Проверка версии на сервере и установка MSI при необходимости
  bad uninstall [-y]       Снять агент (msiexec, нужны права администратора)
  bad service …            Управление службой Windows (от администратора)

HTML (-r): без path — рабочий стол, bad_report_yyyyMMdd_HHmmss.html

Служба:
  bad service status|start|stop|restart

Снятие также: bin\uninstall.cmd
""");
    }
}
