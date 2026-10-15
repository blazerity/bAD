using BadAgent;
using Microsoft.Extensions.Hosting.WindowsServices;
using Serilog;

// Elevated service control: BadAgent.exe service status|start|stop|restart
if (args.Length > 0 && string.Equals(args[0], "service", StringComparison.OrdinalIgnoreCase))
{
    return ServiceCli.Run(args.AsSpan(1).ToArray());
}

// Interactive CLI (bad / BadAgent.exe from console): reports, help — not the Windows Service host.
// SCM starts the process as a Windows service; keep that path unchanged.
// On non-Windows (Linux CI / `dotnet run`), default remains the hosted Worker unless CLI args are explicit.
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
/// True when the process was started as an interactive tool (console), not by the SCM.
/// </summary>
static bool ShouldRunCli(string[] args)
{
    // Explicit CLI verbs/flags always take the report path.
    if (args.Length > 0)
    {
        var a0 = args[0];
        if (a0 is "-?" or "--help" or "help" or "/?"
            or "-h" or "--html" or "html"
            or "report" or "info" or "ascii")
        {
            return true;
        }

        // Unknown first arg on an interactive Windows console → still CLI (shows help/error).
        if (OperatingSystem.IsWindows() && Environment.UserInteractive
            && !WindowsServiceHelpers.IsWindowsService())
        {
            return true;
        }

        return false;
    }

    // No args: Windows interactive console → ASCII report; otherwise service/worker host.
    if (WindowsServiceHelpers.IsWindowsService())
    {
        return false;
    }

    return OperatingSystem.IsWindows() && Environment.UserInteractive;
}
