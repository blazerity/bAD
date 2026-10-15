using BadAgent;
using Microsoft.Extensions.Hosting.WindowsServices;
using Serilog;

// Elevated управление службой: BadAgent.exe service status|start|stop|restart
if (args.Length > 0 && string.Equals(args[0], "service", StringComparison.OrdinalIgnoreCase))
{
    return ServiceCli.Run(args.AsSpan(1).ToArray());
}

// Интерактивный CLI (bad / BadAgent.exe из консоли): отчёты, справка — не хост Windows Service.
// SCM стартует процесс как Windows service; этот путь не менять.
// На non-Windows (Linux CI / `dotnet run`) по умолчанию остаётся hosted Worker, пока CLI-аргументы не явные.
if (ShouldRunCli(args))
{
    return BadCli.Run(args);
}

Directory.CreateDirectory(ConfigStore.LogsDir);

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .WriteTo.Console()
    .WriteTo.File(
        Path.Combine(ConfigStore.LogsDir, "bad-agent-.log"),
        rollingInterval: RollingInterval.Day,
        retainedFileCountLimit: 7)
    .CreateLogger();

try
{
    var builder = Host.CreateApplicationBuilder(args);
    builder.Services.AddWindowsService(options =>
    {
        options.ServiceName = ServiceCli.ServiceName;
    });
    builder.Services.AddSerilog();
    builder.Services.AddSingleton<IInventoryCollector, InventoryCollector>();
    builder.Services.AddHostedService<Worker>();

    var host = builder.Build();
    host.Run();
    return 0;
}
catch (Exception ex)
{
    Log.Fatal(ex, "Agent terminated unexpectedly");
    throw;
}
finally
{
    Log.CloseAndFlush();
}

/// <summary>
/// True, если процесс запущен как интерактивный инструмент (консоль), а не SCM.
/// </summary>
static bool ShouldRunCli(string[] args)
{
    if (args.Length > 0)
    {
        if (BadCli.IsExplicitCliArg(args[0]))
        {
            return true;
        }

        // Неизвестный первый аргумент в интерактивной Windows-консоли → всё равно CLI (help/error).
        if (OperatingSystem.IsWindows() && Environment.UserInteractive
            && !WindowsServiceHelpers.IsWindowsService())
        {
            return true;
        }

        return false;
    }

    // Без аргументов: интерактивная Windows-консоль → ASCII-отчёт; иначе service/worker host.
    if (WindowsServiceHelpers.IsWindowsService())
    {
        return false;
    }

    return OperatingSystem.IsWindows() && Environment.UserInteractive;
}
