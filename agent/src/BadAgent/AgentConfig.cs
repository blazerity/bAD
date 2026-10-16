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

    /// <summary>
    /// Целевая версия агента из remote config (контракт 0.10): <c>latest</c> или semver pin.
    /// Не секрет. Default latest. Алиас JSON: desired_agent_version.
    /// </summary>
    [JsonPropertyName("update_target")]
    public string UpdateTarget { get; set; } = "latest";

    /// <summary>Локально: версия, для которой уже запущен msiexec (anti-loop).</summary>
    [JsonPropertyName("pending_update_version")]
    public string? PendingUpdateVersion { get; set; }

    /// <summary>Локально: UTC ISO старта pending msiexec.</summary>
    [JsonPropertyName("pending_update_started_at")]
    public string? PendingUpdateStartedAt { get; set; }

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

    /// <summary>
    /// Safe knobs, заданные локально вручную (CLI / правка config). Source для панели: <c>agent_local</c>.
    /// Не секреты. См. <see cref="ConfigStore.CliManualSettingKeys"/>.
    /// </summary>
    [JsonPropertyName("agent_local_keys")]
    public List<string> AgentLocalKeys { get; set; } = new();

    /// <summary>
    /// <c>server_url</c> задан локально (CLI). В heartbeat уходит display-only в <c>config_local.server_url</c>,
    /// не remote knob и не элемент <c>keys</c>.
    /// </summary>
    [JsonPropertyName("server_url_local")]
    public bool ServerUrlLocal { get; set; }
}

/// <summary>
/// Inbound heartbeat <c>config_local</c> (контракт API Lead): keys = agent_local safe knobs.
/// </summary>
public sealed class ConfigLocalPayload
{
    [JsonPropertyName("keys")]
    public List<string> Keys { get; set; } = new();

