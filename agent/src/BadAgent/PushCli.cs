namespace BadAgent;

/// <summary>
/// Принудительная отправка на сервер: очередь → inventory → heartbeat.
/// </summary>
public static class PushCli
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

            if (string.Equals(arg, "--update", StringComparison.Ordinal))
            {
                Console.Error.WriteLine(
                    "error: флаг --update снят; для обновления агента используйте: bad update");
                return 2;
            }

            Console.Error.WriteLine($"error: неизвестный аргумент '{arg}'");
            PrintHelp();
            return 2;
        }

        var reply = ServiceChannel.Call(new { op = "push" });
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

            CliOutcome Fail()
            {
                outcome.ExitCode = 1;
                return outcome;
            }

            if (string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                outcome.Line(
                    "Сервер",
                    "не задан server_url. Укажите адрес сервера: bad -c или bad config set server_url <url>",
                    "ошибка");
                return Fail();
            }

            if (string.IsNullOrWhiteSpace(config.ApiKey))
            {
                outcome.Line(
                    "Ключ",
                    "нет ключа. Ждите заявку в панели и кнопку «Разрешить».",
                    "ошибка");
                return Fail();
            }

            if (string.IsNullOrWhiteSpace(config.BadId))
            {
                outcome.Line("bad_id", "не задан", "ошибка");
                return Fail();
            }

            var agentVersion = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, agentVersion);
            var collector = new InventoryCollector();
            using var ct = new CancellationTokenSource(TimeSpan.FromMinutes(10));
            var token = ct.Token;

            DateTime? lastInventoryAt = null;
            bool? lastInventoryOk = null;
            string? lastInventoryError = null;

            var pending = OfflineQueue.CountPending();
            if (pending == 0)
            {
                outcome.Line("Очередь", "пусто", "ok");
            }
            else
            {
                var flush = OfflineQueue.FlushAsync(client, config.ApiKey!, config.BadId ?? "", token).GetAwaiter().GetResult();
                if (flush.BoardChanged)
                {
                    InvalidKeyReset.Forget(config, client, token);
                    outcome.Line("Плата", "другая, заявка отправлена", "ошибка");
                    return Fail();
                }

                if (flush.AuthFailed)
                {
                    if (InvalidKeyReset.IsInvalidApiKey(flush.AuthException))
                    {
                        InvalidKeyReset.Forget(config, client, token);
                    }

                    outcome.Line("Очередь", "API key отклонён (401/403) при отправке очереди", "ошибка");
                    return Fail();
                }

                if (flush.Success && flush.Sent > 0)
                {
                    outcome.Line("Очередь", $"отправлено {flush.Sent}", "ok");
                }
                else if (flush.Deferred)
                {
                    outcome.Line("Очередь", $"отложено до {flush.NextRetryUtc:u}", "без изменений");
                }
                else if (!flush.Success)
                {
                    outcome.Line(
                        "Очередь",
                        $"не удалось отправить: {flush.Error?.Message ?? "сеть"}",
                        "ошибка");
                    return Fail();
                }
                else
                {
                    outcome.Line("Очередь", "отправлено 0", "ok");
                }
            }

            var options = CollectorOptions.FromConfig(config);
            var snap = collector.Collect(config.BadId!, agentVersion, options);
            try
            {
                client.SendInventoryAsync(config.ApiKey!, snap, token).GetAwaiter().GetResult();
                lastInventoryAt = DateTime.UtcNow;
                lastInventoryOk = true;
                lastInventoryError = null;
                outcome.Line("Подпись", "сервер принял", "ok");
                outcome.Line(
                    "Inventory",
                    $"отправлен, ошибок сборщика {snap.CollectorErrors.Count}",
                    "ok");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                if (ex.Message.Contains("Inventory signature required", StringComparison.Ordinal)
                    || ex.Message.Contains("Invalid inventory signature", StringComparison.Ordinal))
                {
                    outcome.Line("Подпись", "сервер не принял", "ошибка");
                    outcome.Line("Inventory", "не отправлен", "ошибка");
                    return Fail();
                }

                if (InvalidKeyReset.IsInvalidApiKey(ex))
                {
                    InvalidKeyReset.Forget(config, client, token);
                }

                outcome.Line("Inventory", "API key отклонён (401/403) при отправке inventory", "ошибка");
                return Fail();
            }
            catch (AgentApiException ex) when (ex.IsBoardChanged)
            {
                InvalidKeyReset.Forget(config, client, token);
                outcome.Line("Плата", "другая, заявка отправлена", "ошибка");
                return Fail();
            }
            catch (Exception ex)
            {
                lastInventoryOk = false;
                lastInventoryError = TextLimit.Truncate(ex.Message, 200);
                try
                {
                    OfflineQueue.EnqueueInventory(snap);
                    outcome.Line(
                        "Inventory",
                        $"не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}",
                        "ошибка");
                }
                catch (Exception qex)
                {
                    outcome.Line(
                        "Inventory",
                        $"не отправлен: {ex.Message}; очередь: {qex.Message}",
                        "ошибка");
                }

                return Fail();
            }

            config = ConfigStore.LoadOrCreate();
            var payload = new HeartbeatQueuePayload
            {
                BadId = config.BadId!,
                LastInventoryAt = lastInventoryAt?.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"),
                ConfigVersion = config.RemoteConfigVersion,
                LastInventoryOk = lastInventoryOk,
                LastInventoryError = lastInventoryError,
                AgentUptimeSeconds = 0,
                SystemDriveFreeBytes = Worker.TrySystemDriveFreeBytes(),
                ConfigLocal = ConfigStore.BuildConfigLocalForHeartbeat(config)
            };

            HeartbeatServerResponse? response;
            try
            {
                response = client.SendHeartbeatAsync(config.ApiKey!, payload, token).GetAwaiter().GetResult();
                outcome.Line("Heartbeat", "принят", "ok");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                if (InvalidKeyReset.IsInvalidApiKey(ex))
                {
                    InvalidKeyReset.Forget(config, client, token);
                }

                outcome.Line("Heartbeat", "API key отклонён (401/403) при heartbeat", "ошибка");
                return Fail();
            }
            catch (Exception ex)
            {
                try
                {
                    OfflineQueue.EnqueueHeartbeat(payload);
                    outcome.Line(
                        "Heartbeat",
                        $"не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}",
                        "ошибка");
                }
                catch (Exception qex)
                {
                    outcome.Line(
                        "Heartbeat",
                        $"не отправлен: {ex.Message}; очередь: {qex.Message}",
                        "ошибка");
                }

                return Fail();
            }

            if (response?.Config?.Settings != null
                && ConfigStore.SaveRemoteConfigIfChanged(config, response.Config))
            {
                outcome.Line("Конфиг", "применён", "ok");
            }

            outcome.Tail.Add("Готово");
            return outcome;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            outcome.Line("Сервер", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }
        catch (Exception ex)
        {
            outcome.Line("Ошибка", ex.Message, "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }
    }

    public static void PrintHelp()
    {
        Console.WriteLine("""
Принудительная синхронизация с сервером bAD:
  bad push                 Очередь → inventory → heartbeat (config с сервера)

Обновление MSI: bad update (флаг push --update снят).

Нужны server_url и api_key в config.json (см. bad -c).
""");
    }
}
