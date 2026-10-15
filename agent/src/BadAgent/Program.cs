using BadAgent;
using Serilog;

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
        options.ServiceName = "BlazerityAssetDiscovery";
    });
    builder.Services.AddSerilog();
    builder.Services.AddSingleton<IInventoryCollector, InventoryCollector>();
    builder.Services.AddHostedService<Worker>();

    var host = builder.Build();
    host.Run();
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
