namespace BadAgent;

public sealed class Worker : BackgroundService
{
    private readonly ILogger<Worker> _logger;
    private readonly IInventoryCollector _collector;
    private readonly IHostApplicationLifetime _lifetime;
    private readonly string _agentVersion;
    private DateTime? _lastInventoryAt;
    private DateTime _authBackoffUntil = DateTime.MinValue;
    private DateTime _nextUpdateCheck = DateTime.MinValue;

    public Worker(
        ILogger<Worker> logger,
        IInventoryCollector collector,
        IHostApplicationLifetime lifetime)
    {
        _logger = logger;
        _collector = collector;
        _lifetime = lifetime;
        _agentVersion = typeof(Worker).Assembly.GetName().Version?.ToString(3) ?? "0.3.0";
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

        // Check for updates on start (then per update_check_interval_hours).
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

                if (string.IsNullOrWhiteSpace(config.ApiKey) || string.IsNullOrWhiteSpace(config.DeviceId))
                {
                    _logger.LogError("Missing api_key or device_id after enroll attempt");
                    await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
                    continue;
                }

                using var client = new BadApiClient(config.ServerUrl, _agentVersion);

                if (DateTime.UtcNow >= _nextUpdateCheck)
                {
                    var updater = new AgentUpdater(_logger, _agentVersion);
                    var applying = await updater.CheckAndApplyAsync(client, config, stoppingToken);
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
            return;
        }

        if (DateTime.UtcNow < _authBackoffUntil)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(config.EnrollmentToken))
        {
            _logger.LogError("No api_key and no enrollment_token; cannot enroll");
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
            config.EnrollmentToken = null; // clear after success
            ConfigStore.Save(config);
            _logger.LogInformation("Enrollment succeeded; enrollment token cleared from config");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Enrollment failed");
            _authBackoffUntil = DateTime.UtcNow.AddMinutes(15);
            throw;
        }
    }

    private async Task RunInventoryAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        _logger.LogInformation("Collecting inventory");
        var snap = _collector.Collect(config.DeviceId!, _agentVersion);
        try
        {
            await client.SendInventoryAsync(config.ApiKey!, snap, ct);
            _lastInventoryAt = DateTime.UtcNow;
            _logger.LogInformation("Inventory uploaded ({Errors} collector errors)", snap.CollectorErrors.Count);
        }
        catch (HttpRequestException ex) when (ex.Message.Contains("401") || ex.Message.Contains("403"))
        {
            await HandleAuthFailureAsync(config, ct);
            throw;
        }
    }

    private async Task RunHeartbeatAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        var last = _lastInventoryAt?.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
        try
        {
            var remote = await client.SendHeartbeatAsync(
                config.ApiKey!,
                config.DeviceId!,
                last,
                config.RemoteConfigVersion,
                ct);
            _logger.LogDebug("Heartbeat sent");
            if (remote?.Settings != null)
            {
                ApplyRemoteConfig(config, remote);
            }
        }
        catch (HttpRequestException ex) when (ex.Message.Contains("401") || ex.Message.Contains("403"))
        {
            await HandleAuthFailureAsync(config, ct);
            throw;
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
            "Applied remote agent config version {Version} (inventory={Inv}h heartbeat={Hb}m update={Upd}h enabled={Enabled})",
            config.RemoteConfigVersion,
            config.InventoryIntervalHours,
            config.HeartbeatIntervalMinutes,
            config.UpdateCheckIntervalHours,
            config.UpdateEnabled);
    }

    private async Task HandleAuthFailureAsync(AgentConfig config, CancellationToken ct)
    {
        _logger.LogWarning("Auth failure from server");
        if (!string.IsNullOrWhiteSpace(config.EnrollmentToken))
        {
            config.ApiKey = null;
            ConfigStore.Save(config);
            await EnsureEnrolledAsync(config, ct);
        }
        else
        {
            _authBackoffUntil = DateTime.UtcNow.AddHours(1);
            _logger.LogError("Auth failed and no enrollment token available; backing off 1h");
        }
    }
}
