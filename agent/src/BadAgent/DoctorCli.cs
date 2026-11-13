using Microsoft.Extensions.Logging.Abstractions;

namespace BadAgent;

/// <summary>
/// Приводит файл настроек сломанного агента к значениям по умолчанию и проверяет связь.
/// </summary>
public static class DoctorCli
{
    public static int Run(string[] args)
    {
        if (args.Length == 1 && BadCli.IsHelpToken(args[0]))
        {
            Console.WriteLine("bad doctor               Починить настройки агента и проверить связь.");
            return 0;
        }

        if (args.Length > 0)
        {
            CliColumns.Write("Связь", "нет", "ошибка");
            return 1;
        }

        try
        {
            if (!File.Exists(ConfigStore.ConfigPath) || !ConfigStore.TryLoadForRead(out var config, out _))
            {
                AgentSigningKey.ClearLocal();
                CliColumns.Write("Ключ", "стёрт", "ok");
                CliColumns.Write("Связь", "нет", "ошибка");
                return 1;
            }

            var fresh = new AgentConfig
            {
                ServerUrl = config.ServerUrl ?? "",
                DeviceId = string.IsNullOrWhiteSpace(config.DeviceId) ? null : config.DeviceId,
                ApiKey = string.IsNullOrWhiteSpace(config.ApiKey) ? null : config.ApiKey,
            };
            ConfigStore.Save(fresh);
            AgentSigningKey.ClearLocal();
            CliColumns.Write("Настройки", "сброшены", "ok");
            CliColumns.Write("Ключ", "стёрт", "ok");

            if (!string.IsNullOrWhiteSpace(fresh.ApiKey))
            {
                TryInstallNewerMsi(fresh);
            }

            return PingCli.Run([]);
        }
        catch
        {
            CliColumns.Write("Связь", "нет", "ошибка");
            return 1;
        }
    }

    private static void TryInstallNewerMsi(AgentConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            return;
        }

        try
        {
            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            using var ct = new CancellationTokenSource(TimeSpan.FromMinutes(15));
            var updater = new AgentUpdater(NullLogger.Instance, agentVersion);
            var applying = updater.CheckAndApplyAsync(client, config, ct.Token).GetAwaiter().GetResult();
            if (applying)
            {
                Console.WriteLine(
                    "Установка MSI запланирована — через несколько секунд. " +
                    "Дождитесь перезапуска службы (не жмите Ctrl+C).");
            }
        }
        catch (Exception)
        {
            Console.Error.WriteLine("error: проверка обновлений не удалась");
        }
    }
}