    /// <summary>Опционально: текущие значения ключей из <see cref="Keys"/> (для UI).</summary>
    [JsonPropertyName("settings")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Dictionary<string, object?>? Settings { get; set; }

    /// <summary>Display-only; не safe knob / не remote merge.</summary>
    [JsonPropertyName("server_url")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ServerUrl { get; set; }
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

    /// <summary>Канон контракта 0.10: <c>latest</c> или semver.</summary>
    [JsonPropertyName("update_target")]
    public string? UpdateTarget { get; set; }

    /// <summary>Документированный алиас для <see cref="UpdateTarget"/>.</summary>
    [JsonPropertyName("desired_agent_version")]
    public string? DesiredAgentVersion { get; set; }

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
    /// <summary>Safe knobs, допустимые в <c>config_local.keys</c> / <c>agent_local_keys</c> (как на сервере).</summary>
    public static readonly HashSet<string> AllowedAgentLocalKeys = new(StringComparer.Ordinal)
    {
        "inventory_interval_hours",
        "heartbeat_interval_minutes",
        "update_check_interval_hours",
        "update_enabled",
        "update_target",
        "collect_hardware",
        "collect_users",
        "collect_software",
    };

    /// <summary>
    /// Scope CLI <c>bad … set</c>: <c>server_url</c> (отдельный флаг), <c>collect_*</c>, интервалы.
    /// Секреты (<c>api_key</c> / <c>enrollment_token</c>) — никогда.
    /// </summary>
    public static readonly HashSet<string> CliManualSettingKeys = new(StringComparer.Ordinal)
    {
        "inventory_interval_hours",
        "heartbeat_interval_minutes",
        "update_check_interval_hours",
        "collect_hardware",
        "collect_users",
        "collect_software",
    };

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
        cfg.AgentLocalKeys = NormalizeAgentLocalKeys(cfg.AgentLocalKeys);
        return ApplyEnvironment(cfg);
    }

    public static void Save(AgentConfig config)
    {
        Directory.CreateDirectory(ProgramDataDir);
        config.AgentLocalKeys = NormalizeAgentLocalKeys(config.AgentLocalKeys);
        var tmp = ConfigPath + ".tmp";
        var json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(tmp, json);
        File.Copy(tmp, ConfigPath, overwrite: true);
        File.Delete(tmp);
    }

    /// <summary>
    /// Применяет только safe knobs с сервера. Не трогает server_url, api_key, device_id, enrollment_token.
    /// Ключи из <see cref="AgentConfig.AgentLocalKeys"/> не перезаписываются (локальный ручной приоритет на агенте).
    /// True, если что-то изменилось.
    /// </summary>
    public static bool ApplyRemoteSettings(AgentConfig config, RemoteAgentSettings settings)
    {
        var changed = false;
        if (settings.InventoryIntervalHours is int inv && inv >= 1
            && !IsAgentLocalKey(config, "inventory_interval_hours")
            && config.InventoryIntervalHours != inv)
        {
            config.InventoryIntervalHours = inv;
            changed = true;
        }

        if (settings.HeartbeatIntervalMinutes is int hb && hb >= 1
            && !IsAgentLocalKey(config, "heartbeat_interval_minutes")
            && config.HeartbeatIntervalMinutes != hb)
        {
            config.HeartbeatIntervalMinutes = hb;
            changed = true;
        }

        if (settings.UpdateCheckIntervalHours is int uch && uch >= 1
            && !IsAgentLocalKey(config, "update_check_interval_hours")
            && config.UpdateCheckIntervalHours != uch)
        {
            config.UpdateCheckIntervalHours = uch;
            changed = true;
        }

        if (settings.UpdateEnabled is bool ue
            && !IsAgentLocalKey(config, "update_enabled")
            && config.UpdateEnabled != ue)
        {
            config.UpdateEnabled = ue;
            changed = true;
        }

        var targetRaw = FirstNonEmpty(
            settings.UpdateTarget,
            settings.DesiredAgentVersion);
        if (targetRaw is not null && !IsAgentLocalKey(config, "update_target"))
        {
            var normalized = VersionUtil.NormalizeDesiredAgentVersion(targetRaw);
            if (normalized is not null
                && !string.Equals(config.UpdateTarget, normalized, StringComparison.OrdinalIgnoreCase))
            {
                config.UpdateTarget = normalized;
                changed = true;
            }
        }

        if (settings.CollectHardware is bool ch
            && !IsAgentLocalKey(config, "collect_hardware")
            && config.CollectHardware != ch)
        {
            config.CollectHardware = ch;
            changed = true;
        }

        if (settings.CollectUsers is bool cu
            && !IsAgentLocalKey(config, "collect_users")
            && config.CollectUsers != cu)
        {
            config.CollectUsers = cu;
            changed = true;
        }

        if (settings.CollectSoftware is bool cs
            && !IsAgentLocalKey(config, "collect_software")
            && config.CollectSoftware != cs)
        {
            config.CollectSoftware = cs;
            changed = true;
        }

        return changed;
    }

    public static bool IsAgentLocalKey(AgentConfig config, string key)
    {
        if (config.AgentLocalKeys is null || config.AgentLocalKeys.Count == 0)
        {
            return false;
        }

        foreach (var k in config.AgentLocalKeys)
        {
            if (string.Equals(k, key, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>
    /// Пометить safe knob как заданный вручную (source <c>agent_local</c>).
    /// False, если ключ не из <see cref="AllowedAgentLocalKeys"/> (секреты / неизвестное).
    /// </summary>
    public static bool MarkAgentLocalKey(AgentConfig config, string key)
    {
        if (string.IsNullOrWhiteSpace(key) || !AllowedAgentLocalKeys.Contains(key))
        {
            return false;
        }

        config.AgentLocalKeys ??= new List<string>();
        if (!IsAgentLocalKey(config, key))
        {
            config.AgentLocalKeys.Add(key);
        }

        return true;
    }

    /// <summary>Снять маркер с одного ключа или со всех (<paramref name="key"/> = null).</summary>
    public static void ClearAgentLocalKey(AgentConfig config, string? key = null)
    {
        if (config.AgentLocalKeys is null)
        {
            config.AgentLocalKeys = new List<string>();
            return;
        }

        if (key is null)
        {
            config.AgentLocalKeys.Clear();
            return;
        }

        config.AgentLocalKeys.RemoveAll(k => string.Equals(k, key, StringComparison.Ordinal));
    }

    public static void MarkServerUrlLocal(AgentConfig config, bool isLocal) =>
        config.ServerUrlLocal = isLocal;

    /// <summary>
    /// Payload <c>config_local</c> для heartbeat: всегда (в т.ч. <c>keys: []</c> — сброс на сервере).
    /// </summary>
    public static ConfigLocalPayload BuildConfigLocalForHeartbeat(AgentConfig config)
    {
        var keys = NormalizeAgentLocalKeys(config.AgentLocalKeys);
        var payload = new ConfigLocalPayload { Keys = keys };
        if (keys.Count > 0)
        {
            var settings = new Dictionary<string, object?>(StringComparer.Ordinal);
            foreach (var key in keys)
            {
                var value = TryGetSafeKnobValue(config, key);
                if (value is not null)
                {
                    settings[key] = value;
                }
            }

            if (settings.Count > 0)
            {
                payload.Settings = settings;
            }
        }

        if (config.ServerUrlLocal && !string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            payload.ServerUrl = config.ServerUrl.Trim().TrimEnd('/');
        }

        return payload;
    }

    public static List<string> NormalizeAgentLocalKeys(IEnumerable<string>? keys)
    {
        var result = new List<string>();
        if (keys is null)
        {
            return result;
        }

        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var raw in keys)
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                continue;
            }

            var key = raw.Trim();
            if (!AllowedAgentLocalKeys.Contains(key) || !seen.Add(key))
            {
                continue;
            }

            result.Add(key);
        }

        result.Sort(StringComparer.Ordinal);
        return result;
    }

    public static object? TryGetSafeKnobValue(AgentConfig config, string key) =>
        key switch
        {
            "inventory_interval_hours" => config.InventoryIntervalHours,
            "heartbeat_interval_minutes" => config.HeartbeatIntervalMinutes,
            "update_check_interval_hours" => config.UpdateCheckIntervalHours,
            "update_enabled" => config.UpdateEnabled,
            "update_target" => config.UpdateTarget,
            "collect_hardware" => config.CollectHardware,
            "collect_users" => config.CollectUsers,
            "collect_software" => config.CollectSoftware,
            _ => null
        };

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

        var target = Environment.GetEnvironmentVariable("BAD_UPDATE_TARGET")
                     ?? Environment.GetEnvironmentVariable("BAD_DESIRED_AGENT_VERSION");
        if (!string.IsNullOrWhiteSpace(target))
        {
            var normalized = VersionUtil.NormalizeDesiredAgentVersion(target);
            if (normalized is not null)
            {
                cfg.UpdateTarget = normalized;
            }
        }

        return cfg;
    }

    private static string? FirstNonEmpty(params string?[] values)
    {
        foreach (var v in values)
        {
            if (!string.IsNullOrWhiteSpace(v))
            {
                return v.Trim();
            }
        }

        return null;
    }
}
