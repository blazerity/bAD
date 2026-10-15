namespace BadAgent;

public sealed class Worker : BackgroundService
{
    private readonly ILogger<Worker> _logger;
    private readonly IInventoryCollector _collector;
    private readonly IHostApplicationLifetime _lifetime;
    private readonly string _agentVersion;
    private readonly DateTime _startedAtUtc = DateTime.UtcNow;
    private DateTime? _lastInventoryAt;
    private bool? _lastInventoryOk;
    private string? _lastInventoryError;
    private DateTime _authBackoffUntil = DateTime.MinValue;
    private DateTime _nextUpdateCheck = DateTime.MinValue;
    /// <summary>Ключ отозван/отклонён — не долбить API до re-enroll / reinstall.</summary>
    private bool _apiKeyRevoked;

    public Worker(
        ILogger<Worker> logger,
        IInventoryCollector collector,
        IHostApplicationLifetime lifetime)
    {
        _logger = logger;
        _collector = collector;
        _lifetime = lifetime;
        _agentVersion = VersionUtil.GetAgentVersion();
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("bAD agent {Version} starting", _agentVersion);

        var config = ConfigStore.LoadOrCreate();
        if (string.IsNullOrWhiteSpace(config.DeviceId))
        {
            config.DeviceId = DeviceIdentity.ResolveDeviceId();
            ConfigStore.Save(config);
        }

        // Проверка обновлений при старте (далее по update_check_interval_hours).
        _nextUpdateCheck = DateTime.UtcNow;

        var inventoryEvery = TimeSpan.FromHours(Math.Max(1, config.InventoryIntervalHours));
        var heartbeatEvery = TimeSpan.FromMinutes(Math.Max(1, config.HeartbeatIntervalMinutes));

        var nextInventory = DateTime.UtcNow;
        var nextHeartbeat = DateTime.UtcNow;

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                config = ConfigStore.LoadOrCreate();
                inventoryEvery = TimeSpan.FromHours(Math.Max(1, config.InventoryIntervalHours));
                heartbeatEvery = TimeSpan.FromMinutes(Math.Max(1, config.HeartbeatIntervalMinutes));

                if (string.IsNullOrWhiteSpace(config.ServerUrl))
                {
                    _logger.LogWarning("server_url not configured; sleeping");
                    await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
                    continue;
                }

                await EnsureEnrolledAsync(config, stoppingToken);
                config = ConfigStore.LoadOrCreate();

                if (_apiKeyRevoked && string.IsNullOrWhiteSpace(config.ApiKey))
                {
                    _logger.LogWarning(
                        "API key revoked/cleared; waiting for re-enroll or reinstall (device_id={DeviceId})",
                        config.DeviceId);
                    await Task.Delay(TimeSpan.FromMinutes(30), stoppingToken);
                    continue;
                }

                if (string.IsNullOrWhiteSpace(config.ApiKey) || string.IsNullOrWhiteSpace(config.DeviceId))
                {
                    _logger.LogError("Missing api_key or device_id after enroll attempt");
                    await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
                    continue;
                }

                using var client = new BadApiClient(config.ServerUrl, _agentVersion);

                // Сначала слить offline queue (если сервер снова доступен).
                await FlushOfflineQueueAsync(client, config, stoppingToken);
                config = ConfigStore.LoadOrCreate();
                if (string.IsNullOrWhiteSpace(config.ApiKey))
                {
                    continue;
                }

                if (DateTime.UtcNow >= _nextUpdateCheck)
                {
                    var updater = new AgentUpdater(_logger, _agentVersion);
                    bool applying;
                    try
                    {
                        applying = await updater.CheckAndApplyAsync(client, config, stoppingToken);
                    }
                    catch (AgentApiException ex) when (ex.IsAuthFailure)
                    {
                        HandleAuthFailure(config, "update", ex);
                        continue;
                    }

                    var updateEvery = TimeSpan.FromHours(Math.Max(1, config.UpdateCheckIntervalHours));
                    _nextUpdateCheck = DateTime.UtcNow + updateEvery;
                    if (applying)
                    {
                        _logger.LogInformation("Exiting so MSI upgrade can replace agent files");
                        _lifetime.StopApplication();
                        return;
                    }
                }

                if (DateTime.UtcNow >= nextInventory)
                {
                    await RunInventoryAsync(client, config, stoppingToken);
                    nextInventory = DateTime.UtcNow + inventoryEvery;
                }

                if (DateTime.UtcNow >= nextHeartbeat)
                {
                    await RunHeartbeatAsync(client, config, stoppingToken);
                    config = ConfigStore.LoadOrCreate();
                    inventoryEvery = TimeSpan.FromHours(Math.Max(1, config.InventoryIntervalHours));
                    heartbeatEvery = TimeSpan.FromMinutes(Math.Max(1, config.HeartbeatIntervalMinutes));
                    nextHeartbeat = DateTime.UtcNow + heartbeatEvery;
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Agent loop error");
            }

            try
            {
                await Task.Delay(TimeSpan.FromSeconds(15), stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
        }

        _logger.LogInformation("bAD agent stopping");
    }

    private async Task EnsureEnrolledAsync(AgentConfig config, CancellationToken ct)
    {
        if (!string.IsNullOrWhiteSpace(config.ApiKey))
        {
            _apiKeyRevoked = false;
            return;
        }

        if (DateTime.UtcNow < _authBackoffUntil)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(config.EnrollmentToken))
        {
            _logger.LogError("No api_key and no enrollment_token; cannot enroll");
            WindowsEventLog.WriteError(
                "bAD: нет api_key и enrollment_token — требуется re-enroll или переустановка MSI.");
            _authBackoffUntil = DateTime.UtcNow.AddHours(1);
            return;
        }

        if (string.IsNullOrWhiteSpace(config.DeviceId))
        {
            config.DeviceId = DeviceIdentity.ResolveDeviceId();
        }

        _logger.LogInformation("Enrolling device {DeviceId}", config.DeviceId);
        using var client = new BadApiClient(config.ServerUrl, _agentVersion);
        try
        {
            var (apiKey, deviceId) = await client.EnrollAsync(
                config.EnrollmentToken!,
                config.DeviceId!,
                Environment.MachineName,
                ct);
            config.ApiKey = apiKey;
            config.DeviceId = deviceId;
            config.EnrollmentToken = null; // очищаем после успеха
            ConfigStore.Save(config);
            _apiKeyRevoked = false;
            _logger.LogInformation("Enrollment succeeded; enrollment token cleared from config");
            WindowsEventLog.WriteInfo($"bAD: устройство {deviceId} успешно зарегистрировано.");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Enrollment failed");
            WindowsEventLog.WriteError("bAD: ошибка enroll", ex);
            _authBackoffUntil = DateTime.UtcNow.AddMinutes(15);
            throw;
        }
    }

