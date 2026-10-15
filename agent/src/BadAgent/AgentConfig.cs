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

    /// <summary>How often to ask the server for a newer MSI (hours). Default 24.</summary>
    [JsonPropertyName("update_check_interval_hours")]
    public int UpdateCheckIntervalHours { get; set; } = 24;

    [JsonPropertyName("update_enabled")]
    public bool UpdateEnabled { get; set; } = true;
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
