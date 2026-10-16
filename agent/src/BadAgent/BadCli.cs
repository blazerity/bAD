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
            or "config" or "settings";

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
        var config = ConfigStore.LoadOrCreate();
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
Использование / Usage:
  bad                      Локальный ASCII-отчёт inventory (то же: bad report | bad info)
  bad -r [path]            HTML-отчёт (то же: bad --report [path]; устар. --html)
  bad -c                   Интерактивная настройка агента (рекомендуется)
  bad -h                   Эта справка (то же: bad --help | bad -?)
  bad config               Показать текущие настройки (без секретов)
  bad config set <k> <v>   Power-user: изменить один параметр

Путь для HTML (-r):
  без path                 Рабочий стол: bad_report_yyyyMMdd_HHmmss.html
  каталог                  Файл с именем по умолчанию в каталоге
  файл                     Указанное имя (добавляется .html при необходимости)

Служба Windows (elevated):
  bad service status|start|stop|restart
""");
    }
}
