using BadAgent;
using Serilog;

// CLI: BadAgent.exe service status|start|stop|restart (elevated). Otherwise run Windows Service host.
if (args.Length > 0 && string.Equals(args[0], "service", StringComparison.OrdinalIgnoreCase))
{
    return ServiceCli.Run(args.AsSpan(1).ToArray());
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
