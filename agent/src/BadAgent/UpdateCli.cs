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
            if (IsHelpToken(arg))
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
                Console.Error.WriteLine(
                    "error: не задан server_url. Укажите адрес сервера: bad -c или bad config set server_url <url>");
                return 1;
            }

            if (string.IsNullOrWhiteSpace(config.ApiKey))
            {
                Console.Error.WriteLine(
                    "error: нет api_key — устройство не зарегистрировано. " +
                    "Нужен enrollment через MSI или enroll на сервере.");
                return 1;
            }

            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            using var ct = new CancellationTokenSource(TimeSpan.FromMinutes(15));
            var token = ct.Token;

            Console.WriteLine("Проверка обновлений на сервере…");
            var logger = NullLogger.Instance;
            var updater = new AgentUpdater(logger, agentVersion);
            try
            {
                var applying = updater.CheckAndApplyAsync(client, config, token).GetAwaiter().GetResult();
                if (applying)
                {
                    Console.WriteLine(
                        "Установка MSI запланирована — через несколько секунд. " +
                        "Дождитесь перезапуска службы (не жмите Ctrl+C).");
                    // Сразу выходим: bad.cmd должен завершиться до msiexec / Restart Manager.
                    Environment.Exit(0);
                }

                Console.WriteLine("Обновление не требуется или отключено в конфиге.");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                Console.Error.WriteLine("error: API key отклонён (401/403) при проверке обновлений");
                return 1;
            }

            Console.WriteLine("Готово.");
            return 0;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            Console.Error.WriteLine($"error: {ServerUrlRules.CleartextHttpRejectedMessage}");
            return 1;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"error: проверка обновлений не удалась: {ex.Message}");
            return 1;
        }
    }

    private static bool IsHelpToken(string s) =>
        s is "-h" or "--help" or "-?" or "/?" or "help";

    public static void PrintHelp()
    {
        Console.WriteLine("""
Проверка и установка обновления агента с сервера bAD:
  bad update               Сверка версии и silent MSI при необходимости

Нужны server_url и api_key в config.json (см. bad -c).
""");
    }
}
