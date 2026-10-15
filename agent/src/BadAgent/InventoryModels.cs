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
    public string AgentVersion { get; set; } = "0.8.0";

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

    /// <summary>
    /// Поколение DRAM на уровне системы, если все планки совпадают (напр. DDR4 / DDR5 / LPDDR5).
    /// </summary>
    [JsonPropertyName("ram_memory_type")]
    public string? RamMemoryType { get; set; }

    /// <summary>Серийник системы / корпуса (Dell Service Tag, если есть).</summary>
    [JsonPropertyName("serial_number")]
    public string? SerialNumber { get; set; }

    /// <summary>Строка продукта / модели (напр. Dell Latitude 5440).</summary>
    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("manufacturer")]
    public string? Manufacturer { get; set; }

    [JsonPropertyName("gpus")]
    public List<GpuInfo>? Gpus { get; set; }

    /// <summary>Физические планки ОЗУ из Win32_PhysicalMemory (если доступно).</summary>
    [JsonPropertyName("ram_modules")]
    public List<RamModuleInfo>? RamModules { get; set; }

    [JsonPropertyName("disks")]
    public List<DiskInfo>? Disks { get; set; }

    [JsonPropertyName("volumes")]
    public List<VolumeInfo>? Volumes { get; set; }
}

public sealed class GpuInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("vendor")]
    public string? Vendor { get; set; }

    [JsonPropertyName("driver_version")]
    public string? DriverVersion { get; set; }

    [JsonPropertyName("adapter_ram_bytes")]
    public long? AdapterRamBytes { get; set; }

    [JsonPropertyName("pnp_device_id")]
    public string? PnpDeviceId { get; set; }
}

public sealed class RamModuleInfo
{
    [JsonPropertyName("capacity_bytes")]
    public long? CapacityBytes { get; set; }

    [JsonPropertyName("speed_mhz")]
    public int? SpeedMhz { get; set; }

    [JsonPropertyName("manufacturer")]
    public string? Manufacturer { get; set; }

    [JsonPropertyName("part_number")]
    public string? PartNumber { get; set; }

    [JsonPropertyName("serial_number")]
    public string? SerialNumber { get; set; }

    [JsonPropertyName("form_factor")]
    public string? FormFactor { get; set; }

    [JsonPropertyName("memory_type")]
    public string? MemoryType { get; set; }

    [JsonPropertyName("bank_label")]
    public string? BankLabel { get; set; }

    [JsonPropertyName("device_locator")]
    public string? DeviceLocator { get; set; }

    /// <summary>Best-effort метка канала из locator/bank, если WMI её отдаёт.</summary>
    [JsonPropertyName("channel")]
    public string? Channel { get; set; }
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

/// <summary>Лёгкий список установленных программ (name + version + publisher).</summary>
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

/// <summary>Какие секции inventory собирать (из AgentConfig / remote-настроек).</summary>
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
