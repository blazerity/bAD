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

    /// <summary>Fallback = <c>agent/VERSION</c> (не server VERSION). В рантайме обычно из assembly.</summary>
    [JsonPropertyName("agent_version")]
    public string AgentVersion { get; set; } = "1.0.2";

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

    /// <summary>TPM / Secure Boot / AV (имена). Soft-fail; без нового collect_*.</summary>
    [JsonPropertyName("security")]
    public SecurityInfo? Security { get; set; }

    /// <summary>Метаданные BSOD minidump (имена/время/число) — без тел файлов.</summary>
    [JsonPropertyName("minidumps")]
    public MinidumpInfo? Minidumps { get; set; }

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

    /// <summary>distinguishedName компьютера в AD, если domain-joined.</summary>
    [JsonPropertyName("ad_distinguished_name")]
    public string? AdDistinguishedName { get; set; }

    /// <summary>Путь OU (без CN=hostname), напр. OU=Laptops,OU=Workstations,DC=contoso,DC=com.</summary>
    [JsonPropertyName("ad_ou")]
    public string? AdOu { get; set; }

    [JsonPropertyName("os")]
    public OsInfo? Os { get; set; }

    /// <summary>UTC ISO из Win32_OperatingSystem.LastBootUpTime.</summary>
    [JsonPropertyName("last_boot_at")]
    public string? LastBootAt { get; set; }

    /// <summary>ID/display часового пояса (best-effort).</summary>
    [JsonPropertyName("timezone")]
    public string? Timezone { get; set; }

    /// <summary>Ожидает перезагрузку (CBS / WindowsUpdate / PendingFileRename).</summary>
    [JsonPropertyName("pending_reboot")]
    public bool? PendingReboot { get; set; }
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

    /// <summary>
    /// SMBIOS system UUID (<c>Win32_ComputerSystemProduct.UUID</c>). Не PK / не device_id.
    /// Null если placeholder (all-F / all-zero).
    /// </summary>
    [JsonPropertyName("smbios_uuid")]
    public string? SmbiosUuid { get; set; }

    /// <summary>Строка продукта / модели (напр. Dell Latitude 5440).</summary>
    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("manufacturer")]
    public string? Manufacturer { get; set; }

    /// <summary>Версия BIOS / SMBIOSBIOSVersion из Win32_BIOS.</summary>
    [JsonPropertyName("bios_version")]
    public string? BiosVersion { get; set; }

    [JsonPropertyName("bios_manufacturer")]
    public string? BiosManufacturer { get; set; }

    [JsonPropertyName("bios_release_date")]
    public string? BiosReleaseDate { get; set; }

    /// <summary>Нормализовано: laptop \| desktop \| server \| vm \| other.</summary>
    [JsonPropertyName("chassis_type")]
    public string? ChassisType { get; set; }

    /// <summary>Сырые коды Win32_SystemEnclosure.ChassisTypes.</summary>
    [JsonPropertyName("chassis_types_raw")]
    public List<int>? ChassisTypesRaw { get; set; }

    [JsonPropertyName("battery")]
    public BatteryInfo? Battery { get; set; }

    [JsonPropertyName("monitors")]
    public List<MonitorInfo>? Monitors { get; set; }

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

public sealed class BatteryInfo
{
    /// <summary>Заряд 0–100, если WMI отдаёт EstimatedChargeRemaining.</summary>
    [JsonPropertyName("charge_percent")]
    public int? ChargePercent { get; set; }

    /// <summary>charging / discharging / full / unknown / …</summary>
    [JsonPropertyName("status")]
    public string? Status { get; set; }

    /// <summary>Сырой BatteryStatus из Win32_Battery.</summary>
    [JsonPropertyName("status_code")]
    public int? StatusCode { get; set; }

    /// <summary>Оценка минут работы (EstimatedRunTime), если cheap/available.</summary>
    [JsonPropertyName("estimated_runtime_minutes")]
    public int? EstimatedRuntimeMinutes { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public sealed class MonitorInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("manufacturer")]
    public string? Manufacturer { get; set; }

    [JsonPropertyName("serial_number")]
    public string? SerialNumber { get; set; }

    [JsonPropertyName("width")]
    public int? Width { get; set; }

    [JsonPropertyName("height")]
    public int? Height { get; set; }

    [JsonPropertyName("year")]
    public int? Year { get; set; }

    [JsonPropertyName("week")]
    public int? Week { get; set; }
}

public sealed class MinidumpInfo
{
    [JsonPropertyName("count")]
    public int Count { get; set; }

    /// <summary>Есть ли %SystemRoot%\Memory.dmp (только факт, без содержимого).</summary>
    [JsonPropertyName("memory_dmp_present")]
    public bool MemoryDmpPresent { get; set; }

    [JsonPropertyName("memory_dmp_path")]
    public string? MemoryDmpPath { get; set; }

    [JsonPropertyName("memory_dmp_modified_at")]
    public string? MemoryDmpModifiedAt { get; set; }

    /// <summary>Метаданные файлов в Minidump\ (cap).</summary>
    [JsonPropertyName("files")]
    public List<MinidumpFileInfo>? Files { get; set; }
}

public sealed class MinidumpFileInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("size_bytes")]
    public long? SizeBytes { get; set; }

    [JsonPropertyName("modified_at")]
    public string? ModifiedAt { get; set; }

    /// <summary>Напр. <c>0x0000009F</c> из заголовка minidump (не тело дампа).</summary>
    [JsonPropertyName("bugcheck_code")]
    public string? BugcheckCode { get; set; }

    /// <summary>До 4 параметров (hex), если есть в заголовке.</summary>
    [JsonPropertyName("bugcheck_parameters")]
    public List<string>? BugcheckParameters { get; set; }

    /// <summary>Короткая причина ≤200 символов.</summary>
    [JsonPropertyName("bugcheck_message")]
    public string? BugcheckMessage { get; set; }
}

public sealed class SecurityInfo
{
    [JsonPropertyName("tpm_present")]
    public bool? TpmPresent { get; set; }

    [JsonPropertyName("tpm_spec_version")]
    public string? TpmSpecVersion { get; set; }

    [JsonPropertyName("secure_boot")]
    public bool? SecureBoot { get; set; }

    [JsonPropertyName("antivirus")]
    public List<AntivirusProductInfo>? Antivirus { get; set; }
}

public sealed class AntivirusProductInfo
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("product_state")]
    public int? ProductState { get; set; }
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

    [JsonPropertyName("serial_number")]
    public string? SerialNumber { get; set; }

    [JsonPropertyName("interface_type")]
    public string? InterfaceType { get; set; }
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
