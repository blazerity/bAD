using System.Text.Json;
using System.Text.Json.Serialization;

namespace BadAgent;

public sealed class AgentConfig
{
    [JsonPropertyName("server_url")]
    public string ServerUrl { get; set; } = "";

    [JsonPropertyName("enrollment_token")]
    public string? EnrollmentToken { get; set; }

    [JsonPropertyName("api_key")]
    public string? ApiKey { get; set; }

    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("inventory_interval_hours")]
    public int InventoryIntervalHours { get; set; } = 6;

    [JsonPropertyName("heartbeat_interval_minutes")]
    public int HeartbeatIntervalMinutes { get; set; } = 15;

    /// <summary>Как часто спрашивать сервер про новый MSI (часы). По умолчанию 24.</summary>
    [JsonPropertyName("update_check_interval_hours")]
    public int UpdateCheckIntervalHours { get; set; } = 24;

    [JsonPropertyName("update_enabled")]
    public bool UpdateEnabled { get; set; } = true;

    /// <summary>Собирать CPU/RAM/disks/volumes. По умолчанию true (как раньше).</summary>
    [JsonPropertyName("collect_hardware")]
    public bool CollectHardware { get; set; } = true;

    /// <summary>Собирать logged_on / last_interactive. По умолчанию true.</summary>
    [JsonPropertyName("collect_users")]
    public bool CollectUsers { get; set; } = true;

    /// <summary>Собирать список установленных программ. По умолчанию false (opt-in).</summary>
    [JsonPropertyName("collect_software")]
    public bool CollectSoftware { get; set; } = false;

    /// <summary>Последняя применённая версия remote config (hash сервера); не секрет.</summary>
    [JsonPropertyName("remote_config_version")]
    public string? RemoteConfigVersion { get; set; }
}

/// <summary>Подмножество knobs AgentConfig, которые сервер может пушить удалённо.</summary>
public sealed class RemoteAgentSettings
{
    [JsonPropertyName("inventory_interval_hours")]
    public int? InventoryIntervalHours { get; set; }

    [JsonPropertyName("heartbeat_interval_minutes")]
    public int? HeartbeatIntervalMinutes { get; set; }

    [JsonPropertyName("update_check_interval_hours")]
    public int? UpdateCheckIntervalHours { get; set; }

    [JsonPropertyName("update_enabled")]
    public bool? UpdateEnabled { get; set; }

    [JsonPropertyName("collect_hardware")]
    public bool? CollectHardware { get; set; }

    [JsonPropertyName("collect_users")]
    public bool? CollectUsers { get; set; }

    [JsonPropertyName("collect_software")]
    public bool? CollectSoftware { get; set; }
}

public sealed class RemoteAgentConfigResponse
{
    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("settings")]
    public RemoteAgentSettings? Settings { get; set; }

    public static RemoteAgentConfigResponse? FromJson(string json)
    {
        return JsonSerializer.Deserialize<RemoteAgentConfigResponse>(json);
    }
}

public static class ConfigStore
{
    public static string ProgramDataDir
    {
        get
        {
            var overrideDir = Environment.GetEnvironmentVariable("BAD_CONFIG_DIR");
            if (!string.IsNullOrWhiteSpace(overrideDir))
            {
                return overrideDir;
            }

            if (OperatingSystem.IsWindows())
            {
                var pd = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
                return Path.Combine(pd, "blazerity", "bAD");
            }

            return Path.Combine(Path.GetTempPath(), "blazerity-bad");
        }
    }

    public static string ConfigPath => Path.Combine(ProgramDataDir, "config.json");
    public static string LogsDir => Path.Combine(ProgramDataDir, "logs");

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    public static AgentConfig LoadOrCreate()
    {
        Directory.CreateDirectory(ProgramDataDir);
        Directory.CreateDirectory(LogsDir);

        var fromEnv = ApplyEnvironment(new AgentConfig());
        if (!File.Exists(ConfigPath))
        {
            Save(fromEnv);
            return fromEnv;
        }

        var json = File.ReadAllText(ConfigPath);
        var cfg = JsonSerializer.Deserialize<AgentConfig>(json) ?? new AgentConfig();
        return ApplyEnvironment(cfg);
    }

    public static void Save(AgentConfig config)
    {
        Directory.CreateDirectory(ProgramDataDir);
        var tmp = ConfigPath + ".tmp";
        var json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(tmp, json);
        File.Copy(tmp, ConfigPath, overwrite: true);
        File.Delete(tmp);
    }

    /// <summary>
    /// Применяет только safe knobs с сервера. Не трогает server_url, api_key, device_id, enrollment_token.
    /// True, если что-то изменилось.
    /// </summary>
    public static bool ApplyRemoteSettings(AgentConfig config, RemoteAgentSettings settings)
    {
        var changed = false;
        if (settings.InventoryIntervalHours is int inv && inv >= 1
            && config.InventoryIntervalHours != inv)
        {
            config.InventoryIntervalHours = inv;
            changed = true;
        }

        if (settings.HeartbeatIntervalMinutes is int hb && hb >= 1
            && config.HeartbeatIntervalMinutes != hb)
        {
            config.HeartbeatIntervalMinutes = hb;
            changed = true;
        }

        if (settings.UpdateCheckIntervalHours is int uch && uch >= 1
            && config.UpdateCheckIntervalHours != uch)
        {
            config.UpdateCheckIntervalHours = uch;
            changed = true;
        }

        if (settings.UpdateEnabled is bool ue && config.UpdateEnabled != ue)
        {
            config.UpdateEnabled = ue;
            changed = true;
        }

        if (settings.CollectHardware is bool ch && config.CollectHardware != ch)
        {
            config.CollectHardware = ch;
            changed = true;
        }

        if (settings.CollectUsers is bool cu && config.CollectUsers != cu)
        {
            config.CollectUsers = cu;
            changed = true;
        }

        if (settings.CollectSoftware is bool cs && config.CollectSoftware != cs)
        {
            config.CollectSoftware = cs;
            changed = true;
        }

        return changed;
    }

    private static AgentConfig ApplyEnvironment(AgentConfig cfg)
    {
        var url = Environment.GetEnvironmentVariable("BAD_SERVER_URL")
                  ?? Environment.GetEnvironmentVariable("SERVERURL");
        if (!string.IsNullOrWhiteSpace(url))
        {
            cfg.ServerUrl = url.Trim().TrimEnd('/');
        }

        var enroll = Environment.GetEnvironmentVariable("BAD_ENROLLMENT_TOKEN")
                     ?? Environment.GetEnvironmentVariable("ENROLLMENTTOKEN");
        if (!string.IsNullOrWhiteSpace(enroll) && string.IsNullOrWhiteSpace(cfg.ApiKey))
        {
            cfg.EnrollmentToken = enroll.Trim();
        }

        var apiKey = Environment.GetEnvironmentVariable("BAD_API_KEY");
        if (!string.IsNullOrWhiteSpace(apiKey))
        {
            cfg.ApiKey = apiKey.Trim();
        }

        var updateHours = Environment.GetEnvironmentVariable("BAD_UPDATE_CHECK_INTERVAL_HOURS");
        if (int.TryParse(updateHours, out var hours) && hours > 0)
        {
            cfg.UpdateCheckIntervalHours = hours;
        }

        var updateEnabled = Environment.GetEnvironmentVariable("BAD_UPDATE_ENABLED");
        if (!string.IsNullOrWhiteSpace(updateEnabled))
        {
            cfg.UpdateEnabled = updateEnabled is "1" or "true" or "TRUE" or "yes";
        }

        return cfg;
    }
}
