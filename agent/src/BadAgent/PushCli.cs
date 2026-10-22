using Microsoft.Extensions.Logging.Abstractions;

namespace BadAgent;

/// <summary>
/// Принудительная отправка на сервер: очередь → inventory → heartbeat (и опционально проверка обновлений).
/// </summary>
public static class PushCli
{
    public static int Run(string[] args)
    {
        var runUpdate = false;
        foreach (var arg in args)
        {
            if (IsHelpToken(arg))
            {
                PrintHelp();
                return 0;
            }

            if (string.Equals(arg, "--update", StringComparison.Ordinal))
            {
                runUpdate = true;
                continue;
            }

            Console.Error.WriteLine($"error: неизвестный аргумент '{arg}' (допустимо: --update)");
            PrintHelp();
            return 2;
        }

        return RunPush(runUpdate);
    }

    private static int RunPush(bool runUpdate)
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

            if (string.IsNullOrWhiteSpace(config.DeviceId))
            {
                Console.Error.WriteLine("error: не задан device_id");
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

            Console.WriteLine("[1/3] Слив офлайн-очереди…");
            var pending = OfflineQueue.CountPending();
            if (pending == 0)
            {
                Console.WriteLine("      Очередь пуста.");
            }
            else
            {
                Console.WriteLine($"      Ожидает отправки: {pending}");
                var flush = OfflineQueue.FlushAsync(client, config.ApiKey!, token).GetAwaiter().GetResult();
                if (flush.AuthFailed)
                {
                    Console.Error.WriteLine("error: API key отклонён (401/403) при отправке очереди");
                    return 1;
                }

                if (flush.Success && flush.Sent > 0)
                {
                    Console.WriteLine($"      Отправлено записей: {flush.Sent}");
                }
                else if (flush.Deferred)
                {
                    Console.WriteLine($"      Отложено до {flush.NextRetryUtc:u}");
                }
                else if (!flush.Success)
                {
                    Console.Error.WriteLine($"error: не удалось отправить очередь: {flush.Error?.Message ?? "сеть"}");
                    return 1;
                }
            }

            Console.WriteLine("[2/3] Сбор и отправка inventory…");
            var options = CollectorOptions.FromConfig(config);
            var snap = collector.Collect(config.DeviceId!, agentVersion, options);
            try
            {
                client.SendInventoryAsync(config.ApiKey!, snap, token).GetAwaiter().GetResult();
                lastInventoryAt = DateTime.UtcNow;
                lastInventoryOk = true;
                lastInventoryError = null;
                Console.WriteLine(
                    $"      Inventory отправлен (ошибок сборщика: {snap.CollectorErrors.Count}).");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                Console.Error.WriteLine("error: API key отклонён (401/403) при отправке inventory");
                return 1;
            }
            catch (Exception ex)
            {
                lastInventoryOk = false;
                lastInventoryError = Truncate(ex.Message, 200);
                try
                {
                    OfflineQueue.EnqueueInventory(snap);
                    Console.Error.WriteLine(
                        $"error: inventory не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}");
                }
                catch (Exception qex)
                {
                    Console.Error.WriteLine($"error: inventory не отправлен: {ex.Message}; очередь: {qex.Message}");
                }

                return 1;
            }

            Console.WriteLine("[3/3] Heartbeat…");
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
                Console.WriteLine("      Heartbeat принят сервером.");
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                Console.Error.WriteLine("error: API key отклонён (401/403) при heartbeat");
                return 1;
            }
            catch (Exception ex)
            {
                try
                {
                    OfflineQueue.EnqueueHeartbeat(payload);
                    Console.Error.WriteLine(
                        $"error: heartbeat не отправлен, сохранён в очередь ({OfflineQueue.CountPending()}): {ex.Message}");
                }
                catch (Exception qex)
                {
                    Console.Error.WriteLine($"error: heartbeat не отправлен: {ex.Message}; очередь: {qex.Message}");
                }

                return 1;
            }

            if (response?.Config?.Settings != null)
            {
                ApplyRemoteConfig(config, response.Config);
                Console.WriteLine("      Применена удалённая конфигурация агента.");
            }

            // --update или actions.update_check с панели (request-refresh).
            var wantUpdate = runUpdate || response?.Actions?.UpdateCheck == true;
            if (wantUpdate)
            {
                Console.WriteLine(
                    runUpdate
                        ? "[+] Проверка обновлений (--update)…"
                        : "[+] Проверка обновлений (запрос с панели)…");
                config = ConfigStore.LoadOrCreate();
                var logger = NullLogger.Instance;
                var updater = new AgentUpdater(logger, agentVersion);
                try
                {
                    var applying = updater.CheckAndApplyAsync(client, config, token).GetAwaiter().GetResult();
                    if (applying)
                    {
                        Console.WriteLine(
                            "      Запущена установка MSI — завершите push и дождитесь перезапуска службы.");
                    }
                    else
                    {
                        Console.WriteLine("      Обновление не требуется или отключено в конфиге.");
                    }
                }
                catch (AgentApiException ex) when (ex.IsAuthFailure)
                {
                    Console.Error.WriteLine("error: API key отклонён (401/403) при проверке обновлений");
                    return 1;
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"error: проверка обновлений не удалась: {ex.Message}");
                    return 1;
                }
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
            Console.Error.WriteLine($"error: {ex.Message}");
            return 1;
        }
    }

    private static void ApplyRemoteConfig(AgentConfig config, RemoteAgentConfigResponse remote)
    {
        if (remote.Settings is null)
        {
            return;
        }

        var changed = ConfigStore.ApplyRemoteSettings(config, remote.Settings);
        if (!string.IsNullOrWhiteSpace(remote.Version)
            && !string.Equals(config.RemoteConfigVersion, remote.Version, StringComparison.Ordinal))
        {
            config.RemoteConfigVersion = remote.Version;
            changed = true;
        }

        if (changed)
        {
            ConfigStore.Save(config);
        }
    }

    private static bool IsHelpToken(string s) =>
        s is "-h" or "--help" or "-?" or "/?" or "help";

    private static string Truncate(string text, int max)
    {
        if (string.IsNullOrEmpty(text) || text.Length <= max)
        {
            return text;
        }

        return text[..max];
    }

    public static void PrintHelp()
    {
        Console.WriteLine("""
Принудительная синхронизация с сервером bAD:
  bad push                 Очередь → inventory → heartbeat (config с сервера)
  bad push --update        То же + проверка и установка обновления агента

Нужны server_url и api_key в config.json (см. bad -c).
""");
    }
}
