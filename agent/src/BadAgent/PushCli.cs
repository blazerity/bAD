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

        return RunPush();
    }

    private static int RunPush()
    {
        try
        {
            var config = ConfigStore.LoadOrCreate();
            if (string.IsNullOrWhiteSpace(config.DeviceId))
            {
                config.DeviceId = DeviceIdentity.ResolveDeviceId();
                ConfigStore.Save(config);
            }

            if (string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                CliColumns.Write(
                    "Сервер",
                    "не задан server_url. Укажите адрес сервера: bad -c или bad config set server_url <url>",
                    "ошибка");
                return 1;
            }

            if (string.IsNullOrWhiteSpace(config.ApiKey))
            {
                CliColumns.Write(
                    "Ключ",
                    "нет ключа. Ждите заявку в панели и кнопку «Разрешить».",
                    "ошибка");
                return 1;
            }

            if (string.IsNullOrWhiteSpace(config.DeviceId))
            {
                CliColumns.Write("device_id", "не задан", "ошибка");
                return 1;
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
                CliColumns.Write("Очередь", "пусто", "ok");
            }
            else
            {
                var flush = OfflineQueue.FlushAsync(client, config.ApiKey!, token).GetAwaiter().GetResult();
                if (flush.AuthFailed)
                {
                    CliColumns.Write("Очередь", "API key отклонён (401/403) при отправке очереди", "ошибка");
                    return 1;
                }

                if (flush.Success && flush.Sent > 0)
                {
                    CliColumns.Write("Очередь", $"отправлено {flush.Sent}", "ok");
                }
                else if (flush.Deferred)
                {
                    CliColumns.Write("Очередь", $"отложено до {flush.NextRetryUtc:u}", "без изменений");
                }
                else if (!flush.Success)
                {
                    CliColumns.Write(
                        "Очередь",
                        $"не удалось отправить: {flush.Error?.Message ?? "сеть"}",
                        "ошибка");
                    return 1;
                }
                else
                {
                    CliColumns.Write("Очередь", "отправлено 0", "ok");
                }
            }

            var options = CollectorOptions.FromConfig(config);
            var snap = collector.Collect(config.DeviceId!, agentVersion, options);
            try
            {
                client.SendInventoryAsync(config.ApiKey!, snap, token).GetAwaiter().GetResult();
                lastInventoryAt = DateTime.UtcNow;
                lastInventoryOk = true;
                lastInventoryError = null;
                CliColumns.Write("Подпись", "сервер принял", "ok");
                CliColumns.Write(
                    "Inventory",
                    $"отправлен, ошибок сборщика {snap.CollectorErrors.Count}",
                    "ok");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                if (ex.Message.Contains("Inventory signature required", StringComparison.Ordinal)
                    || ex.Message.Contains("Invalid inventory signature", StringComparison.Ordinal))
                {
                    CliColumns.Write("Подпись", "сервер не принял", "ошибка");
                    CliColumns.Write("Inventory", "не отправлен", "ошибка");
                    return 1;
                }

                CliColumns.Write("Inventory", "API key отклонён (401/403) при отправке inventory", "ошибка");
                return 1;
            }
            catch (Exception ex)
            {
                lastInventoryOk = false;
                lastInventoryError = TextLimit.Truncate(ex.Message, 200);
                try
                {
                    OfflineQueue.EnqueueInventory(snap);
                    CliColumns.Write(
                        "Inventory",
                        $"не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}",
                        "ошибка");
                }
                catch (Exception qex)
                {
                    CliColumns.Write(
                        "Inventory",
                        $"не отправлен: {ex.Message}; очередь: {qex.Message}",
                        "ошибка");
                }

                return 1;
            }

            config = ConfigStore.LoadOrCreate();
            var payload = new HeartbeatQueuePayload
            {
                DeviceId = config.DeviceId!,
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
                CliColumns.Write("Heartbeat", "принят", "ok");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                CliColumns.Write("Heartbeat", "API key отклонён (401/403) при heartbeat", "ошибка");
                return 1;
            }
            catch (Exception ex)
            {
                try
                {
                    OfflineQueue.EnqueueHeartbeat(payload);
                    CliColumns.Write(
                        "Heartbeat",
                        $"не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}",
                        "ошибка");
                }
                catch (Exception qex)
                {
                    CliColumns.Write(
                        "Heartbeat",
                        $"не отправлен: {ex.Message}; очередь: {qex.Message}",
                        "ошибка");
                }

                return 1;
            }

            if (response?.Config?.Settings != null && ApplyRemoteConfig(config, response.Config))
            {
                CliColumns.Write("Конфиг", "применён", "ok");
            }

            MinidumpHeartbeatUpload.RunAsync(client, config.ApiKey!, response?.Actions?.UploadMinidump, null, token)
                .GetAwaiter()
                .GetResult();

            Console.WriteLine("Готово");
            return 0;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            CliColumns.Write("Сервер", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
            return 1;
        }
        catch (Exception ex)
        {
            CliColumns.Write("Ошибка", ex.Message, "ошибка");
            return 1;
        }
    }

    private static bool ApplyRemoteConfig(AgentConfig config, RemoteAgentConfigResponse remote)
    {
        if (!ConfigStore.TakeRemoteConfig(config, remote))
        {
            return false;
        }

        ConfigStore.Save(config);
        return true;
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
