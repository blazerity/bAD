using System.Runtime.Versioning;
using System.ServiceProcess;

namespace BadAgent;

/// <summary>
/// Elevated CLI для Windows-службы <c>badagent</c>.
/// Usage: BadAgent.exe service status|start|stop|restart
/// </summary>
public static class ServiceCli
{
    public const string ServiceName = "badagent";

    public static int Run(string[] args)
    {
        if (args.Length == 0)
        {
            PrintUsage();
            return 2;
        }

        var cmd = args[0].Trim().ToLowerInvariant();
        if (cmd is "start" or "stop" or "restart" && !WindowsElevation.IsElevated())
        {
            return WindowsElevation.OfferRunAsAdmin();
        }

        try
        {
            return cmd switch
            {
                "status" => Status(),
                "start" => Start(),
                "stop" => Stop(),
                "restart" => Restart(),
                "help" or "-h" or "--help" or "-?" or "/?" => PrintUsage(),
                _ => Unknown(cmd)
            };
        }
        catch (InvalidOperationException ex)
        {
            CliColumns.Write("Служба", ex.Message, "ошибка");
            return 1;
        }
        catch (System.ComponentModel.Win32Exception ex)
        {
            CliColumns.Write("Служба", ex.Message, "ошибка");
            return 1;
        }
        catch (PlatformNotSupportedException ex)
        {
            CliColumns.Write("Служба", ex.Message, "ошибка");
            return 1;
        }
    }

    private static int Unknown(string cmd)
    {
        Console.Error.WriteLine($"error: unknown service command '{cmd}'");
        PrintUsage();
        return 2;
    }

    private static int PrintUsage()
    {
        Console.WriteLine("""
bad service status       Состояние службы badagent
bad service start        Запуск
bad service stop         Остановка
bad service restart      Перезапуск
""");
        return 0;
    }

    [SupportedOSPlatform("windows")]
    private static ServiceController Open()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Service control is only supported on Windows.");
        }

        return new ServiceController(ServiceName);
    }

    private static int Status()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Service control is only supported on Windows.");
        }

        using var sc = Open();
        sc.Refresh();
        CliColumns.Write("Служба", ServiceName, "ok");
        CliColumns.Write("Состояние", sc.Status.ToString());
        return 0;
    }

    private static int Start()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Service control is only supported on Windows.");
        }

        using var sc = Open();
        sc.Refresh();
        if (sc.Status is ServiceControllerStatus.Running or ServiceControllerStatus.StartPending)
        {
            CliColumns.Write("Служба", ServiceName, "без изменений");
            CliColumns.Write("Состояние", sc.Status.ToString());
            return 0;
        }

        sc.Start();
        sc.WaitForStatus(ServiceControllerStatus.Running, TimeSpan.FromSeconds(60));
        CliColumns.Write("Служба", ServiceName, "ok");
        CliColumns.Write("Состояние", sc.Status.ToString());
        return 0;
    }

    private static int Stop()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Service control is only supported on Windows.");
        }

        using var sc = Open();
        sc.Refresh();
        if (sc.Status is ServiceControllerStatus.Stopped or ServiceControllerStatus.StopPending)
        {
            CliColumns.Write("Служба", ServiceName, "без изменений");
            CliColumns.Write("Состояние", sc.Status.ToString());
            return 0;
        }

        sc.Stop();
        sc.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(60));
        CliColumns.Write("Служба", ServiceName, "ok");
        CliColumns.Write("Состояние", sc.Status.ToString());
        return 0;
    }

    private static int Restart()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Service control is only supported on Windows.");
        }

        using var sc = Open();
        sc.Refresh();
        if (sc.Status is not (ServiceControllerStatus.Stopped or ServiceControllerStatus.StopPending))
        {
            sc.Stop();
            sc.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(60));
        }

        sc.Refresh();
        sc.Start();
        sc.WaitForStatus(ServiceControllerStatus.Running, TimeSpan.FromSeconds(60));
        CliColumns.Write("Служба", ServiceName, "ok");
        CliColumns.Write("Состояние", sc.Status.ToString());
        return 0;
    }
}
