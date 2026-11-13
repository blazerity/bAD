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

            if (IsInfoCommand(args))
            {
                return RunInfo(args, collector);
            }

            if (IsHtml(args, out var htmlPathArg))
            {
                return RunHtml(htmlPathArg, collector);
            }

            if (IsPushCommand(args, out var pushRest))
            {
                return PushCli.Run(pushRest);
            }

            if (IsPingCommand(args, out var pingRest))
            {
                return PingCli.Run(pingRest);
            }

            if (IsDoctorCommand(args, out var doctorRest))
            {
                return DoctorCli.Run(doctorRest);
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

    public static bool IsHelpToken(string s) =>
        s is "-h" or "--help" or "-?" or "/?" or "help";

    /// <summary>Глаголы/флаги первого аргумента: всегда локальный report CLI (не service host).</summary>
    public static bool IsExplicitCliArg(string arg) =>
        IsHelpToken(arg)
            || arg is "-c" or "--configure"
            or "-r" or "--report" or "--html" or "html"
            or "report" or "info" or "ascii"
            or "config" or "settings"
            or "push"
            or "ping"
            or "doctor"
            or "update"
            or "uninstall" or "unistall";

    private static bool IsHelp(string[] args) =>
        args.Length > 0 && IsHelpToken(args[0]);

    private static bool IsInteractiveConfig(string[] args) =>
        args.Length > 0 && args[0] is "-c" or "--configure";

    private static bool IsAsciiCommand(string cmd) =>
        cmd is "report" or "ascii";

    private static bool IsInfoCommand(string[] args) =>
        args.Length > 0 && args[0] == "info";

    private static bool TakeCommand(
        string[] args, out string[] rest, StringComparison comparison, params string[] verbs)
    {
        if (args.Length > 0)
        {
            foreach (var verb in verbs)
            {
                if (string.Equals(args[0], verb, comparison))
                {
                    rest = args.AsSpan(1).ToArray();
                    return true;
                }
            }
        }

        rest = [];
        return false;
    }

    private static bool IsConfigCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.Ordinal, "config", "settings");

    private static bool IsPushCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.OrdinalIgnoreCase, "push");

    private static bool IsPingCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.OrdinalIgnoreCase, "ping");

    private static bool IsDoctorCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.OrdinalIgnoreCase, "doctor");

    private static bool IsUpdateCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.OrdinalIgnoreCase, "update");

    // unistall — частая опечатка
    private static bool IsUninstallCommand(string[] args, out string[] rest) =>
        TakeCommand(args, out rest, StringComparison.OrdinalIgnoreCase, "uninstall", "unistall");

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

    private static int RunInfo(string[] args, IInventoryCollector? collector)
    {
        if (args.Length > 1)
        {
            if (args.Skip(1).All(IsHelpToken))
            {
                PrintInfoHelp();
                return 0;
            }

            PrintHelp();
            return 2;
        }

        var (snap, config) = Collect(collector);
        CliColumns.Write("Версия", VersionUtil.GetAgentVersion());
        CliColumns.Write("Сервер", config.ServerUrl);
        CliColumns.Write("Hostname", snap.Host?.Hostname);
        CliColumns.Write("device_id", snap.DeviceId);
        CliColumns.Write("Модель", snap.Hardware?.Model);
        return 0;
    }

    private static void PrintInfoHelp()
    {
        Console.WriteLine("bad info                 Версия, сервер, имя, device_id, модель");
    }

    private static int RunHtml(string? pathArg, IInventoryCollector? collector)
    {
        var (snap, config) = Collect(collector);
        var path = ReportPathResolver.ResolveHtmlPath(pathArg, DateTime.Now);
        try
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            if (!string.IsNullOrWhiteSpace(config.ServerUrl) && !string.IsNullOrWhiteSpace(config.ApiKey))
            {
                try
                {
                    var version = VersionUtil.GetAgentVersion();
                    using var client = new BadApiClient(config.ServerUrl, version);
                    using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(3));
                    var serverHtml = client.TryPostReportHtmlAsync(config.ApiKey!, snap, cts.Token)
                        .GetAwaiter()
                        .GetResult();
                    if (!string.IsNullOrEmpty(serverHtml))
                    {
                        File.WriteAllText(path, serverHtml);
                        CliColumns.Write("Отчёт", path, "ok");
                        return 0;
                    }
                }
                catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
                {
                    CliColumns.Write("Отчёт", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
                    return 1;
                }
                catch
                {
                    // Сервер без маршрута / не HTML / сеть — локальный HtmlReportWriter.
                }
            }

            var html = HtmlReportWriter.Write(snap, config);
            File.WriteAllText(path, html);
            CliColumns.Write("Отчёт", path, "ok");
            return 0;
        }
        catch (Exception ex)
        {
            CliColumns.Write("Отчёт", ex.Message, "ошибка");
            return 1;
        }
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
Использование: bad <команда>

Отчёт
  bad                      Локальный отчёт inventory
  bad info                 Версия, сервер, имя, device_id, модель
  bad -r [path]            HTML-отчёт

Сервер
  bad -c                   Настройка агента
  bad config               Показать настройки
  bad config set <ключ> <значение>   Один параметр
  bad push                 Очередь, снимок, heartbeat
  bad ping                 Проверка связи
  bad doctor               Сброс настроек и проверка связи
  bad update               Проверка версии и установка

Служба
  bad service status       Состояние службы badagent
  bad service start        Запуск
  bad service stop         Остановка
  bad service restart      Перезапуск
  bad uninstall [-y]       Снять агент
""");
    }
}