    private async Task FlushOfflineQueueAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(config.ApiKey))
        {
            return;
        }

        var pending = OfflineQueue.CountPending();
        if (pending == 0)
        {
            return;
        }

        _logger.LogInformation("Flushing offline queue ({Count} pending)", pending);
        var result = await OfflineQueue.FlushAsync(client, config.ApiKey!, ct);
        if (result.AuthFailed)
        {
            HandleAuthFailure(config, "queue", result.AuthException);
            return;
        }

        if (result.Deferred)
        {
            _logger.LogDebug("Offline queue backoff until {Until}", result.NextRetryUtc);
            return;
        }

        if (result.Success)
        {
            if (result.Sent > 0)
            {
                _logger.LogInformation("Offline queue sent {Sent} item(s)", result.Sent);
            }

            return;
        }

        _logger.LogWarning(
            result.Error,
            "Offline queue flush failed; next retry in {Delay}, failures={Failures}",
            result.RetryAfter,
            result.Failures);
    }

    private async Task RunInventoryAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        _logger.LogInformation(
            "Collecting inventory (hardware={Hw} users={Users} software={Sw})",
            config.CollectHardware,
            config.CollectUsers,
            config.CollectSoftware);
        var options = CollectorOptions.FromConfig(config);
        var snap = _collector.Collect(config.DeviceId!, _agentVersion, options);
        try
        {
            await client.SendInventoryAsync(config.ApiKey!, snap, ct);
            _lastInventoryAt = DateTime.UtcNow;
            _lastInventoryOk = true;
            _lastInventoryError = null;
            _logger.LogInformation("Inventory uploaded ({Errors} collector errors)", snap.CollectorErrors.Count);
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            _lastInventoryOk = false;
            _lastInventoryError = Truncate("auth_failed", 200);
            HandleAuthFailure(config, "inventory", ex);
        }
        catch (Exception ex)
        {
            _lastInventoryOk = false;
            _lastInventoryError = Truncate(ex.Message, 200);
            try
            {
                OfflineQueue.EnqueueInventory(snap);
                _logger.LogWarning(
                    ex,
                    "Inventory upload failed; queued locally ({Pending} pending)",
                    OfflineQueue.CountPending());
            }
            catch (Exception qex)
            {
                _logger.LogError(qex, "Failed to persist inventory to offline queue");
            }
        }
    }

    private async Task RunHeartbeatAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        var last = _lastInventoryAt?.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
        var uptime = (long)Math.Max(0, (DateTime.UtcNow - _startedAtUtc).TotalSeconds);
        var freeBytes = TrySystemDriveFreeBytes();
        var payload = new HeartbeatQueuePayload
        {
            DeviceId = config.DeviceId!,
            LastInventoryAt = last,
            ConfigVersion = config.RemoteConfigVersion,
            LastInventoryOk = _lastInventoryOk,
            LastInventoryError = _lastInventoryError,
            AgentUptimeSeconds = uptime,
            SystemDriveFreeBytes = freeBytes
        };

        try
        {
            var remote = await client.SendHeartbeatAsync(config.ApiKey!, payload, ct);
            _logger.LogDebug("Heartbeat sent");
            if (remote?.Settings != null)
            {
                ApplyRemoteConfig(config, remote);
            }
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            HandleAuthFailure(config, "heartbeat", ex);
        }
        catch (Exception ex)
        {
            try
            {
                OfflineQueue.EnqueueHeartbeat(payload);
                _logger.LogWarning(
                    ex,
                    "Heartbeat failed; queued locally ({Pending} pending)",
                    OfflineQueue.CountPending());
            }
            catch (Exception qex)
            {
                _logger.LogError(qex, "Failed to persist heartbeat to offline queue");
            }
        }
    }

    private void ApplyRemoteConfig(AgentConfig config, RemoteAgentConfigResponse remote)
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

        if (!changed)
        {
            return;
        }

        ConfigStore.Save(config);
        _logger.LogInformation(
            "Applied remote agent config version {Version} (inventory={Inv}h heartbeat={Hb}m update={Upd}h enabled={Enabled} target={Target} hw={Hw} users={Users} sw={Sw})",
            config.RemoteConfigVersion,
            config.InventoryIntervalHours,
            config.HeartbeatIntervalMinutes,
            config.UpdateCheckIntervalHours,
            config.UpdateEnabled,
            config.UpdateTarget,
            config.CollectHardware,
            config.CollectUsers,
            config.CollectSoftware);
    }

    /// <summary>
    /// 401/403: очистить api_key (device_id оставить), очередь не трогаем (после re-enroll flush).
    /// Не долбить сервер, ждать re-enroll/reinstall.
    /// </summary>
    private void HandleAuthFailure(AgentConfig config, string operation, Exception? ex = null)
    {
        _logger.LogError(
            ex,
            "Auth failure ({Operation}): clearing api_key, keeping device_id={DeviceId}; stop posting until re-enroll",
            operation,
            config.DeviceId);
        WindowsEventLog.WriteError(
            $"bAD: API key отклонён ({operation}, 401/403). Ключ очищен, device_id сохранён. " +
            "Нужен re-enroll (enrollment token) или переустановка MSI.",
            ex);

        config.ApiKey = null;
        ConfigStore.Save(config);
        _apiKeyRevoked = true;
        _authBackoffUntil = DateTime.UtcNow.AddHours(1);

        // Если MSI снова дал enrollment_token — попробуем на следующем витке EnsureEnrolled.
    }

    /// <summary>Свободные байты системного диска через DriveInfo (без WMI).</summary>
    public static long? TrySystemDriveFreeBytes()
    {
        try
        {
            string root;
            if (OperatingSystem.IsWindows())
            {
                root = Path.GetPathRoot(Environment.SystemDirectory) ?? "C:\\";
            }
            else
            {
                root = "/";
            }

            var drive = new DriveInfo(root);
            if (!drive.IsReady)
            {
                return null;
            }

            return drive.AvailableFreeSpace;
        }
        catch
        {
            return null;
        }
    }

    private static string Truncate(string text, int max)
    {
        if (string.IsNullOrEmpty(text) || text.Length <= max)
        {
            return text;
        }

        return text[..max];
    }
}
