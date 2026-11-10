namespace BadAgent;

/// <summary>
/// Одна проверка связи: heartbeat без действий из ответа.
/// </summary>
public static class PingCli
{
    public static int Run(string[] args)
    {
        if (args.Length == 1 && BadCli.IsHelpToken(args[0]))
        {
            Console.WriteLine("bad ping                 Проверка связи с сервером.");
            return 0;
        }

        if (args.Length > 0)
        {
            Console.WriteLine("Связи нет.");
            return 1;
        }

        try
        {
            if (!ConfigStore.TryLoadForRead(out var config, out _))
            {
                Console.WriteLine("Связи нет.");
                return 1;
            }

            if (string.IsNullOrWhiteSpace(config.ServerUrl)
                || string.IsNullOrWhiteSpace(config.ApiKey)
                || string.IsNullOrWhiteSpace(config.DeviceId))
            {
                Console.WriteLine("Связи нет.");
                return 1;
            }

            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            _ = client.SendHeartbeatAsync(
                config.ApiKey,
                new HeartbeatQueuePayload { DeviceId = config.DeviceId },
                cts.Token).GetAwaiter().GetResult();
            Console.WriteLine("Связь есть.");
            return 0;
        }
        catch
        {
            Console.WriteLine("Связи нет.");
            return 1;
        }
    }
}
