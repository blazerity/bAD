namespace BadAgent;

/// <summary>
/// Interactive local CLI (<c>bad</c> / BadAgent.exe when not running as Windows Service).
/// Collects inventory locally — does not require server connectivity.
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

    /// <summary>First-arg verbs/flags that always take the local report CLI path (not the service host).</summary>
    public static bool IsExplicitCliArg(string arg) =>
        arg is "-?" or "--help" or "help" or "/?"
            or "-h" or "--html" or "html"
            or "report" or "info" or "ascii";

    private static bool IsHelp(string[] args) =>
        args.Length > 0 && args[0] is "-?" or "--help" or "help" or "/?";

    private static bool IsAsciiCommand(string cmd) =>
        cmd is "report" or "info" or "ascii";

    private static bool IsHtml(string[] args, out string? pathArg)
    {
        pathArg = null;
        if (args.Length == 0)
        {
            return false;
        }

        var a0 = args[0];
        if (a0 is "-h" or "--html" or "html")
        {
            pathArg = args.Length > 1 ? args[1] : null;
            return true;
        }

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
  bad                  Локальный ASCII-отчёт inventory (то же: bad report | bad info)
  bad -h [path]        HTML-отчёт (то же: bad --html [path])
  bad -?               Эта справка (то же: bad --help)

Путь для HTML:
  без path             Рабочий стол пользователя: bad_report_yyyyMMdd_HHmmss.html
  каталог              Файл с именем по умолчанию в каталоге
  файл                 Указанное имя (добавляется .html при необходимости)

Служба Windows (elevated):
  bad service status|start|stop|restart

Заметки:
  Сбор локальный — сервер не требуется. Учитываются collect_* из config.json.
  Код выхода: 0 — успех, иначе ошибка.
""");
    }
}
