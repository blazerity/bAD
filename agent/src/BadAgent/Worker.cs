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
    /// <summary>Ждём «Разрешить» в панели (POST /v1/enrollment-requests → pending).</summary>
    private bool _enrollmentRequestPending;

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
        _ = Task.Run(() => AgentUpdater.DeleteStaleDownloads(_logger));

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

                if (DateTime.UtcNow < _authBackoffUntil)
                {
                    var wait = _authBackoffUntil - DateTime.UtcNow;
                    if (wait > TimeSpan.FromMinutes(1))
                    {
                        wait = TimeSpan.FromMinutes(1);
                    }

                    await Task.Delay(wait, stoppingToken);
                    continue;
                }

                await EnsureEnrolledAsync(config, stoppingToken);
                config = ConfigStore.LoadOrCreate();

                if (_apiKeyRevoked && string.IsNullOrWhiteSpace(config.ApiKey))
                {
                    if (!string.IsNullOrWhiteSpace(config.EnrollmentCode))
                    {
                        _logger.LogWarning(
                            "API key revoked/cleared; waiting for re-enroll with enrollment code (device_id={DeviceId})",
                            config.DeviceId);
                        await Task.Delay(TimeSpan.FromMinutes(30), stoppingToken);
                        continue;
                    }
                }

                if (string.IsNullOrWhiteSpace(config.ApiKey))
                {
                    if (_enrollmentRequestPending)
                    {
                        // Опрос enrollment-requests — см. интервал в конце цикла (~15 с).
                    }
                    else
                    {
                        _logger.LogError("Missing api_key or device_id after enroll attempt");
                        await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
                        continue;
                    }
                }

                if (string.IsNullOrWhiteSpace(config.DeviceId))
                {
                    _logger.LogError("Missing device_id after enroll attempt");
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
            catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
            {
                _logger.LogError("{Message}", ServerUrlRules.CleartextHttpRejectedMessage);
                WindowsEventLog.WriteError(ServerUrlRules.CleartextHttpRejectedMessage);
                try
                {
                    await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
                }
                catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
                {
                    break;
                }
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
            _enrollmentRequestPending = false;
            return;
        }

        if (DateTime.UtcNow < _authBackoffUntil)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(config.DeviceId))
        {
            config.DeviceId = DeviceIdentity.ResolveDeviceId();
        }

        using var client = new BadApiClient(config.ServerUrl, _agentVersion);
        try
        {
            if (!string.IsNullOrWhiteSpace(config.EnrollmentCode))
            {
                await EnrollWithCodeAsync(client, config, ct);
                return;
            }

            await PollEnrollmentRequestAsync(client, config, ct);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Enrollment failed");
            WindowsEventLog.WriteError("bAD: ошибка enroll", ex);
            _authBackoffUntil = DateTime.UtcNow.AddMinutes(15);
            throw;
        }
    }

    private async Task EnrollWithCodeAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        _enrollmentRequestPending = false;
        _logger.LogInformation("Enrolling device {DeviceId} with enrollment code", config.DeviceId);
        var enrollResult = await client.EnrollAsync(
            config.EnrollmentCode!.Trim(),
            config.DeviceId!,
            Environment.MachineName,
            ct);
        ApplyEnrollmentSecrets(config, enrollResult.ApiKey, enrollResult.DeviceId, enrollResult.SigningKeyBase64);
        config.EnrollmentCode = null;
        ConfigStore.Save(config);
        _apiKeyRevoked = false;
        _logger.LogInformation("Enrollment succeeded; enrollment secrets cleared from config");
        WindowsEventLog.WriteInfo($"bAD: устройство {enrollResult.DeviceId} успешно зарегистрировано.");
    }

    private async Task PollEnrollmentRequestAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        var (hostname, ip, serial) = EnrollmentHints.ForRequest();
        var fingerprint = EnrollmentProof.TryFingerprintHex();
        if (string.IsNullOrWhiteSpace(fingerprint))
        {
            _logger.LogError("Файл enrollment_proof не прочитан, заявка не отправлена");
            _authBackoffUntil = DateTime.UtcNow.AddMinutes(15);
            return;
        }

        var result = await client.SubmitEnrollmentRequestAsync(
            hostname,
            ip,
            serial,
            fingerprint,
            string.IsNullOrWhiteSpace(config.DeviceId) ? null : config.DeviceId,
            ct);
        if (result.RouteMissing)
        {
            _enrollmentRequestPending = false;
            _logger.LogError(
                "Server has no /v1/enrollment-requests; set enrollment_code or upgrade server");
            WindowsEventLog.WriteError(
                "bAD: сервер без enrollment-requests — нужен одноразовый код или обновление сервера.");
            _authBackoffUntil = DateTime.UtcNow.AddHours(1);
            return;
        }

        if (string.Equals(result.Status, "pending", StringComparison.OrdinalIgnoreCase))
        {
            if (!_enrollmentRequestPending)
            {
                _logger.LogInformation(
                    "Enrollment request submitted for {Hostname}; waiting for admin approval",
                    hostname);
                WindowsEventLog.WriteInfo(
                    "bAD: заявка на регистрацию отправлена — ожидание «Разрешить» в панели.");
            }

            _enrollmentRequestPending = true;
            return;
        }

        if (string.Equals(result.Status, "approved", StringComparison.OrdinalIgnoreCase)
            && !string.IsNullOrWhiteSpace(result.ApiKey))
        {
            config.ApiKey = result.ApiKey;
            if (!string.IsNullOrWhiteSpace(result.SigningKeyBase64))
            {
                AgentSigningKey.SavePrivateKeyBase64(result.SigningKeyBase64);
            }

            ConfigStore.Save(config);
            _apiKeyRevoked = false;
            _enrollmentRequestPending = false;
            _logger.LogInformation("Enrollment approved for device {DeviceId}", config.DeviceId);
            WindowsEventLog.WriteInfo($"bAD: регистрация разрешена, устройство {config.DeviceId}.");
            return;
        }

        if (string.Equals(result.Status, "approved", StringComparison.OrdinalIgnoreCase))
        {
            _enrollmentRequestPending = true;
            _logger.LogDebug("Enrollment approved but secrets not ready; will retry");
            return;
        }

        _logger.LogWarning("Unexpected enrollment-requests status {Status}", result.Status);
        _enrollmentRequestPending = true;
    }

    private void ApplyEnrollmentSecrets(
        AgentConfig config,
        string apiKey,
        string deviceId,
        string? signingKeyBase64)
    {
        config.ApiKey = apiKey;
        config.DeviceId = deviceId;
        if (!string.IsNullOrWhiteSpace(signingKeyBase64))
        {
            AgentSigningKey.SavePrivateKeyBase64(signingKeyBase64);
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
        var result = await OfflineQueue.FlushAsync(client, config.ApiKey!, ct, _logger);
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
            await client.SendInventoryAsync(config.ApiKey!, snap, ct, _logger);
            _lastInventoryAt = DateTime.UtcNow;
            _lastInventoryOk = true;
            _lastInventoryError = null;
            _logger.LogInformation("Inventory uploaded ({Errors} collector errors)", snap.CollectorErrors.Count);
        }
        catch (AgentApiException ex) when (
            ex.IsAuthFailure
            && (ex.Message.Contains("Inventory signature required", StringComparison.Ordinal)
                || ex.Message.Contains("Invalid inventory signature", StringComparison.Ordinal)))
        {
            _lastInventoryOk = false;
            _lastInventoryError = TextLimit.Truncate(ex.Message, 200);
            _logger.LogError(ex, "Сервер не принял подпись снимка");
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            _lastInventoryOk = false;
            _lastInventoryError = TextLimit.Truncate("auth_failed", 200);
            HandleAuthFailure(config, "inventory", ex);
        }
        catch (Exception ex)
        {
            _lastInventoryOk = false;
            _lastInventoryError = TextLimit.Truncate(ex.Message, 200);
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
            SystemDriveFreeBytes = freeBytes,
            // Provenance для панели: source agent_local (keys / optional settings / server_url).
            ConfigLocal = ConfigStore.BuildConfigLocalForHeartbeat(config)
        };

        try
        {
            var response = await client.SendHeartbeatAsync(config.ApiKey!, payload, ct);
            _logger.LogDebug("Heartbeat sent");
            if (response?.Config?.Settings != null)
            {
                ApplyRemoteConfig(config, response.Config);
            }

            await MinidumpHeartbeatUpload.RunAsync(
                client,
                config.ApiKey!,
                response?.Actions?.UploadMinidump,
                _logger,
                ct);

            config = ConfigStore.LoadOrCreate();

            if (response?.Actions?.Uninstall == true)
            {
                if (AgentUninstaller.TryStartSilentUninstall(_logger))
                {
                    _logger.LogInformation("Выход после запуска msiexec uninstall");
                    _lifetime.StopApplication();
                    return;
                }

                return;
            }

            if (response?.Actions?.Inventory == true)
            {
                await RunInventoryAsync(client, config, ct);
                config = ConfigStore.LoadOrCreate();
            }

            if (response?.Actions?.UpdateCheck == true)
            {
                _nextUpdateCheck = DateTime.UtcNow;
                var updater = new AgentUpdater(_logger, _agentVersion);
                bool applying;
                try
                {
                    applying = await updater.CheckAndApplyAsync(client, config, ct);
                }
                catch (AgentApiException ex) when (ex.IsAuthFailure)
                {
                    HandleAuthFailure(config, "update", ex);
                    return;
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
        if (!ConfigStore.TakeRemoteConfig(config, remote))
        {
            return;
        }

        ConfigStore.Save(config);
        _collector.ResetHeavySectionCache();
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
    /// 401/403: api_key и device_id не трогаем. Иначе уже зарегистрированная машина
    /// после MSI теряет ключ и <c>bad push</c> пишет «нет api_key».
    /// </summary>
    private void HandleAuthFailure(AgentConfig config, string operation, Exception? ex = null)
    {
        _logger.LogError(
            ex,
            "Auth failure ({Operation}): keeping api_key and device_id={DeviceId}; backing off",
            operation,
            config.DeviceId);
        WindowsEventLog.WriteError(
            $"bAD: API key отклонён ({operation}, 401/403). Ключ в config.json сохранён, device_id={config.DeviceId}.",
            ex);

        _apiKeyRevoked = true;
        _enrollmentRequestPending = false;
        _authBackoffUntil = DateTime.UtcNow.AddHours(1);
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

}
