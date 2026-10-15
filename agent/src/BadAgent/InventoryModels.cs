using System.Text.Json.Serialization;

namespace BadAgent;

public sealed class InventorySnapshot
{
    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; set; } = 2;

    [JsonPropertyName("device_id")]
    public string DeviceId { get; set; } = "";

    [JsonPropertyName("collected_at")]
    public string CollectedAt { get; set; } = "";

    [JsonPropertyName("agent_version")]
    public string AgentVersion { get; set; } = "0.5.0";

    [JsonPropertyName("host")]
    public HostInfo? Host { get; set; }

    [JsonPropertyName("hardware")]
    public HardwareInfo? Hardware { get; set; }

    [JsonPropertyName("network")]
    public NetworkInfo? Network { get; set; }

    [JsonPropertyName("users")]
    public UsersInfo? Users { get; set; }

    [JsonPropertyName("software")]
    public SoftwareInfo? Software { get; set; }

    [JsonPropertyName("collector_errors")]
    public List<CollectorError> CollectorErrors { get; set; } = new();
}

public sealed class CollectorError
{
    [JsonPropertyName("section")]
    public string Section { get; set; } = "";

    [JsonPropertyName("error")]
    public string Error { get; set; } = "";
}

public sealed class HostInfo
{
    [JsonPropertyName("hostname")]
    public string? Hostname { get; set; }

    [JsonPropertyName("domain")]
    public string? Domain { get; set; }

    [JsonPropertyName("os")]
    public OsInfo? Os { get; set; }
}

public sealed class OsInfo
{
    [JsonPropertyName("caption")]
    public string? Caption { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("build")]
    public string? Build { get; set; }

    [JsonPropertyName("arch")]
    public string? Arch { get; set; }

    [JsonPropertyName("install_date")]
    public string? InstallDate { get; set; }
}

public sealed class HardwareInfo
{
    [JsonPropertyName("cpu")]
    public CpuInfo? Cpu { get; set; }

    [JsonPropertyName("ram_bytes")]
    public long? RamBytes { get; set; }

    [JsonPropertyName("disks")]
    public List<DiskInfo>? Disks { get; set; }

    [JsonPropertyName("volumes")]
    public List<VolumeInfo>? Volumes { get; set; }
}

public sealed class CpuInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("cores")]
    public int? Cores { get; set; }

    [JsonPropertyName("logical")]
    public int? Logical { get; set; }
}

public sealed class DiskInfo
{
    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("size_bytes")]
    public long? SizeBytes { get; set; }

    [JsonPropertyName("media_type")]
    public string? MediaType { get; set; }
}

public sealed class VolumeInfo
{
    [JsonPropertyName("letter")]
    public string? Letter { get; set; }

    [JsonPropertyName("size_bytes")]
    public long? SizeBytes { get; set; }

    [JsonPropertyName("free_bytes")]
    public long? FreeBytes { get; set; }
}

public sealed class NetworkInfo
{
    [JsonPropertyName("nics")]
    public List<NicInfo>? Nics { get; set; }
}

public sealed class NicInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("mac")]
    public string? Mac { get; set; }

    [JsonPropertyName("ipv4")]
    public List<string>? Ipv4 { get; set; }

    [JsonPropertyName("ipv6")]
    public List<string>? Ipv6 { get; set; }

    [JsonPropertyName("dhcp")]
    public bool? Dhcp { get; set; }
}

public sealed class UsersInfo
{
    [JsonPropertyName("logged_on")]
    public List<string>? LoggedOn { get; set; }

    [JsonPropertyName("last_interactive")]
    public string? LastInteractive { get; set; }
}

/// <summary>Lightweight installed-programs list (name + version + publisher).</summary>
public sealed class SoftwareInfo
{
    [JsonPropertyName("programs")]
    public List<InstalledProgram>? Programs { get; set; }
}

public sealed class InstalledProgram
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("publisher")]
    public string? Publisher { get; set; }
}

/// <summary>Which inventory sections to collect (from AgentConfig / remote knobs).</summary>
public sealed class CollectorOptions
{
    public bool CollectHardware { get; set; } = true;
    public bool CollectUsers { get; set; } = true;
    public bool CollectSoftware { get; set; } = false;

    public static CollectorOptions FromConfig(AgentConfig config) => new()
    {
        CollectHardware = config.CollectHardware,
        CollectUsers = config.CollectUsers,
        CollectSoftware = config.CollectSoftware,
    };
}

public interface IInventoryCollector
{
    InventorySnapshot Collect(string deviceId, string agentVersion, CollectorOptions? options = null);
}
