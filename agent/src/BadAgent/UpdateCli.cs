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

        var reply = ServiceChannel.Call(new { op = "update" });
        if (reply is null)
        {
            ServiceChannel.ServiceDown();
            return 1;
        }

        return ServiceChannel.Print(reply);
    }

    internal static CliOutcome Execute()
    {
        var outcome = new CliOutcome();
        try
        {
            var config = ConfigStore.LoadOrCreate();
            if (string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                outcome.Line(
                    "Обновление",
                    "не задан server_url. Укажите адрес сервера: bad -c или bad config set server_url <url>",
                    "ошибка");
                outcome.ExitCode = 1;
                return outcome;
            }

            if (string.IsNullOrWhiteSpace(config.ApiKey))
            {
                outcome.Line(
                    "Обновление",
                    "нет ключа. Ждите заявку в панели и кнопку «Разрешить».",
                    "ошибка");
                outcome.ExitCode = 1;
                return outcome;
            }

            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            using var ct = new CancellationTokenSource(TimeSpan.FromMinutes(15));
            var logger = NullLogger.Instance;
            var updater = new AgentUpdater(logger, agentVersion);
            try
            {
                var applying = updater.CheckAndApplyAsync(client, config, ct.Token).GetAwaiter().GetResult();
                if (applying)
                {
                    outcome.Line("Обновление", "установка запланирована", "ok");
                    outcome.StopAfterReply = true;
                    return outcome;
                }

                outcome.Line("Обновление", "не требуется", "без изменений");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                if (InvalidKeyReset.IsInvalidApiKey(ex))
                {
                    InvalidKeyReset.Forget(config, client, CancellationToken.None);
                }

                outcome.KeyRejected = true;
                outcome.Line("Обновление", "API key отклонён (401/403) при проверке обновлений", "ошибка");
                outcome.ExitCode = 1;
                return outcome;
            }

            outcome.Tail.Add("Готово");
            return outcome;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            outcome.Line("Обновление", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }
        catch (Exception ex)
        {
            outcome.Line("Обновление", $"проверка обновлений не удалась: {ex.Message}", "ошибка");
            outcome.ExitCode = 1;
            return outcome;
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
