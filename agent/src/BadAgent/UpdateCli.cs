using Microsoft.Extensions.Logging.Abstractions;

namespace BadAgent;

/// <summary>
/// Проверка обновления агента на сервере и установка MSI при необходимости.
/// </summary>
public static class UpdateCli
{
    public static int Run(string[] args)
    {
        foreach (var arg in args)
        {
            if (BadCli.IsHelpToken(arg))
            {
                PrintHelp();
                return 0;
            }

            Console.Error.WriteLine($"error: неизвестный аргумент '{arg}'");
            PrintHelp();
            return 2;
        }

        return RunUpdate();
    }

    private static int RunUpdate()
    {
        try
        {
            var config = ConfigStore.LoadOrCreate();
            if (string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                CliColumns.Write(
                    "Обновление",
                    "не задан server_url. Укажите адрес сервера: bad -c или bad config set server_url <url>",
                    "ошибка");
                return 1;
            }

            if (string.IsNullOrWhiteSpace(config.ApiKey))
            {
                CliColumns.Write(
                    "Обновление",
                    "нет ключа. Ждите заявку в панели и кнопку «Разрешить».",
                    "ошибка");
                return 1;
            }

            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            using var ct = new CancellationTokenSource(TimeSpan.FromMinutes(15));
            var token = ct.Token;

            var logger = NullLogger.Instance;
            var updater = new AgentUpdater(logger, agentVersion);
            try
            {
                var applying = updater.CheckAndApplyAsync(client, config, token).GetAwaiter().GetResult();
                if (applying)
                {
                    CliColumns.Write("Обновление", "установка запланирована", "ok");
                    // Сразу выходим: bad.cmd должен завершиться до msiexec / Restart Manager.
                    Environment.Exit(0);
                }

                CliColumns.Write("Обновление", "не требуется", "без изменений");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                CliColumns.Write("Обновление", "API key отклонён (401/403) при проверке обновлений", "ошибка");
                return 1;
            }

            Console.WriteLine("Готово");
            return 0;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            CliColumns.Write("Обновление", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
            return 1;
        }
        catch (Exception ex)
        {
            CliColumns.Write("Обновление", $"проверка обновлений не удалась: {ex.Message}", "ошибка");
            return 1;
        }
    }

    public static void PrintHelp()
    {
        Console.WriteLine("""
Проверка и установка обновления агента с сервера bAD:
  bad update               Сверка версии и silent MSI при необходимости

Нужны server_url и api_key в config.json (см. bad -c).
""");
    }
}
